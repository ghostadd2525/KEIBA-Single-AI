# -*- coding: utf-8 -*-
"""
Version14 Evidence Reliability Research

Evaluates Evidence Feature *reliability* (not predictive effect).
Does NOT mutate Prediction / PE / CE / AI / Challenge / Resolver.
Research-only. No Young Horse Score productization.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-evidence-reliability/1.0"

V14_FEATURES: tuple[str, ...] = (
    "popularity",
    "win_odds",
    "trainer",
    "sire",
    "damsire",
    "breeder",
    "oikiri_time",
    "oikiri_rating",
    "owner",
    "sale_price",
)

# Alias for docs / user wording
FEATURE_LABELS = {
    "popularity": "Popularity",
    "win_odds": "Odds",
    "trainer": "Trainer",
    "sire": "Sire",
    "damsire": "Damsire",
    "breeder": "Breeder",
    "oikiri_time": "WorkoutTime",
    "oikiri_rating": "WorkoutRating",
    "owner": "Owner",
    "sale_price": "SalePrice",
}

NUMERIC_FEATURES = frozenset({"popularity", "win_odds", "oikiri_time", "sale_price"})


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_value(raw: str | None) -> Any:
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() == "null" or s == '""':
        return None
    try:
        v = json.loads(s)
    except Exception:
        v = s
    if v is None:
        return None
    if isinstance(v, str) and v.strip() in {"", "-", "null", "None", "N/A"}:
        return None
    return v


def _is_filled(val: Any, missing_reason: str | None) -> bool:
    if missing_reason:
        # explicit missing
        if val is None:
            return False
    return val is not None


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            h -= p * math.log2(p)
    return h


def _parse_sale_num(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    import re

    s = str(val)
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*万", s)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    try:
        return float(s.replace(",", ""))
    except (TypeError, ValueError):
        return None


def _to_float(feature_id: str, val: Any) -> float | None:
    if feature_id == "sale_price":
        return _parse_sale_num(val)
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


class EvidenceReliabilityResearch:
    def __init__(self, features: tuple[str, ...] = V14_FEATURES) -> None:
        migrate()
        self.features = features

    def _load_rows(self) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT
                  f.snapshot_id,
                  f.prediction_id,
                  f.race_id,
                  f.horse_number,
                  f.feature_id,
                  f.value_json,
                  f.missing_reason,
                  f.asof_clamped,
                  f.observed_at,
                  s.race_date,
                  s.capture_status,
                  s.anti_leak_violations,
                  s.field_coverage,
                  p.created_at AS prediction_created_at,
                  rr.winner_horse_number
                FROM research_snapshot_features f
                JOIN research_prediction_snapshots s ON s.snapshot_id = f.snapshot_id
                LEFT JOIN predictions p ON p.id = f.prediction_id
                LEFT JOIN race_results rr ON rr.race_id = f.race_id
                WHERE f.race_id NOT LIKE '2099%'
                  AND s.capture_status = 'complete'
                  AND f.feature_id IN ({placeholders})
                ORDER BY s.race_date ASC, f.race_id ASC, f.horse_number ASC
                """.format(
                    placeholders=",".join("?" * len(self.features))
                ),
                tuple(self.features),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _reliability_score(self, m: dict[str, Any]) -> float:
        """
        0..100 composite. Higher = more reliable Evidence for research use.
        Does NOT encode predictive strength.
        """
        coverage = float(m.get("coverage") or 0.0)
        availability = float(m.get("availability") or 0.0)
        selection_bias = float(m.get("selection_bias") or 0.0)
        temporal_bias = float(m.get("temporal_bias") or 0.0)
        leak_risk = float(m.get("leak_risk") or 0.0)
        variance_pen = float(m.get("variance_penalty") or 0.0)
        stability = float(m.get("stability") or 0.0)
        weekly_drift = float(m.get("weekly_drift") or 0.0)

        score = 100.0 * (
            0.22 * coverage
            + 0.13 * availability
            + 0.15 * (1.0 - _clamp01(selection_bias))
            + 0.10 * (1.0 - _clamp01(temporal_bias))
            + 0.20 * (1.0 - _clamp01(leak_risk))
            + 0.08 * (1.0 - _clamp01(variance_pen))
            + 0.07 * _clamp01(stability)
            + 0.05 * (1.0 - _clamp01(weekly_drift))
        )
        return round(_clamp01(score / 100.0) * 100.0, 1)

    def analyze_features(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_feat: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            by_feat[str(r["feature_id"])].append(r)

        # popularity lookup for selection bias (same race/horse)
        pop_map: dict[tuple[str, int], float | None] = {}
        for r in by_feat.get("popularity", []):
            val = _parse_value(r.get("value_json"))
            key = (str(r["race_id"]), int(r["horse_number"]))
            try:
                pop_map[key] = float(val) if val is not None else None
            except (TypeError, ValueError):
                pop_map[key] = None

        out: list[dict[str, Any]] = []
        for fid in self.features:
            items = by_feat.get(fid, [])
            total = len(items)
            filled_rows = []
            missing_rows = []
            missing_reasons: Counter[str] = Counter()
            asof_n = 0
            leak_obs_n = 0
            race_filled: dict[str, int] = defaultdict(int)
            race_total: dict[str, int] = defaultdict(int)
            week_stats: dict[str, dict[str, float]] = defaultdict(
                lambda: {"filled": 0.0, "total": 0.0, "num_sum": 0.0, "num_n": 0.0}
            )
            cat_counts: Counter[str] = Counter()
            num_vals: list[float] = []

            for r in items:
                rid = str(r["race_id"])
                race_total[rid] += 1
                val = _parse_value(r.get("value_json"))
                miss = r.get("missing_reason")
                filled = _is_filled(val, miss)
                # treat "-" strings already handled
                if not filled and miss:
                    missing_reasons[str(miss)] += 1
                elif not filled:
                    missing_reasons["empty_value"] += 1

                if int(r.get("asof_clamped") or 0) == 1:
                    asof_n += 1

                # temporal leak: observed_at > prediction_created_at
                obs = r.get("observed_at")
                pred_at = r.get("prediction_created_at")
                if obs and pred_at:
                    try:
                        from .anti_leak import anti_leak_ok

                        if not anti_leak_ok(
                            observed_at=str(obs), prediction_created_at=str(pred_at)
                        ):
                            leak_obs_n += 1
                    except Exception:
                        pass

                week = str(r.get("race_date") or "")[:10]
                week_stats[week]["total"] += 1
                if filled:
                    filled_rows.append(r)
                    race_filled[rid] += 1
                    week_stats[week]["filled"] += 1
                    if fid in NUMERIC_FEATURES or fid == "sale_price":
                        num = _to_float(fid, val)
                        if num is not None:
                            num_vals.append(num)
                            week_stats[week]["num_sum"] += num
                            week_stats[week]["num_n"] += 1
                    else:
                        cat_counts[str(val).strip()[:80]] += 1
                else:
                    missing_rows.append(r)

            coverage = _safe_div(len(filled_rows), total) or 0.0
            missing_rate = 1.0 - coverage
            races = list(race_total.keys())
            availability = (
                sum(1 for rid in races if race_filled.get(rid, 0) > 0) / len(races)
                if races
                else 0.0
            )

            # Selection bias: |mean(pop|filled) - mean(pop|missing)| / scale
            # If never missing, use concentration of values on favorites (pop<=3 share vs uniform)
            sel_bias = 0.0
            sel_detail: dict[str, Any] = {}
            if missing_rows and filled_rows:
                pop_f = [
                    pop_map.get((str(r["race_id"]), int(r["horse_number"])))
                    for r in filled_rows
                ]
                pop_m = [
                    pop_map.get((str(r["race_id"]), int(r["horse_number"])))
                    for r in missing_rows
                ]
                pop_f = [p for p in pop_f if p is not None]
                pop_m = [p for p in pop_m if p is not None]
                if pop_f and pop_m:
                    mf = statistics.mean(pop_f)
                    mm = statistics.mean(pop_m)
                    # larger gap => stronger selection into missingness
                    sel_bias = _clamp01(abs(mf - mm) / 8.0)
                    sel_detail = {
                        "mean_pop_filled": round(mf, 3),
                        "mean_pop_missing": round(mm, 3),
                        "mode": "missingness_vs_popularity",
                    }
            else:
                # always present: check favorite concentration of numeric/pop-linked
                if fid == "popularity" and num_vals:
                    fav_share = sum(1 for x in num_vals if x <= 3) / len(num_vals)
                    # not bias by itself; mild flag only if weird
                    sel_bias = 0.0
                    sel_detail = {"mode": "always_present", "fav_share_p1_3": round(fav_share, 3)}
                elif num_vals and pop_map:
                    # correlate value extremity with popularity for odds
                    pairs = []
                    for r in filled_rows:
                        key = (str(r["race_id"]), int(r["horse_number"]))
                        p = pop_map.get(key)
                        v = _to_float(fid, _parse_value(r.get("value_json")))
                        if p is not None and v is not None:
                            pairs.append((p, v))
                    if len(pairs) >= 20:
                        # crude: compare mean value for pop<=3 vs pop>=7
                        a = [v for p, v in pairs if p <= 3]
                        b = [v for p, v in pairs if p >= 7]
                        if a and b:
                            # normalized difference
                            sel_bias = _clamp01(
                                abs(statistics.mean(a) - statistics.mean(b))
                                / (abs(statistics.mean(a + b)) + 1e-6)
                                / 3.0
                            )
                            sel_detail = {
                                "mode": "value_vs_popularity_strata",
                                "mean_val_fav": round(statistics.mean(a), 3),
                                "mean_val_long": round(statistics.mean(b), 3),
                            }
                else:
                    sel_detail = {"mode": "always_present_or_insufficient"}

            # Weekly coverage series
            weeks = sorted(week_stats.keys())
            week_cov = []
            week_means = []
            for w in weeks:
                st = week_stats[w]
                if st["total"] <= 0:
                    continue
                week_cov.append(st["filled"] / st["total"])
                if st["num_n"] > 0:
                    week_means.append(st["num_sum"] / st["num_n"])

            if len(week_cov) >= 2:
                weekly_drift = _clamp01(
                    max(week_cov) - min(week_cov)
                    if max(week_cov) - min(week_cov) > 0
                    else 0.0
                )
                # also include mean absolute delta
                deltas = [abs(week_cov[i] - week_cov[i - 1]) for i in range(1, len(week_cov))]
                weekly_drift = _clamp01(max(weekly_drift, statistics.mean(deltas)))
            elif len(week_cov) == 1:
                weekly_drift = 0.0  # insufficient history → unknown, don't punish hard
            else:
                weekly_drift = 1.0

            # Temporal bias: asof usage + weekly drift + short history penalty
            asof_rate = _safe_div(asof_n, total) or 0.0
            history_pen = 0.35 if len(weeks) < 4 else 0.0
            temporal_bias = _clamp01(0.55 * asof_rate + 0.30 * weekly_drift + history_pen)

            # Leak risk: asof_clamped + observed_at violations
            leak_obs_rate = _safe_div(leak_obs_n, total) or 0.0
            # asof_clamped means observation clock was forced to prediction time → research caution
            leak_risk = _clamp01(0.70 * asof_rate + 0.30 * leak_obs_rate)

            # Variance / stability
            variance_penalty = 0.0
            stability = 1.0
            if num_vals and len(num_vals) >= 5:
                mu = statistics.mean(num_vals)
                sd = statistics.pstdev(num_vals)
                cv = abs(sd / mu) if abs(mu) > 1e-9 else 0.0
                variance_penalty = _clamp01(cv / 3.0)
                if len(week_means) >= 2:
                    msd = statistics.pstdev(week_means)
                    mean_level = abs(statistics.mean(week_means)) + 1e-9
                    stability = 1.0 - _clamp01((msd / mean_level) / 2.0)
                else:
                    stability = 1.0 - 0.5 * variance_penalty
            elif cat_counts:
                # high entropy relative to log2(n_cats) => diverse; low entropy may be unstable classes
                h = _entropy(cat_counts)
                max_h = math.log2(len(cat_counts)) if len(cat_counts) > 1 else 1.0
                # neither collapse nor chaos: prefer mid-high normalized entropy
                norm = h / max_h if max_h > 0 else 0.0
                variance_penalty = _clamp01(abs(norm - 0.7) / 0.7)
                stability = 1.0 - weekly_drift
            else:
                variance_penalty = 1.0
                stability = 0.0

            # anti_leak_violations on snapshots (aggregate)
            # stored as int or json; already joined per row
            snap_viol = 0
            for r in items:
                v = r.get("anti_leak_violations")
                try:
                    snap_viol += int(v or 0)
                except (TypeError, ValueError):
                    if isinstance(v, str) and v not in {"", "[]", "0", "null"}:
                        snap_viol += 1

            metrics = {
                "feature_id": fid,
                "label": FEATURE_LABELS.get(fid, fid),
                "n_cells": total,
                "n_filled": len(filled_rows),
                "n_missing": len(missing_rows),
                "coverage": round(coverage, 4),
                "availability": round(availability, 4),
                "missing": round(missing_rate, 4),
                "missing_reasons": dict(missing_reasons.most_common(8)),
                "selection_bias": round(sel_bias, 4),
                "selection_bias_detail": sel_detail,
                "temporal_bias": round(temporal_bias, 4),
                "leak_risk": round(leak_risk, 4),
                "asof_clamped_rate": round(asof_rate, 4),
                "observed_after_prediction_rate": round(leak_obs_rate, 4),
                "variance_penalty": round(variance_penalty, 4),
                "stability": round(stability, 4),
                "weekly_drift": round(weekly_drift, 4),
                "weeks_observed": len(weeks),
                "weekly_coverage": [
                    {"date": w, "coverage": round(week_stats[w]["filled"] / week_stats[w]["total"], 4)}
                    for w in weeks
                    if week_stats[w]["total"] > 0
                ],
                "snapshot_anti_leak_violation_sum": snap_viol,
            }
            metrics["reliability_score"] = self._reliability_score(metrics)
            out.append(metrics)

        out.sort(key=lambda x: (-x["reliability_score"], x["feature_id"]))
        for i, m in enumerate(out, start=1):
            m["rank"] = i
        return out

    def reweight_archetypes(
        self, reliability: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Re-evaluate V13 archetypes with reliability weights (research only)."""
        rel_map = {m["feature_id"]: float(m["reliability_score"]) for m in reliability}
        # map rule keys to features
        rule_feature_map = {
            "popularity": "popularity",
            "win_odds": "win_odds",
            "trainer": "trainer",
            "sire": "sire",
            "damsire": "damsire",
            "breeder": "breeder",
            "oikiri_time": "oikiri_time",
            "oikiri_rating": "oikiri_rating",
            "owner": "owner",
            "sale_price": "sale_price",
        }

        # Prefer live recompute via V13 if available; else read JSON report
        archetypes: list[dict[str, Any]] = []
        try:
            from .young_horse_archetypes import YoungHorseArchetypeResearch

            v13 = YoungHorseArchetypeResearch().analyze()
            archetypes = v13.get("archetypes") or []
        except Exception:
            path = evidence_root() / "reports" / "v13-younghorse-archetypes.json"
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                archetypes = payload.get("archetypes") or []

        reweighted = []
        for a in archetypes:
            rules = a.get("rules") or {}
            feats = []
            for k in rules.keys():
                fid = rule_feature_map.get(k)
                if fid and fid in rel_map:
                    feats.append(fid)
            if not feats:
                # fallback average of all
                weights = list(rel_map.values()) or [50.0]
                mean_rel = statistics.mean(weights)
            else:
                mean_rel = statistics.mean([rel_map[f] for f in feats])
            wr = a.get("win_rate") or 0.0
            pr = a.get("place_rate") or 0.0
            roi = a.get("roi") if a.get("roi") is not None else 0.0
            base = a.get("research_rank_score")
            if base is None:
                base = 0.45 * wr + 0.25 * pr + 0.20 * max(min(roi, 2.0), -1.0) / 2.0
            w = mean_rel / 100.0
            score = round(float(base) * w, 6)
            if a.get("overfit_risk"):
                score = round(score * 0.55, 6)
            reweighted.append(
                {
                    "id": a.get("id"),
                    "label": a.get("label"),
                    "source": a.get("source"),
                    "n_horses": a.get("n_horses"),
                    "n_races": a.get("n_races"),
                    "win_rate": wr,
                    "place_rate": pr,
                    "roi": a.get("roi"),
                    "strict_rate": a.get("strict_rate"),
                    "soft_rate": a.get("soft_rate"),
                    "features_used": feats,
                    "mean_feature_reliability": round(mean_rel, 1),
                    "reliability_weight": round(w, 4),
                    "base_research_score": round(float(base), 6),
                    "reliability_weighted_score": score,
                    "overfit_risk": a.get("overfit_risk"),
                }
            )

        # Prefer stable (non-overfit) then weighted score
        reweighted.sort(
            key=lambda x: (
                0 if not x.get("overfit_risk") else 1,
                -(x.get("reliability_weighted_score") or 0.0),
                -(x.get("mean_feature_reliability") or 0.0),
                -(x.get("n_horses") or 0),
            )
        )
        for i, row in enumerate(reweighted, start=1):
            row["rank"] = i
        return {
            "count": len(reweighted),
            "top": reweighted[:25],
            "note": "Archetype scores multiplied by mean Reliability Score of involved features / 100.",
        }

    def analyze(self) -> dict[str, Any]:
        rows = self._load_rows()
        features = self.analyze_features(rows)
        archetypes = self.reweight_archetypes(features)
        n_snaps = len({r["snapshot_id"] for r in rows})
        n_races = len({r["race_id"] for r in rows})
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "shadow_only": True,
            "prediction_mutation": "FORBIDDEN",
            "resolver_mutation": "FORBIDDEN",
            "sample": {
                "feature_rows": len(rows),
                "snapshots": n_snaps,
                "races": n_races,
                "features": list(self.features),
                "exploratory": n_races < 100,
                "note": "Reliability is about Evidence trustworthiness, not win-rate effect.",
            },
            "features": features,
            "archetype_reweight": archetypes,
        }


def write_reliability_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = report.get("sample") or {}
    lines = [
        "# Version14 Research - Evidence Reliability",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** Research only / Reliability not Effect / Prediction+Resolver FORBIDDEN  ",
        "",
        "## Sample",
        "",
        f"- Feature rows: `{s.get('feature_rows')}`",
        f"- Snapshots: `{s.get('snapshots')}` / Races: `{s.get('races')}`",
        f"- Exploratory: `{s.get('exploratory')}`",
        "",
        "## Reliability Score (0-100)",
        "",
        "| Rank | Feature | Score | Coverage | Availability | Missing | SelBias | TempBias | LeakRisk | Stability | Drift |",
        "|-----:|---------|------:|---------:|-------------:|--------:|--------:|---------:|---------:|----------:|------:|",
    ]
    for m in report.get("features") or []:
        lines.append(
            f"| {m.get('rank')} | `{m.get('label')}` | {m.get('reliability_score')} | "
            f"{_pct(m.get('coverage'))} | {_pct(m.get('availability'))} | {_pct(m.get('missing'))} | "
            f"{m.get('selection_bias')} | {m.get('temporal_bias')} | {m.get('leak_risk')} | "
            f"{m.get('stability')} | {m.get('weekly_drift')} |"
        )
    lines.extend(
        [
            "",
            "## Score formula (research)",
            "",
            "```",
            "100 * (",
            "  0.22*Coverage + 0.13*Availability",
            "  + 0.15*(1-SelectionBias) + 0.10*(1-TemporalBias)",
            "  + 0.20*(1-LeakRisk) + 0.08*(1-VariancePenalty)",
            "  + 0.07*Stability + 0.05*(1-WeeklyDrift)",
            ")",
            "```",
            "",
            "## Archetype reweight (top)",
            "",
            "| Rank | Archetype | N | MeanFeatRel | Weight | WeightedScore | Win | ROI |",
            "|-----:|-----------|--:|------------:|-------:|--------------:|----:|----:|",
        ]
    )
    for a in ((report.get("archetype_reweight") or {}).get("top") or [])[:15]:
        lines.append(
            f"| {a.get('rank')} | `{a.get('label')}` | {a.get('n_horses')} | "
            f"{a.get('mean_feature_reliability')} | {a.get('reliability_weight')} | "
            f"{a.get('reliability_weighted_score')} | {_pct(a.get('win_rate'))} | "
            f"{_pct(a.get('roi')) if a.get('roi') is not None else 'N/A'} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "```",
            "Action Type: Evidence Reliability Research",
            "Prediction Mutation: FORBIDDEN",
            "Resolver Mutation: FORBIDDEN",
            "Young Horse Score: NOT CREATED",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_stability_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version14 Research - Feature Stability",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "| Feature | Stability | WeeklyDrift | Weeks | VariancePenalty | Weekly Coverage |",
        "|---------|----------:|------------:|------:|----------------:|-----------------|",
    ]
    for m in report.get("features") or []:
        weeks = ", ".join(
            f"{w.get('date')}:{_pct(w.get('coverage'))}"
            for w in (m.get("weekly_coverage") or [])[:6]
        )
        lines.append(
            f"| `{m.get('label')}` | {m.get('stability')} | {m.get('weekly_drift')} | "
            f"{m.get('weeks_observed')} | {m.get('variance_penalty')} | {weeks} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Stability high = smaller week-to-week mean/coverage movement.",
            "- With only few race dates, drift estimates are coarse (exploratory).",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_selection_bias_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version14 Research - Selection Bias & Leak Risk",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "| Feature | SelBias | LeakRisk | ASOF rate | Obs>Pred rate | Missing reasons | Detail |",
        "|---------|--------:|---------:|----------:|--------------:|-----------------|--------|",
    ]
    for m in report.get("features") or []:
        reasons = ", ".join(
            f"{k}:{v}" for k, v in (m.get("missing_reasons") or {}).items()
        )
        detail = json.dumps(m.get("selection_bias_detail") or {}, ensure_ascii=False)
        lines.append(
            f"| `{m.get('label')}` | {m.get('selection_bias')} | {m.get('leak_risk')} | "
            f"{_pct(m.get('asof_clamped_rate'))} | {_pct(m.get('observed_after_prediction_rate'))} | "
            f"{reasons} | `{detail}` |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "- **SelectionBias**: missingness or value distribution skewed by popularity strata.",
            "- **LeakRisk**: dominated by `asof_clamped` (observation clock forced to prediction time).",
            "- High ASOF rate means Evidence may be temporally softened for harvest; treat cautiously in research.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    report = EvidenceReliabilityResearch().analyze()
    root = repo_root()
    docs = root / "docs" / "research"
    write_reliability_md(report, docs / "v14-evidence-reliability.md")
    write_stability_md(report, docs / "v14-feature-stability.md")
    write_selection_bias_md(report, docs / "v14-selection-bias.md")
    json_path = evidence_root() / "reports" / "v14-evidence-reliability.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "reliability": str(docs / "v14-evidence-reliability.md"),
        "stability": str(docs / "v14-feature-stability.md"),
        "selection_bias": str(docs / "v14-selection-bias.md"),
        "json": str(json_path),
    }
    return report
