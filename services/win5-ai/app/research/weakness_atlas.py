# -*- coding: utf-8 -*-
"""
Version15 Weakness Atlas

Quantify where SingleAI loses across Prediction Corpus segments.
Research-only. Does NOT mutate Prediction / PE / CE / AI / Challenge /
Resolver / ResultAutomation. Does NOT implement fixes.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .analyzer import extract_runners, soft_hit, strict_hit, tie_group, unique_top_pick
from .config import evidence_root, repo_root
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-weakness-atlas/1.0"

MIN_N_STABLE = 5


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _distance_bucket(distance: Any) -> str:
    try:
        d = int(distance or 0)
    except (TypeError, ValueError):
        return "unknown"
    if d <= 0:
        return "unknown"
    if d <= 1400:
        return "sprint"
    if d <= 1800:
        return "mile"
    if d <= 2200:
        return "middle"
    return "long"


def _surface_key(surface: Any) -> str:
    s = str(surface or "").strip().lower()
    if not s or s in {"none", "null"}:
        return "unknown"
    if "芝" in s or s == "turf":
        return "turf"
    if "ダ" in s or "dirt" in s:
        return "dirt"
    return "unknown"


def _field_bucket(n: int | None) -> str:
    if not n or n <= 0:
        return "unknown"
    if n <= 10:
        return "field_<=10"
    if n <= 14:
        return "field_11-14"
    if n <= 16:
        return "field_15-16"
    return "field_17+"


def _pop_band(pop: Any) -> str:
    try:
        p = int(float(pop))
    except (TypeError, ValueError):
        return "unknown"
    if p <= 0:
        return "unknown"
    if p == 1:
        return "pop_1"
    if p <= 3:
        return "pop_2-3"
    if p <= 6:
        return "pop_4-6"
    return "pop_7+"


def _odds_band(odds: Any) -> str:
    try:
        o = float(odds)
    except (TypeError, ValueError):
        return "unknown"
    if o <= 0:
        return "unknown"
    if o < 4:
        return "odds_short"
    if o < 10:
        return "odds_mid"
    if o < 20:
        return "odds_long"
    return "odds_heavy"


def _class_family(class_label: str | None, age_group: str | None) -> str:
    text = str(class_label or "")
    age = str(age_group or "")
    if age == "2yo_newcomer" or "新馬" in text:
        return "newcomer"
    if age in {"2yo_maiden", "3yo_maiden"} or "未勝利" in text:
        return "maiden"
    if any(x in text for x in ("G1", "G2", "G3", "重賞")) or (
        text.endswith("S") and "クラス" not in text
    ):
        return "stakes"
    if age in {"2yo_other", "3yo_other"} or "2歳" in text or "3歳" in text:
        return "young_other"
    if age == "older" or any(
        x in text for x in ("1勝", "2勝", "3勝", "オープン", "以上")
    ):
        return "open_or_older"
    return "unknown"


def _race_type(is_young: int, class_family: str) -> str:
    if is_young:
        return "young_horse"
    if class_family == "stakes":
        return "stakes"
    if class_family == "unknown":
        return "unknown"
    return "normal"


def _going_key(going: Any) -> str:
    g = str(going or "").strip()
    if not g or g in {"?", "None", "null"}:
        return "unknown"
    return g


def _weather_key(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return "unknown"
    for k in ("weather", "天候", "tenko"):
        v = payload.get(k)
        if v:
            return str(v)
    return "unknown"


def weakness_index(
    *,
    strict_rate: float | None,
    soft_rate: float | None,
    roi: float | None,
    tie_rate: float | None,
    reliability: float | None,
    resolver_lose_rate: float | None,
    evidence_coverage: float | None,
) -> float:
    """
    0..100 — higher = weaker / more painful segment.
    Research metric only (not a product score).
    """
    miss_strict = 1.0 - (strict_rate if strict_rate is not None else 0.0)
    miss_soft = 1.0 - (soft_rate if soft_rate is not None else 0.0)
    # ROI: -100% => 1.0 weakness, 0% => 0.5, +100%+ => 0
    if roi is None:
        roi_w = 0.5
    else:
        roi_w = _clamp01(0.5 - 0.5 * max(min(roi, 1.0), -1.0))
    tie_w = tie_rate if tie_rate is not None else 0.0
    rel = (reliability if reliability is not None else 50.0) / 100.0
    rel_w = 1.0 - _clamp01(rel)
    rlose = resolver_lose_rate if resolver_lose_rate is not None else 0.0
    evi_w = 1.0 - (evidence_coverage if evidence_coverage is not None else 0.0)
    score = 100.0 * (
        0.28 * miss_strict
        + 0.12 * miss_soft
        + 0.18 * roi_w
        + 0.12 * _clamp01(tie_w)
        + 0.12 * rel_w
        + 0.10 * _clamp01(rlose)
        + 0.08 * _clamp01(evi_w)
    )
    return round(_clamp01(score / 100.0) * 100.0, 1)


class WeaknessAtlas:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()

    def _load_reliability_map(self) -> dict[str, float]:
        path = self.evidence / "reports" / "v14-evidence-reliability.json"
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        out = {}
        for f in payload.get("features") or []:
            fid = str(f.get("feature_id") or "")
            if fid:
                out[fid] = float(f.get("reliability_score") or 50.0)
        return out

    def _load_shadow_index(self) -> dict[str, dict[str, Any]]:
        path = self.evidence / "reports" / "v105-shadow-resolver.json"
        out: dict[str, dict[str, Any]] = {}
        if not path.exists():
            return out
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return out
        for row in payload.get("resolver_records") or []:
            rid = str(row.get("race_id") or "")
            if rid:
                out[rid] = row
        return out

    def _bundle_for_row(self, conn, row: dict[str, Any]) -> dict[str, Any]:
        # prefer live prediction bundle
        if row.get("prediction_id") is not None:
            r = conn.execute(
                "SELECT bundle_json FROM predictions WHERE id=?",
                (int(row["prediction_id"]),),
            ).fetchone()
            if r:
                try:
                    return json.loads(r["bundle_json"] or "{}")
                except Exception:
                    pass
        # historical research bundles
        r = conn.execute(
            """
            SELECT bundle_json FROM research_historical_bundles
            WHERE race_id=? AND has_bundle=1
            ORDER BY updated_at DESC LIMIT 1
            """,
            (str(row["race_id"]),),
        ).fetchone()
        if r:
            try:
                return json.loads(r["bundle_json"] or "{}")
            except Exception:
                pass
        return {}

    def _research_meta(self, conn, race_id: str) -> dict[str, Any]:
        """V16 research_race_meta overlay (read-only for atlas)."""
        try:
            row = conn.execute(
                """
                SELECT surface, distance, going, weather, field_size, venue,
                       class_label, race_class, age_group, course_type
                FROM research_race_meta WHERE race_id=?
                """,
                (race_id,),
            ).fetchone()
        except Exception:
            return {}
        return dict(row) if row else {}

    def _result_meta(self, conn, race_id: str) -> dict[str, Any]:
        rr = conn.execute(
            """
            SELECT surface, distance, going, field_size, result_json, venue
            FROM race_results WHERE race_id=?
            """,
            (race_id,),
        ).fetchone()
        race = conn.execute(
            """
            SELECT surface, distance, class_label, venue
            FROM races WHERE race_id=?
            """,
            (race_id,),
        ).fetchone()
        rmeta = self._research_meta(conn, race_id)
        meta = {
            "surface": None,
            "distance": None,
            "going": None,
            "field_size": None,
            "venue": None,
            "class_label": None,
            "age_group": None,
            "race_class": None,
            "course_type": None,
            "weather": "unknown",
            "win_payout": {},
        }
        payload = {}
        if rr:
            meta["surface"] = rr["surface"]
            meta["distance"] = rr["distance"]
            meta["going"] = rr["going"]
            meta["field_size"] = rr["field_size"]
            meta["venue"] = rr["venue"]
            try:
                payload = json.loads(rr["result_json"] or "{}")
            except Exception:
                payload = {}
            pays = (payload.get("payouts") or {}).get("単勝") or {}
            if isinstance(pays, dict):
                for k, v in pays.items():
                    try:
                        meta["win_payout"][int(k)] = float(v)
                    except (TypeError, ValueError):
                        continue
            meta["weather"] = _weather_key(payload)
        if race:
            meta["surface"] = meta["surface"] or race["surface"]
            meta["distance"] = meta["distance"] or race["distance"]
            meta["class_label"] = race["class_label"]
            meta["venue"] = meta["venue"] or race["venue"]
        # Prefer V16 research completion for unknown holes
        if rmeta:
            meta["surface"] = meta["surface"] or rmeta.get("surface")
            meta["distance"] = meta["distance"] or rmeta.get("distance")
            meta["going"] = meta["going"] or rmeta.get("going")
            meta["field_size"] = meta["field_size"] or rmeta.get("field_size")
            meta["venue"] = meta["venue"] or rmeta.get("venue")
            meta["class_label"] = meta["class_label"] or rmeta.get("class_label") or rmeta.get(
                "race_class"
            )
            meta["age_group"] = rmeta.get("age_group")
            meta["race_class"] = rmeta.get("race_class") or rmeta.get("class_label")
            meta["course_type"] = rmeta.get("course_type")
            if meta.get("weather") in (None, "", "unknown") and rmeta.get("weather"):
                meta["weather"] = rmeta.get("weather")
        return meta

    def _build_race_records(self) -> list[dict[str, Any]]:
        conn = connect()
        shadow_idx = self._load_shadow_index()
        try:
            rows = conn.execute(
                """
                SELECT * FROM research_prediction_corpus
                WHERE race_id NOT LIKE '2099%'
                ORDER BY race_date ASC, race_id ASC
                """
            ).fetchall()
            out: list[dict[str, Any]] = []
            for raw in rows:
                row = dict(raw)
                race_id = str(row["race_id"])
                bundle = self._bundle_for_row(conn, row)
                runners = extract_runners(bundle)
                winner = row.get("winner_horse_number")
                winner_i = int(winner) if winner is not None else None
                has_eval = bool(runners) and winner_i is not None
                g = tie_group(runners) if runners else []
                pick = unique_top_pick(runners) if runners else row.get("prediction_pick")
                try:
                    pick_i = int(pick) if pick is not None else None
                except (TypeError, ValueError):
                    pick_i = None

                s_hit = strict_hit(runners, winner_i) if has_eval else None
                so_hit = soft_hit(runners, winner_i) if has_eval else None

                rmeta = self._result_meta(conn, race_id)
                class_label = (
                    row.get("class_label")
                    or rmeta.get("class_label")
                    or rmeta.get("race_class")
                )
                age_group = row.get("age_group") or rmeta.get("age_group") or "unknown"
                if age_group == "unknown" and rmeta.get("age_group"):
                    age_group = rmeta.get("age_group") or "unknown"
                class_family = _class_family(class_label, age_group)
                surface = _surface_key(row.get("surface") or rmeta.get("surface"))
                distance = row.get("distance") or rmeta.get("distance")
                field_size = rmeta.get("field_size") or (len(runners) if runners else None)
                venue = row.get("venue") or rmeta.get("venue") or "unknown"
                going = _going_key(rmeta.get("going"))
                weather = rmeta.get("weather") or "unknown"
                race_class = rmeta.get("race_class") or class_label or "unknown"
                course_type = rmeta.get("course_type") or (
                    surface if surface != "unknown" else "unknown"
                )

                # popularity / odds of prediction pick
                pop = None
                odds = None
                if pick_i is not None and runners:
                    for r in runners:
                        if int(r.get("horse_number") or 0) == pick_i:
                            pop = r.get("popularity")
                            odds = r.get("odds") or r.get("win_odds")
                            break
                # snapshot features override if present
                if row.get("has_evidence_snapshot") and pick_i is not None:
                    snap = conn.execute(
                        """
                        SELECT feature_id, value_json FROM research_snapshot_features
                        WHERE race_id=? AND horse_number=?
                          AND feature_id IN ('popularity','win_odds')
                        """,
                        (race_id, pick_i),
                    ).fetchall()
                    for s in snap:
                        try:
                            val = json.loads(s["value_json"])
                        except Exception:
                            val = s["value_json"]
                        if s["feature_id"] == "popularity" and val is not None:
                            pop = val
                        if s["feature_id"] == "win_odds" and val is not None:
                            odds = val

                # ROI: 100yen on strict pick
                stake = 0
                ret = 0.0
                if has_eval and pick_i is not None:
                    stake = 100
                    if s_hit:
                        pay = rmeta["win_payout"].get(pick_i)
                        if pay is None and odds is not None:
                            try:
                                pay = float(odds) * 100.0
                            except (TypeError, ValueError):
                                pay = 0.0
                        ret = float(pay or 0.0)

                shadow = shadow_idx.get(race_id) or {}
                shadow_outcome = row.get("shadow_outcome") or shadow.get("outcome")
                # normalize
                if shadow_outcome not in {"win", "lose", "draw"}:
                    shadow_outcome = None

                out.append(
                    {
                        "race_id": race_id,
                        "source": row.get("source"),
                        "age_group": age_group or "unknown",
                        "class_family": class_family,
                        "race_class": str(race_class or "unknown"),
                        "course_type": str(course_type or "unknown"),
                        "race_type": _race_type(int(row.get("is_young_horse") or 0), class_family),
                        "is_young_horse": int(row.get("is_young_horse") or 0),
                        "surface": surface,
                        "distance_bucket": _distance_bucket(distance),
                        "field_bucket": _field_bucket(
                            int(field_size) if field_size is not None else None
                        ),
                        "venue": str(venue or "unknown"),
                        "going": going,
                        "weather": weather,
                        "pop_band": _pop_band(pop),
                        "odds_band": _odds_band(odds),
                        "is_tie": int(len(g) >= 2) if runners else int(row.get("is_tie") or 0),
                        "has_eval": int(has_eval),
                        "strict": int(bool(s_hit)) if s_hit is not None else None,
                        "soft": int(bool(so_hit)) if so_hit is not None else None,
                        "stake": stake,
                        "returns": ret,
                        "has_evidence": int(row.get("has_evidence_snapshot") or 0),
                        "completeness": float(row.get("completeness") or 0.0),
                        "shadow_outcome": shadow_outcome,
                        "class_label": class_label,
                    }
                )
            return out
        finally:
            conn.close()

    def _aggregate(
        self,
        records: list[dict[str, Any]],
        *,
        axis: str,
        reliability_map: dict[str, float],
    ) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in records:
            key = str(r.get(axis) or "unknown")
            groups[key].append(r)

        global_rel = (
            statistics_mean(list(reliability_map.values()))
            if reliability_map
            else 50.0
        )

        rows = []
        for key, items in groups.items():
            n = len(items)
            eval_items = [x for x in items if x.get("has_eval")]
            n_eval = len(eval_items)
            strict_n = sum(x["strict"] for x in eval_items if x.get("strict") is not None)
            soft_n = sum(x["soft"] for x in eval_items if x.get("soft") is not None)
            stakes = sum(x["stake"] for x in eval_items)
            returns = sum(x["returns"] for x in eval_items)
            tie_n = sum(x["is_tie"] for x in items)
            evi_n = sum(x["has_evidence"] for x in items)
            shadow_items = [x for x in items if x.get("shadow_outcome")]
            rwin = sum(1 for x in shadow_items if x["shadow_outcome"] == "win")
            rlose = sum(1 for x in shadow_items if x["shadow_outcome"] == "lose")
            rdraw = sum(1 for x in shadow_items if x["shadow_outcome"] == "draw")

            strict_rate = _safe_div(strict_n, n_eval)
            soft_rate = _safe_div(soft_n, n_eval)
            roi = _safe_div(returns - stakes, stakes) if stakes else None
            tie_rate = _safe_div(tie_n, n)
            evi_cov = _safe_div(evi_n, n)
            # segment reliability: blend global reliability with evidence coverage
            reliability = round(
                global_rel * 0.7 + 100.0 * (evi_cov or 0.0) * 0.3,
                1,
            )
            rlose_rate = _safe_div(rlose, len(shadow_items)) if shadow_items else None

            wi = weakness_index(
                strict_rate=strict_rate,
                soft_rate=soft_rate,
                roi=roi,
                tie_rate=tie_rate,
                reliability=reliability,
                resolver_lose_rate=rlose_rate if rlose_rate is not None else 0.0,
                evidence_coverage=evi_cov,
            )
            # improvement ROI research estimate: recover to global median strict
            # filled later
            rows.append(
                {
                    "axis": axis,
                    "segment": key,
                    "n": n,
                    "n_eval": n_eval,
                    "strict_hits": strict_n,
                    "soft_hits": soft_n,
                    "strict_rate": strict_rate,
                    "soft_rate": soft_rate,
                    "roi": roi,
                    "tie_rate": tie_rate,
                    "reliability": reliability,
                    "resolver_win": rwin,
                    "resolver_lose": rlose,
                    "resolver_draw": rdraw,
                    "resolver_lose_rate": rlose_rate,
                    "evidence_coverage": evi_cov,
                    "weakness_index": wi,
                    "stable": n_eval >= MIN_N_STABLE,
                }
            )

        # priority = weakness * log1p(n_eval)
        for r in rows:
            n_eval = r["n_eval"]
            r["priority_score"] = round(
                float(r["weakness_index"]) * math.log1p(n_eval), 2
            )
        rows.sort(key=lambda x: (-x["priority_score"], -x["weakness_index"], -x["n"]))
        for i, r in enumerate(rows, start=1):
            r["rank"] = i
        return rows

    def analyze(self) -> dict[str, Any]:
        records = self._build_race_records()
        rel_map = self._load_reliability_map()

        axes = [
            "race_type",
            "age_group",
            "class_family",
            "race_class",
            "course_type",
            "surface",
            "distance_bucket",
            "field_bucket",
            "venue",
            "going",
            "weather",
            "pop_band",
            "odds_band",
        ]
        by_axis: dict[str, list[dict[str, Any]]] = {}
        for axis in axes:
            by_axis[axis] = self._aggregate(records, axis=axis, reliability_map=rel_map)

        # global baseline
        all_eval = [r for r in records if r.get("has_eval")]
        g_strict = _safe_div(
            sum(r["strict"] for r in all_eval if r.get("strict") is not None),
            len(all_eval),
        )
        g_soft = _safe_div(
            sum(r["soft"] for r in all_eval if r.get("soft") is not None),
            len(all_eval),
        )
        g_stakes = sum(r["stake"] for r in all_eval)
        g_returns = sum(r["returns"] for r in all_eval)
        g_roi = _safe_div(g_returns - g_stakes, g_stakes) if g_stakes else None

        # improvement ROI research estimate vs global strict
        atlas_flat = []
        for axis, rows in by_axis.items():
            for r in rows:
                gap = max((g_strict or 0.0) - (r.get("strict_rate") or 0.0), 0.0)
                # expected extra hits if raised to global strict
                expected_extra_hits = gap * r["n_eval"]
                # crude yen uplift assuming avg winning payout ~ mean positive return unit
                avg_win_pay = 0.0
                # use 200 as neutral placeholder if unknown
                avg_win_pay = 250.0
                improvement_roi_est = round(expected_extra_hits * avg_win_pay, 1)
                r["strict_gap_vs_global"] = round(gap, 4)
                r["improvement_roi_est_yen"] = improvement_roi_est
                r["improvement_extra_hits_est"] = round(expected_extra_hits, 2)
                atlas_flat.append(r)

        # priority map: top stable segments across axes
        priority = [
            r
            for r in atlas_flat
            if r.get("stable") and r.get("segment") not in {"unknown"}
        ]
        priority.sort(key=lambda x: (-x["priority_score"], -x["weakness_index"]))
        for i, r in enumerate(priority, start=1):
            r["priority_rank"] = i

        # also include unknown-heavy axes as data-quality weaknesses
        data_gaps = [
            r
            for r in atlas_flat
            if r.get("segment") == "unknown" and r.get("n", 0) >= 20
        ]
        data_gaps.sort(key=lambda x: -x["n"])

        report = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "shadow_only": True,
            "prediction_mutation": "FORBIDDEN",
            "implementation_forbidden": True,
            "sample": {
                "prediction_corpus": len(records),
                "evaluable": len(all_eval),
                "young_horse": sum(1 for r in records if r.get("is_young_horse")),
                "tie": sum(1 for r in records if r.get("is_tie")),
                "with_evidence": sum(1 for r in records if r.get("has_evidence")),
                "with_shadow": sum(1 for r in records if r.get("shadow_outcome")),
                "global_strict_rate": g_strict,
                "global_soft_rate": g_soft,
                "global_roi": g_roi,
                "exploratory": len(all_eval) < 500,
            },
            "by_axis": by_axis,
            "priority_map": priority[:40],
            "data_gaps": data_gaps[:20],
            "roadmap": self._roadmap(priority[:15], data_gaps[:8], g_strict),
        }
        return report

    def _roadmap(
        self,
        priority: list[dict[str, Any]],
        data_gaps: list[dict[str, Any]],
        g_strict: float | None,
    ) -> list[dict[str, Any]]:
        steps = []
        # research roadmap only — no implementation
        for i, p in enumerate(priority[:8], start=1):
            steps.append(
                {
                    "order": i,
                    "type": "segment_weakness",
                    "axis": p.get("axis"),
                    "segment": p.get("segment"),
                    "weakness_index": p.get("weakness_index"),
                    "priority_score": p.get("priority_score"),
                    "n_eval": p.get("n_eval"),
                    "strict_rate": p.get("strict_rate"),
                    "improvement_roi_est_yen": p.get("improvement_roi_est_yen"),
                    "action_research": (
                        f"Investigate {p.get('axis')}={p.get('segment')} losses; "
                        "collect more Evidence; do NOT change Prediction yet."
                    ),
                }
            )
        base = len(steps)
        for j, g in enumerate(data_gaps[:5], start=1):
            steps.append(
                {
                    "order": base + j,
                    "type": "data_quality",
                    "axis": g.get("axis"),
                    "segment": "unknown",
                    "n": g.get("n"),
                    "action_research": (
                        f"Reduce unknown on axis `{g.get('axis')}` via metadata backfill "
                        "(Research ingest only)."
                    ),
                }
            )
        steps.append(
            {
                "order": len(steps) + 1,
                "type": "guardrail",
                "action_research": (
                    f"Keep global Strict={_pct(g_strict)} as baseline. "
                    "No Prediction/Resolver/PE/CE/AI changes in V15."
                ),
            }
        )
        return steps


def statistics_mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 50.0


def write_atlas_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = report.get("sample") or {}
    lines = [
        "# Version15 Research - Weakness Atlas",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** Research only / Quantification only / Implementation FORBIDDEN  ",
        "",
        "## Global",
        "",
        f"- Prediction Corpus: `{s.get('prediction_corpus')}` (evaluable `{s.get('evaluable')}`)",
        f"- Young Horse: `{s.get('young_horse')}` / Tie: `{s.get('tie')}`",
        f"- Evidence: `{s.get('with_evidence')}` / Shadow: `{s.get('with_shadow')}`",
        f"- Global Strict: `{_pct(s.get('global_strict_rate'))}`",
        f"- Global Soft: `{_pct(s.get('global_soft_rate'))}`",
        f"- Global ROI: `{_pct(s.get('global_roi')) if s.get('global_roi') is not None else 'N/A'}`",
        f"- Exploratory: `{s.get('exploratory')}`",
        "",
        "## Weakness Index",
        "",
        "0-100 (higher = weaker). Combines Strict miss, Soft miss, ROI pain,",
        "Tie rate, Reliability, Resolver lose, Evidence coverage.",
        "",
    ]
    for axis, rows in (report.get("by_axis") or {}).items():
        lines.extend(
            [
                f"### Axis: `{axis}`",
                "",
                "| Seg | N | Eval | Strict | Soft | ROI | Tie | Rel | R-Win | R-Lose | Evi | WI |",
                "|-----|--:|-----:|-------:|-----:|----:|----:|----:|------:|-------:|----:|---:|",
            ]
        )
        for r in rows[:12]:
            lines.append(
                f"| `{r.get('segment')}` | {r.get('n')} | {r.get('n_eval')} | "
                f"{_pct(r.get('strict_rate'))} | {_pct(r.get('soft_rate'))} | "
                f"{_pct(r.get('roi')) if r.get('roi') is not None else 'N/A'} | "
                f"{_pct(r.get('tie_rate'))} | {r.get('reliability')} | "
                f"{r.get('resolver_win')} | {r.get('resolver_lose')} | "
                f"{_pct(r.get('evidence_coverage'))} | {r.get('weakness_index')} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Decision",
            "",
            "```",
            "Action Type: Weakness Atlas (Research Quantification)",
            "Prediction Mutation: FORBIDDEN",
            "Resolver Mutation: FORBIDDEN",
            "Implementation: FORBIDDEN in V15",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_priority_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version15 Research - Weakness Priority Map",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "PriorityScore = WeaknessIndex * log(1 + N_eval). Unknown segments excluded.",
        "",
        "| Rank | Axis | Segment | N_eval | WI | Priority | Strict | Soft | ROI | ExtraHitsEst | ImpROI_yen |",
        "|-----:|------|---------|-------:|---:|---------:|-------:|-----:|----:|-------------:|-----------:|",
    ]
    for r in report.get("priority_map") or []:
        lines.append(
            f"| {r.get('priority_rank')} | `{r.get('axis')}` | `{r.get('segment')}` | "
            f"{r.get('n_eval')} | {r.get('weakness_index')} | {r.get('priority_score')} | "
            f"{_pct(r.get('strict_rate'))} | {_pct(r.get('soft_rate'))} | "
            f"{_pct(r.get('roi')) if r.get('roi') is not None else 'N/A'} | "
            f"{r.get('improvement_extra_hits_est')} | {r.get('improvement_roi_est_yen')} |"
        )
    lines.extend(
        [
            "",
            "## Data gaps (unknown mass)",
            "",
            "| Axis | Unknown N | WI | Note |",
            "|------|----------:|---:|------|",
        ]
    )
    for g in report.get("data_gaps") or []:
        lines.append(
            f"| `{g.get('axis')}` | {g.get('n')} | {g.get('weakness_index')} | metadata missing |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_roadmap_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version15 Research - Improvement Roadmap",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**IMPORTANT:** Research roadmap only. No Prediction/Resolver/PE/CE/AI implementation.",
        "",
        "| Order | Type | Focus | WI/N | Research Action | Est. Imp ROI (yen) |",
        "|------:|------|-------|-----:|-----------------|-------------------:|",
    ]
    for step in report.get("roadmap") or []:
        focus = (
            f"{step.get('axis')}={step.get('segment')}"
            if step.get("axis")
            else step.get("type")
        )
        wi = step.get("weakness_index")
        n = step.get("n_eval") or step.get("n")
        lines.append(
            f"| {step.get('order')} | `{step.get('type')}` | `{focus}` | "
            f"{wi if wi is not None else n} | {step.get('action_research')} | "
            f"{step.get('improvement_roi_est_yen', 'N/A')} |"
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Do not change Prediction ranks / PE / CE / AI / Challenge / Resolver / ResultAutomation.",
            "- Improvement ROI estimates are research heuristics (extra hits * illustrative payout).",
            "- Next allowed work: Evidence backfill / metadata enrichment / deeper diagnosis only.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    report = WeaknessAtlas().analyze()
    root = repo_root()
    docs = root / "docs" / "research"
    write_atlas_md(report, docs / "v15-weakness-atlas.md")
    write_priority_md(report, docs / "v15-priority-map.md")
    write_roadmap_md(report, docs / "v15-improvement-roadmap.md")
    json_path = evidence_root() / "reports" / "v15-weakness-atlas.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    # drop bulky by_axis duplication already in report
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "atlas": str(docs / "v15-weakness-atlas.md"),
        "priority": str(docs / "v15-priority-map.md"),
        "roadmap": str(docs / "v15-improvement-roadmap.md"),
        "json": str(json_path),
    }
    return report
