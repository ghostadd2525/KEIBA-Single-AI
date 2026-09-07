# -*- coding: utf-8 -*-
"""
Version17 Evidence Discovery Research

Horse-racing evidence research (not AI mutation).
Uses Research Platform (V10–V16) to discover win/lose conditions and
feature combinations.

FORBIDDEN to mutate:
  Prediction Logic / PE / CE / AI Score / Challenge /
  ResultAutomation / Resolver / Shadow Resolver / Production
"""
from __future__ import annotations

import itertools
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .analyzer import (
    EvidenceAnalyzer,
    _ig_bits,
    extract_runners,
    soft_hit,
    strict_hit,
    tie_group,
    unique_top_pick,
)
from .config import evidence_root, repo_root
from .ranking_engine import CATEGORICAL_FEATURES, cascade_resolve, feature_score, resolve_by_score
from .weakness_atlas import _distance_bucket, _field_bucket, _surface_key
from .young_horse_archetypes import discretize_horse
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-evidence-discovery/1.0"

CONFIDENT_MIN_N = 20
CONFIDENT_Z = 1.96  # ~95%

HORSE_FEATURES: tuple[str, ...] = (
    "popularity",
    "win_odds",
    "trainer",
    "owner",
    "breeder",
    "sire",
    "damsire",
    "oikiri_time",
    "oikiri_rating",
)

RACE_AXES: tuple[str, ...] = (
    "field_bucket",
    "surface",
    "distance_bucket",
    "going",
    "weather",
    "venue",
)

FEATURE_LABELS = {
    "popularity": "Popularity",
    "win_odds": "Win Odds",
    "trainer": "Trainer",
    "owner": "Owner",
    "breeder": "Breeder",
    "sire": "Sire",
    "damsire": "Damsire",
    "oikiri_time": "WorkoutTime",
    "oikiri_rating": "WorkoutRating",
    "field_bucket": "Field Size",
    "surface": "Surface",
    "distance_bucket": "Distance",
    "going": "Going",
    "weather": "Weather",
    "venue": "Venue",
}

# Target research categories
CATEGORY_ORDER = (
    "2yo_newcomer",
    "2yo_maiden",
    "3yo_maiden",
    "class_1win",
    "class_2win",
    "class_3win",
    "open",
    "stakes",
    "other",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def wilson_ci(successes: int, n: int, z: float = CONFIDENT_Z) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        return (0.0, 1.0)
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p + z2 / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n)
    lo = max(0.0, (centre - margin) / denom)
    hi = min(1.0, (centre + margin) / denom)
    return (lo, hi)


def classify_gate(
    *,
    n: int,
    successes: int,
    baseline: float,
) -> dict[str, Any]:
    """
    Confident if N>=20 and 95% Wilson CI lower bound > baseline.
    Otherwise exploratory (still reported, separated).
    """
    rate = _safe_div(successes, n) or 0.0
    lo, hi = wilson_ci(successes, n)
    confident = bool(n >= CONFIDENT_MIN_N and lo > baseline)
    return {
        "n": n,
        "successes": successes,
        "rate": rate,
        "ci95_low": round(lo, 4),
        "ci95_high": round(hi, 4),
        "baseline": baseline,
        "confident": confident,
        "exploratory": not confident,
        "gate_reason": (
            "pass"
            if confident
            else (
                f"n<{CONFIDENT_MIN_N}"
                if n < CONFIDENT_MIN_N
                else "ci95_low_not_above_baseline"
            )
        ),
    }


def _is_named_stakes(label: str | None) -> bool:
    t = str(label or "").strip()
    if not t or "クラス" in t or "未勝利" in t or "新馬" in t:
        return False
    if any(x in t for x in ("G1", "G2", "G3", "重賞", "ステークス", "記念", "杯", "賞")):
        return True
    # named stakes shorthand: 招福S / ジュニアC
    if len(t) <= 16 and (t.endswith("S") or t.endswith("C")):
        return True
    return False


def research_category(class_label: str | None, age_group: str | None, race_class: str | None = None) -> str:
    labels = [str(class_label or "").strip(), str(race_class or "").strip()]
    text = " ".join(x for x in labels if x)
    age = str(age_group or "")
    if age == "2yo_newcomer" or "2歳新馬" in text or (
        "新馬" in text and "2歳" in text
    ):
        return "2yo_newcomer"
    if age == "2yo_maiden" or "2歳未勝利" in text:
        return "2yo_maiden"
    if age == "3yo_maiden" or "3歳未勝利" in text:
        return "3yo_maiden"
    if "1勝" in text:
        return "class_1win"
    if "2勝" in text:
        return "class_2win"
    if "3勝" in text:
        return "class_3win"
    if any(_is_named_stakes(x) for x in labels) or any(
        x in text for x in ("G1", "G2", "G3", "重賞")
    ):
        return "stakes"
    if "オープン" in text or re.search(r"\bOP\b", text):
        return "open"
    if age == "older" and "勝" not in text:
        return "open"
    return "other"


def _laplace_prior(wins: Counter[str], apps: Counter[str], alpha: float = 1.0) -> dict[str, float]:
    out = {}
    for k, a in apps.items():
        out[k] = (wins.get(k, 0) + alpha) / (a + 2 * alpha)
    return out


class EvidenceDiscoveryResearch:
    def __init__(self) -> None:
        migrate()
        self.analyzer = EvidenceAnalyzer(features=HORSE_FEATURES)
        self.root = repo_root()
        self.evidence = evidence_root()

    def load_corpus(self) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT
                  c.corpus_id, c.race_id, c.race_date, c.venue, c.surface, c.distance,
                  c.class_label, c.age_group, c.is_young_horse, c.is_tie, c.tie_size,
                  c.winner_horse_number, c.prediction_pick, c.source, c.prediction_id,
                  c.has_evidence_snapshot, c.meta_json,
                  s.snapshot_id, s.capture_status, s.field_coverage,
                  p.bundle_json,
                  m.field_size AS meta_field_size,
                  m.weather AS meta_weather,
                  m.going AS meta_going,
                  m.race_class AS meta_race_class,
                  m.course_type AS meta_course_type,
                  m.surface AS meta_surface,
                  m.distance AS meta_distance,
                  m.age_group AS meta_age_group
                FROM research_prediction_corpus c
                LEFT JOIN research_prediction_snapshots s
                  ON s.race_id = c.race_id AND s.capture_status = 'complete'
                LEFT JOIN predictions p ON p.id = COALESCE(s.prediction_id, c.prediction_id)
                LEFT JOIN research_race_meta m ON m.race_id = c.race_id
                WHERE c.winner_horse_number IS NOT NULL
                  AND c.race_id NOT LIKE '2099%'
                ORDER BY c.race_date ASC, c.race_id ASC
                """
            ).fetchall()
            seen: set[str] = set()
            out: list[dict[str, Any]] = []
            for raw in rows:
                row = dict(raw)
                rid = str(row["race_id"])
                if rid in seen:
                    continue
                seen.add(rid)
                # prefer hist bundle if prediction bundle empty
                bundle = {}
                try:
                    bundle = json.loads(row.get("bundle_json") or "{}")
                except Exception:
                    bundle = {}
                if not extract_runners(bundle):
                    hb = conn.execute(
                        """
                        SELECT bundle_json FROM research_historical_bundles
                        WHERE race_id=? AND has_bundle=1
                        ORDER BY updated_at DESC LIMIT 1
                        """,
                        (rid,),
                    ).fetchone()
                    if hb:
                        try:
                            bundle = json.loads(hb["bundle_json"] or "{}")
                        except Exception:
                            pass
                        row["bundle_json"] = hb["bundle_json"]

                runners = extract_runners(bundle)
                winner = int(row["winner_horse_number"])
                if not runners:
                    continue
                s_hit = strict_hit(runners, winner)
                so_hit = soft_hit(runners, winner)
                pick = unique_top_pick(runners)
                try:
                    pick_i = int(pick) if pick is not None else (
                        int(row["prediction_pick"]) if row.get("prediction_pick") is not None else None
                    )
                except (TypeError, ValueError):
                    pick_i = None

                surface = _surface_key(row.get("meta_surface") or row.get("surface"))
                distance = row.get("meta_distance") or row.get("distance")
                field_size = row.get("meta_field_size") or len(runners)
                going = str(row.get("meta_going") or "unknown") or "unknown"
                weather = str(row.get("meta_weather") or "unknown") or "unknown"
                if going in {"None", "", "null"}:
                    going = "unknown"
                if weather in {"None", "", "null"}:
                    weather = "unknown"
                class_label = row.get("class_label") or row.get("meta_race_class")
                age_group = row.get("meta_age_group") or row.get("age_group") or "unknown"
                category = research_category(
                    class_label, age_group, row.get("meta_race_class")
                )

                out.append(
                    {
                        **row,
                        "runners": runners,
                        "winner": winner,
                        "pick": pick_i,
                        "strict": int(bool(s_hit)),
                        "soft": int(bool(so_hit)),
                        "is_tie_group": int(len(tie_group(runners)) >= 2),
                        "surface": surface,
                        "distance_bucket": _distance_bucket(distance),
                        "field_bucket": _field_bucket(
                            int(field_size) if field_size else None
                        ),
                        "going": going,
                        "weather": weather,
                        "venue": str(row.get("venue") or "unknown"),
                        "category": category,
                        "class_label": class_label,
                        "age_group": age_group,
                        "has_snapshot": bool(row.get("snapshot_id")),
                    }
                )
            return out
        finally:
            conn.close()

    def _cat_priors_loo(
        self,
        races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        holdout_idx: int,
        feature_id: str,
    ) -> dict[str, float]:
        wins: Counter[str] = Counter()
        apps: Counter[str] = Counter()
        for i, race in enumerate(races):
            if i == holdout_idx:
                continue
            snap = str(race.get("snapshot_id") or "")
            if not snap:
                continue
            winner = int(race["winner"])
            vals = (fmap.get(snap) or {}).get(feature_id) or {}
            for hn, val in vals.items():
                if val is None:
                    continue
                key = str(val).strip()
                if not key or key in {"-", "null", "None"}:
                    continue
                apps[key] += 1
                if int(hn) == winner:
                    wins[key] += 1
        return _laplace_prior(wins, apps)

    def _pick_by_feature(
        self,
        *,
        feature_id: str,
        runners: list[dict[str, Any]],
        values: dict[int, Any],
        cat_prior: dict[str, float] | None,
        group: list[dict[str, Any]] | None = None,
    ) -> tuple[int | None, str]:
        target = group if group is not None else runners
        scores: dict[int, float | None] = {}
        for r in target:
            hn = int(r.get("horse_number") or 0)
            scores[hn] = feature_score(
                feature_id, values.get(hn), cat_prior=cat_prior
            )
        return resolve_by_score(target, scores)

    def feature_importance(
        self, races: list[dict[str, Any]], fmap: dict[str, dict[str, dict[int, Any]]]
    ) -> dict[str, Any]:
        evidence_races = [r for r in races if r.get("has_snapshot")]
        by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in evidence_races:
            by_cat[r["category"]].append(r)
        by_cat["ALL"] = evidence_races

        results: dict[str, list[dict[str, Any]]] = {}
        for cat, subset in by_cat.items():
            if not subset:
                continue
            solo = {
                f: {
                    "feature_id": f,
                    "label": FEATURE_LABELS.get(f, f),
                    "field_resolved": 0,
                    "field_correct": 0,
                    "field_missing": 0,
                    "tie_eligible": 0,
                    "tie_resolved": 0,
                    "tie_correct": 0,
                    "ig_sum": 0.0,
                    "ig_n": 0,
                    "coverage_cells": 0,
                    "coverage_filled": 0,
                }
                for f in HORSE_FEATURES
            }
            for idx, race in enumerate(subset):
                runners = race["runners"]
                winner = race["winner"]
                g = tie_group(runners)
                snap = str(race["snapshot_id"])
                feat_maps = fmap.get(snap) or {}
                # map subset index for LOO — use global evidence index
                global_idx = evidence_races.index(race)
                for fid in HORSE_FEATURES:
                    values = feat_maps.get(fid) or {}
                    for r in runners:
                        hn = int(r.get("horse_number") or 0)
                        solo[fid]["coverage_cells"] += 1
                        v = values.get(hn)
                        if v is not None and str(v) not in {"", "-", "null", "None"}:
                            solo[fid]["coverage_filled"] += 1
                    cat_prior = None
                    if fid in CATEGORICAL_FEATURES:
                        cat_prior = self._cat_priors_loo(
                            evidence_races, fmap, global_idx, fid
                        )
                    pick, status = self._pick_by_feature(
                        feature_id=fid,
                        runners=runners,
                        values=values,
                        cat_prior=cat_prior,
                        group=runners,
                    )
                    if status == "missing":
                        solo[fid]["field_missing"] += 1
                    elif status == "resolved":
                        solo[fid]["field_resolved"] += 1
                        if pick == winner:
                            solo[fid]["field_correct"] += 1
                    if len(g) >= 2:
                        solo[fid]["tie_eligible"] += 1
                        tpick, tstatus = self._pick_by_feature(
                            feature_id=fid,
                            runners=runners,
                            values=values,
                            cat_prior=cat_prior,
                            group=g,
                        )
                        if tstatus == "resolved":
                            solo[fid]["tie_resolved"] += 1
                            solo[fid]["ig_sum"] += _ig_bits(len(g), True)
                            solo[fid]["ig_n"] += 1
                            if tpick == winner:
                                solo[fid]["tie_correct"] += 1

            ranked = []
            for fid, st in solo.items():
                field_n = st["field_resolved"]
                field_rate = _safe_div(st["field_correct"], field_n)
                tie_rate = _safe_div(st["tie_correct"], st["tie_resolved"])
                avg_ig = _safe_div(st["ig_sum"], st["ig_n"]) or 0.0
                cov = _safe_div(st["coverage_filled"], st["coverage_cells"]) or 0.0
                score = (
                    0.45 * (field_rate or 0.0)
                    + 0.25 * (tie_rate or 0.0)
                    + 0.20 * min(avg_ig / 2.0, 1.0)
                    + 0.10 * cov
                )
                gate = classify_gate(
                    n=field_n,
                    successes=st["field_correct"],
                    baseline=1.0 / max(len(subset[0]["runners"]), 2) if subset else 0.1,
                )
                # use random-field baseline ~ 1/mean field size
                mean_field = sum(len(r["runners"]) for r in subset) / max(len(subset), 1)
                gate = classify_gate(
                    n=field_n,
                    successes=st["field_correct"],
                    baseline=1.0 / max(mean_field, 2.0),
                )
                ranked.append(
                    {
                        **st,
                        "n_races": len(subset),
                        "field_hit_rate": field_rate,
                        "tie_hit_rate": tie_rate,
                        "avg_ig": round(avg_ig, 4),
                        "coverage": round(cov, 4),
                        "importance_score": round(score, 4),
                        "gate": gate,
                    }
                )
            ranked.sort(key=lambda x: (-x["importance_score"], x["feature_id"]))
            for i, r in enumerate(ranked, 1):
                r["rank"] = i
            results[cat] = ranked

        # Race-axis importance: strict rate lift vs global by axis segment
        global_strict = _safe_div(sum(r["strict"] for r in races), len(races)) or 0.0
        race_axis_imp: dict[str, list[dict[str, Any]]] = {}
        for axis in RACE_AXES:
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for r in races:
                groups[str(r.get(axis) or "unknown")].append(r)
            rows = []
            for seg, items in groups.items():
                if seg == "unknown":
                    continue
                n = len(items)
                hits = sum(x["strict"] for x in items)
                rate = _safe_div(hits, n) or 0.0
                gate = classify_gate(n=n, successes=hits, baseline=global_strict)
                rows.append(
                    {
                        "axis": axis,
                        "label": FEATURE_LABELS.get(axis, axis),
                        "segment": seg,
                        "n": n,
                        "strict_rate": rate,
                        "lift_vs_global": round(rate - global_strict, 4),
                        "gate": gate,
                    }
                )
            rows.sort(key=lambda x: (-abs(x["lift_vs_global"]), -x["n"]))
            race_axis_imp[axis] = rows
        return {
            "by_category_horse_features": results,
            "race_axis_segments": race_axis_imp,
            "evidence_races": len(evidence_races),
            "all_races": len(races),
        }

    def interactions(
        self, races: list[dict[str, Any]], fmap: dict[str, dict[str, dict[int, Any]]]
    ) -> dict[str, Any]:
        evidence = [r for r in races if r.get("has_snapshot")]
        pairs = [
            ("popularity", "sire"),
            ("popularity", "trainer"),
            ("sire", "trainer"),
            ("sire", "going"),  # going is race-level; handled separately
            ("popularity", "distance_bucket"),
            ("popularity", "win_odds"),
            ("trainer", "breeder"),
            ("oikiri_rating", "popularity"),
            ("owner", "sire"),
            ("damsire", "sire"),
        ]
        horse_pairs = [
            (a, b)
            for a, b in pairs
            if a in HORSE_FEATURES and b in HORSE_FEATURES
        ]
        pair_stats: dict[str, dict[str, Any]] = {}
        for a, b in horse_pairs:
            key = f"{a}×{b}"
            pair_stats[key] = {
                "features": [a, b],
                "labels": [FEATURE_LABELS.get(a, a), FEATURE_LABELS.get(b, b)],
                "tie_eligible": 0,
                "cascade_resolved": 0,
                "cascade_correct": 0,
                "solo_a_correct": 0,
                "solo_b_correct": 0,
            }

        for idx, race in enumerate(evidence):
            runners = race["runners"]
            winner = race["winner"]
            g = tie_group(runners)
            if len(g) < 2:
                continue
            snap = str(race["snapshot_id"])
            feat_maps = fmap.get(snap) or {}
            cat_priors = {
                fid: self._cat_priors_loo(evidence, fmap, idx, fid)
                for fid in HORSE_FEATURES
                if fid in CATEGORICAL_FEATURES
            }
            for a, b in horse_pairs:
                key = f"{a}×{b}"
                st = pair_stats[key]
                st["tie_eligible"] += 1
                values_by_feature = {
                    a: feat_maps.get(a) or {},
                    b: feat_maps.get(b) or {},
                }
                # solo
                for fid, bucket in ((a, "solo_a_correct"), (b, "solo_b_correct")):
                    prior = cat_priors.get(fid) if fid in CATEGORICAL_FEATURES else None
                    pick, status = self._pick_by_feature(
                        feature_id=fid,
                        runners=runners,
                        values=values_by_feature[fid],
                        cat_prior=prior,
                        group=g,
                    )
                    if status == "resolved" and pick == winner:
                        st[bucket] += 1
                pick, status, _used = cascade_resolve(
                    g,
                    [a, b],
                    values_by_feature,
                    cat_priors,
                )
                if status == "resolved":
                    st["cascade_resolved"] += 1
                    if pick == winner:
                        st["cascade_correct"] += 1

        interactions_2 = []
        for key, st in pair_stats.items():
            n = st["cascade_resolved"]
            hits = st["cascade_correct"]
            best_solo = max(st["solo_a_correct"], st["solo_b_correct"])
            rate = _safe_div(hits, n)
            gate = classify_gate(n=n, successes=hits, baseline=0.5)
            interactions_2.append(
                {
                    **st,
                    "key": key,
                    "cascade_hit_rate": rate,
                    "lift_vs_best_solo": hits - best_solo,
                    "gate": gate,
                }
            )
        interactions_2.sort(
            key=lambda x: (
                -int(x["gate"]["confident"]),
                -(x["cascade_hit_rate"] or 0),
                -x["cascade_resolved"],
            )
        )

        # 3-way mined bins on winners vs field (evidence races)
        combo3: Counter[str] = Counter()
        combo3_win: Counter[str] = Counter()
        combo2: Counter[str] = Counter()
        combo2_win: Counter[str] = Counter()
        for idx, race in enumerate(evidence):
            snap = str(race["snapshot_id"])
            feat_maps = fmap.get(snap) or {}
            cat_priors = {
                fid: self._cat_priors_loo(evidence, fmap, idx, fid)
                for fid in HORSE_FEATURES
                if fid in CATEGORICAL_FEATURES
            }
            oikiri_times = []
            for hn, v in (feat_maps.get("oikiri_time") or {}).items():
                try:
                    oikiri_times.append(float(v))
                except (TypeError, ValueError):
                    pass
            for r in race["runners"]:
                hn = int(r.get("horse_number") or 0)
                values = {fid: (feat_maps.get(fid) or {}).get(hn) for fid in HORSE_FEATURES}
                bins = discretize_horse(
                    values=values,
                    cat_priors=cat_priors,
                    race_oikiri_times=oikiri_times,
                )
                # attach race axes as pseudo bins
                bins["surface"] = race["surface"]
                bins["distance_bucket"] = race["distance_bucket"]
                bins["going"] = race["going"]
                is_win = hn == race["winner"]
                keys2 = [
                    ("popularity", "sire"),
                    ("popularity", "trainer"),
                    ("sire", "trainer"),
                    ("popularity", "distance_bucket"),
                    ("sire", "going"),
                    ("popularity", "surface"),
                    ("oikiri_rating", "popularity"),
                ]
                for a, b in keys2:
                    if bins.get(a) and bins.get(b) and "MISS" not in str(bins.get(a)):
                        k = f"{a}={bins[a]}|{b}={bins[b]}"
                        combo2[k] += 1
                        if is_win:
                            combo2_win[k] += 1
                for a, b, c in (
                    ("popularity", "sire", "trainer"),
                    ("popularity", "oikiri_rating", "sire"),
                    ("popularity", "surface", "distance_bucket"),
                ):
                    if all(bins.get(x) and "MISS" not in str(bins.get(x)) for x in (a, b, c)):
                        k = f"{a}={bins[a]}|{b}={bins[b]}|{c}={bins[c]}"
                        combo3[k] += 1
                        if is_win:
                            combo3_win[k] += 1

        def _mine(counter, win_counter, kind: str) -> list[dict[str, Any]]:
            rows = []
            for k, n in counter.most_common(80):
                w = win_counter.get(k, 0)
                # baseline ~ 1/mean field among evidence
                mean_field = sum(len(r["runners"]) for r in evidence) / max(len(evidence), 1)
                gate = classify_gate(n=n, successes=w, baseline=1.0 / max(mean_field, 2))
                rows.append(
                    {
                        "kind": kind,
                        "pattern": k,
                        "n_horses": n,
                        "wins": w,
                        "win_rate": _safe_div(w, n),
                        "gate": gate,
                    }
                )
            rows.sort(
                key=lambda x: (
                    -int(x["gate"]["confident"]),
                    -(x["win_rate"] or 0),
                    -x["n_horses"],
                )
            )
            return rows

        return {
            "cascade_2way": interactions_2,
            "mined_2way": _mine(combo2, combo2_win, "2way"),
            "mined_3way": _mine(combo3, combo3_win, "3way"),
        }

    def segment_comparison(self, races: list[dict[str, Any]]) -> dict[str, Any]:
        global_strict = _safe_div(sum(r["strict"] for r in races), len(races)) or 0.0
        global_soft = _safe_div(sum(r["soft"] for r in races), len(races)) or 0.0
        by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in races:
            by_cat[r["category"]].append(r)

        rows = []
        for cat in CATEGORY_ORDER:
            items = by_cat.get(cat) or []
            if not items:
                rows.append(
                    {
                        "category": cat,
                        "n": 0,
                        "note": "no_samples",
                        "exploratory": True,
                    }
                )
                continue
            n = len(items)
            s = sum(x["strict"] for x in items)
            so = sum(x["soft"] for x in items)
            ties = sum(x["is_tie_group"] for x in items)
            evi = sum(1 for x in items if x.get("has_snapshot"))
            gate = classify_gate(n=n, successes=s, baseline=global_strict)
            # meta distribution hints
            surf = Counter(x["surface"] for x in items)
            dist = Counter(x["distance_bucket"] for x in items)
            rows.append(
                {
                    "category": cat,
                    "n": n,
                    "strict_rate": _safe_div(s, n),
                    "soft_rate": _safe_div(so, n),
                    "tie_rate": _safe_div(ties, n),
                    "evidence_n": evi,
                    "lift_vs_global_strict": round((_safe_div(s, n) or 0) - global_strict, 4),
                    "surface_mix": dict(surf.most_common(5)),
                    "distance_mix": dict(dist.most_common(5)),
                    "gate": gate,
                    "research_notes": _category_notes(cat),
                }
            )
        return {
            "global_strict": global_strict,
            "global_soft": global_soft,
            "categories": rows,
        }

    def failure_analysis(self, races: list[dict[str, Any]], fmap) -> dict[str, Any]:
        fails = [r for r in races if not r["strict"]]
        wins_n = sum(1 for r in races if r["strict"])
        return self._outcome_slice(fails, fmap, label="failure", complement_n=wins_n)

    def winner_analysis(self, races: list[dict[str, Any]], fmap) -> dict[str, Any]:
        wins = [r for r in races if r["strict"]]
        fail_n = sum(1 for r in races if not r["strict"])
        return self._outcome_slice(wins, fmap, label="winner", complement_n=fail_n)

    def _outcome_slice(
        self,
        subset: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        *,
        label: str,
        complement_n: int,
    ) -> dict[str, Any]:
        n = len(subset)
        by_cat = Counter(r["category"] for r in subset)
        by_surface = Counter(r["surface"] for r in subset)
        by_distance = Counter(r["distance_bucket"] for r in subset)
        by_going = Counter(r["going"] for r in subset)
        by_venue = Counter(r["venue"] for r in subset)
        by_field = Counter(r["field_bucket"] for r in subset)
        by_pop = Counter()
        by_odds = Counter()
        evidence = [r for r in subset if r.get("has_snapshot")]

        for race in evidence:
            snap = str(race["snapshot_id"])
            feat = fmap.get(snap) or {}
            pick = race.get("pick")
            if pick is None:
                continue
            pop = (feat.get("popularity") or {}).get(int(pick))
            odds = (feat.get("win_odds") or {}).get(int(pick))
            try:
                p = int(float(pop))
                if p == 1:
                    by_pop["pop_1"] += 1
                elif p <= 3:
                    by_pop["pop_2-3"] += 1
                elif p <= 6:
                    by_pop["pop_4-6"] += 1
                else:
                    by_pop["pop_7+"] += 1
            except (TypeError, ValueError):
                by_pop["unknown"] += 1
            try:
                o = float(odds)
                if o < 4:
                    by_odds["odds_short"] += 1
                elif o < 10:
                    by_odds["odds_mid"] += 1
                elif o < 20:
                    by_odds["odds_long"] += 1
                else:
                    by_odds["odds_heavy"] += 1
            except (TypeError, ValueError):
                by_odds["unknown"] += 1

        conditions = []
        for name, counter in (
            ("category", by_cat),
            ("surface", by_surface),
            ("distance_bucket", by_distance),
            ("going", by_going),
            ("venue", by_venue),
            ("field_bucket", by_field),
            ("pick_popularity", by_pop),
            ("pick_odds", by_odds),
        ):
            for seg, cnt in counter.most_common(12):
                if seg in {"unknown", ""}:
                    continue
                gate = classify_gate(n=n, successes=cnt, baseline=0.0)
                # share of this outcome slice
                conditions.append(
                    {
                        "axis": name,
                        "segment": seg,
                        "count": cnt,
                        "share": _safe_div(cnt, n),
                        "gate": {
                            **gate,
                            # for composition shares, confident only if n(slice)>=20
                            "confident": n >= CONFIDENT_MIN_N and cnt >= 5,
                            "exploratory": not (n >= CONFIDENT_MIN_N and cnt >= 5),
                        },
                    }
                )

        return {
            "label": label,
            "n": n,
            "complement_n": complement_n,
            "evidence_n": len(evidence),
            "by_category": dict(by_cat),
            "conditions": conditions,
            "sample_race_ids": [r["race_id"] for r in subset[:15]],
            "exploratory": n < CONFIDENT_MIN_N,
        }

    def evidence_hypotheses(
        self,
        *,
        importance: dict[str, Any],
        interactions: dict[str, Any],
        segments: dict[str, Any],
        failures: dict[str, Any],
        winners: dict[str, Any],
    ) -> dict[str, Any]:
        confident: list[dict[str, Any]] = []
        exploratory: list[dict[str, Any]] = []

        def _push(item: dict[str, Any]) -> None:
            gate = item.get("gate") or {}
            if gate.get("confident"):
                confident.append(item)
            else:
                exploratory.append(item)

        # from horse feature importance ALL
        for row in importance.get("by_category_horse_features", {}).get("ALL") or []:
            _push(
                {
                    "type": "feature_importance",
                    "category": "ALL",
                    "statement": (
                        f"{row['label']} field-hit={_pct(row.get('field_hit_rate'))} "
                        f"on n={row.get('field_resolved')} (evidence races)"
                    ),
                    "feature": row["feature_id"],
                    "gate": row.get("gate"),
                    "metrics": {
                        "importance_score": row.get("importance_score"),
                        "field_hit_rate": row.get("field_hit_rate"),
                        "coverage": row.get("coverage"),
                    },
                }
            )

        for row in interactions.get("mined_2way") or []:
            _push(
                {
                    "type": "interaction_2way",
                    "statement": f"Pattern {row['pattern']} win_rate={_pct(row.get('win_rate'))} n={row['n_horses']}",
                    "gate": row.get("gate"),
                    "metrics": row,
                }
            )
        for row in interactions.get("mined_3way") or []:
            _push(
                {
                    "type": "interaction_3way",
                    "statement": f"Pattern {row['pattern']} win_rate={_pct(row.get('win_rate'))} n={row['n_horses']}",
                    "gate": row.get("gate"),
                    "metrics": row,
                }
            )
        for row in segments.get("categories") or []:
            if not row.get("n"):
                continue
            _push(
                {
                    "type": "segment",
                    "statement": (
                        f"Category {row['category']} Strict={_pct(row.get('strict_rate'))} "
                        f"n={row['n']} lift={row.get('lift_vs_global_strict')}"
                    ),
                    "gate": row.get("gate"),
                    "metrics": row,
                    "research_notes": row.get("research_notes"),
                }
            )

        # improvement candidates (suggestions only — not implementation)
        suggestions = []
        for h in confident[:10]:
            suggestions.append(
                {
                    "from_hypothesis": h.get("statement"),
                    "candidate": "Investigate as Research follow-up only; do NOT change Prediction yet.",
                    "ticket": "future-improvement-ticket",
                }
            )
        if not confident:
            suggestions.append(
                {
                    "from_hypothesis": None,
                    "candidate": (
                        "No confident (N>=20 & CI95) hypotheses yet — expand Evidence snapshots "
                        "and class-label coverage before any product change."
                    ),
                    "ticket": "future-improvement-ticket",
                }
            )

        return {
            "confident": confident[:40],
            "exploratory": exploratory[:60],
            "improvement_candidates": suggestions,
            "counts": {
                "confident": len(confident),
                "exploratory": len(exploratory),
            },
        }

    def analyze(self) -> dict[str, Any]:
        races = self.load_corpus()
        evidence = [r for r in races if r.get("has_snapshot")]
        snap_ids = [str(r["snapshot_id"]) for r in evidence]
        fmap = self.analyzer.load_feature_map(snap_ids)

        importance = self.feature_importance(races, fmap)
        interactions = self.interactions(races, fmap)
        segments = self.segment_comparison(races)
        failures = self.failure_analysis(races, fmap)
        winners = self.winner_analysis(races, fmap)
        discovery = self.evidence_hypotheses(
            importance=importance,
            interactions=interactions,
            segments=segments,
            failures=failures,
            winners=winners,
        )

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "shadow_only": True,
            "prediction_mutation": "FORBIDDEN",
            "resolver_mutation": "FORBIDDEN",
            "sample": {
                "unique_races": len(races),
                "with_evidence": len(evidence),
                "strict_hits": sum(r["strict"] for r in races),
                "soft_hits": sum(r["soft"] for r in races),
                "global_strict": _safe_div(sum(r["strict"] for r in races), len(races)),
                "global_soft": _safe_div(sum(r["soft"] for r in races), len(races)),
                "by_category": dict(Counter(r["category"] for r in races)),
                "confident_min_n": CONFIDENT_MIN_N,
                "confidence_level": 0.95,
                "exploratory": len(evidence) < 100,
            },
            "feature_importance": importance,
            "interactions": interactions,
            "segment_comparison": segments,
            "failure_analysis": failures,
            "winner_analysis": winners,
            "evidence_discovery": discovery,
        }


def _category_notes(cat: str) -> str:
    return {
        "2yo_newcomer": "Debut — pedigree (sire/damsire/breeder) & workout may dominate; no form.",
        "2yo_maiden": "Early career — market + workout; limited form depth.",
        "3yo_maiden": "Form begins — prior-run signals may matter more than debut.",
        "class_1win": "Class step — consistency / trainer patterns candidate.",
        "class_2win": "Mid class — pace/distance specialization candidate.",
        "class_3win": "Upper class — class drop/rise and weight effects candidate.",
        "open": "Open — competitive fields; popularity reliability candidate.",
        "stakes": "Stakes — market (popularity/odds) often dominates; pedigree secondary.",
        "other": "Unclassified labels — improve race_class metadata first.",
    }.get(cat, "")


def _write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_feature_discovery_md(report: dict[str, Any], path: Path) -> None:
    s = report.get("sample") or {}
    imp = report.get("feature_importance") or {}
    lines = [
        "# Version17 Research - Feature Discovery",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** Evidence Discovery / Prediction FORBIDDEN  ",
        "",
        "## Sample",
        "",
        f"- Unique races: `{s.get('unique_races')}` / Evidence: `{s.get('with_evidence')}`",
        f"- Global Strict: `{_pct(s.get('global_strict'))}` / Soft: `{_pct(s.get('global_soft'))}`",
        f"- Categories: `{json.dumps(s.get('by_category') or {}, ensure_ascii=False)}`",
        f"- Exploratory corpus: `{s.get('exploratory')}`",
        "",
        "## Horse-feature importance (Evidence races)",
        "",
    ]
    for cat, rows in (imp.get("by_category_horse_features") or {}).items():
        lines.extend(
            [
                f"### Category `{cat}`",
                "",
                "| Rank | Feature | FieldHit | TieHit | IG | Cov | Score | Gate |",
                "|-----:|---------|---------:|-------:|---:|----:|------:|------|",
            ]
        )
        for r in rows:
            g = r.get("gate") or {}
            gate = "CONFIDENT" if g.get("confident") else f"exploratory:{g.get('gate_reason')}"
            lines.append(
                f"| {r.get('rank')} | `{r.get('label')}` | {_pct(r.get('field_hit_rate'))} | "
                f"{_pct(r.get('tie_hit_rate'))} | {r.get('avg_ig')} | {_pct(r.get('coverage'))} | "
                f"{r.get('importance_score')} | {gate} |"
            )
        lines.append("")
    lines.extend(["## Race-axis segment lifts", ""])
    for axis, rows in (imp.get("race_axis_segments") or {}).items():
        lines.append(f"### `{FEATURE_LABELS.get(axis, axis)}`")
        lines.append("")
        lines.append("| Segment | N | Strict | Lift | Gate |")
        lines.append("|---------|--:|-------:|-----:|------|")
        for r in rows[:10]:
            g = r.get("gate") or {}
            gate = "CONFIDENT" if g.get("confident") else "exploratory"
            lines.append(
                f"| `{r.get('segment')}` | {r.get('n')} | {_pct(r.get('strict_rate'))} | "
                f"{r.get('lift_vs_global')} | {gate} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Guardrails",
            "",
            "- No Prediction / PE / CE / AI / Resolver / Shadow changes",
            "- Horse-feature importance requires Evidence snapshots",
            "",
        ]
    )
    _write_lines(path, lines)


def write_interactions_md(report: dict[str, Any], path: Path) -> None:
    inter = report.get("interactions") or {}
    lines = [
        "# Version17 Research - Feature Interactions",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "## Cascade 2-feature (Tie groups)",
        "",
        "| Pair | Eligible | Resolved | HitRate | LiftVsSolo | Gate |",
        "|------|---------:|---------:|--------:|-----------:|------|",
    ]
    for r in inter.get("cascade_2way") or []:
        g = r.get("gate") or {}
        gate = "CONFIDENT" if g.get("confident") else "exploratory"
        lines.append(
            f"| `{' × '.join(r.get('labels') or [])}` | {r.get('tie_eligible')} | "
            f"{r.get('cascade_resolved')} | {_pct(r.get('cascade_hit_rate'))} | "
            f"{r.get('lift_vs_best_solo')} | {gate} |"
        )
    lines.extend(
        [
            "",
            "## Mined 2-feature patterns (winner bins)",
            "",
            "| Pattern | N | Wins | WinRate | Gate |",
            "|---------|--:|-----:|--------:|------|",
        ]
    )
    for r in (inter.get("mined_2way") or [])[:25]:
        g = r.get("gate") or {}
        gate = "CONFIDENT" if g.get("confident") else "exploratory"
        lines.append(
            f"| `{r.get('pattern')}` | {r.get('n_horses')} | {r.get('wins')} | "
            f"{_pct(r.get('win_rate'))} | {gate} |"
        )
    lines.extend(
        [
            "",
            "## Mined 3-feature patterns",
            "",
            "| Pattern | N | Wins | WinRate | Gate |",
            "|---------|--:|-----:|--------:|------|",
        ]
    )
    for r in (inter.get("mined_3way") or [])[:25]:
        g = r.get("gate") or {}
        gate = "CONFIDENT" if g.get("confident") else "exploratory"
        lines.append(
            f"| `{r.get('pattern')}` | {r.get('n_horses')} | {r.get('wins')} | "
            f"{_pct(r.get('win_rate'))} | {gate} |"
        )
    lines.append("")
    _write_lines(path, lines)


def write_segment_md(report: dict[str, Any], path: Path) -> None:
    seg = report.get("segment_comparison") or {}
    lines = [
        "# Version17 Research - Segment Comparison",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"Global Strict=`{_pct(seg.get('global_strict'))}` Soft=`{_pct(seg.get('global_soft'))}`",
        "",
        "| Category | N | Strict | Soft | Tie | Evidence | Lift | Gate | Notes |",
        "|----------|--:|-------:|-----:|----:|---------:|-----:|------|-------|",
    ]
    for r in seg.get("categories") or []:
        if not r.get("n"):
            lines.append(
                f"| `{r.get('category')}` | 0 | — | — | — | — | — | exploratory | {r.get('note')} |"
            )
            continue
        g = r.get("gate") or {}
        gate = "CONFIDENT" if g.get("confident") else "exploratory"
        lines.append(
            f"| `{r.get('category')}` | {r.get('n')} | {_pct(r.get('strict_rate'))} | "
            f"{_pct(r.get('soft_rate'))} | {_pct(r.get('tie_rate'))} | {r.get('evidence_n')} | "
            f"{r.get('lift_vs_global_strict')} | {gate} | {r.get('research_notes')} |"
        )
    lines.extend(
        [
            "",
            "## Research questions by segment",
            "",
            "- 新馬: 父系・血統・追い切りが効くか？",
            "- 未勝利: 前走/フォーム情報が効き始めるか？",
            "- 重賞: 人気・オッズが支配的か？",
            "",
        ]
    )
    _write_lines(path, lines)


def write_failure_md(report: dict[str, Any], path: Path) -> None:
    f = report.get("failure_analysis") or {}
    lines = [
        "# Version17 Research - Failure Analysis",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"Strict misses: `{f.get('n')}` (wins complement `{f.get('complement_n')}`)",
        f"Evidence among misses: `{f.get('evidence_n')}`",
        f"Slice exploratory: `{f.get('exploratory')}`",
        "",
        "## Condition composition of misses",
        "",
        "| Axis | Segment | Count | Share | Gate |",
        "|------|---------|------:|------:|------|",
    ]
    for c in f.get("conditions") or []:
        g = c.get("gate") or {}
        gate = "CONFIDENT" if g.get("confident") else "exploratory"
        lines.append(
            f"| `{c.get('axis')}` | `{c.get('segment')}` | {c.get('count')} | "
            f"{_pct(c.get('share'))} | {gate} |"
        )
    lines.extend(
        [
            "",
            "## Sample miss race_ids",
            "",
            ", ".join(f"`{x}`" for x in (f.get("sample_race_ids") or [])),
            "",
            "## Note",
            "",
            "Failure = Prediction Strict miss. No product mutation from this report.",
            "",
        ]
    )
    _write_lines(path, lines)


def write_winner_md(report: dict[str, Any], path: Path) -> None:
    w = report.get("winner_analysis") or {}
    lines = [
        "# Version17 Research - Winner Analysis",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"Strict hits: `{w.get('n')}` (miss complement `{w.get('complement_n')}`)",
        f"Evidence among hits: `{w.get('evidence_n')}`",
        f"Slice exploratory: `{w.get('exploratory')}`",
        "",
        "## Condition composition of hits",
        "",
        "| Axis | Segment | Count | Share | Gate |",
        "|------|---------|------:|------:|------|",
    ]
    for c in w.get("conditions") or []:
        g = c.get("gate") or {}
        gate = "CONFIDENT" if g.get("confident") else "exploratory"
        lines.append(
            f"| `{c.get('axis')}` | `{c.get('segment')}` | {c.get('count')} | "
            f"{_pct(c.get('share'))} | {gate} |"
        )
    lines.extend(
        [
            "",
            "## Sample hit race_ids",
            "",
            ", ".join(f"`{x}`" for x in (w.get("sample_race_ids") or [])),
            "",
        ]
    )
    _write_lines(path, lines)


def write_discovery_md(report: dict[str, Any], path: Path) -> None:
    d = report.get("evidence_discovery") or {}
    lines = [
        "# Version17 Research - Evidence Discovery",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"Gate: N>=`{CONFIDENT_MIN_N}` and Wilson 95% CI lower > baseline",
        "",
        f"Counts: confident=`{(d.get('counts') or {}).get('confident')}` "
        f"/ exploratory=`{(d.get('counts') or {}).get('exploratory')}`",
        "",
        "## Confident hypotheses",
        "",
    ]
    conf = d.get("confident") or []
    if not conf:
        lines.append("_None passed the confident gate in this run._")
        lines.append("")
    for h in conf:
        lines.append(f"- **[{h.get('type')}]** {h.get('statement')}")
    lines.extend(["", "## Exploratory hypotheses (separated)", ""])
    for h in (d.get("exploratory") or [])[:40]:
        g = h.get("gate") or {}
        lines.append(
            f"- [{h.get('type')}] {h.get('statement')} "
            f"(reason=`{g.get('gate_reason')}`)"
        )
    lines.extend(
        [
            "",
            "## Improvement candidates (NOT implemented)",
            "",
            "These are ticket suggestions only. Do not change Prediction/PE/CE/Resolver.",
            "",
        ]
    )
    for s in d.get("improvement_candidates") or []:
        lines.append(f"- {s.get('candidate')} — ref: `{s.get('from_hypothesis')}`")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "```",
            "Action Type: Evidence Discovery (Research)",
            "Prediction Mutation: FORBIDDEN",
            "PE/CE/AI/Resolver/Shadow Mutation: FORBIDDEN",
            "Implementation of fixes: SEPARATE TICKET",
            "```",
            "",
        ]
    )
    _write_lines(path, lines)


def run_and_write() -> dict[str, Any]:
    report = EvidenceDiscoveryResearch().analyze()
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    write_feature_discovery_md(report, docs / "v17-feature-discovery.md")
    write_interactions_md(report, docs / "v17-feature-interactions.md")
    write_segment_md(report, docs / "v17-segment-comparison.md")
    write_failure_md(report, docs / "v17-failure-analysis.md")
    write_winner_md(report, docs / "v17-winner-analysis.md")
    write_discovery_md(report, docs / "v17-evidence-discovery.md")
    json_path = evidence_root() / "reports" / "v17-evidence-discovery.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "feature_discovery": str(docs / "v17-feature-discovery.md"),
        "interactions": str(docs / "v17-feature-interactions.md"),
        "segments": str(docs / "v17-segment-comparison.md"),
        "failures": str(docs / "v17-failure-analysis.md"),
        "winners": str(docs / "v17-winner-analysis.md"),
        "discovery": str(docs / "v17-evidence-discovery.md"),
        "json": str(json_path),
    }
    return report
