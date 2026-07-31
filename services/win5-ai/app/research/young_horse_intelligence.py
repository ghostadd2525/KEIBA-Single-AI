# -*- coding: utf-8 -*-
"""
Version12 Young Horse Intelligence Research

Research-only analysis for debut / young-horse races.
Does NOT mutate Prediction / PE / CE / AI / Challenge / ResultAutomation.
Does NOT create Young Horse Score.
Does NOT change Tie Resolver.
"""
from __future__ import annotations

import itertools
import json
import math
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
from .ranking_engine import (
    CATEGORICAL_FEATURES,
    cascade_resolve,
    feature_score,
    resolve_by_score,
)

SCHEMA_VERSION = "expect-younghorse-intelligence/1.0"

V12_FEATURES: tuple[str, ...] = (
    "popularity",
    "win_odds",
    "trainer",
    "sire",
    "damsire",
    "breeder",
    "oikiri_time",
    "oikiri_rating",
)

YOUNG_AGE_GROUPS = frozenset(
    {
        "2yo_newcomer",
        "2yo_maiden",
        "2yo_other",
        "3yo_maiden",
        "3yo_other",
    }
)

DEBUT_AGE_GROUPS = frozenset({"2yo_newcomer"})


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _pct(x: float | None, digits: int = 1) -> str:
    if x is None:
        return "N/A"
    return f"{x * 100:.{digits}f}%"


def _safe_div(a: float, b: float) -> float | None:
    if b <= 0:
        return None
    return a / b


def _laplace_prior(
    wins: dict[str, int], apps: dict[str, int]
) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, n in apps.items():
        w = wins.get(k, 0)
        out[k] = (w + 1.0) / (n + 2.0)
    return out


class YoungHorseIntelligence:
    """Offline Young Horse feature / interaction research."""

    def __init__(self, features: tuple[str, ...] = V12_FEATURES) -> None:
        migrate()
        self.features = features
        self.analyzer = EvidenceAnalyzer(features=features)

    def load_young_corpus(self) -> list[dict[str, Any]]:
        """
        Young Horse races with complete Evidence snapshot + Prediction Bundle + Winner.
        Read-only; does not rebuild corpus.
        """
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT
                  c.corpus_id,
                  c.race_id,
                  c.race_date,
                  c.venue,
                  c.surface,
                  c.distance,
                  c.class_label,
                  c.age_group,
                  c.is_tie,
                  c.tie_size,
                  c.winner_horse_number,
                  c.prediction_pick,
                  c.source,
                  c.prediction_id,
                  s.snapshot_id,
                  s.capture_status,
                  s.field_coverage,
                  p.bundle_json
                FROM research_prediction_corpus c
                JOIN research_prediction_snapshots s
                  ON s.race_id = c.race_id
                 AND s.capture_status = 'complete'
                JOIN predictions p ON p.id = s.prediction_id
                WHERE c.is_young_horse = 1
                  AND c.winner_horse_number IS NOT NULL
                  AND c.race_id NOT LIKE '2099%'
                  AND c.age_group IN ('2yo_newcomer','2yo_maiden','2yo_other','3yo_maiden','3yo_other')
                ORDER BY c.race_date ASC, c.race_id ASC
                """
            ).fetchall()
            # de-dupe by race_id (prefer earliest snapshot via ORDER + first)
            seen: set[str] = set()
            out: list[dict[str, Any]] = []
            for r in rows:
                rid = str(r["race_id"])
                if rid in seen:
                    continue
                seen.add(rid)
                out.append(dict(r))
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
            snap = str(race["snapshot_id"])
            winner = int(race["winner_horse_number"])
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

    def analyze(self) -> dict[str, Any]:
        races = self.load_young_corpus()
        snap_ids = [str(r["snapshot_id"]) for r in races]
        fmap = self.analyzer.load_feature_map(snap_ids)

        n = len(races)
        by_age = Counter(str(r.get("age_group") or "unknown") for r in races)
        debut_n = sum(1 for r in races if r.get("age_group") in DEBUT_AGE_GROUPS)

        baseline_strict = 0
        baseline_soft = 0
        tie_ge2 = 0
        race_records: list[dict[str, Any]] = []

        # per-feature accumulators
        solo: dict[str, dict[str, Any]] = {
            f: {
                "feature_id": f,
                "field_resolved": 0,
                "field_correct": 0,
                "field_missing": 0,
                "tie_eligible": 0,
                "tie_resolved": 0,
                "tie_correct_strict": 0,
                "tie_soft_hit_after": 0,
                "ig_sum": 0.0,
                "ig_n": 0,
                "winner_is_feature_best_field": 0,
                "coverage_cells": 0,
                "coverage_filled": 0,
            }
            for f in self.features
        }

        # pairwise interaction on tie groups
        pairs = list(itertools.combinations(self.features, 2))
        pair_stats: dict[tuple[str, str], dict[str, Any]] = {
            p: {
                "features": list(p),
                "tie_eligible": 0,
                "cascade_resolved": 0,
                "cascade_correct": 0,
                "solo_a_correct": 0,
                "solo_b_correct": 0,
                "lift_vs_best_solo": 0,
                "ig_sum": 0.0,
                "ig_n": 0,
            }
            for p in pairs
        }

        for idx, row in enumerate(races):
            bundle = {}
            try:
                bundle = json.loads(row.get("bundle_json") or "{}")
            except Exception:
                bundle = {}
            runners = extract_runners(bundle)
            if not runners:
                continue
            winner = int(row["winner_horse_number"])
            g = tie_group(runners)
            base_strict = strict_hit(runners, winner)
            base_soft = soft_hit(runners, winner)
            if base_strict:
                baseline_strict += 1
            if base_soft:
                baseline_soft += 1
            if len(g) >= 2:
                tie_ge2 += 1

            snap = str(row["snapshot_id"])
            feat_maps = fmap.get(snap) or {}

            race_feat: dict[str, Any] = {}
            for fid in self.features:
                values = feat_maps.get(fid) or {}
                # coverage
                for r in runners:
                    hn = int(r.get("horse_number") or 0)
                    solo[fid]["coverage_cells"] += 1
                    if values.get(hn) is not None and str(values.get(hn)) not in {
                        "",
                        "-",
                        "null",
                        "None",
                    }:
                        solo[fid]["coverage_filled"] += 1

                cat_prior = None
                if fid in CATEGORICAL_FEATURES:
                    cat_prior = self._cat_priors_loo(races, fmap, idx, fid)

                # Field-level: feature-best among all runners
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
                        solo[fid]["winner_is_feature_best_field"] += 1

                # Tie-level (Soft/Strict/IG) when |G|>=2
                tie_pick = None
                tie_status = "skip"
                ig = 0.0
                if len(g) >= 2:
                    solo[fid]["tie_eligible"] += 1
                    tie_pick, tie_status = self._pick_by_feature(
                        feature_id=fid,
                        runners=runners,
                        values=values,
                        cat_prior=cat_prior,
                        group=g,
                    )
                    if tie_status == "resolved":
                        solo[fid]["tie_resolved"] += 1
                        ig = _ig_bits(len(g), True)
                        solo[fid]["ig_sum"] += ig
                        solo[fid]["ig_n"] += 1
                        if tie_pick == winner:
                            solo[fid]["tie_correct_strict"] += 1
                        # soft after resolve: winner in G already; strict is the gain
                        if base_soft:
                            solo[fid]["tie_soft_hit_after"] += 1
                    elif tie_status == "unresolved_tie":
                        # remaining unknown; approximate no IG
                        solo[fid]["ig_n"] += 1

                race_feat[fid] = {
                    "field_pick": pick,
                    "field_status": status,
                    "tie_pick": tie_pick,
                    "tie_status": tie_status,
                    "ig": ig,
                }

            # Pairwise cascade on tie groups
            if len(g) >= 2:
                values_by_feature = {
                    fid: (feat_maps.get(fid) or {}) for fid in self.features
                }
                cat_priors = {
                    fid: self._cat_priors_loo(races, fmap, idx, fid)
                    for fid in self.features
                    if fid in CATEGORICAL_FEATURES
                }
                for a, b in pairs:
                    st = pair_stats[(a, b)]
                    st["tie_eligible"] += 1
                    # solo correctness for lift
                    pa = race_feat[a]["tie_pick"]
                    pb = race_feat[b]["tie_pick"]
                    if race_feat[a]["tie_status"] == "resolved" and pa == winner:
                        st["solo_a_correct"] += 1
                    if race_feat[b]["tie_status"] == "resolved" and pb == winner:
                        st["solo_b_correct"] += 1
                    pick, status, used = cascade_resolve(
                        g,
                        [a, b],
                        values_by_feature,
                        cat_priors,
                    )
                    if status == "resolved":
                        st["cascade_resolved"] += 1
                        st["ig_sum"] += _ig_bits(len(g), True)
                        st["ig_n"] += 1
                        if pick == winner:
                            st["cascade_correct"] += 1

            race_records.append(
                {
                    "race_id": row["race_id"],
                    "age_group": row.get("age_group"),
                    "class_label": row.get("class_label"),
                    "venue": row.get("venue"),
                    "winner": winner,
                    "baseline_strict": base_strict,
                    "baseline_soft": base_soft,
                    "tie_size": len(g),
                    "features": race_feat,
                }
            )

        # finalize solo metrics
        solo_rows = []
        for fid, s in solo.items():
            field_n = s["field_resolved"]
            tie_n = s["tie_eligible"]
            row = {
                **s,
                "coverage": _safe_div(s["coverage_filled"], s["coverage_cells"]),
                "field_win_rate": _safe_div(s["field_correct"], field_n),
                "tie_resolve_rate": _safe_div(s["tie_resolved"], tie_n),
                "tie_strict_win_rate": _safe_div(
                    s["tie_correct_strict"], s["tie_resolved"]
                ),
                "avg_ig": _safe_div(s["ig_sum"], s["ig_n"]) if s["ig_n"] else None,
                "soft_to_strict_recovery": _safe_div(
                    s["tie_correct_strict"], max(s["tie_soft_hit_after"], 1)
                )
                if s["tie_soft_hit_after"]
                else _safe_div(s["tie_correct_strict"], s["tie_resolved"]),
            }
            # research ranking score (NOT product Young Horse Score)
            # exploratory composite for ordering docs only
            cov = row["coverage"] or 0.0
            fwr = row["field_win_rate"] or 0.0
            trr = row["tie_resolve_rate"] or 0.0
            twr = row["tie_strict_win_rate"] or 0.0
            ig = row["avg_ig"] or 0.0
            row["research_rank_score"] = round(
                0.30 * fwr + 0.25 * twr + 0.20 * trr + 0.15 * ig / 3.0 + 0.10 * cov,
                6,
            )
            solo_rows.append(row)
        solo_rows.sort(
            key=lambda r: (
                -(r.get("research_rank_score") or 0.0),
                -(r.get("field_win_rate") or 0.0),
                -(r.get("coverage") or 0.0),
            )
        )
        for i, r in enumerate(solo_rows, start=1):
            r["rank"] = i

        # finalize pairs
        pair_rows = []
        for (a, b), st in pair_stats.items():
            best_solo = max(st["solo_a_correct"], st["solo_b_correct"])
            lift = st["cascade_correct"] - best_solo
            pair_rows.append(
                {
                    **st,
                    "cascade_resolve_rate": _safe_div(
                        st["cascade_resolved"], st["tie_eligible"]
                    ),
                    "cascade_win_rate": _safe_div(
                        st["cascade_correct"], st["cascade_resolved"]
                    ),
                    "lift_vs_best_solo": lift,
                    "avg_ig": _safe_div(st["ig_sum"], st["ig_n"])
                    if st["ig_n"]
                    else None,
                }
            )
        pair_rows.sort(
            key=lambda r: (
                -(r.get("lift_vs_best_solo") or -999),
                -(r.get("cascade_win_rate") or 0.0),
                -(r.get("cascade_resolve_rate") or 0.0),
            )
        )

        # debut-only slice summary
        debut_records = [
            r for r in race_records if r.get("age_group") in DEBUT_AGE_GROUPS
        ]

        report = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "shadow_only": True,
            "young_horse_score": "NOT_CREATED",
            "prediction_mutation": "FORBIDDEN",
            "resolver_mutation": "FORBIDDEN",
            "sample": {
                "young_races_with_evidence": n,
                "debut_2yo_newcomer": debut_n,
                "by_age": dict(by_age),
                "baseline_strict_hits": baseline_strict,
                "baseline_soft_hits": baseline_soft,
                "baseline_strict_rate": _safe_div(baseline_strict, n),
                "baseline_soft_rate": _safe_div(baseline_soft, n),
                "tie_races_ge2": tie_ge2,
                "exploratory": n < 100,
                "note": "Low sample; treat as exploratory research, not adoption gate.",
            },
            "features": self.features,
            "solo": solo_rows,
            "interactions": pair_rows[:40],
            "ranking": [
                {
                    "rank": r["rank"],
                    "feature_id": r["feature_id"],
                    "research_rank_score": r["research_rank_score"],
                    "field_win_rate": r["field_win_rate"],
                    "tie_resolve_rate": r["tie_resolve_rate"],
                    "tie_strict_win_rate": r["tie_strict_win_rate"],
                    "avg_ig": r["avg_ig"],
                    "coverage": r["coverage"],
                }
                for r in solo_rows
            ],
            "debut_sample_size": len(debut_records),
            "race_records": race_records,
        }
        return report


def write_feature_analysis_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = report.get("sample") or {}
    lines = [
        "# Version12 Research - Young Horse Feature Analysis",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** Research only / Prediction mutation FORBIDDEN / No Young Horse Score  ",
        "",
        "## Sample",
        "",
        f"- Young races with Evidence: `{s.get('young_races_with_evidence')}`",
        f"- 2歳新馬 (debut): `{s.get('debut_2yo_newcomer')}`",
        f"- Baseline Strict: `{s.get('baseline_strict_hits')}` ({_pct(s.get('baseline_strict_rate'))})",
        f"- Baseline Soft: `{s.get('baseline_soft_hits')}` ({_pct(s.get('baseline_soft_rate'))})",
        f"- Tie races (|G|>=2): `{s.get('tie_races_ge2')}`",
        f"- Exploratory: `{s.get('exploratory')}`",
        "",
        "### Age breakdown",
        "",
        "| Age | Count |",
        "|-----|------:|",
    ]
    for k, v in (s.get("by_age") or {}).items():
        lines.append(f"| `{k}` | {v} |")
    lines.extend(
        [
            "",
            "## Solo Feature Effects",
            "",
            "| Feature | Coverage | Field WinRate | Tie Resolve | Tie StrictWR | Avg IG |",
            "|---------|---------:|--------------:|------------:|-------------:|-------:|",
        ]
    )
    for r in report.get("solo") or []:
        lines.append(
            f"| `{r['feature_id']}` | {_pct(r.get('coverage'))} | {_pct(r.get('field_win_rate'))} | "
            f"{_pct(r.get('tie_resolve_rate'))} | {_pct(r.get('tie_strict_win_rate'))} | "
            f"{(r.get('avg_ig') if r.get('avg_ig') is not None else 'N/A')} |"
        )
    lines.extend(
        [
            "",
            "## Definitions",
            "",
            "- **Field WinRate**: feature-best horse among full field equals Winner",
            "- **Tie Resolve**: unique pick inside model_rank tie group G",
            "- **Tie StrictWR**: resolved pick equals Winner",
            "- **IG**: information gain vs uniform pick in G (bits)",
            "- Categoricals use leave-one-out Laplace prior (research shadow only)",
            "",
            "## Decision",
            "",
            "```",
            "Action Type: Young Horse Intelligence Research",
            "Young Horse Score: NOT CREATED",
            "Prediction Mutation: FORBIDDEN",
            "Resolver Mutation: FORBIDDEN",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_interactions_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version12 Research - Young Horse Feature Interactions",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** Research only / cascade pairs on Tie groups  ",
        "",
        "## Pairwise Cascade (top)",
        "",
        "| A | B | Tie N | ResolveRate | CascadeWR | Lift vs best solo | Avg IG |",
        "|---|---|------:|------------:|----------:|------------------:|-------:|",
    ]
    for r in (report.get("interactions") or [])[:25]:
        feats = r.get("features") or ["?", "?"]
        lines.append(
            f"| `{feats[0]}` | `{feats[1]}` | {r.get('tie_eligible')} | "
            f"{_pct(r.get('cascade_resolve_rate'))} | {_pct(r.get('cascade_win_rate'))} | "
            f"{r.get('lift_vs_best_solo')} | {r.get('avg_ig') if r.get('avg_ig') is not None else 'N/A'} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "- Cascade applies A then B inside Tie group G.",
            "- Lift = cascade_correct - max(solo_A_correct, solo_B_correct).",
            "- Positive lift suggests complementary interaction (exploratory at low N).",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_ranking_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version12 Research - Young Horse Feature Ranking",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**IMPORTANT:** This is a research ordering only. **No Young Horse Score is produced.**  ",
        "",
        "## Ranking",
        "",
        "| Rank | Feature | ResearchScore | FieldWR | TieResolve | TieStrictWR | IG | Coverage |",
        "|-----:|---------|--------------:|--------:|-----------:|------------:|---:|---------:|",
    ]
    for r in report.get("ranking") or []:
        lines.append(
            f"| {r.get('rank')} | `{r.get('feature_id')}` | {r.get('research_rank_score')} | "
            f"{_pct(r.get('field_win_rate'))} | {_pct(r.get('tie_resolve_rate'))} | "
            f"{_pct(r.get('tie_strict_win_rate'))} | "
            f"{r.get('avg_ig') if r.get('avg_ig') is not None else 'N/A'} | "
            f"{_pct(r.get('coverage'))} |"
        )
    lines.extend(
        [
            "",
            "## Composite (docs ordering only)",
            "",
            "```",
            "0.30*FieldWR + 0.25*TieStrictWR + 0.20*TieResolve + 0.15*(IG/3) + 0.10*Coverage",
            "```",
            "",
            "Not an adoption gate. Not a product score. Not wired into Prediction.",
            "",
            f"Sample size: `{(report.get('sample') or {}).get('young_races_with_evidence')}` "
            f"(exploratory={(report.get('sample') or {}).get('exploratory')})",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    report = YoungHorseIntelligence().analyze()
    root = repo_root()
    docs = root / "docs" / "research"
    write_feature_analysis_md(report, docs / "v12-younghorse-feature-analysis.md")
    write_interactions_md(report, docs / "v12-younghorse-interactions.md")
    write_ranking_md(report, docs / "v12-younghorse-ranking.md")

    # strip bulky race_records from markdown path already done; keep in JSON
    json_path = evidence_root() / "reports" / "v12-younghorse-intelligence.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    report["_outputs"] = {
        "feature_analysis": str(docs / "v12-younghorse-feature-analysis.md"),
        "interactions": str(docs / "v12-younghorse-interactions.md"),
        "ranking": str(docs / "v12-younghorse-ranking.md"),
        "json": str(json_path),
    }
    return report
