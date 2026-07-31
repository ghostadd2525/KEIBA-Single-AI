# -*- coding: utf-8 -*-
"""
Version10.4 Evidence Ranking Engine

Statistical Evidence Priority for future Tie Resolver.
Shadow only — does NOT mutate Prediction / PE / CE / AI / ResultAutomation.
Does NOT implement production Tie Resolver.
"""
from __future__ import annotations

import csv
import json
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .analyzer import (
    EvidenceAnalyzer,
    _ig_bits,
    _parse_json_value,
    extract_runners,
    soft_hit,
    strict_hit,
    tie_group,
    unique_top_pick,
)
from .config import repo_root

V104_FEATURES: tuple[str, ...] = (
    "popularity",
    "win_odds",
    "expected_popularity",
    "trainer",
    "sire",
    "damsire",
    "breeder",
    "owner",
    "sale_price",
    "oikiri_time",
    "oikiri_rating",
)

ORDINAL_LOWER_BETTER = frozenset(
    {"popularity", "win_odds", "expected_popularity", "oikiri_time"}
)
ORDINAL_HIGHER_BETTER = frozenset({"sale_price"})
OIKIRI_LETTER_SCORE = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
CATEGORICAL_FEATURES = frozenset(
    {"trainer", "sire", "damsire", "breeder", "owner"}
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_sale_price(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value)
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*万", s)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def feature_score(
    feature_id: str,
    value: Any,
    *,
    cat_prior: dict[str, float] | None = None,
) -> float | None:
    """
    Higher score = preferred pick within tie group.
    Returns None if value missing / unscored.
    """
    if value is None:
        return None

    if feature_id in ORDINAL_LOWER_BETTER:
        try:
            return -float(value)
        except (TypeError, ValueError):
            return None

    if feature_id in ORDINAL_HIGHER_BETTER:
        num = _parse_sale_price(value) if feature_id == "sale_price" else None
        if num is None:
            try:
                num = float(value)
            except (TypeError, ValueError):
                return None
        return float(num)

    if feature_id == "oikiri_rating":
        text = str(value).strip().upper()
        for ch in text:
            if ch in OIKIRI_LETTER_SCORE:
                return float(OIKIRI_LETTER_SCORE[ch])
        return None

    if feature_id in CATEGORICAL_FEATURES:
        if not cat_prior:
            return None
        key = str(value).strip()
        return float(cat_prior.get(key, 0.0))

    return None


def resolve_by_score(
    group: list[dict[str, Any]],
    scores: dict[int, float | None],
) -> tuple[int | None, str]:
    if not group:
        return None, "empty"
    scored: list[tuple[float, int]] = []
    for r in group:
        hn = int(r.get("horse_number") or 0)
        sc = scores.get(hn)
        if sc is None:
            return None, "missing"
        scored.append((sc, hn))
    scored.sort(key=lambda x: (-x[0], x[1]))
    best = scored[0][0]
    tops = [hn for sc, hn in scored if sc == best]
    if len(tops) == 1:
        return tops[0], "resolved"
    return None, "unresolved_tie"


def cascade_resolve(
    group: list[dict[str, Any]],
    feature_order: list[str],
    values_by_feature: dict[str, dict[int, Any]],
    cat_priors: dict[str, dict[str, float]],
) -> tuple[int | None, str, str | None]:
    """
    Apply features in order; first unique resolve wins.
    Returns (pick, status, winning_feature).
    """
    remaining = list(group)
    for fid in feature_order:
        vals = values_by_feature.get(fid) or {}
        scores = {
            int(r.get("horse_number") or 0): feature_score(
                fid,
                vals.get(int(r.get("horse_number") or 0)),
                cat_prior=cat_priors.get(fid),
            )
            for r in remaining
        }
        if any(scores.get(int(r.get("horse_number") or 0)) is None for r in remaining):
            continue
        pick, status = resolve_by_score(remaining, scores)
        if status == "resolved" and pick is not None:
            return pick, "resolved", fid
        if status == "unresolved_tie":
            # shrink remaining to tied best set
            scored = []
            for r in remaining:
                hn = int(r.get("horse_number") or 0)
                scored.append((scores[hn], hn))
            best = max(scored, key=lambda x: x[0])[0]
            keep = {hn for sc, hn in scored if sc == best}
            remaining = [r for r in remaining if int(r.get("horse_number") or 0) in keep]
            if len(remaining) == 1:
                return int(remaining[0]["horse_number"]), "resolved", fid
    # fail-open: baseline horse_number among remaining
    if remaining:
        pick = unique_top_pick(remaining)
        return pick, "fallback_baseline", None
    return None, "empty", None


def _entropy(counts: Counter) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    return h


def mutual_information_binary(xs: list[Any], ys: list[int]) -> float:
    """MI(X;Y) for discrete X and binary Y."""
    n = len(xs)
    if n == 0 or len(ys) != n:
        return 0.0
    joint: Counter = Counter()
    mx: Counter = Counter()
    my: Counter = Counter()
    for x, y in zip(xs, ys):
        joint[(x, y)] += 1
        mx[x] += 1
        my[y] += 1
    mi = 0.0
    for (x, y), c in joint.items():
        pxy = c / n
        px = mx[x] / n
        py = my[y] / n
        if pxy > 0 and px > 0 and py > 0:
            mi += pxy * math.log2(pxy / (px * py))
    return max(0.0, mi)


def _bin_ordinal(values: list[float], v: float, bins: int = 4) -> str:
    if not values:
        return "na"
    ordered = sorted(values)
    # quantile edges
    qs = []
    for i in range(1, bins):
        idx = int(len(ordered) * i / bins)
        idx = min(max(idx, 0), len(ordered) - 1)
        qs.append(ordered[idx])
    for i, edge in enumerate(qs):
        if v <= edge:
            return f"q{i}"
    return f"q{bins - 1}"


@dataclass
class FeatureImportance:
    feature_id: str
    coverage: float
    missing_rate: float
    tie_races: int
    tie_eligible: int
    tie_resolved: int
    tie_resolution_rate: float | None
    tie_correct: int
    strict_hit: int
    soft_hit: int
    soft_hit_rate: float | None
    soft_to_strict_improve_rate: float | None
    soft_to_strict_recovered: int
    soft_not_strict: int
    information_gain_mean: float | None
    mutual_information: float | None
    permutation_importance: float | None
    lift: float | None
    winner_rank_mean: float | None
    within_tie_diversity_rate: float | None
    composite_score: float
    tier: str
    notes: str = ""
    rank: int | None = None


@dataclass
class ShadowStrategyResult:
    strategy_id: str
    description: str
    n_tie_races: int
    resolved: int
    fallback: int
    strict_hits: int
    soft_hits: int
    baseline_strict: int
    baseline_soft: int
    strict_improve: int
    soft_improve: int
    strict_rate: float
    soft_rate: float
    strict_delta: float
    soft_delta: float


class EvidenceRankingEngine:
    """Generate Evidence Priority (tiers) from statistics only."""

    def __init__(
        self,
        *,
        features: tuple[str, ...] = V104_FEATURES,
        perm_shuffles: int = 30,
        seed: int = 104,
    ) -> None:
        self.features = features
        self.perm_shuffles = perm_shuffles
        self.rng = random.Random(seed)
        self.base = EvidenceAnalyzer(features=features)

    def build_corpus(self) -> tuple[list[dict[str, Any]], dict[str, dict[str, dict[int, Any]]]]:
        corpus = self.base.load_eval_corpus()
        fmap = self.base.load_feature_map([c["snapshot_id"] for c in corpus])
        races: list[dict[str, Any]] = []
        for row in corpus:
            bundle = json.loads(row["bundle_json"] or "{}")
            runners = extract_runners(bundle)
            if not runners:
                continue
            winner = int(row["winner_horse_number"])
            g = tie_group(runners)
            races.append(
                {
                    "snapshot_id": row["snapshot_id"],
                    "prediction_id": row["prediction_id"],
                    "race_id": row["race_id"],
                    "race_date": row.get("race_date"),
                    "winner": winner,
                    "runners": runners,
                    "tie_group": g,
                    "tie_size": len(g),
                    "strict": strict_hit(runners, winner),
                    "soft": soft_hit(runners, winner),
                    "soft_not_strict": soft_hit(runners, winner)
                    and not strict_hit(runners, winner),
                }
            )
        return races, fmap

    def build_categorical_priors(
        self,
        races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
    ) -> dict[str, dict[str, float]]:
        """Empirical P(win | category) over full field appearances (Laplace)."""
        priors: dict[str, dict[str, float]] = {}
        for fid in self.features:
            if fid not in CATEGORICAL_FEATURES:
                continue
            wins: Counter = Counter()
            apps: Counter = Counter()
            for rec in races:
                vals = fmap.get(rec["snapshot_id"], {}).get(fid, {})
                for r in rec["runners"]:
                    hn = int(r.get("horse_number") or 0)
                    v = vals.get(hn)
                    if v is None:
                        continue
                    key = str(v).strip()
                    apps[key] += 1
                    if hn == rec["winner"]:
                        wins[key] += 1
            prior: dict[str, float] = {}
            for key, n in apps.items():
                prior[key] = (wins[key] + 1.0) / (n + 2.0)
            priors[fid] = prior
        return priors

    def prior_for_race(
        self,
        *,
        feature_id: str,
        exclude_race_id: str,
        races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
    ) -> dict[str, float]:
        """Leave-one-out empirical prior (exclude the evaluated race)."""
        if feature_id not in CATEGORICAL_FEATURES:
            return {}
        wins: Counter = Counter()
        apps: Counter = Counter()
        for rec in races:
            if rec["race_id"] == exclude_race_id:
                continue
            vals = fmap.get(rec["snapshot_id"], {}).get(feature_id, {})
            for r in rec["runners"]:
                hn = int(r.get("horse_number") or 0)
                v = vals.get(hn)
                if v is None:
                    continue
                key = str(v).strip()
                apps[key] += 1
                if hn == rec["winner"]:
                    wins[key] += 1
        return {
            key: (wins[key] + 1.0) / (n + 2.0) for key, n in apps.items()
        }

    def analyze(self) -> dict[str, Any]:
        races, fmap = self.build_corpus()
        tie_races = [r for r in races if r["tie_size"] >= 2]
        # Global prior only for documentation / fallback; metrics use LOO.
        cat_priors_global = self.build_categorical_priors(races, fmap)

        n_all = len(races)
        n_tie = len(tie_races)
        baseline_strict = sum(1 for r in tie_races if r["strict"])
        baseline_soft = sum(1 for r in tie_races if r["soft"])
        soft_not_strict = sum(1 for r in tie_races if r["soft_not_strict"])

        coverage_stats = self.base._coverage_all_snapshots()

        importances: list[FeatureImportance] = []
        for fid in self.features:
            cov_meta = coverage_stats.get(fid, {"total": 0, "filled": 0})
            total = int(cov_meta.get("total") or 0)
            filled = int(cov_meta.get("filled") or 0)
            coverage = (filled / total) if total else 0.0

            metrics = self._feature_tie_metrics(
                feature_id=fid,
                tie_races=tie_races,
                all_races=races,
                fmap=fmap,
                soft_not_strict=soft_not_strict,
                baseline_strict=baseline_strict,
                baseline_soft=baseline_soft,
            )
            mi = self._mutual_information(
                feature_id=fid,
                tie_races=tie_races,
                fmap=fmap,
                cat_prior=cat_priors_global.get(fid),
            )
            perm = self._permutation_importance(
                feature_id=fid,
                tie_races=tie_races,
                all_races=races,
                fmap=fmap,
            )
            lift = metrics["lift"]
            soft2strict = metrics["soft_to_strict_improve_rate"]
            resolve_rate = metrics["tie_resolution_rate"]
            ig = metrics["information_gain_mean"]

            composite = self._composite_score(
                coverage=coverage,
                soft_to_strict=soft2strict,
                lift=lift,
                mi=mi,
                perm=perm,
                resolve_rate=resolve_rate,
                ig=ig,
            )
            tier = self._assign_tier(
                coverage=coverage,
                soft_to_strict=soft2strict,
                lift=lift,
                mi=mi,
                perm=perm,
                resolve_rate=resolve_rate,
                eligible=metrics["tie_eligible"],
            )
            notes = []
            if filled == 0:
                notes.append("NOT_COLLECTED")
            if fid in CATEGORICAL_FEATURES:
                notes.append("ranked_by_loo_empirical_win_prior")
            if metrics["tie_eligible"] == 0:
                notes.append("no_tie_eligible")

            importances.append(
                FeatureImportance(
                    feature_id=fid,
                    coverage=round(coverage, 6),
                    missing_rate=round(1.0 - coverage, 6),
                    tie_races=n_tie,
                    tie_eligible=metrics["tie_eligible"],
                    tie_resolved=metrics["tie_resolved"],
                    tie_resolution_rate=resolve_rate,
                    tie_correct=metrics["tie_correct"],
                    strict_hit=metrics["strict_hit"],
                    soft_hit=metrics["soft_hit"],
                    soft_hit_rate=metrics["soft_hit_rate"],
                    soft_to_strict_improve_rate=soft2strict,
                    soft_to_strict_recovered=metrics["soft_to_strict_recovered"],
                    soft_not_strict=soft_not_strict,
                    information_gain_mean=ig,
                    mutual_information=None if mi is None else round(mi, 6),
                    permutation_importance=None if perm is None else round(perm, 6),
                    lift=None if lift is None else round(lift, 6),
                    winner_rank_mean=metrics["winner_rank_mean"],
                    within_tie_diversity_rate=metrics["within_tie_diversity_rate"],
                    composite_score=round(composite, 6),
                    tier=tier,
                    notes="; ".join(notes),
                )
            )

        ordered = sorted(
            importances,
            key=lambda m: (
                {"S": 4, "A": 3, "B": 2, "C": 1}.get(m.tier, 0),
                m.composite_score,
                m.coverage,
            ),
            reverse=True,
        )
        for i, m in enumerate(ordered, start=1):
            m.rank = i

        priority_order = [m.feature_id for m in ordered if m.tier in ("S", "A", "B")]
        for m in ordered:
            if m.feature_id not in priority_order:
                priority_order.append(m.feature_id)

        shadow = self._simulate_strategies(
            tie_races=tie_races,
            all_races=races,
            fmap=fmap,
            priority_order=priority_order,
            ordered=ordered,
            baseline_strict=baseline_strict,
            baseline_soft=baseline_soft,
        )

        report = {
            "schema": "expect-evidence-ranking/1.0",
            "analyzed_at": _now(),
            "hard_lock": {
                "prediction_logic": "unchanged",
                "pe": "unchanged",
                "ce": "unchanged",
                "ai_score": "unchanged",
                "result_automation": "unchanged",
                "challenge": "unchanged",
                "resolver_production": "not_implemented",
                "shadow_only": True,
            },
            "corpus": {
                "n_races_all": n_all,
                "n_tie_races": n_tie,
                "baseline_strict_tie": baseline_strict,
                "baseline_soft_tie": baseline_soft,
                "soft_not_strict_tie": soft_not_strict,
                "avg_tie_size": (
                    sum(r["tie_size"] for r in tie_races) / n_tie if n_tie else None
                ),
            },
            "features": [asdict(m) for m in ordered],
            "evidence_priority": priority_order,
            "tiers": {
                "S": [m.feature_id for m in ordered if m.tier == "S"],
                "A": [m.feature_id for m in ordered if m.tier == "A"],
                "B": [m.feature_id for m in ordered if m.tier == "B"],
                "C": [m.feature_id for m in ordered if m.tier == "C"],
            },
            "shadow_strategies": [asdict(s) for s in shadow],
            "definitions": self._definitions(),
        }
        return report

    def _feature_tie_metrics(
        self,
        *,
        feature_id: str,
        tie_races: list[dict[str, Any]],
        all_races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        soft_not_strict: int,
        baseline_strict: int,
        baseline_soft: int,
    ) -> dict[str, Any]:
        eligible = 0
        resolved = 0
        correct = 0
        strict_n = 0
        soft_n = 0
        recovered = 0
        ig_sum = 0.0
        ig_n = 0
        div_n = 0
        div_d = 0
        winner_ranks: list[int] = []
        random_expect_sum = 0.0
        random_expect_n = 0

        for rec in tie_races:
            g = rec["tie_group"]
            vals = fmap.get(rec["snapshot_id"], {}).get(feature_id, {})
            cat_prior = None
            if feature_id in CATEGORICAL_FEATURES:
                cat_prior = self.prior_for_race(
                    feature_id=feature_id,
                    exclude_race_id=rec["race_id"],
                    races=all_races,
                    fmap=fmap,
                )
            scores = {
                int(r.get("horse_number") or 0): feature_score(
                    feature_id,
                    vals.get(int(r.get("horse_number") or 0)),
                    cat_prior=cat_prior,
                )
                for r in g
            }
            g_vals = [vals.get(int(r.get("horse_number") or 0)) for r in g]
            div_d += 1
            if all(v is not None for v in g_vals) and len(set(map(str, g_vals))) > 1:
                div_n += 1

            field_scores = {
                int(r.get("horse_number") or 0): feature_score(
                    feature_id,
                    vals.get(int(r.get("horse_number") or 0)),
                    cat_prior=cat_prior,
                )
                for r in rec["runners"]
            }
            if all(v is not None for v in field_scores.values()):
                ranked = sorted(
                    field_scores.items(), key=lambda x: (-(x[1] or -1e18), x[0])
                )
                for i, (hn, _) in enumerate(ranked, start=1):
                    if hn == rec["winner"]:
                        winner_ranks.append(i)
                        break

            if any(scores.get(int(r.get("horse_number") or 0)) is None for r in g):
                if rec["strict"]:
                    strict_n += 1
                if rec["soft"]:
                    soft_n += 1
                continue

            eligible += 1
            pick, status = resolve_by_score(g, scores)
            random_expect_sum += 1.0 / max(len(g), 1)
            random_expect_n += 1

            if status == "resolved" and pick is not None:
                resolved += 1
                if pick == rec["winner"]:
                    correct += 1
                shadow_strict = pick == rec["winner"]
                ig_sum += _ig_bits(len(g), True)
                ig_n += 1
                if rec["soft_not_strict"] and pick == rec["winner"]:
                    recovered += 1
            else:
                shadow_strict = rec["strict"]
                scored = [
                    (scores[int(r["horse_number"])], int(r["horse_number"])) for r in g
                ]
                best = max(scored, key=lambda x: x[0])[0]
                rem = sum(1 for sc, _ in scored if sc == best)
                ig_sum += _ig_bits(len(g), False, rem)
                ig_n += 1

            if shadow_strict:
                strict_n += 1
            if rec["soft"]:
                soft_n += 1

        n_tie = len(tie_races)
        resolve_rate = (resolved / eligible) if eligible else None
        soft2 = (recovered / soft_not_strict) if soft_not_strict else None
        lift = None
        if resolved > 0 and random_expect_n > 0:
            p_correct = correct / resolved
            p_rand = random_expect_sum / random_expect_n
            lift = (p_correct / p_rand) if p_rand > 0 else None

        return {
            "tie_eligible": eligible,
            "tie_resolved": resolved,
            "tie_resolution_rate": None if resolve_rate is None else round(resolve_rate, 6),
            "tie_correct": correct,
            "strict_hit": strict_n,
            "soft_hit": soft_n,
            "soft_hit_rate": (soft_n / n_tie) if n_tie else None,
            "soft_to_strict_improve_rate": None if soft2 is None else round(soft2, 6),
            "soft_to_strict_recovered": recovered,
            "information_gain_mean": (round(ig_sum / ig_n, 6) if ig_n else None),
            "lift": lift,
            "winner_rank_mean": (
                round(sum(winner_ranks) / len(winner_ranks), 4) if winner_ranks else None
            ),
            "within_tie_diversity_rate": (round(div_n / div_d, 6) if div_d else None),
        }

    def _mutual_information(
        self,
        *,
        feature_id: str,
        tie_races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        cat_prior: dict[str, float] | None,
    ) -> float | None:
        xs: list[Any] = []
        ys: list[int] = []
        numeric_pool: list[float] = []

        # gather numeric values for binning
        if feature_id not in CATEGORICAL_FEATURES:
            for rec in tie_races:
                vals = fmap.get(rec["snapshot_id"], {}).get(feature_id, {})
                for r in rec["tie_group"]:
                    hn = int(r.get("horse_number") or 0)
                    sc = feature_score(
                        feature_id, vals.get(hn), cat_prior=cat_prior
                    )
                    if sc is not None:
                        numeric_pool.append(float(sc))

        for rec in tie_races:
            vals = fmap.get(rec["snapshot_id"], {}).get(feature_id, {})
            for r in rec["tie_group"]:
                hn = int(r.get("horse_number") or 0)
                raw = vals.get(hn)
                if raw is None:
                    continue
                if feature_id in CATEGORICAL_FEATURES:
                    x = str(raw).strip()
                else:
                    sc = feature_score(feature_id, raw, cat_prior=cat_prior)
                    if sc is None:
                        continue
                    x = _bin_ordinal(numeric_pool, float(sc))
                xs.append(x)
                ys.append(1 if hn == rec["winner"] else 0)

        if len(xs) < 8:
            return None
        return mutual_information_binary(xs, ys)

    def _permutation_importance(
        self,
        *,
        feature_id: str,
        tie_races: list[dict[str, Any]],
        all_races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
    ) -> float | None:
        """Drop in correct-resolve rate when shuffling feature within G (LOO prior)."""

        def correct_rate(use_shuffle: bool) -> tuple[float, int]:
            correct = 0
            n = 0
            for rec in tie_races:
                g = rec["tie_group"]
                vals = dict(fmap.get(rec["snapshot_id"], {}).get(feature_id, {}))
                hns = [int(r.get("horse_number") or 0) for r in g]
                if any(vals.get(hn) is None for hn in hns):
                    continue
                if use_shuffle:
                    shuffled = list(hns)
                    self.rng.shuffle(shuffled)
                    vals = {hn: vals[src] for hn, src in zip(hns, shuffled)}
                cat_prior = None
                if feature_id in CATEGORICAL_FEATURES:
                    cat_prior = self.prior_for_race(
                        feature_id=feature_id,
                        exclude_race_id=rec["race_id"],
                        races=all_races,
                        fmap=fmap,
                    )
                scores = {
                    hn: feature_score(feature_id, vals.get(hn), cat_prior=cat_prior)
                    for hn in hns
                }
                if any(v is None for v in scores.values()):
                    continue
                pick, status = resolve_by_score(g, scores)
                n += 1
                if status == "resolved" and pick == rec["winner"]:
                    correct += 1
            return (correct / n if n else 0.0), n

        base, n = correct_rate(False)
        if n < 3:
            return None
        drops = []
        for _ in range(self.perm_shuffles):
            shuf, _ = correct_rate(True)
            drops.append(base - shuf)
        return sum(drops) / len(drops) if drops else None

    def _composite_score(
        self,
        *,
        coverage: float,
        soft_to_strict: float | None,
        lift: float | None,
        mi: float | None,
        perm: float | None,
        resolve_rate: float | None,
        ig: float | None,
    ) -> float:
        def nz(x: float | None, default: float = 0.0) -> float:
            return default if x is None else float(x)

        # normalize lift ~ [0,3] → [0,1]
        lift_n = min(max(nz(lift), 0.0), 3.0) / 3.0
        mi_n = min(max(nz(mi), 0.0), 1.0)
        perm_n = min(max(nz(perm), 0.0), 1.0)
        return (
            0.28 * nz(soft_to_strict)
            + 0.18 * lift_n
            + 0.16 * mi_n
            + 0.16 * perm_n
            + 0.12 * nz(resolve_rate)
            + 0.10 * coverage
        )

    def _assign_tier(
        self,
        *,
        coverage: float,
        soft_to_strict: float | None,
        lift: float | None,
        mi: float | None,
        perm: float | None,
        resolve_rate: float | None,
        eligible: int,
    ) -> str:
        s2s = soft_to_strict or 0.0
        lift_v = lift or 0.0
        mi_v = mi or 0.0
        perm_v = perm or 0.0
        res = resolve_rate or 0.0

        if eligible <= 0 and coverage < 0.5:
            return "C"
        if (
            coverage >= 0.9
            and s2s >= 0.15
            and (lift_v >= 1.2 or mi_v >= 0.02 or perm_v >= 0.05)
        ):
            return "S"
        if coverage >= 0.8 and (
            s2s > 0 or lift_v >= 1.1 or mi_v >= 0.01 or perm_v >= 0.02
        ):
            return "A"
        if coverage >= 0.5 or (eligible > 0 and res > 0):
            return "B"
        return "C"

    def _simulate_strategies(
        self,
        *,
        tie_races: list[dict[str, Any]],
        all_races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        priority_order: list[str],
        ordered: list[FeatureImportance],
        baseline_strict: int,
        baseline_soft: int,
    ) -> list[ShadowStrategyResult]:
        strategies: list[tuple[str, str, list[str]]] = [
            ("baseline", "model_rank→win_prob→horse_number (no evidence)", []),
            (
                "tier_cascade",
                "Evidence Priority cascade (Tier S→A→B→C by composite)",
                priority_order,
            ),
            (
                "market_cascade",
                "popularity → win_odds → expected_popularity",
                ["popularity", "win_odds", "expected_popularity"],
            ),
            (
                "popularity_then_trainer",
                "popularity → trainer → sire",
                ["popularity", "trainer", "sire"],
            ),
            (
                "horse_intel",
                "sire → damsire → breeder → trainer → owner",
                ["sire", "damsire", "breeder", "trainer", "owner"],
            ),
            (
                "oikiri_then_market",
                "oikiri_rating → oikiri_time → popularity",
                ["oikiri_rating", "oikiri_time", "popularity"],
            ),
        ]
        # single-feature strategies for Tier S/A
        for m in ordered:
            if m.tier in ("S", "A"):
                strategies.append(
                    (f"single_{m.feature_id}", f"single feature: {m.feature_id}", [m.feature_id])
                )

        results: list[ShadowStrategyResult] = []
        for sid, desc, order in strategies:
            results.append(
                self._eval_strategy(
                    strategy_id=sid,
                    description=desc,
                    feature_order=order,
                    tie_races=tie_races,
                    all_races=all_races,
                    fmap=fmap,
                    baseline_strict=baseline_strict,
                    baseline_soft=baseline_soft,
                )
            )
        results.sort(key=lambda s: (s.strict_delta, s.soft_delta, s.strict_rate), reverse=True)
        return results

    def _eval_strategy(
        self,
        *,
        strategy_id: str,
        description: str,
        feature_order: list[str],
        tie_races: list[dict[str, Any]],
        all_races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        baseline_strict: int,
        baseline_soft: int,
    ) -> ShadowStrategyResult:
        n = len(tie_races)
        strict_n = 0
        soft_n = 0
        resolved = 0
        fallback = 0
        for rec in tie_races:
            g = rec["tie_group"]
            soft_n += int(rec["soft"])
            if not feature_order:
                pick = unique_top_pick(rec["runners"])
                if pick == rec["winner"]:
                    strict_n += 1
                continue

            values_by_feature = {
                fid: fmap.get(rec["snapshot_id"], {}).get(fid, {})
                for fid in feature_order
            }
            loo_priors: dict[str, dict[str, float]] = {}
            for fid in feature_order:
                if fid in CATEGORICAL_FEATURES:
                    loo_priors[fid] = self.prior_for_race(
                        feature_id=fid,
                        exclude_race_id=rec["race_id"],
                        races=all_races,
                        fmap=fmap,
                    )
            pick, status, _ = cascade_resolve(
                g, feature_order, values_by_feature, loo_priors
            )
            if status == "resolved":
                resolved += 1
            else:
                fallback += 1
            if pick == rec["winner"]:
                strict_n += 1

        strict_rate = strict_n / n if n else 0.0
        soft_rate = soft_n / n if n else 0.0
        base_s = baseline_strict / n if n else 0.0
        base_o = baseline_soft / n if n else 0.0
        return ShadowStrategyResult(
            strategy_id=strategy_id,
            description=description,
            n_tie_races=n,
            resolved=resolved,
            fallback=fallback,
            strict_hits=strict_n,
            soft_hits=soft_n,
            baseline_strict=baseline_strict,
            baseline_soft=baseline_soft,
            strict_improve=strict_n - baseline_strict,
            soft_improve=0,  # soft set unchanged by resolver
            strict_rate=round(strict_rate, 6),
            soft_rate=round(soft_rate, 6),
            strict_delta=round(strict_rate - base_s, 6),
            soft_delta=round(soft_rate - base_o, 6),
        )

    @staticmethod
    def _definitions() -> dict[str, str]:
        return {
            "scope": "Tie races only (|G|>=2)",
            "coverage": "filled/total cells on complete snapshots",
            "tie_resolution_rate": "unique argmax score within G among eligible",
            "soft_to_strict_improve_rate": "recovered Soft∧¬Strict / Soft∧¬Strict on tie races",
            "information_gain": "mean bits log2(|G|)-log2(remaining) after feature partition",
            "mutual_information": "MI(feature_bin_or_category; is_winner) over horses in tie groups",
            "permutation_importance": "drop in correct-resolve rate when shuffling feature within G (LOO prior)",
            "lift": "P(correct|resolved) / E[1/|G|] on eligible resolved races",
            "categorical_ranking": "leave-one-out Laplace win prior P(win|category) excluding eval race",
            "tiers": "S/A/B/C from coverage + soft→strict + lift/MI/perm gates",
            "shadow_only": "strategies do not write Prediction ranks",
        }


def write_importance_csv(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "rank",
        "tier",
        "feature_id",
        "composite_score",
        "coverage",
        "missing_rate",
        "tie_races",
        "tie_eligible",
        "tie_resolved",
        "tie_resolution_rate",
        "tie_correct",
        "strict_hit",
        "soft_hit",
        "soft_hit_rate",
        "soft_to_strict_improve_rate",
        "soft_to_strict_recovered",
        "information_gain_mean",
        "mutual_information",
        "permutation_importance",
        "lift",
        "winner_rank_mean",
        "within_tie_diversity_rate",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in report.get("features") or []:
            w.writerow({k: row.get(k) for k in fields})


def write_tier_csv(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "priority_rank",
        "tier",
        "feature_id",
        "composite_score",
        "soft_to_strict_improve_rate",
        "lift",
        "mutual_information",
        "permutation_importance",
        "coverage",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for i, fid in enumerate(report.get("evidence_priority") or [], start=1):
            feat = next(
                (f for f in (report.get("features") or []) if f["feature_id"] == fid),
                {},
            )
            w.writerow(
                {
                    "priority_rank": i,
                    "tier": feat.get("tier"),
                    "feature_id": fid,
                    "composite_score": feat.get("composite_score"),
                    "soft_to_strict_improve_rate": feat.get("soft_to_strict_improve_rate"),
                    "lift": feat.get("lift"),
                    "mutual_information": feat.get("mutual_information"),
                    "permutation_importance": feat.get("permutation_importance"),
                    "coverage": feat.get("coverage"),
                }
            )


def write_ranking_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = report["corpus"]
    lines: list[str] = []
    lines.append("# Version10.4 Research — Evidence Ranking Engine")
    lines.append("")
    lines.append(f"**Date:** {report.get('analyzed_at')}  ")
    lines.append("**Type:** Statistical Evidence Priority（Prediction 順位は変更しない）  ")
    lines.append("**Scope:** Tie races only (`|G| >= 2`)  ")
    lines.append(
        "**Hard Lock:** PE / CE / AI Score / Prediction Logic / ResultAutomation / Challenge **変更禁止**  "
    )
    lines.append("**Resolver:** 本番未実装（Shadow Simulation のみ）")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 0. Verdict")
    lines.append("")
    lines.append("| 指標 | 値 |")
    lines.append("|------|----|")
    lines.append(f"| 全評価レース | {c.get('n_races_all')} |")
    lines.append(f"| Tie レース（|G|≥2） | **{c.get('n_tie_races')}** |")
    lines.append(
        f"| Baseline Strict（Tie） | {c.get('baseline_strict_tie')}/{c.get('n_tie_races')} |"
    )
    lines.append(
        f"| Baseline Soft（Tie） | {c.get('baseline_soft_tie')}/{c.get('n_tie_races')} |"
    )
    lines.append(f"| Soft∧¬Strict（Tie） | {c.get('soft_not_strict_tie')} |")
    lines.append(f"| 平均タイ頭数 | {(c.get('avg_tie_size') or 0):.3f} |")
    lines.append("")
    lines.append("### Evidence Priority（自動生成）")
    lines.append("")
    lines.append("| Priority | Tier | Feature | Score | Soft→Strict | Lift | MI | Perm | Coverage |")
    lines.append("|--------:|:----:|---------|------:|------------:|-----:|---:|-----:|---------:|")
    for i, fid in enumerate(report.get("evidence_priority") or [], start=1):
        f = next((x for x in report["features"] if x["feature_id"] == fid), {})
        lines.append(
            f"| {i} | {f.get('tier')} | `{fid}` | {f.get('composite_score')} | "
            f"{_pct(f.get('soft_to_strict_improve_rate'))} | {_num(f.get('lift'))} | "
            f"{_num(f.get('mutual_information'))} | {_num(f.get('permutation_importance'))} | "
            f"{_pct(f.get('coverage'))} |"
        )
    lines.append("")
    tiers = report.get("tiers") or {}
    lines.append(
        f"- **Tier S:** {', '.join(f'`{x}`' for x in tiers.get('S') or []) or '—'}  "
    )
    lines.append(
        f"- **Tier A:** {', '.join(f'`{x}`' for x in tiers.get('A') or []) or '—'}  "
    )
    lines.append(
        f"- **Tier B:** {', '.join(f'`{x}`' for x in tiers.get('B') or []) or '—'}  "
    )
    lines.append(
        f"- **Tier C:** {', '.join(f'`{x}`' for x in tiers.get('C') or []) or '—'}  "
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. 定義")
    lines.append("")
    for k, v in (report.get("definitions") or {}).items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("### Tier ゲート（統計のみ）")
    lines.append("")
    lines.append("| Tier | 条件 |")
    lines.append("|:----:|------|")
    lines.append(
        "| S | coverage≥0.9 ∧ Soft→Strict≥0.15 ∧ (lift≥1.2 ∨ MI≥0.02 ∨ perm≥0.05) |"
    )
    lines.append(
        "| A | coverage≥0.8 ∧ (Soft→Strict>0 ∨ lift≥1.1 ∨ MI≥0.01 ∨ perm≥0.02) |"
    )
    lines.append("| B | coverage≥0.5 ∨ Tie eligible あり |")
    lines.append("| C | 上記以外 / 低 Coverage |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Feature Importance 詳細")
    lines.append("")
    for f in report.get("features") or []:
        lines.append(f"### `{f['feature_id']}` — Tier {f.get('tier')}")
        lines.append("")
        lines.append("| 指標 | 値 |")
        lines.append("|------|----|")
        for key in [
            "rank",
            "composite_score",
            "coverage",
            "missing_rate",
            "tie_eligible",
            "tie_resolution_rate",
            "tie_correct",
            "strict_hit",
            "soft_hit",
            "soft_to_strict_improve_rate",
            "information_gain_mean",
            "mutual_information",
            "permutation_importance",
            "lift",
            "winner_rank_mean",
            "within_tie_diversity_rate",
            "notes",
        ]:
            val = f.get(key)
            if key in (
                "coverage",
                "missing_rate",
                "tie_resolution_rate",
                "soft_to_strict_improve_rate",
            ):
                val = _pct(val) if not isinstance(val, str) else val
            lines.append(f"| {key} | {val} |")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. 【Decision】")
    lines.append("")
    lines.append("```")
    lines.append("Action Type: Evidence Ranking (shadow statistics)")
    lines.append("Implementation Required: Ranking Engine only")
    lines.append("Deployment Required: Optional CLI")
    lines.append("Production Required: No (Prediction unchanged)")
    lines.append("Resolver Required: No (V10.4 does not ship Resolver)")
    lines.append("Risk: Low")
    lines.append("Expected Next Action: Use Evidence Priority in future Tie Resolver design")
    lines.append("```")
    lines.append("")
    lines.append("Related: `v104-feature-importance.csv` · `v104-tier-ranking.csv` · `v104-shadow-resolver.md`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_shadow_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Version10.4 Research — Shadow Resolver Simulation")
    lines.append("")
    lines.append(f"**Date:** {report.get('analyzed_at')}  ")
    lines.append("**重要:** Prediction 順位は変更しない。本番 Resolver は未実装。  ")
    lines.append("**対象:** Tie races only")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 0. Strategy 比較")
    lines.append("")
    lines.append(
        "| Rank | Strategy | Strict | Soft | StrictΔ | Resolved | Fallback | 説明 |"
    )
    lines.append("|-----:|----------|-------:|-----:|--------:|---------:|---------:|------|")
    for i, s in enumerate(report.get("shadow_strategies") or [], start=1):
        lines.append(
            f"| {i} | `{s['strategy_id']}` | {_pct(s.get('strict_rate'))} | "
            f"{_pct(s.get('soft_rate'))} | {s.get('strict_improve'):+d} "
            f"({_pct(s.get('strict_delta'))}) | {s.get('resolved')} | {s.get('fallback')} | "
            f"{s.get('description')} |"
        )
    lines.append("")
    lines.append("Soft Hit はタイ群所属で決まるため、Resolver では **SoftΔ = 0**（集合は不変）。")
    lines.append("評価の主指標は **Strict 改善**（Soft∧¬Strict の回収）。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Evidence Priority Cascade")
    lines.append("")
    lines.append("```")
    lines.append(" → ".join(report.get("evidence_priority") or []))
    lines.append("```")
    lines.append("")
    lines.append("Fail-open: 特徴で解けない場合は既存 baseline（馬番タイブレーク）へフォールバック。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. 解釈")
    lines.append("")
    best = (report.get("shadow_strategies") or [None])[0]
    if best:
        lines.append(
            f"1. 最良 Shadow 戦略は **`{best['strategy_id']}`** "
            f"（Strict {best.get('strict_hits')}/{best.get('n_tie_races')}, "
            f"Δ {best.get('strict_improve'):+d}）。"
        )
    lines.append("2. 本番 Prediction Bundle への書き込みは行っていない。")
    lines.append("3. 次フェーズで Resolver を実装する場合、本 Priority / Tier を入力契約とする。")
    lines.append("")
    lines.append("```")
    lines.append("Resolver Production: NOT IMPLEMENTED (V10.4)")
    lines.append("Prediction Mutation: FORBIDDEN")
    lines.append("```")
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


def run_and_write(
    *,
    ranking_md: Path | None = None,
    importance_csv: Path | None = None,
    tier_csv: Path | None = None,
    shadow_md: Path | None = None,
    json_path: Path | None = None,
) -> dict[str, Any]:
    engine = EvidenceRankingEngine()
    report = engine.analyze()
    root = repo_root()
    ranking_md = ranking_md or (root / "docs/research/v104-evidence-ranking.md")
    importance_csv = importance_csv or (
        root / "docs/research/v104-feature-importance.csv"
    )
    tier_csv = tier_csv or (root / "docs/research/v104-tier-ranking.csv")
    shadow_md = shadow_md or (root / "docs/research/v104-shadow-resolver.md")
    json_path = json_path or (
        root / "evidence/research/reports/v104-evidence-ranking.json"
    )

    write_ranking_md(report, ranking_md)
    write_importance_csv(report, importance_csv)
    write_tier_csv(report, tier_csv)
    write_shadow_md(report, shadow_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "ranking_md": str(ranking_md),
        "importance_csv": str(importance_csv),
        "tier_csv": str(tier_csv),
        "shadow_md": str(shadow_md),
        "json": str(json_path),
    }
    return report
