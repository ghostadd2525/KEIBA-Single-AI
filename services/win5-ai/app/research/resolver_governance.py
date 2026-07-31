# -*- coding: utf-8 -*-
"""
Version10.6 Resolver Governance

Adoption gate for Version10.5 Shadow Resolver.
Shadow-only governance layer — does NOT mutate Prediction / Production.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root
from .ranking_engine import (
    CATEGORICAL_FEATURES,
    EvidenceRankingEngine,
    feature_score,
    resolve_by_score,
)
from .shadow_resolver import ShadowTieResolver

ADOPTION_GATE = {
    "min_tie_races": 100,
    "min_resolver_win_rate": 0.60,
    "max_resolver_lose_rate": 0.05,
    "min_strict_improvement_rate": 0.05,
    "min_roi_change": 0.0,
    "min_coverage": 0.95,
    "min_confidence_median": 0.70,
}

TIER_WEIGHT = {"S": 1.0, "A": 0.8, "B": 0.6, "C": 0.4}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _pct(x: float | None) -> str:
    if x is None:
        return "N/A"
    return f"{x * 100:.1f}%"


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _period_keys(date_text: str | None) -> dict[str, str]:
    if not date_text:
        return {"daily": "unknown", "weekly": "unknown", "monthly": "unknown"}
    dt = datetime.fromisoformat(str(date_text))
    iso = dt.isocalendar()
    return {
        "daily": dt.date().isoformat(),
        "weekly": f"{iso.year}-W{iso.week:02d}",
        "monthly": dt.strftime("%Y-%m"),
    }


def _distance_bucket(distance: int | None) -> str:
    d = int(distance or 0)
    if d <= 0:
        return "distance:unknown"
    if d <= 1400:
        return "distance:sprint"
    if d <= 1800:
        return "distance:mile"
    if d <= 2200:
        return "distance:middle"
    return "distance:long"


def _surface_key(surface: str | None) -> str:
    s = str(surface or "").strip()
    if "芝" in s:
        return "surface:turf"
    if "ダ" in s:
        return "surface:dirt"
    return "surface:unknown"


def _class_key(class_label: str | None) -> str:
    s = str(class_label or "").strip()
    return f"class:{s}" if s else "class:unknown"


def _age_group_key(class_label: str | None) -> str:
    s = str(class_label or "").strip()
    if "2歳新馬" in s or s == "新馬":
        return "age_group:2yo_newcomer"
    if "2歳未勝利" in s:
        return "age_group:2yo_maiden"
    if "3歳未勝利" in s:
        return "age_group:3yo_maiden"
    if any(x in s for x in ("4歳以上", "3歳以上", "古馬", "1勝クラス", "2勝クラス", "3勝クラス", "オープン", "G1", "G2", "G3", "L")):
        return "age_group:older"
    return "age_group:unknown"


def _confidence_dist(vals: list[float]) -> dict[str, float | None]:
    if not vals:
        return {"p50": None, "p75": None, "min": None, "max": None, "avg": None}
    ordered = sorted(vals)
    p75_idx = min(len(ordered) - 1, int(0.75 * (len(ordered) - 1)))
    return {
        "p50": round(float(median(ordered)), 6),
        "p75": round(float(ordered[p75_idx]), 6),
        "min": round(float(ordered[0]), 6),
        "max": round(float(ordered[-1]), 6),
        "avg": round(sum(ordered) / len(ordered), 6),
    }


class ResolverGovernance:
    def __init__(self) -> None:
        self.shadow = ShadowTieResolver()
        self.ranking = EvidenceRankingEngine()

    def _load_v104(self) -> dict[str, Any]:
        path = evidence_root() / "reports" / "v104-evidence-ranking.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return self.ranking.analyze()

    def _load_v105(self) -> dict[str, Any]:
        path = evidence_root() / "reports" / "v105-shadow-resolver.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return self.shadow.analyze()

    def _race_meta(self, race_ids: list[str]) -> dict[str, dict[str, Any]]:
        migrate()
        if not race_ids:
            return {}
        conn = connect()
        try:
            out: dict[str, dict[str, Any]] = {}
            chunk = 200
            for i in range(0, len(race_ids), chunk):
                part = race_ids[i : i + chunk]
                placeholders = ",".join("?" * len(part))
                rows = conn.execute(
                    f"""
                    SELECT
                      rr.race_id,
                      rr.race_date,
                      COALESCE(rr.venue, r.venue) AS venue,
                      COALESCE(rr.surface, r.surface) AS surface,
                      COALESCE(rr.distance, r.distance) AS distance,
                      r.class_label,
                      r.grade,
                      r.extra_json
                    FROM race_results rr
                    LEFT JOIN races r ON r.race_id = rr.race_id
                    WHERE rr.race_id IN ({placeholders})
                    """,
                    part,
                ).fetchall()
                for row in rows:
                    meta = dict(row)
                    extra = {}
                    try:
                        extra = json.loads(meta.get("extra_json") or "{}")
                    except Exception:
                        extra = {}
                    class_label = meta.get("class_label") or extra.get("class_label") or extra.get("class_name")
                    out[str(meta["race_id"])] = {
                        "race_date": meta.get("race_date"),
                        "venue": meta.get("venue"),
                        "surface": meta.get("surface"),
                        "distance": meta.get("distance"),
                        "class_label": class_label,
                        "grade": meta.get("grade") or extra.get("grade"),
                    }
            return out
        finally:
            conn.close()

    def _confidence_for_record(
        self,
        *,
        record: dict[str, Any],
        all_races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        priority_order: list[str],
        feature_meta: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        race_by_id = {str(r["race_id"]): r for r in all_races}
        rec = race_by_id.get(str(record["race_id"]))
        if not rec:
            return {
                "confidence": 0.0,
                "evidence_match_count": 0,
                "evidence_match_ratio": 0.0,
                "tier_agreement": 0.0,
                "coverage_score": 0.0,
                "missing_score": 0.0,
            }

        stop_feature = record.get("used_feature")
        stop_depth = (
            priority_order.index(stop_feature) + 1
            if stop_feature in priority_order
            else min(5, len(priority_order))
        )
        considered = priority_order[:stop_depth]
        values_by_feature = fmap.get(rec["snapshot_id"], {})
        shadow_pick = record.get("shadow_pick")

        complete_count = 0
        support_count = 0
        support_tier_weight_sum = 0.0
        coverage_vals: list[float] = []
        missing_vals: list[float] = []
        for fid in considered:
            vals = values_by_feature.get(fid, {})
            g = rec["tie_group"]
            cat_prior = None
            if fid in CATEGORICAL_FEATURES:
                cat_prior = self.ranking.prior_for_race(
                    feature_id=fid,
                    exclude_race_id=rec["race_id"],
                    races=all_races,
                    fmap=fmap,
                )
            scores = {
                int(r.get("horse_number") or 0): feature_score(
                    fid,
                    vals.get(int(r.get("horse_number") or 0)),
                    cat_prior=cat_prior,
                )
                for r in g
            }
            meta = feature_meta.get(fid) or {}
            coverage_vals.append(float(meta.get("coverage") or 0.0))
            missing_vals.append(1.0 - float(meta.get("missing_rate") or 0.0))
            if any(v is None for v in scores.values()):
                continue
            complete_count += 1
            pick, status = resolve_by_score(g, scores)
            if status == "resolved" and pick == shadow_pick:
                support_count += 1
                support_tier_weight_sum += TIER_WEIGHT.get(
                    str(meta.get("tier") or "C"), 0.4
                )

        total = max(len(considered), 1)
        evidence_match_ratio = support_count / max(complete_count, 1)
        tier_agreement = (
            support_tier_weight_sum / support_count
            if support_count
            else TIER_WEIGHT.get(str(record.get("used_tier") or "C"), 0.4)
        )
        coverage_score = sum(coverage_vals) / len(coverage_vals) if coverage_vals else 0.0
        missing_score = complete_count / total
        confidence = _clip01(
            0.45 * evidence_match_ratio
            + 0.20 * tier_agreement
            + 0.20 * coverage_score
            + 0.15 * missing_score
        )
        return {
            "confidence": round(confidence, 6),
            "evidence_match_count": support_count,
            "evidence_match_ratio": round(evidence_match_ratio, 6),
            "tier_agreement": round(tier_agreement, 6),
            "coverage_score": round(coverage_score, 6),
            "missing_score": round(missing_score, 6),
        }

    def _segment_keys(self, meta: dict[str, Any]) -> list[str]:
        keys = ["all_tie"]
        keys.append(_age_group_key(meta.get("class_label")))
        keys.append(_class_key(meta.get("class_label")))
        keys.append(_surface_key(meta.get("surface")))
        keys.append(_distance_bucket(meta.get("distance")))
        venue = str(meta.get("venue") or "").strip()
        keys.append(f"venue:{venue}" if venue else "venue:unknown")
        return keys

    def _gate_eval(self, summary: dict[str, Any]) -> dict[str, Any]:
        tie_n = int(summary.get("tie_races") or 0)
        win_rate = float(summary.get("resolver_win_rate") or 0.0)
        lose_rate = float(summary.get("resolver_lose_rate") or 0.0)
        strict_imp = float(summary.get("strict_improvement_rate") or 0.0)
        roi_change = float(summary.get("roi_change") or 0.0)
        coverage = float(summary.get("coverage_avg") or 0.0)
        conf_median = float((summary.get("confidence_distribution") or {}).get("p50") or 0.0)

        checks = {
            "tie_races": tie_n >= ADOPTION_GATE["min_tie_races"],
            "resolver_win_rate": win_rate >= ADOPTION_GATE["min_resolver_win_rate"],
            "resolver_lose_rate": lose_rate <= ADOPTION_GATE["max_resolver_lose_rate"],
            "strict_improvement_rate": strict_imp >= ADOPTION_GATE["min_strict_improvement_rate"],
            "roi_change": roi_change >= ADOPTION_GATE["min_roi_change"],
            "coverage_avg": coverage >= ADOPTION_GATE["min_coverage"],
            "confidence_median": conf_median >= ADOPTION_GATE["min_confidence_median"],
        }
        if tie_n < ADOPTION_GATE["min_tie_races"]:
            status = "sample_insufficient"
        elif all(checks.values()):
            status = "eligible"
        elif (
            lose_rate > ADOPTION_GATE["max_resolver_lose_rate"]
            or roi_change < ADOPTION_GATE["min_roi_change"]
        ):
            status = "rejected"
        else:
            status = "watching"

        progress = {
            "tie_races": round(min(tie_n / ADOPTION_GATE["min_tie_races"], 1.0), 6),
            "resolver_win_rate": round(min(win_rate / ADOPTION_GATE["min_resolver_win_rate"], 1.0), 6)
            if ADOPTION_GATE["min_resolver_win_rate"] > 0
            else 1.0,
            "resolver_lose_rate": round(
                min(
                    ADOPTION_GATE["max_resolver_lose_rate"] / max(lose_rate, 1e-9),
                    1.0,
                ),
                6,
            ),
            "strict_improvement_rate": round(
                min(strict_imp / ADOPTION_GATE["min_strict_improvement_rate"], 1.0), 6
            )
            if ADOPTION_GATE["min_strict_improvement_rate"] > 0
            else 1.0,
            "coverage_avg": round(min(coverage / ADOPTION_GATE["min_coverage"], 1.0), 6)
            if ADOPTION_GATE["min_coverage"] > 0
            else 1.0,
            "confidence_median": round(
                min(conf_median / ADOPTION_GATE["min_confidence_median"], 1.0), 6
            )
            if ADOPTION_GATE["min_confidence_median"] > 0
            else 1.0,
        }
        return {"status": status, "checks": checks, "progress": progress}

    def _summarize(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(rows)
        baseline = sum(1 for r in rows if r.get("prediction_pick") == r.get("winner"))
        shadow = sum(1 for r in rows if r.get("shadow_pick") == r.get("winner"))
        wins = sum(1 for r in rows if r.get("outcome") == "win")
        loses = sum(1 for r in rows if r.get("outcome") == "lose")
        draws = sum(1 for r in rows if r.get("outcome") == "draw")
        confidences = [float(r.get("confidence") or 0.0) for r in rows]
        feature_usage = Counter(
            str(r.get("used_feature") or "fallback") for r in rows
        )
        tier_usage = Counter(str(r.get("used_tier") or "fallback") for r in rows)
        stop_usage = Counter(str(r.get("cascade_stop") or "fallback") for r in rows)
        coverage_vals = [float(r.get("coverage_score") or 0.0) for r in rows]
        used_feature_coverage = [
            float(r.get("used_feature_coverage") or 0.0)
            for r in rows
            if r.get("used_feature_coverage") is not None
        ]

        summary = {
            "tie_races": n,
            "resolver_win": wins,
            "resolver_lose": loses,
            "resolver_draw": draws,
            "resolver_win_rate": round(wins / n, 6) if n else None,
            "resolver_lose_rate": round(loses / n, 6) if n else None,
            "resolver_draw_rate": round(draws / n, 6) if n else None,
            "baseline_strict_hits": baseline,
            "shadow_strict_hits": shadow,
            "strict_improvement": shadow - baseline,
            "strict_improvement_rate": round((shadow - baseline) / n, 6) if n else None,
            "soft_improvement_rate": 0.0,
            "roi_change": round((shadow - baseline) / n, 6) if n else None,
            "feature_usage_rate": {
                k: round(v / n, 6) for k, v in feature_usage.items()
            } if n else {},
            "tier_usage_rate": {
                k: round(v / n, 6) for k, v in tier_usage.items()
            } if n else {},
            "cascade_stop_rate": {
                k: round(v / n, 6) for k, v in stop_usage.items()
            } if n else {},
            "feature_usage_count": dict(feature_usage),
            "tier_usage_count": dict(tier_usage),
            "cascade_stop_count": dict(stop_usage),
            "coverage_avg": round(sum(coverage_vals) / len(coverage_vals), 6) if coverage_vals else None,
            "used_feature_coverage_avg": round(sum(used_feature_coverage) / len(used_feature_coverage), 6)
            if used_feature_coverage
            else None,
            "confidence_distribution": _confidence_dist(confidences),
        }
        summary["gate"] = self._gate_eval(summary)
        return summary

    def analyze(self) -> dict[str, Any]:
        v104 = self._load_v104()
        v105 = self._load_v105()
        all_races, fmap = self.ranking.build_corpus()
        priority_order = list(v104.get("evidence_priority") or [])
        feature_meta = {
            str(f["feature_id"]): f for f in (v104.get("features") or [])
        }
        race_meta = self._race_meta([str(r.get("race_id")) for r in (v105.get("resolver_records") or [])])

        records: list[dict[str, Any]] = []
        by_period: dict[str, dict[str, list[dict[str, Any]]]] = {
            "daily": defaultdict(list),
            "weekly": defaultdict(list),
            "monthly": defaultdict(list),
            "cumulative": {"all": []},
        }
        by_segment: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in v105.get("resolver_records") or []:
            meta = race_meta.get(str(row.get("race_id")), {})
            conf = self._confidence_for_record(
                record=row,
                all_races=all_races,
                fmap=fmap,
                priority_order=priority_order,
                feature_meta=feature_meta,
            )
            used_meta = feature_meta.get(str(row.get("used_feature") or "")) or {}
            enriched = {
                **row,
                **meta,
                **conf,
                "used_feature_coverage": used_meta.get("coverage"),
                "used_feature_missing_rate": used_meta.get("missing_rate"),
                "used_feature_priority_rank": (
                    priority_order.index(row["used_feature"]) + 1
                    if row.get("used_feature") in priority_order
                    else None
                ),
            }
            records.append(enriched)
            p = _period_keys(meta.get("race_date") or row.get("race_date"))
            by_period["daily"][p["daily"]].append(enriched)
            by_period["weekly"][p["weekly"]].append(enriched)
            by_period["monthly"][p["monthly"]].append(enriched)
            by_period["cumulative"]["all"].append(enriched)
            for key in self._segment_keys(meta):
                by_segment[key].append(enriched)

        cumulative = self._summarize(records)
        segment_rows = []
        for key, items in sorted(by_segment.items()):
            segment_rows.append(
                {"segment": key, **self._summarize(items)}
            )

        period_rows = {}
        for period in ("daily", "weekly", "monthly"):
            period_rows[period] = [
                {"period_key": key, **self._summarize(items)}
                for key, items in sorted(by_period[period].items())
            ]

        dashboard = {
            "schema_version": "expect-resolver-governance-dashboard/1.0",
            "generated_at": _now(),
            "current_status": cumulative["gate"]["status"],
            "eligible": cumulative["gate"]["status"] == "eligible",
            "watching": cumulative["gate"]["status"] == "watching",
            "rejected": cumulative["gate"]["status"] == "rejected",
            "sample_insufficient": cumulative["gate"]["status"] == "sample_insufficient",
            "confidence": cumulative["confidence_distribution"],
            "progress": cumulative["gate"]["progress"],
            "summary": cumulative,
            "top_segments": segment_rows[:12],
        }

        return {
            "schema_version": "expect-resolver-governance/1.0",
            "generated_at": dashboard["generated_at"],
            "shadow_only": True,
            "production_prediction": "unchanged",
            "adoption_gate": ADOPTION_GATE,
            "v104_input": {
                "evidence_priority": priority_order,
                "tiers": v104.get("tiers"),
            },
            "v105_summary": v105.get("summary"),
            "cumulative": cumulative,
            "segments": segment_rows,
            "periods": period_rows,
            "records": records,
            "dashboard": dashboard,
        }


def write_governance_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = report["cumulative"]
    gate = c["gate"]
    lines = [
        "# Version10.6 Research — Resolver Governance",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Purpose:** Shadow Resolver の Production 採用可否を自動判定  ",
        "**重要:** Prediction順位変更禁止 / ResolverはShadowのみ / Production反映禁止  ",
        "",
        "## 0. Current Status",
        "",
        f"- Current Status: `{gate.get('status')}`",
        f"- Eligible: `{gate.get('status') == 'eligible'}`",
        f"- Confidence Median: `{c['confidence_distribution'].get('p50')}`",
        "",
        "| 指標 | 値 |",
        "|------|----|",
        f"| Tie races | {c.get('tie_races')} |",
        f"| Resolver Win / Lose / Draw | {c.get('resolver_win')} / {c.get('resolver_lose')} / {c.get('resolver_draw')} |",
        f"| Strict Improvement | {c.get('strict_improvement')} ({_pct(c.get('strict_improvement_rate'))}) |",
        f"| ROI Change | {_pct(c.get('roi_change'))} |",
        f"| Coverage Avg | {_pct(c.get('coverage_avg'))} |",
        f"| Confidence Median | {_pct(c['confidence_distribution'].get('p50'))} |",
        "",
        "## 1. Gate 判定",
        "",
        "| Gate | Threshold | Actual | Pass |",
        "|------|-----------|--------|------|",
        f"| Tie races | >= {report['adoption_gate']['min_tie_races']} | {c.get('tie_races')} | {gate['checks']['tie_races']} |",
        f"| Resolver Win Rate | >= {_pct(report['adoption_gate']['min_resolver_win_rate'])} | {_pct(c.get('resolver_win_rate'))} | {gate['checks']['resolver_win_rate']} |",
        f"| Resolver Lose Rate | <= {_pct(report['adoption_gate']['max_resolver_lose_rate'])} | {_pct(c.get('resolver_lose_rate'))} | {gate['checks']['resolver_lose_rate']} |",
        f"| Strict Improvement | >= {_pct(report['adoption_gate']['min_strict_improvement_rate'])} | {_pct(c.get('strict_improvement_rate'))} | {gate['checks']['strict_improvement_rate']} |",
        f"| ROI Change | >= {_pct(report['adoption_gate']['min_roi_change'])} | {_pct(c.get('roi_change'))} | {gate['checks']['roi_change']} |",
        f"| Coverage | >= {_pct(report['adoption_gate']['min_coverage'])} | {_pct(c.get('coverage_avg'))} | {gate['checks']['coverage_avg']} |",
        f"| Confidence Median | >= {_pct(report['adoption_gate']['min_confidence_median'])} | {_pct(c['confidence_distribution'].get('p50'))} | {gate['checks']['confidence_median']} |",
        "",
        "## 2. Segment Snapshot",
        "",
        "| Segment | Tie | Status | Win | Lose | StrictΔ | Confidence p50 |",
        "|---------|----:|--------|----:|-----:|--------:|---------------:|",
    ]
    for row in report.get("segments")[:20]:
        lines.append(
            f"| `{row.get('segment')}` | {row.get('tie_races')} | {row['gate']['status']} | "
            f"{row.get('resolver_win')} | {row.get('resolver_lose')} | {row.get('strict_improvement')} | "
            f"{row['confidence_distribution'].get('p50') if row['confidence_distribution'].get('p50') is not None else 'N/A'} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_gate_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version10.6 Research — Adoption Gate",
        "",
        "## Production採用条件",
        "",
        "| Gate | Threshold |",
        "|------|-----------|",
    ]
    for k, v in report.get("adoption_gate", {}).items():
        disp = _pct(v) if isinstance(v, float) and 0 <= v <= 1 else v
        lines.append(f"| `{k}` | {disp} |")
    lines.extend(
        [
            "",
            "## Status Rules",
            "",
            "- `eligible`: すべての Gate を満たす",
            "- `sample_insufficient`: Tie sample が閾値未満",
            "- `rejected`: Lose rate 超過 または ROI悪化",
            "- `watching`: 上記以外",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_confidence_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = report["cumulative"]["confidence_distribution"]
    lines = [
        "# Version10.6 Research — Confidence Model",
        "",
        "Confidence は 0〜1 で算出し、以下を合成する。",
        "",
        "- Evidence一致数: considered features のうち Shadow pick を支持した割合",
        "- Tier一致: 支持 feature の Tier weight（S=1.0, A=0.8, B=0.6, C=0.4）",
        "- Coverage: V10.4 feature coverage の平均",
        "- Missing: 当該 tie race で complete に評価できた feature 比率",
        "",
        "式:",
        "",
        "```",
        "confidence = 0.45*evidence_match_ratio + 0.20*tier_agreement + 0.20*coverage_score + 0.15*missing_score",
        "```",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| p50 | {c.get('p50')} |",
        f"| p75 | {c.get('p75')} |",
        f"| min | {c.get('min')} |",
        f"| max | {c.get('max')} |",
        f"| avg | {c.get('avg')} |",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_weekly_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version10.6 Research — Weekly Governance",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "| Week | Tie | Status | Win | Lose | Draw | StrictΔ | Coverage | Confidence p50 |",
        "|------|----:|--------|----:|-----:|-----:|--------:|---------:|---------------:|",
    ]
    for row in report.get("periods", {}).get("weekly", []):
        lines.append(
            f"| `{row.get('period_key')}` | {row.get('tie_races')} | {row['gate']['status']} | "
            f"{row.get('resolver_win')} | {row.get('resolver_lose')} | {row.get('resolver_draw')} | "
            f"{row.get('strict_improvement')} | {_pct(row.get('coverage_avg'))} | "
            f"{_pct(row['confidence_distribution'].get('p50'))} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write(
    *,
    governance_md: Path | None = None,
    gate_md: Path | None = None,
    confidence_md: Path | None = None,
    weekly_md: Path | None = None,
    json_path: Path | None = None,
) -> dict[str, Any]:
    report = ResolverGovernance().analyze()
    root = repo_root()
    governance_md = governance_md or (root / "docs/research/v106-resolver-governance.md")
    gate_md = gate_md or (root / "docs/research/v106-adoption-gate.md")
    confidence_md = confidence_md or (root / "docs/research/v106-confidence-model.md")
    weekly_md = weekly_md or (root / "docs/research/v106-weekly-governance.md")
    json_path = json_path or (evidence_root() / "reports" / "v106-resolver-governance.json")

    write_governance_md(report, governance_md)
    write_gate_md(report, gate_md)
    write_confidence_md(report, confidence_md)
    write_weekly_md(report, weekly_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "governance_md": str(governance_md),
        "gate_md": str(gate_md),
        "confidence_md": str(confidence_md),
        "weekly_md": str(weekly_md),
        "json": str(json_path),
    }
    return report
