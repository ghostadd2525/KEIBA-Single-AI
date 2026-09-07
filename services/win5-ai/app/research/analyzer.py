# -*- coding: utf-8 -*-
"""
Version10.2 Evidence Analyzer

Shadow evaluation only — does NOT mutate Prediction / PE / CE / AI scores.
Reads research_prediction_snapshots + research_snapshot_features (+ predictions, race_results).
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .config import repo_root

# Features requested by V10.2 / V10.3 analyzer
V102_FEATURES: tuple[str, ...] = (
    "popularity",
    "win_odds",
    "expected_popularity",
    "trainer",
    "sire",
    "damsire",
    "breeder",
    "owner",
    "oikiri_time",
    "oikiri_rating",
)

# Ordinal features: lower rank_key is better (picked first in tie group)
ORDINAL_LOWER_BETTER = frozenset(
    {"popularity", "win_odds", "expected_popularity", "oikiri_time"}
)
# Letter rating A..E → numeric (higher better)
OIKIRI_LETTER_SCORE = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}

# Categorical: no intrinsic order without priors — report diversity only
CATEGORICAL_FEATURES = frozenset(
    {"trainer", "sire", "damsire", "breeder", "owner"}
)


@dataclass
class FeatureMetrics:
    feature_id: str
    rankable: bool
    coverage: float
    missing_rate: float
    cells_total: int
    cells_filled: int
    races_with_feature: int
    tie_races: int
    tie_races_eligible: int  # tie + full coverage on G
    tie_resolved: int
    tie_resolution_rate: float | None
    tie_correct: int
    baseline_strict_hits: int
    feature_strict_hits: int
    strict_hit_improve_rate: float | None
    soft_not_strict: int
    soft_to_strict_recovered: int
    soft_to_strict_improve_rate: float | None
    information_gain_mean: float | None
    information_gain_sum: float | None
    winner_rank_hist: dict[str, int] = field(default_factory=dict)
    winner_rank_mean: float | None = None
    within_tie_diversity_rate: float | None = None
    notes: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def extract_runners(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Locate evaluation.runners (Prediction Bundle)."""
    ev = bundle.get("evaluation")
    if isinstance(ev, dict):
        rs = ev.get("runners")
        if isinstance(rs, list) and rs:
            return list(rs)

    def _walk(obj: Any, depth: int = 0) -> list[dict[str, Any]] | None:
        if depth > 5:
            return None
        if isinstance(obj, dict):
            rs = obj.get("runners")
            if (
                isinstance(rs, list)
                and rs
                and isinstance(rs[0], dict)
                and "model_rank" in rs[0]
            ):
                return list(rs)
            for v in obj.values():
                found = _walk(v, depth + 1)
                if found is not None:
                    return found
        return None

    return _walk(bundle) or []


def unique_top_pick(runners: list[dict[str, Any]]) -> int | None:
    """Baseline Strict pick: model_rank ↑, win_prob ↓, horse_number ↑."""
    if not runners:
        return None
    ordered = sorted(
        runners,
        key=lambda r: (
            int(r.get("model_rank") or 999),
            -float(r.get("win_prob") or 0.0),
            int(r.get("horse_number") or 0),
        ),
    )
    return int(ordered[0]["horse_number"])


def tie_group(runners: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Horses sharing the minimum model_rank."""
    if not runners:
        return []
    ranks = [int(r.get("model_rank") or 999) for r in runners]
    mn = min(ranks)
    return [r for r in runners if int(r.get("model_rank") or 999) == mn]


def soft_hit(runners: list[dict[str, Any]], winner: int) -> bool:
    g = tie_group(runners)
    return any(int(r.get("horse_number") or 0) == winner for r in g)


def strict_hit(runners: list[dict[str, Any]], winner: int) -> bool:
    top = unique_top_pick(runners)
    return top is not None and top == winner


def _parse_json_value(raw: str | None) -> Any:
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() == "null":
        return None
    try:
        return json.loads(s)
    except Exception:
        return s


def feature_sort_key(feature_id: str, value: Any) -> tuple[int, float | str]:
    """
    Return sort key for tie resolution.
    Lower tuple sorts first (= preferred pick) for ordinal features.
    Categorical: not used for picking.
    """
    if value is None:
        return (1, 0.0)  # missing sorts last / ineligible

    if feature_id in ORDINAL_LOWER_BETTER:
        try:
            return (0, float(value))
        except (TypeError, ValueError):
            return (1, 0.0)

    if feature_id == "oikiri_rating":
        # Accept "A", "仕上十分 A", etc.
        text = str(value).strip().upper()
        letter = None
        for ch in text:
            if ch in OIKIRI_LETTER_SCORE:
                letter = ch
        if letter is None and text in OIKIRI_LETTER_SCORE:
            letter = text
        if letter is None:
            return (1, 0.0)
        # higher letter score → preferred → negate for ascending sort
        return (0, -float(OIKIRI_LETTER_SCORE[letter]))

    # categorical: stable but not semantically ranked
    return (0, str(value))


def resolve_tie_by_feature(
    *,
    feature_id: str,
    group: list[dict[str, Any]],
    values_by_hn: dict[int, Any],
) -> tuple[int | None, str]:
    """
    Shadow resolver on tie group G.
    Returns (picked_horse_number | None, status).
    status: resolved | unresolved_tie | missing | not_rankable | empty
    """
    if not group:
        return None, "empty"
    if feature_id in CATEGORICAL_FEATURES:
        return None, "not_rankable"

    scored: list[tuple[tuple[int, float | str], int]] = []
    for r in group:
        hn = int(r.get("horse_number") or 0)
        val = values_by_hn.get(hn)
        if val is None:
            return None, "missing"
        scored.append((feature_sort_key(feature_id, val), hn))

    scored.sort(key=lambda x: (x[0], x[1]))
    best_key = scored[0][0]
    winners = [hn for key, hn in scored if key == best_key]
    if len(winners) == 1:
        return winners[0], "resolved"
    return None, "unresolved_tie"


def winner_feature_rank(
    *,
    feature_id: str,
    runners: list[dict[str, Any]],
    values_by_hn: dict[int, Any],
    winner: int,
) -> int | None:
    """1-based rank of winner among all runners by feature (ordinal only)."""
    if feature_id in CATEGORICAL_FEATURES:
        return None
    scored: list[tuple[tuple[int, float | str], int]] = []
    for r in runners:
        hn = int(r.get("horse_number") or 0)
        val = values_by_hn.get(hn)
        if val is None:
            return None
        scored.append((feature_sort_key(feature_id, val), hn))
    scored.sort(key=lambda x: (x[0], x[1]))
    for i, (_, hn) in enumerate(scored, start=1):
        if hn == winner:
            return i
    return None


def _ig_bits(group_size: int, resolved: bool, remaining: int = 1) -> float:
    """Entropy reduction vs uniform pick in G."""
    if group_size <= 1:
        return 0.0
    prior = math.log2(group_size)
    if resolved:
        return prior  # posterior entropy 0
    if remaining <= 0:
        remaining = group_size
    return max(0.0, prior - math.log2(remaining))


class EvidenceAnalyzer:
    """Offline statistical analyzer for Research Evidence features."""

    def __init__(self, features: tuple[str, ...] = V102_FEATURES) -> None:
        migrate()
        self.features = features

    def load_eval_corpus(self) -> list[dict[str, Any]]:
        """
        Snapshots ∩ race_results with winner.
        Excludes canary 2099-* and failed captures.
        """
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT
                  s.snapshot_id,
                  s.prediction_id,
                  s.race_id,
                  s.capture_status,
                  s.field_coverage,
                  p.bundle_json,
                  p.created_at AS prediction_created_at,
                  r.winner_horse_number,
                  r.race_date
                FROM research_prediction_snapshots s
                JOIN predictions p ON p.id = s.prediction_id
                JOIN race_results r ON r.race_id = s.race_id
                WHERE s.capture_status = 'complete'
                  AND r.winner_horse_number IS NOT NULL
                  AND s.race_id NOT LIKE '2099%'
                ORDER BY s.prediction_id ASC
                """
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def load_feature_map(
        self, snapshot_ids: list[str]
    ) -> dict[str, dict[str, dict[int, Any]]]:
        """
        snapshot_id → feature_id → horse_number → value
        """
        if not snapshot_ids:
            return {}
        conn = connect()
        try:
            out: dict[str, dict[str, dict[int, Any]]] = defaultdict(
                lambda: defaultdict(dict)
            )
            # chunk IN clause
            chunk = 200
            for i in range(0, len(snapshot_ids), chunk):
                part = snapshot_ids[i : i + chunk]
                placeholders = ",".join("?" * len(part))
                rows = conn.execute(
                    f"""
                    SELECT snapshot_id, feature_id, horse_number, value_json, missing_reason
                    FROM research_snapshot_features
                    WHERE snapshot_id IN ({placeholders})
                    """,
                    part,
                ).fetchall()
                for r in rows:
                    val = _parse_json_value(r["value_json"])
                    out[str(r["snapshot_id"])][str(r["feature_id"])][
                        int(r["horse_number"])
                    ] = val
            return out
        finally:
            conn.close()

    def analyze(self) -> dict[str, Any]:
        corpus = self.load_eval_corpus()
        snap_ids = [c["snapshot_id"] for c in corpus]
        fmap = self.load_feature_map(snap_ids)

        # Global baseline
        n = len(corpus)
        baseline_strict = 0
        baseline_soft = 0
        soft_not_strict = 0
        tie_ge2 = 0
        tie_ge3 = 0
        race_records: list[dict[str, Any]] = []

        for row in corpus:
            bundle = json.loads(row["bundle_json"] or "{}")
            runners = extract_runners(bundle)
            winner = int(row["winner_horse_number"])
            g = tie_group(runners)
            g_size = len(g)
            is_strict = strict_hit(runners, winner)
            is_soft = soft_hit(runners, winner)
            if is_strict:
                baseline_strict += 1
            if is_soft:
                baseline_soft += 1
            if is_soft and not is_strict:
                soft_not_strict += 1
            if g_size >= 2:
                tie_ge2 += 1
            if g_size >= 3:
                tie_ge3 += 1
            race_records.append(
                {
                    "snapshot_id": row["snapshot_id"],
                    "prediction_id": row["prediction_id"],
                    "race_id": row["race_id"],
                    "winner": winner,
                    "runners": runners,
                    "tie_size": g_size,
                    "strict": is_strict,
                    "soft": is_soft,
                    "soft_not_strict": is_soft and not is_strict,
                }
            )

        # Coverage corpus: all complete snapshot feature rows (incl. without results)
        coverage_stats = self._coverage_all_snapshots()

        feature_metrics: list[FeatureMetrics] = []
        for fid in self.features:
            feature_metrics.append(
                self._analyze_feature(
                    feature_id=fid,
                    race_records=race_records,
                    fmap=fmap,
                    coverage=coverage_stats.get(fid, {"total": 0, "filled": 0}),
                    baseline_strict=baseline_strict,
                    soft_not_strict=soft_not_strict,
                    n_races=n,
                    tie_ge2=tie_ge2,
                )
            )

        report = {
            "schema": "expect-evidence-analyzer/1.0",
            "analyzed_at": _now(),
            "corpus": {
                "n_races": n,
                "baseline_strict_hits": baseline_strict,
                "baseline_strict_rate": (baseline_strict / n) if n else None,
                "baseline_soft_hits": baseline_soft,
                "baseline_soft_rate": (baseline_soft / n) if n else None,
                "soft_not_strict": soft_not_strict,
                "oracle_ceiling_strict_rate": (baseline_soft / n) if n else None,
                "tie_races_ge2": tie_ge2,
                "tie_races_ge3": tie_ge3,
                "avg_tie_size": (
                    sum(r["tie_size"] for r in race_records) / n if n else None
                ),
            },
            "features": [asdict(m) for m in feature_metrics],
            "ranking": self._rank_features(feature_metrics),
            "definitions": self._definitions(),
            "hard_lock": {
                "prediction_logic": "unchanged",
                "pe": "unchanged",
                "ce": "unchanged",
                "ai_score": "unchanged",
                "shadow_only": True,
            },
        }
        return report

    def _coverage_all_snapshots(self) -> dict[str, dict[str, int]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT f.feature_id,
                       COUNT(*) AS total,
                       SUM(
                         CASE
                           WHEN f.value_json IS NOT NULL
                            AND TRIM(f.value_json) != ''
                            AND LOWER(TRIM(f.value_json)) != 'null'
                           THEN 1 ELSE 0
                         END
                       ) AS filled
                FROM research_snapshot_features f
                JOIN research_prediction_snapshots s ON s.snapshot_id = f.snapshot_id
                WHERE s.capture_status = 'complete'
                GROUP BY f.feature_id
                """
            ).fetchall()
            out = {str(r["feature_id"]): {"total": int(r["total"]), "filled": int(r["filled"] or 0)} for r in rows}
            # ensure all V102 features present
            for fid in self.features:
                out.setdefault(fid, {"total": 0, "filled": 0})
            # For features never indexed, estimate denominator from runner cells of known features
            if out.get("popularity", {}).get("total", 0) > 0:
                denom = out["popularity"]["total"]
                for fid in self.features:
                    if out[fid]["total"] == 0:
                        out[fid] = {"total": denom, "filled": 0}
            return out
        finally:
            conn.close()

    def _analyze_feature(
        self,
        *,
        feature_id: str,
        race_records: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        coverage: dict[str, int],
        baseline_strict: int,
        soft_not_strict: int,
        n_races: int,
        tie_ge2: int,
    ) -> FeatureMetrics:
        total = int(coverage.get("total") or 0)
        filled = int(coverage.get("filled") or 0)
        cov = (filled / total) if total else 0.0
        missing = 1.0 - cov if total else 1.0
        rankable = feature_id not in CATEGORICAL_FEATURES

        tie_eligible = 0
        tie_resolved = 0
        tie_correct = 0
        feature_strict = 0
        recovered = 0
        ig_sum = 0.0
        ig_n = 0
        diversity_num = 0
        diversity_den = 0
        winner_ranks: list[int] = []
        races_with = 0

        for rec in race_records:
            sid = rec["snapshot_id"]
            runners = rec["runners"]
            winner = rec["winner"]
            g = tie_group(runners)
            values = fmap.get(sid, {}).get(feature_id, {})

            # race-level presence
            present = sum(1 for r in runners if values.get(int(r.get("horse_number") or 0)) is not None)
            if present > 0:
                races_with += 1

            wr = winner_feature_rank(
                feature_id=feature_id,
                runners=runners,
                values_by_hn=values,
                winner=winner,
            )
            if wr is not None:
                winner_ranks.append(wr)

            # baseline strict contribution already counted globally; recompute shadow pick
            baseline_is_strict = rec["strict"]
            shadow_strict = baseline_is_strict

            if len(g) >= 2:
                # diversity
                diversity_den += 1
                g_vals = [values.get(int(r.get("horse_number") or 0)) for r in g]
                if all(v is not None for v in g_vals) and len(set(map(str, g_vals))) > 1:
                    diversity_num += 1

                if rankable:
                    pick, status = resolve_tie_by_feature(
                        feature_id=feature_id, group=g, values_by_hn=values
                    )
                    if status != "missing":
                        tie_eligible += 1
                    if status == "resolved" and pick is not None:
                        tie_resolved += 1
                        if pick == winner:
                            tie_correct += 1
                        # shadow strict: use feature pick instead of baseline top
                        shadow_strict = pick == winner
                        ig_sum += _ig_bits(len(g), True)
                        ig_n += 1
                        if rec["soft_not_strict"] and pick == winner:
                            recovered += 1
                    elif status == "unresolved_tie":
                        # remaining = size of best-key group
                        scored = []
                        for r in g:
                            hn = int(r.get("horse_number") or 0)
                            scored.append(feature_sort_key(feature_id, values.get(hn)))
                        if scored:
                            best = min(scored)
                            rem = sum(1 for k in scored if k == best)
                            ig_sum += _ig_bits(len(g), False, rem)
                            ig_n += 1
                    # missing: not eligible

            if shadow_strict:
                feature_strict += 1

        hist = Counter(str(x) for x in winner_ranks)
        notes = []
        if filled == 0:
            notes.append("NOT_COLLECTED")
        if feature_id in CATEGORICAL_FEATURES:
            notes.append("CATEGORICAL_NO_PRIOR — resolver metrics N/A without win-rate prior")
        if not rankable:
            resolve_rate = None
            strict_improve = None
            soft_improve = None
            ig_mean = None
        else:
            resolve_rate = (tie_resolved / tie_eligible) if tie_eligible else None
            strict_improve = (
                (feature_strict - baseline_strict) / n_races if n_races else None
            )
            soft_improve = (
                (recovered / soft_not_strict) if soft_not_strict else None
            )
            ig_mean = (ig_sum / ig_n) if ig_n else None

        return FeatureMetrics(
            feature_id=feature_id,
            rankable=rankable,
            coverage=round(cov, 6),
            missing_rate=round(missing, 6),
            cells_total=total,
            cells_filled=filled,
            races_with_feature=races_with,
            tie_races=tie_ge2,
            tie_races_eligible=tie_eligible,
            tie_resolved=tie_resolved,
            tie_resolution_rate=None if resolve_rate is None else round(resolve_rate, 6),
            tie_correct=tie_correct,
            baseline_strict_hits=baseline_strict,
            feature_strict_hits=feature_strict,
            strict_hit_improve_rate=None
            if strict_improve is None
            else round(strict_improve, 6),
            soft_not_strict=soft_not_strict,
            soft_to_strict_recovered=recovered,
            soft_to_strict_improve_rate=None
            if soft_improve is None
            else round(soft_improve, 6),
            information_gain_mean=None if ig_mean is None else round(ig_mean, 6),
            information_gain_sum=None if ig_n == 0 else round(ig_sum, 6),
            winner_rank_hist=dict(sorted(hist.items(), key=lambda x: int(x[0]))),
            winner_rank_mean=(
                round(sum(winner_ranks) / len(winner_ranks), 4) if winner_ranks else None
            ),
            within_tie_diversity_rate=(
                round(diversity_num / diversity_den, 6) if diversity_den else None
            ),
            notes="; ".join(notes),
        )

    def _rank_features(self, metrics: list[FeatureMetrics]) -> list[dict[str, Any]]:
        """
        Rank by Soft→Strict improve, then Strict improve, then IG, then coverage.
        Non-rankable / zero-coverage sink to bottom.
        """

        def score(m: FeatureMetrics) -> tuple:
            if m.cells_filled <= 0:
                return (0, -1, -1, -1, m.coverage)
            if not m.rankable:
                # diversity as weak signal
                return (
                    1,
                    m.within_tie_diversity_rate or 0.0,
                    m.coverage,
                    0.0,
                    0.0,
                )
            return (
                2,
                m.soft_to_strict_improve_rate or 0.0,
                m.strict_hit_improve_rate or 0.0,
                m.information_gain_mean or 0.0,
                m.coverage,
            )

        ordered = sorted(metrics, key=score, reverse=True)
        out = []
        for i, m in enumerate(ordered, start=1):
            out.append(
                {
                    "rank": i,
                    "feature_id": m.feature_id,
                    "soft_to_strict_improve_rate": m.soft_to_strict_improve_rate,
                    "strict_hit_improve_rate": m.strict_hit_improve_rate,
                    "information_gain_mean": m.information_gain_mean,
                    "tie_resolution_rate": m.tie_resolution_rate,
                    "coverage": m.coverage,
                    "rankable": m.rankable,
                    "notes": m.notes,
                }
            )
        return out

    @staticmethod
    def _definitions() -> dict[str, str]:
        return {
            "coverage": "filled_cells / total_cells over complete snapshots",
            "missing_rate": "1 - coverage",
            "tie_races": "races where |tie_group| >= 2 (min model_rank shared)",
            "tie_resolution_rate": "among eligible tie races (full feature on G), unique argmin/argmax pick rate",
            "strict_hit": "unique top (model_rank, win_prob, horse_number) == winner",
            "soft_hit": "winner ∈ tie_group (min model_rank)",
            "strict_hit_improve_rate": "(strict_hits_with_shadow_resolver - baseline_strict) / n_races",
            "soft_to_strict_improve_rate": "recovered Soft∧¬Strict races / Soft∧¬Strict count",
            "information_gain": "mean bits: log2(|G|) - log2(|remaining|) after feature partition on G",
            "winner_rank_distribution": "1-based rank of winner by feature across full field (ordinal only)",
            "shadow_only": "resolver applied only in analysis; stored Prediction ranks unchanged",
        }


def write_csv(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "rank",
        "feature_id",
        "coverage",
        "missing_rate",
        "tie_races",
        "tie_races_eligible",
        "tie_resolved",
        "tie_resolution_rate",
        "tie_correct",
        "strict_hit_improve_rate",
        "soft_to_strict_improve_rate",
        "soft_to_strict_recovered",
        "soft_not_strict",
        "information_gain_mean",
        "winner_rank_mean",
        "within_tie_diversity_rate",
        "rankable",
        "cells_filled",
        "cells_total",
        "notes",
    ]
    by_id = {f["feature_id"]: f for f in report.get("features") or []}
    ranking = report.get("ranking") or []
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in ranking:
            fid = row["feature_id"]
            full = by_id.get(fid, {})
            w.writerow(
                {
                    "rank": row.get("rank"),
                    "feature_id": fid,
                    "coverage": full.get("coverage"),
                    "missing_rate": full.get("missing_rate"),
                    "tie_races": full.get("tie_races"),
                    "tie_races_eligible": full.get("tie_races_eligible"),
                    "tie_resolved": full.get("tie_resolved"),
                    "tie_resolution_rate": full.get("tie_resolution_rate"),
                    "tie_correct": full.get("tie_correct"),
                    "strict_hit_improve_rate": full.get("strict_hit_improve_rate"),
                    "soft_to_strict_improve_rate": full.get("soft_to_strict_improve_rate"),
                    "soft_to_strict_recovered": full.get("soft_to_strict_recovered"),
                    "soft_not_strict": full.get("soft_not_strict"),
                    "information_gain_mean": full.get("information_gain_mean"),
                    "winner_rank_mean": full.get("winner_rank_mean"),
                    "within_tie_diversity_rate": full.get("within_tie_diversity_rate"),
                    "rankable": full.get("rankable"),
                    "cells_filled": full.get("cells_filled"),
                    "cells_total": full.get("cells_total"),
                    "notes": full.get("notes"),
                }
            )


def write_markdown(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = report["corpus"]
    lines: list[str] = []
    lines.append("# Version10.2 Research — Evidence Analysis")
    lines.append("")
    lines.append(f"**Date:** {report.get('analyzed_at')}  ")
    lines.append("**Type:** Shadow statistical evaluation（Prediction 順位は変更しない）  ")
    lines.append("**Input:** `research_prediction_snapshots` ∩ `research_snapshot_features` ∩ `race_results`  ")
    lines.append("**Hard Lock:** PE / CE / AI Score / Prediction Logic **変更なし**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 0. Verdict")
    lines.append("")
    lines.append("| 指標 | 値 |")
    lines.append("|------|----|")
    lines.append(f"| 評価レース数 | **{c['n_races']}** |")
    lines.append(
        f"| Baseline Strict Hit | **{c['baseline_strict_hits']}/{c['n_races']}** "
        f"({(c['baseline_strict_rate'] or 0)*100:.1f}%) |"
    )
    lines.append(
        f"| Baseline Soft Hit | **{c['baseline_soft_hits']}/{c['n_races']}** "
        f"({(c['baseline_soft_rate'] or 0)*100:.1f}%) |"
    )
    lines.append(f"| Soft∧¬Strict（回収余地） | **{c['soft_not_strict']}** |")
    lines.append(f"| Tie レース（|G|≥2） | **{c['tie_races_ge2']}** |")
    lines.append(f"| Rank Degeneracy（|G|≥3） | **{c['tie_races_ge3']}** |")
    lines.append(f"| 平均タイ頭数 | **{(c['avg_tie_size'] or 0):.3f}** |")
    lines.append("")

    # Top findings from ranking
    ranking = report.get("ranking") or []
    lines.append("### Feature 有効性ランキング（要約）")
    lines.append("")
    lines.append("| Rank | Feature | Soft→Strict | StrictΔ | IG(bit) | Coverage | 判定 |")
    lines.append("|-----:|---------|------------:|--------:|--------:|---------:|------|")
    for row in ranking:
        fid = row["feature_id"]
        s2s = row.get("soft_to_strict_improve_rate")
        st = row.get("strict_hit_improve_rate")
        ig = row.get("information_gain_mean")
        cov = row.get("coverage")
        notes = row.get("notes") or ""
        if cov == 0 or (isinstance(cov, float) and cov <= 0):
            verdict = "NOT_COLLECTED"
        elif not row.get("rankable"):
            verdict = "CATEGORICAL"
        elif (s2s or 0) > 0 or (st or 0) > 0:
            verdict = "PROMISING"
        elif (s2s or 0) == 0 and (st or 0) == 0 and cov and cov > 0:
            verdict = "COLLECTED_NO_LIFT"
        else:
            verdict = "WEAK"
        lines.append(
            f"| {row['rank']} | `{fid}` | "
            f"{_pct(s2s)} | {_pct(st)} | {_num(ig)} | {_pct(cov)} | {verdict} |"
        )
    lines.append("")
    lines.append(
        "判定凡例: **PROMISING**=Shadow Resolver で Strict/Soft回収が正、"
        "**COLLECTED_NO_LIFT**=取得済みだが改善ゼロ、**CATEGORICAL**=順位付けルール未定義、"
        "**NOT_COLLECTED**=Collector 未実装。"
    )
    lines.append("")
    # Key findings for market features if present
    by_id = {f["feature_id"]: f for f in (report.get("features") or [])}
    pop = by_id.get("popularity") or {}
    if pop.get("cells_filled"):
        lines.append("### 重要所見")
        lines.append("")
        lines.append(
            f"- 市場系（popularity/win_odds/expected_popularity）: "
            f"Tie解消 {_pct(pop.get('tie_resolution_rate'))} / "
            f"Tie正解 {pop.get('tie_correct')}/{pop.get('tie_resolved')} / "
            f"Soft→Strict {_pct(pop.get('soft_to_strict_improve_rate'))}。"
        )
        lines.append(
            "- **解消 ≠ 正解**: 一意化できても勝ち馬ヒット率は別指標。V10.3 では単一argmin固定を避け、"
            "複合ルールや fail-open を検討する。"
        )
        lines.append(
            "- trainer は Coverage 高・タイ内 diversity 高だがカテゴリカル prior が無いと未解決。"
        )
        lines.append(
            "- sire/damsire/breeder/oikiri_* は NOT_COLLECTED — Collector 後に再計測。"
        )
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. 定義")
    lines.append("")
    for k, v in (report.get("definitions") or {}).items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("Ordinal の Tie 解決方向:")
    lines.append("")
    lines.append("| Feature | 規則 |")
    lines.append("|---------|------|")
    lines.append("| popularity / expected_popularity | 小さいほど良い（argmin） |")
    lines.append("| win_odds | 小さいほど良い（argmin） |")
    lines.append("| oikiri_time | 小さいほど良い（argmin） |")
    lines.append("| oikiri_rating | A>B>C>D>E（argmax letter） |")
    lines.append("| trainer / sire / damsire / breeder | カテゴリカル — prior 無しでは未解決 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Feature 別詳細")
    lines.append("")
    for f in report.get("features") or []:
        fid = f["feature_id"]
        lines.append(f"### `{fid}`")
        lines.append("")
        lines.append("| 指標 | 値 |")
        lines.append("|------|----|")
        lines.append(f"| Coverage | {_pct(f.get('coverage'))} ({f.get('cells_filled')}/{f.get('cells_total')}) |")
        lines.append(f"| Missing率 | {_pct(f.get('missing_rate'))} |")
        lines.append(f"| Tieレース数（全体） | {f.get('tie_races')} |")
        lines.append(f"| Tie eligible（G上フル） | {f.get('tie_races_eligible')} |")
        lines.append(f"| Tie解消数 / 率 | {f.get('tie_resolved')} / {_pct(f.get('tie_resolution_rate'))} |")
        lines.append(f"| Tie正解数 | {f.get('tie_correct')} |")
        lines.append(f"| Strict Hit改善率 | {_pct(f.get('strict_hit_improve_rate'))} |")
        lines.append(
            f"| Soft→Strict改善率 | {_pct(f.get('soft_to_strict_improve_rate'))} "
            f"({f.get('soft_to_strict_recovered')}/{f.get('soft_not_strict')}) |"
        )
        lines.append(f"| Information Gain (mean bit) | {_num(f.get('information_gain_mean'))} |")
        lines.append(f"| Winner順位平均 | {_num(f.get('winner_rank_mean'))} |")
        lines.append(f"| Winner順位分布 | `{json.dumps(f.get('winner_rank_hist') or {}, ensure_ascii=False)}` |")
        lines.append(f"| Within-tie diversity | {_pct(f.get('within_tie_diversity_rate'))} |")
        lines.append(f"| Rankable | {f.get('rankable')} |")
        if f.get("notes"):
            lines.append(f"| Notes | {f.get('notes')} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 3. 解釈（Prediction 非改変）")
    lines.append("")
    lines.append("1. 本レポートは **Shadow Resolver** 評価のみ。保存済み `model_rank` / `win_prob` は未変更。")
    lines.append("2. Soft∧¬Strict が Resolver の理論回収上限（Oracle = Soft Hit）。")
    lines.append("3. NOT_COLLECTED Feature（sire / damsire / breeder / oikiri_*）は V10.1 で取得可能性のみ確認済み。Collector 実装後に再計測。")
    lines.append("4. カテゴリカル Feature は勝率 prior を持たない限り Tie Resolver に直接使えない。")
    lines.append("5. 次フェーズ Version10.3 Tie Resolver は、本ランキングで PROMISING / 高 Coverage の Feature から採用する。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. 【Decision】")
    lines.append("")
    lines.append("```")
    lines.append("Action Type: Evidence Analysis (read-only + analyzer code)")
    lines.append("Implementation Required: Analyzer only (no Prediction change)")
    lines.append("Deployment Required: Optional (CLI on EC2)")
    lines.append("Configuration Required: No")
    lines.append("Production Required: No (Prediction 非改変)")
    lines.append("Rollback Required: No")
    lines.append("Risk: Low")
    lines.append("Expected Next Action: Version10.3 Tie Resolver design/impl using PROMISING features")
    lines.append("```")
    lines.append("")
    lines.append(f"CSV: `docs/research/v102-feature-ranking.csv`  ")
    lines.append(f"Generated: `{report.get('analyzed_at')}`")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _pct(x: float | None) -> str:
    if x is None:
        return "N/A"
    return f"{x * 100:.1f}%"


def _num(x: float | None) -> str:
    if x is None:
        return "N/A"
    return f"{x:.4f}"


def default_doc_paths() -> tuple[Path, Path]:
    root = repo_root()
    return (
        root / "docs" / "research" / "v102-evidence-analysis.md",
        root / "docs" / "research" / "v102-feature-ranking.csv",
    )


def run_and_write(
    *,
    md_path: Path | None = None,
    csv_path: Path | None = None,
    json_path: Path | None = None,
) -> dict[str, Any]:
    analyzer = EvidenceAnalyzer()
    report = analyzer.analyze()
    md_default, csv_default = default_doc_paths()
    md_path = md_path or md_default
    csv_path = csv_path or csv_default
    write_markdown(report, md_path)
    write_csv(report, csv_path)
    if json_path is None:
        json_path = repo_root() / "evidence" / "research" / "reports" / "v102-evidence-analysis.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "markdown": str(md_path),
        "csv": str(csv_path),
        "json": str(json_path),
    }
    return report
