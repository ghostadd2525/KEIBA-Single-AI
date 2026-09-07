#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version10.5 Shadow Tie Resolver

Uses Version10.4 Evidence Priority as input.
Shadow only — does NOT mutate Prediction / PE / CE / AI / ResultAutomation.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .analyzer import unique_top_pick
from .config import evidence_root, repo_root
from .ranking_engine import (
    CATEGORICAL_FEATURES,
    EvidenceRankingEngine,
    cascade_resolve,
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _pct(x: float | None) -> str:
    if x is None:
        return "N/A"
    return f"{x * 100:.1f}%"


def _iso_week_id(date_text: str | None) -> str:
    if not date_text:
        return "unknown"
    dt = datetime.fromisoformat(str(date_text))
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


@dataclass
class ResolverRaceRecord:
    race_id: str
    race_date: str | None
    prediction_id: int
    tie_size: int
    winner: int
    prediction_pick: int | None
    shadow_pick: int | None
    outcome: str
    status: str
    used_feature: str | None
    used_tier: str | None
    cascade_stop: str
    prediction_winner_rank: int | None
    shadow_winner_rank: int | None
    tie_horse_numbers: list[int]
    shadow_top3: list[int]


class ShadowTieResolver:
    """Offline shadow resolver for tie races only."""

    def __init__(self) -> None:
        self.ranking = EvidenceRankingEngine()

    def load_v104_priority(self) -> dict[str, Any]:
        path = evidence_root() / "reports" / "v104-evidence-ranking.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return self.ranking.analyze()

    def _shadow_top_order(
        self,
        *,
        rec: dict[str, Any],
        fmap: dict[str, dict[str, dict[int, Any]]],
        all_races: list[dict[str, Any]],
        priority_order: list[str],
    ) -> tuple[list[int], str, str | None]:
        group = list(rec["tie_group"])
        values_by_feature = {
            fid: fmap.get(rec["snapshot_id"], {}).get(fid, {})
            for fid in priority_order
        }
        loo_priors: dict[str, dict[str, float]] = {}
        for fid in priority_order:
            if fid in CATEGORICAL_FEATURES:
                loo_priors[fid] = self.ranking.prior_for_race(
                    feature_id=fid,
                    exclude_race_id=rec["race_id"],
                    races=all_races,
                    fmap=fmap,
                )
        pick, status, used_feature = cascade_resolve(
            group,
            priority_order,
            values_by_feature,
            loo_priors,
        )
        base_order = [
            int(r["horse_number"])
            for r in sorted(
                group,
                key=lambda r: (
                    int(r.get("model_rank") or 999),
                    -float(r.get("win_prob") or 0.0),
                    int(r.get("horse_number") or 0),
                ),
            )
        ]
        if pick is None:
            return base_order, status, used_feature
        rest = [hn for hn in base_order if hn != pick]
        return [pick, *rest], status, used_feature

    @staticmethod
    def _winner_rank(order: list[int], winner: int) -> int | None:
        for i, hn in enumerate(order, start=1):
            if hn == winner:
                return i
        return None

    def analyze(self) -> dict[str, Any]:
        v104 = self.load_v104_priority()
        priority_order = list(v104.get("evidence_priority") or [])
        feature_meta = {
            str(f["feature_id"]): f for f in (v104.get("features") or [])
        }

        all_races, fmap = self.ranking.build_corpus()
        tie_races = [r for r in all_races if r["tie_size"] >= 2]

        records: list[ResolverRaceRecord] = []
        feature_usage: Counter[str] = Counter()
        tier_usage: Counter[str] = Counter()
        stop_usage: Counter[str] = Counter()

        baseline_strict = 0
        shadow_strict = 0
        resolver_win = 0
        resolver_lose = 0
        resolver_draw = 0

        for rec in tie_races:
            prediction_pick = unique_top_pick(rec["runners"])
            winner = int(rec["winner"])
            if prediction_pick == winner:
                baseline_strict += 1

            shadow_order, status, used_feature = self._shadow_top_order(
                rec=rec,
                fmap=fmap,
                all_races=all_races,
                priority_order=priority_order,
            )
            shadow_pick = shadow_order[0] if shadow_order else None
            if shadow_pick == winner:
                shadow_strict += 1

            base_ok = prediction_pick == winner
            shadow_ok = shadow_pick == winner
            if shadow_ok and not base_ok:
                outcome = "win"
                resolver_win += 1
            elif base_ok and not shadow_ok:
                outcome = "lose"
                resolver_lose += 1
            else:
                outcome = "draw"
                resolver_draw += 1

            used_tier = None
            if used_feature:
                feature_usage[used_feature] += 1
                used_tier = str((feature_meta.get(used_feature) or {}).get("tier") or "")
                if used_tier:
                    tier_usage[used_tier] += 1
            stop_label = "fallback" if not used_feature else used_feature
            stop_usage[stop_label] += 1

            tie_hns = [int(r.get("horse_number") or 0) for r in rec["tie_group"]]
            records.append(
                ResolverRaceRecord(
                    race_id=str(rec["race_id"]),
                    race_date=rec.get("race_date"),
                    prediction_id=int(rec["prediction_id"]),
                    tie_size=int(rec["tie_size"]),
                    winner=winner,
                    prediction_pick=prediction_pick,
                    shadow_pick=shadow_pick,
                    outcome=outcome,
                    status=status,
                    used_feature=used_feature,
                    used_tier=used_tier,
                    cascade_stop=stop_label,
                    prediction_winner_rank=self._winner_rank(tie_hns, winner),
                    shadow_winner_rank=self._winner_rank(shadow_order, winner),
                    tie_horse_numbers=tie_hns,
                    shadow_top3=shadow_order[:3],
                )
            )

        n_tie = len(tie_races)
        weekly: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "tie_races": 0,
                "baseline_strict": 0,
                "shadow_strict": 0,
                "resolver_win": 0,
                "resolver_lose": 0,
                "resolver_draw": 0,
            }
        )
        for row in records:
            week_id = _iso_week_id(row.race_date)
            wk = weekly[week_id]
            wk["tie_races"] += 1
            wk["baseline_strict"] += int(row.prediction_pick == row.winner)
            wk["shadow_strict"] += int(row.shadow_pick == row.winner)
            wk["resolver_win"] += int(row.outcome == "win")
            wk["resolver_lose"] += int(row.outcome == "lose")
            wk["resolver_draw"] += int(row.outcome == "draw")

        weekly_rows = []
        for week_id, meta in sorted(weekly.items()):
            tie_n = int(meta["tie_races"] or 0)
            weekly_rows.append(
                {
                    "week_id": week_id,
                    **meta,
                    "baseline_strict_rate": (
                        round(meta["baseline_strict"] / tie_n, 6) if tie_n else None
                    ),
                    "shadow_strict_rate": (
                        round(meta["shadow_strict"] / tie_n, 6) if tie_n else None
                    ),
                }
            )

        dashboard = {
            "schema_version": "expect-shadow-resolver-dashboard/1.0",
            "generated_at": _now(),
            "shadow_only": True,
            "production_applied": False,
            "summary": {
                "n_tie_races": n_tie,
                "baseline_strict_hits": baseline_strict,
                "shadow_strict_hits": shadow_strict,
                "strict_delta": shadow_strict - baseline_strict,
                "resolver_win": resolver_win,
                "resolver_lose": resolver_lose,
                "resolver_draw": resolver_draw,
                "baseline_strict_rate": round(baseline_strict / n_tie, 6) if n_tie else None,
                "shadow_strict_rate": round(shadow_strict / n_tie, 6) if n_tie else None,
            },
            "evidence_priority": [
                {
                    "priority_rank": i,
                    "feature_id": fid,
                    "tier": (feature_meta.get(fid) or {}).get("tier"),
                }
                for i, fid in enumerate(priority_order, start=1)
            ],
            "feature_usage": [
                {
                    "feature_id": fid,
                    "tier": (feature_meta.get(fid) or {}).get("tier"),
                    "used_count": int(n),
                }
                for fid, n in feature_usage.most_common()
            ],
            "tier_usage": dict(sorted(tier_usage.items())),
            "cascade_stop_usage": dict(sorted(stop_usage.items())),
            "weekly": weekly_rows,
            "recent_races": [r.__dict__ for r in records[:20]],
        }

        return {
            "schema_version": "expect-shadow-tie-resolver/1.0",
            "generated_at": dashboard["generated_at"],
            "shadow_only": True,
            "production_applied": False,
            "hard_lock": {
                "prediction": "unchanged",
                "pe": "unchanged",
                "ce": "unchanged",
                "ai": "unchanged",
                "challenge": "unchanged",
                "result_automation": "unchanged",
            },
            "corpus": {
                "n_races_all": len(all_races),
                "n_tie_races": n_tie,
            },
            "summary": dashboard["summary"],
            "v104_input": {
                "evidence_priority": priority_order,
                "tiers": v104.get("tiers"),
            },
            "resolver_records": [r.__dict__ for r in records],
            "feature_usage": dashboard["feature_usage"],
            "tier_usage": dashboard["tier_usage"],
            "cascade_stop_usage": dashboard["cascade_stop_usage"],
            "weekly": weekly_rows,
            "dashboard": dashboard,
        }


def write_shadow_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = report["summary"]
    lines = [
        "# Version10.5 Research — Shadow Tie Resolver",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Input:** Version10.4 Tier Ranking / Evidence Priority  ",
        "**重要:** Prediction順位変更禁止 / Production未反映 / Shadow only  ",
        "",
        "---",
        "",
        "## 0. Verdict",
        "",
        "| 指標 | 値 |",
        "|------|----|",
        f"| Tie races | {report['corpus'].get('n_tie_races')} |",
        f"| Baseline Strict | {s.get('baseline_strict_hits')} ({_pct(s.get('baseline_strict_rate'))}) |",
        f"| Shadow Strict | {s.get('shadow_strict_hits')} ({_pct(s.get('shadow_strict_rate'))}) |",
        f"| Strict Δ | {s.get('strict_delta'):+d} |",
        f"| Resolver Win | {s.get('resolver_win')} |",
        f"| Resolver Lose | {s.get('resolver_lose')} |",
        f"| Resolver Draw | {s.get('resolver_draw')} |",
        "",
        "## 1. Evidence Priority Input",
        "",
        "| Priority | Tier | Feature |",
        "|---------:|:----:|---------|",
    ]
    for row in report["dashboard"].get("evidence_priority") or []:
        lines.append(
            f"| {row.get('priority_rank')} | {row.get('tier')} | `{row.get('feature_id')}` |"
        )
    lines.extend(
        [
            "",
            "## 2. Race Comparison",
            "",
            "| Race | Winner | Prediction Pick | Shadow Pick | Outcome | Used Feature | Tier | Shadow Winner Rank |",
            "|------|-------:|----------------:|------------:|---------|--------------|------|-------------------:|",
        ]
    )
    for row in report.get("resolver_records") or []:
        lines.append(
            f"| `{row.get('race_id')}` | {row.get('winner')} | {row.get('prediction_pick')} | "
            f"{row.get('shadow_pick')} | {row.get('outcome')} | "
            f"{row.get('used_feature') or 'fallback'} | {row.get('used_tier') or '—'} | "
            f"{row.get('shadow_winner_rank') if row.get('shadow_winner_rank') is not None else 'N/A'} |"
        )
    lines.extend(
        [
            "",
            "## 3. Usage",
            "",
            "### Feature使用回数",
            "",
            "| Feature | Tier | Used |",
            "|---------|:----:|-----:|",
        ]
    )
    for row in report.get("feature_usage") or []:
        lines.append(
            f"| `{row.get('feature_id')}` | {row.get('tier')} | {row.get('used_count')} |"
        )
    lines.extend(
        [
            "",
            "### Tier使用回数",
            "",
            "| Tier | Used |",
            "|:----:|-----:|",
        ]
    )
    for tier, used in (report.get("tier_usage") or {}).items():
        lines.append(f"| {tier} | {used} |")
    lines.extend(
        [
            "",
            "### Cascade停止位置",
            "",
            "| Stop | Count |",
            "|------|------:|",
        ]
    )
    for stop, count in (report.get("cascade_stop_usage") or {}).items():
        lines.append(f"| `{stop}` | {count} |")
    lines.extend(
        [
            "",
            "## 4. Decision",
            "",
            "```",
            "Action Type: Shadow Tie Resolver",
            "Implementation Required: Shadow only",
            "Deployment Required: Optional research CLI / dashboard",
            "Production Required: No",
            "Prediction Mutation: FORBIDDEN",
            "Adoption Gate: Review ~6 months ROI in Version11",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_weekly_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version10.5 Research — Resolver Weekly Report",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**対象:** Tie races only / Shadow only  ",
        "",
        "| Week | Tie | Baseline Strict | Shadow Strict | Resolver Win | Lose | Draw |",
        "|------|----:|----------------:|--------------:|-------------:|-----:|-----:|",
    ]
    for row in report.get("weekly") or []:
        lines.append(
            f"| `{row.get('week_id')}` | {row.get('tie_races')} | "
            f"{row.get('baseline_strict')} ({_pct(row.get('baseline_strict_rate'))}) | "
            f"{row.get('shadow_strict')} ({_pct(row.get('shadow_strict_rate'))}) | "
            f"{row.get('resolver_win')} | {row.get('resolver_lose')} | {row.get('resolver_draw')} |"
        )
    lines.extend(
        [
            "",
            "Shadow Resolver は Prediction を書き換えず、半年程度の Evidence 蓄積後に ROI を確認して Version11 で採用可否を判断する。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_dashboard_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dash = report["dashboard"]
    s = dash["summary"]
    lines = [
        "# Version10.5 Research — Resolver Dashboard",
        "",
        f"**Generated:** {dash.get('generated_at')}  ",
        "**Ops Use:** Shadow resolver observability only  ",
        "",
        "## Summary",
        "",
        f"- Tie races: `{s.get('n_tie_races')}`",
        f"- Baseline strict: `{s.get('baseline_strict_hits')}` ({_pct(s.get('baseline_strict_rate'))})",
        f"- Shadow strict: `{s.get('shadow_strict_hits')}` ({_pct(s.get('shadow_strict_rate'))})",
        f"- Resolver Win/Lose/Draw: `{s.get('resolver_win')}` / `{s.get('resolver_lose')}` / `{s.get('resolver_draw')}`",
        "",
        "## Feature Usage",
        "",
        "| Feature | Tier | Used |",
        "|---------|:----:|-----:|",
    ]
    for row in dash.get("feature_usage") or []:
        lines.append(
            f"| `{row.get('feature_id')}` | {row.get('tier')} | {row.get('used_count')} |"
        )
    lines.extend(
        [
            "",
            "## Cascade Stop",
            "",
            "| Stop | Count |",
            "|------|------:|",
        ]
    )
    for stop, count in (dash.get("cascade_stop_usage") or {}).items():
        lines.append(f"| `{stop}` | {count} |")
    lines.extend(
        [
            "",
            "## Weekly",
            "",
            "| Week | Tie | Shadow Strict | Win | Lose | Draw |",
            "|------|----:|--------------:|----:|-----:|-----:|",
        ]
    )
    for row in dash.get("weekly") or []:
        lines.append(
            f"| `{row.get('week_id')}` | {row.get('tie_races')} | "
            f"{row.get('shadow_strict')} ({_pct(row.get('shadow_strict_rate'))}) | "
            f"{row.get('resolver_win')} | {row.get('resolver_lose')} | {row.get('resolver_draw')} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write(
    *,
    shadow_md: Path | None = None,
    weekly_md: Path | None = None,
    dashboard_md: Path | None = None,
    json_path: Path | None = None,
) -> dict[str, Any]:
    report = ShadowTieResolver().analyze()
    root = repo_root()
    shadow_md = shadow_md or (root / "docs/research/v105-shadow-resolver.md")
    weekly_md = weekly_md or (root / "docs/research/v105-resolver-weekly.md")
    dashboard_md = dashboard_md or (root / "docs/research/v105-resolver-dashboard.md")
    json_path = json_path or (evidence_root() / "reports" / "v105-shadow-resolver.json")

    write_shadow_md(report, shadow_md)
    write_weekly_md(report, weekly_md)
    write_dashboard_md(report, dashboard_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "shadow_md": str(shadow_md),
        "weekly_md": str(weekly_md),
        "dashboard_md": str(dashboard_md),
        "json": str(json_path),
    }
    return report
