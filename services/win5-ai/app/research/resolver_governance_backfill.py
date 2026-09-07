# -*- coding: utf-8 -*-
"""
Version10.7 Research Expansion (Backfill Replay)

Replay Prediction history in chronological order.
For each tie race:
  - Use only Evidence where evidence.observed_at <= prediction.created_at
  - Re-run Evidence Ranking (tiers / evidence_priority) using only available Evidence
  - Run Shadow Resolver (shadow only)
  - Run Governance decision (shadow only)

Production mutation is forbidden. This module is Research-only.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from ..data.db import connect, migrate
from .analyzer import _parse_json_value, extract_runners, strict_hit, soft_hit, tie_group, unique_top_pick
from .config import evidence_root, repo_root
from .ranking_engine import (
    CATEGORICAL_FEATURES,
    EvidenceRankingEngine,
    feature_score,
    resolve_by_score,
)
from .resolver_governance import ADOPTION_GATE, TIER_WEIGHT, _clip01
from .ranking_engine import cascade_resolve


V107_DEFAULT_MAX_TIE_RACES = 150


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _pct(x: float | None) -> str:
    if x is None:
        return "N/A"
    return f"{x * 100:.1f}%"


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


def _parse_dt(dt_text: Any) -> datetime | None:
    if dt_text is None:
        return None
    try:
        s = str(dt_text).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _period_month(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _period_year(dt: datetime) -> str:
    return dt.strftime("%Y")


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


def _age_group_key(class_label: str | None) -> str:
    s = str(class_label or "").strip()
    if "2歳新馬" in s or s == "新馬":
        return "age_group:2yo_newcomer"
    if "2歳未勝利" in s:
        return "age_group:2yo_maiden"
    if "3歳未勝利" in s:
        return "age_group:3yo_maiden"
    if any(
        x in s
        for x in (
            "4歳以上",
            "3歳以上",
            "古馬",
            "1勝クラス",
            "2勝クラス",
            "3勝クラス",
            "オープン",
            "G1",
            "G2",
            "G3",
            "L",
        )
    ):
        return "age_group:older"
    return "age_group:unknown"


def _class_key(class_label: str | None) -> str:
    s = str(class_label or "").strip()
    return f"class:{s}" if s else "class:unknown"


def _segment_keys(meta: dict[str, Any]) -> list[str]:
    keys = ["all_tie"]
    keys.append(_age_group_key(meta.get("class_label")))
    keys.append(_class_key(meta.get("class_label")))
    keys.append(_surface_key(meta.get("surface")))
    keys.append(_distance_bucket(meta.get("distance")))
    venue = str(meta.get("venue") or "").strip()
    keys.append(f"venue:{venue}" if venue else "venue:unknown")
    return keys


@dataclass
class BackfillTieRace:
    prediction_id: int
    prediction_created_at: datetime
    race_id: str
    snapshot_id: str | None
    race_meta: dict[str, Any]
    winner: int
    runners: list[dict[str, Any]]
    tie_group: list[dict[str, Any]]
    tie_size: int
    strict: bool
    soft: bool
    soft_not_strict: bool

    # precomputed for ranks and output
    prediction_pick: int | None


class ResolverGovernanceBackfill:
    def __init__(
        self,
        *,
        perm_shuffles: int = 5,
        max_tie_races: int = V107_DEFAULT_MAX_TIE_RACES,
        seed: int = 107,
    ) -> None:
        self.perm_shuffles = perm_shuffles
        self.max_tie_races = max_tie_races
        self.seed = seed
        self.features = EvidenceRankingEngine().features

    def _load_tie_races(self) -> list[BackfillTieRace]:
        migrate()
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT
                  p.id AS prediction_id,
                  p.created_at AS prediction_created_at,
                  COALESCE(s.race_id, p.race_id) AS race_id,
                  s.snapshot_id,
                  rr.race_date,
                  rr.venue,
                  rr.surface,
                  rr.distance,
                  rr.winner_horse_number,
                  rs.class_label,
                  p.bundle_json
                FROM predictions p
                LEFT JOIN research_prediction_snapshots s ON s.prediction_id = p.id
                JOIN race_results rr ON rr.race_id = COALESCE(s.race_id, p.race_id)
                LEFT JOIN races rs ON rs.race_id = rr.race_id
                WHERE rr.winner_horse_number IS NOT NULL
                  AND COALESCE(s.race_id, p.race_id) NOT LIKE '2099%'
                ORDER BY p.created_at ASC, p.id ASC
                """
            ).fetchall()

            out: list[BackfillTieRace] = []
            for r in rows:
                dt = _parse_dt(r["prediction_created_at"])
                if not dt:
                    continue
                bundle = json.loads(r["bundle_json"] or "{}")
                runners = extract_runners(bundle)
                if not runners:
                    continue
                g = tie_group(runners)
                if len(g) < 2:
                    continue
                winner = int(r["winner_horse_number"])
                snapshot_id = r["snapshot_id"]
                pred_pick = unique_top_pick(runners)
                out.append(
                    BackfillTieRace(
                        prediction_id=int(r["prediction_id"]),
                        prediction_created_at=dt,
                        race_id=str(r["race_id"]),
                        snapshot_id=str(snapshot_id)
                        if snapshot_id is not None
                        else None,
                        race_meta={
                            "race_date": r["race_date"],
                            "venue": r["venue"],
                            "surface": r["surface"],
                            "distance": r["distance"],
                            "class_label": r["class_label"],
                        },
                        winner=winner,
                        runners=runners,
                        tie_group=g,
                        tie_size=len(g),
                        strict=bool(strict_hit(runners, winner)),
                        soft=bool(soft_hit(runners, winner)),
                        soft_not_strict=bool(
                            soft_hit(runners, winner) and not strict_hit(runners, winner)
                        ),
                        prediction_pick=pred_pick,
                    )
                )
                if len(out) >= self.max_tie_races:
                    break
            return out
        finally:
            conn.close()

    def _load_time_filtered_fmap(
        self, tie_races: list[BackfillTieRace]
    ) -> dict[str, dict[str, dict[int, Any]]]:
        if not tie_races:
            return {}
        sid_by_pred: dict[int, str] = {}
        pred_created_by_id: dict[int, datetime] = {}
        for tr in tie_races:
            if tr.snapshot_id is None:
                continue
            sid_by_pred[tr.prediction_id] = tr.snapshot_id
            pred_created_by_id[tr.prediction_id] = tr.prediction_created_at

        if not sid_by_pred:
            return {}
        snapshot_ids = list({sid for sid in sid_by_pred.values()})

        placeholders = ",".join("?" * len(snapshot_ids))
        feature_list = list(self.features)
        feat_ph = ",".join("?" * len(feature_list))

        conn = connect()
        try:
            # observed_at <= prediction_created_at (per prediction) enforced by SQL join
            rows = conn.execute(
                f"""
                SELECT
                  f.snapshot_id,
                  f.feature_id,
                  f.horse_number,
                  f.value_json,
                  f.observed_at
                FROM research_snapshot_features f
                JOIN research_prediction_snapshots s ON s.snapshot_id = f.snapshot_id
                JOIN predictions p ON p.id = s.prediction_id
                WHERE f.snapshot_id IN ({placeholders})
                  AND f.feature_id IN ({feat_ph})
                  AND f.value_json IS NOT NULL
                  AND TRIM(f.value_json) != ''
                  AND LOWER(TRIM(f.value_json)) != 'null'
                  AND f.observed_at IS NOT NULL
                  AND f.observed_at <= p.created_at
                """,
                snapshot_ids + feature_list,
            ).fetchall()

            fmap: dict[str, dict[str, dict[int, Any]]] = defaultdict(
                lambda: defaultdict(dict)
            )
            for row in rows:
                sid = str(row["snapshot_id"])
                fid = str(row["feature_id"])
                hn = int(row["horse_number"])
                val = _parse_json_value(row["value_json"])
                fmap[sid][fid][hn] = val
            return fmap
        finally:
            conn.close()

    def _load_snapshot_feature_totals(
        self, tie_races: list[BackfillTieRace]
    ) -> dict[str, dict[str, tuple[int, int]]]:
        """
        snapshot_id -> feature_id -> (filled, total)
        filled/total are evaluated with observed_at <= prediction.created_at.
        """
        if not tie_races:
            return {}
        snapshot_ids = list({tr.snapshot_id for tr in tie_races if tr.snapshot_id})
        if not snapshot_ids:
            return {}
        placeholders = ",".join("?" * len(snapshot_ids))
        feature_list = list(self.features)
        feat_ph = ",".join("?" * len(feature_list))

        conn = connect()
        try:
            rows = conn.execute(
                f"""
                SELECT
                  f.snapshot_id,
                  f.feature_id,
                  COUNT(*) AS total,
                  SUM(
                    CASE
                      WHEN f.value_json IS NOT NULL
                       AND TRIM(f.value_json) != ''
                       AND LOWER(TRIM(f.value_json)) != 'null'
                       AND f.observed_at IS NOT NULL
                       AND f.observed_at <= p.created_at
                      THEN 1 ELSE 0
                    END
                  ) AS filled
                FROM research_snapshot_features f
                JOIN research_prediction_snapshots s ON s.snapshot_id = f.snapshot_id
                JOIN predictions p ON p.id = s.prediction_id
                WHERE f.snapshot_id IN ({placeholders})
                  AND f.feature_id IN ({feat_ph})
                GROUP BY f.snapshot_id, f.feature_id
                """,
                snapshot_ids + feature_list,
            ).fetchall()

            out: dict[str, dict[str, tuple[int, int]]] = defaultdict(dict)
            for row in rows:
                sid = str(row["snapshot_id"])
                fid = str(row["feature_id"])
                filled = int(row["filled"] or 0)
                total = int(row["total"] or 0)
                out[sid][fid] = (filled, total)
            return out
        finally:
            conn.close()

    def _coverage_for_feature(
        self,
        *,
        feature_id: str,
        coverage_total: dict[str, int],
        coverage_filled: dict[str, int],
    ) -> float:
        total = int(coverage_total.get(feature_id) or 0)
        filled = int(coverage_filled.get(feature_id) or 0)
        if total <= 0:
            return 0.0
        return filled / total

    def _compute_evidence_ranking(
        self,
        *,
        engine: EvidenceRankingEngine,
        cumulative_races: list[BackfillTieRace],
        cumulative_tie_races: list[BackfillTieRace],
        fmap: dict[str, dict[str, dict[int, Any]]],
        coverage_total: dict[str, int],
        coverage_filled: dict[str, int],
    ) -> dict[str, Any]:
        """
        Compute evidence_priority and per-feature tier/coverage for governance.
        We use the same underlying metrics as EvidenceRankingEngine, but coverage
        is time-filtered (observed_at <= prediction_created_at) and limited to
        tie races within backfill replay.
        """
        # Build ranking-engine expected race dicts
        # ranking_engine expects: snapshot_id, prediction_id, race_id, winner, runners, tie_group, strict/soft/soft_not_strict
        all_races = [
            {
                "snapshot_id": tr.snapshot_id,
                "prediction_id": tr.prediction_id,
                "race_id": tr.race_id,
                "winner": tr.winner,
                "runners": tr.runners,
                "tie_group": tr.tie_group,
                "tie_size": tr.tie_size,
                "strict": tr.strict,
                "soft": tr.soft,
                "soft_not_strict": tr.soft_not_strict,
            }
            for tr in cumulative_races
        ]
        tie_races = [
            {
                "snapshot_id": tr.snapshot_id,
                "prediction_id": tr.prediction_id,
                "race_id": tr.race_id,
                "winner": tr.winner,
                "runners": tr.runners,
                "tie_group": tr.tie_group,
                "tie_size": tr.tie_size,
                "strict": tr.strict,
                "soft": tr.soft,
                "soft_not_strict": tr.soft_not_strict,
            }
            for tr in cumulative_tie_races
        ]

        baseline_strict = sum(1 for r in tie_races if r["strict"])
        baseline_soft = sum(1 for r in tie_races if r["soft"])
        soft_not_strict = sum(1 for r in tie_races if r["soft_not_strict"])

        cat_priors_global = engine.build_categorical_priors(all_races, fmap)

        # Build feature meta with tiers
        importances = []
        for fid in engine.features:
            coverage = self._coverage_for_feature(
                feature_id=fid,
                coverage_total=coverage_total,
                coverage_filled=coverage_filled,
            )
            metrics = engine._feature_tie_metrics(
                feature_id=fid,
                tie_races=tie_races,
                all_races=all_races,
                fmap=fmap,
                soft_not_strict=soft_not_strict,
                baseline_strict=baseline_strict,
                baseline_soft=baseline_soft,
            )
            mi = engine._mutual_information(
                feature_id=fid,
                tie_races=tie_races,
                fmap=fmap,
                cat_prior=cat_priors_global.get(fid),
            )
            perm = engine._permutation_importance(
                feature_id=fid,
                tie_races=tie_races,
                all_races=all_races,
                fmap=fmap,
            )
            lift = metrics["lift"]
            soft2strict = metrics["soft_to_strict_improve_rate"]
            resolve_rate = metrics["tie_resolution_rate"]
            ig = metrics["information_gain_mean"]

            composite = engine._composite_score(
                coverage=coverage,
                soft_to_strict=soft2strict,
                lift=lift,
                mi=mi,
                perm=perm,
                resolve_rate=resolve_rate,
                ig=ig,
            )
            tier = engine._assign_tier(
                coverage=coverage,
                soft_to_strict=soft2strict,
                lift=lift,
                mi=mi,
                perm=perm,
                resolve_rate=resolve_rate,
                eligible=metrics["tie_eligible"],
            )
            notes = []
            if coverage <= 0:
                notes.append("coverage=0")
            if fid in CATEGORICAL_FEATURES:
                notes.append("loo_cat_prior")
            importances.append(
                {
                    "feature_id": fid,
                    "coverage": coverage,
                    "missing_rate": 1.0 - coverage if coverage else 1.0,
                    "tier": tier,
                    "composite_score": composite,
                    "metrics": metrics,
                    "lift": lift,
                    "soft_to_strict_improve_rate": soft2strict,
                    "mutual_information": mi,
                    "permutation_importance": perm,
                }
            )

        ordered = sorted(
            importances,
            key=lambda m: (
                {"S": 4, "A": 3, "B": 2, "C": 1}.get(m["tier"], 0),
                m["composite_score"],
                m["coverage"],
            ),
            reverse=True,
        )
        priority_order = [m["feature_id"] for m in ordered if m["tier"] in ("S", "A", "B")]
        for m in ordered:
            if m["feature_id"] not in priority_order:
                priority_order.append(m["feature_id"])

        feature_meta = {m["feature_id"]: m for m in ordered}
        return {
            "ordered": ordered,
            "evidence_priority": priority_order,
            "feature_meta": feature_meta,
        }

    def _shadow_for_tie_race(
        self,
        *,
        engine: EvidenceRankingEngine,
        tie_race: BackfillTieRace,
        cumulative_races: list[BackfillTieRace],
        cumulative_tie_races: list[BackfillTieRace],
        evidence_priority: list[str],
        fmap: dict[str, dict[str, dict[int, Any]]],
        feature_meta: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        group = list(tie_race.tie_group)
        values_by_feature = {
            fid: fmap.get(tie_race.snapshot_id or "", {}).get(fid, {})
            for fid in evidence_priority
        }
        loo_priors: dict[str, dict[str, float]] = {}
        # Build engine races dicts for priors
        all_races = [
            {
                "snapshot_id": tr.snapshot_id,
                "prediction_id": tr.prediction_id,
                "race_id": tr.race_id,
                "winner": tr.winner,
                "runners": tr.runners,
                "tie_group": tr.tie_group,
                "tie_size": tr.tie_size,
                "strict": tr.strict,
                "soft": tr.soft,
                "soft_not_strict": tr.soft_not_strict,
            }
            for tr in cumulative_races
        ]
        for fid in evidence_priority:
            if fid in CATEGORICAL_FEATURES:
                loo_priors[fid] = engine.prior_for_race(
                    feature_id=fid,
                    exclude_race_id=tie_race.race_id,
                    races=all_races,
                    fmap=fmap,
                )

        pick, status, used_feature = cascade_resolve(
            group,
            evidence_priority,
            values_by_feature,
            loo_priors,
        )
        shadow_pick = pick
        base_ok = tie_race.prediction_pick == tie_race.winner
        shadow_ok = shadow_pick == tie_race.winner
        if shadow_ok and not base_ok:
            outcome = "win"
        elif base_ok and not shadow_ok:
            outcome = "lose"
        else:
            outcome = "draw"

        used_tier = None
        if used_feature:
            used_tier = feature_meta.get(used_feature, {}).get("tier")

        confidence = self._confidence_for_record(
            engine=engine,
            tie_race=tie_race,
            cumulative_races=cumulative_races,
            fmap=fmap,
            evidence_priority=evidence_priority,
            feature_meta=feature_meta,
            shadow_pick=shadow_pick,
            used_feature=used_feature,
            used_tier=used_tier,
        )

        return {
            "prediction_pick": tie_race.prediction_pick,
            "shadow_pick": shadow_pick,
            "outcome": outcome,
            "used_feature": used_feature,
            "used_tier": used_tier,
            "cascade_stop": used_feature or "fallback",
            "confidence": confidence["confidence"],
            "coverage_score": confidence["coverage_score"],
            "missing_score": confidence["missing_score"],
            "evidence_match_ratio": confidence["evidence_match_ratio"],
            "tier_agreement": confidence["tier_agreement"],
        }

    def _confidence_for_record(
        self,
        *,
        engine: EvidenceRankingEngine,
        tie_race: BackfillTieRace,
        cumulative_races: list[BackfillTieRace],
        fmap: dict[str, dict[str, dict[int, Any]]],
        evidence_priority: list[str],
        feature_meta: dict[str, dict[str, Any]],
        shadow_pick: int,
        used_feature: str | None,
        used_tier: str | None,
    ) -> dict[str, Any]:
        stop_depth = (
            evidence_priority.index(used_feature) + 1
            if used_feature in evidence_priority
            else min(5, len(evidence_priority))
        )
        considered = evidence_priority[:stop_depth]

        values_by_feature = fmap.get(tie_race.snapshot_id or "", {})
        g = tie_race.tie_group
        all_races = [
            {
                "snapshot_id": tr.snapshot_id,
                "prediction_id": tr.prediction_id,
                "race_id": tr.race_id,
                "winner": tr.winner,
                "runners": tr.runners,
                "tie_group": tr.tie_group,
                "tie_size": tr.tie_size,
                "strict": tr.strict,
                "soft": tr.soft,
                "soft_not_strict": tr.soft_not_strict,
            }
            for tr in cumulative_races
        ]

        complete_count = 0
        support_count = 0
        support_tier_weight_sum = 0.0

        coverage_vals: list[float] = []
        for fid in considered:
            meta = feature_meta.get(fid) or {}
            coverage_vals.append(float(meta.get("coverage") or 0.0))

        for fid in considered:
            vals = values_by_feature.get(fid, {})
            cat_prior = None
            if fid in CATEGORICAL_FEATURES:
                cat_prior = engine.prior_for_race(
                    feature_id=fid,
                    exclude_race_id=tie_race.race_id,
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
            if any(v is None for v in scores.values()):
                continue
            complete_count += 1
            pick, status = resolve_by_score(g, scores)
            if status == "resolved" and pick == shadow_pick:
                support_count += 1
                tier = feature_meta.get(fid, {}).get("tier") or "C"
                support_tier_weight_sum += TIER_WEIGHT.get(str(tier), 0.4)

        total = max(len(considered), 1)
        evidence_match_ratio = support_count / max(complete_count, 1)
        tier_agreement = (
            support_tier_weight_sum / support_count
            if support_count
            else TIER_WEIGHT.get(str(used_tier or "C"), 0.4)
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
            "evidence_match_ratio": round(evidence_match_ratio, 6),
            "tier_agreement": round(tier_agreement, 6),
            "coverage_score": round(coverage_score, 6),
            "missing_score": round(missing_score, 6),
        }

    def _gate_status(self, *, n_tie: int, win: int, lose: int, strict_impr: int, coverage_avg: float, conf_p50: float) -> str:
        if n_tie < ADOPTION_GATE["min_tie_races"]:
            return "sample_insufficient"
        win_rate = win / n_tie if n_tie else 0.0
        lose_rate = lose / n_tie if n_tie else 0.0
        strict_impr_rate = strict_impr / n_tie if n_tie else 0.0
        roi_change = strict_impr_rate
        # Confidence median is already p50 in [0,1]
        ok = (
            win_rate >= ADOPTION_GATE["min_resolver_win_rate"]
            and lose_rate <= ADOPTION_GATE["max_resolver_lose_rate"]
            and strict_impr_rate >= ADOPTION_GATE["min_strict_improvement_rate"]
            and roi_change >= ADOPTION_GATE["min_roi_change"]
            and coverage_avg >= ADOPTION_GATE["min_coverage"]
            and conf_p50 >= ADOPTION_GATE["min_confidence_median"]
        )
        return "eligible" if ok else "rejected"

    def run(self) -> dict[str, Any]:
        tie_races = self._load_tie_races()
        fmap = self._load_time_filtered_fmap(tie_races)
        snapshot_stats = self._load_snapshot_feature_totals(tie_races)

        engine = EvidenceRankingEngine(perm_shuffles=self.perm_shuffles, seed=self.seed)

        cumulative_races: list[BackfillTieRace] = []
        cumulative_tie_races: list[BackfillTieRace] = []

        # Running coverage totals for each feature_id
        coverage_total: dict[str, int] = {fid: 0 for fid in self.features}
        coverage_filled: dict[str, int] = {fid: 0 for fid in self.features}

        # Records for each tie race (resolved with evidence ranking at that time)
        evaluated: list[dict[str, Any]] = []

        # Chronological replay
        tie_races_sorted = sorted(tie_races, key=lambda tr: tr.prediction_created_at)
        for tr in tie_races_sorted:
            cumulative_races.append(tr)
            cumulative_tie_races.append(tr)

            # Update coverage totals using snapshot_stats (or estimate if snapshot missing)
            if tr.snapshot_id and tr.snapshot_id in snapshot_stats:
                for fid in self.features:
                    filled, total = snapshot_stats[tr.snapshot_id].get(fid, (0, 0))
                    coverage_total[fid] += int(total or 0)
                    coverage_filled[fid] += int(filled or 0)
            else:
                # Estimate: each runner has one cell per feature
                denom = len(tr.runners)
                for fid in self.features:
                    coverage_total[fid] += denom
                    coverage_filled[fid] += 0

            # Evidence ranking with current cumulative tie corpus
            ranking = self._compute_evidence_ranking(
                engine=engine,
                cumulative_races=cumulative_races,
                cumulative_tie_races=cumulative_tie_races,
                fmap=fmap,
                coverage_total=coverage_total,
                coverage_filled=coverage_filled,
            )

            # Shadow resolver evaluation for current tie race
            shadow = self._shadow_for_tie_race(
                engine=engine,
                tie_race=tr,
                cumulative_races=cumulative_races,
                cumulative_tie_races=cumulative_tie_races,
                evidence_priority=ranking["evidence_priority"],
                fmap=fmap,
                feature_meta=ranking["feature_meta"],
            )

            baseline_strict = 1 if tr.prediction_pick == tr.winner else 0
            shadow_strict = 1 if shadow["shadow_pick"] == tr.winner else 0

            evaluated.append(
                {
                    "prediction_id": tr.prediction_id,
                    "prediction_created_at": tr.prediction_created_at.isoformat(),
                    "race_id": tr.race_id,
                    "winner": tr.winner,
                    "prediction_pick": tr.prediction_pick,
                    "shadow_pick": shadow["shadow_pick"],
                    "outcome": shadow["outcome"],
                    "used_feature": shadow["used_feature"],
                    "used_tier": shadow["used_tier"],
                    "cascade_stop": shadow["cascade_stop"],
                    "confidence": shadow["confidence"],
                    "coverage_score": shadow["coverage_score"],
                    "missing_score": shadow["missing_score"],
                    "evidence_match_ratio": shadow["evidence_match_ratio"],
                    "tier_agreement": shadow["tier_agreement"],
                    "race_meta": tr.race_meta,
                    "baseline_strict": baseline_strict,
                    "shadow_strict": shadow_strict,
                }
            )
            if len(evaluated) >= self.max_tie_races:
                break

        # Governance history monthly/yearly
        # cumulative metrics (as of each month/year end)
        evaluated_dt = [(rec, _parse_dt(rec["prediction_created_at"])) for rec in evaluated]
        evaluated_dt = [(rec, dt) for rec, dt in evaluated_dt if dt]
        if not evaluated_dt:
            return {
                "tie_races": 0,
                "monthly": [],
                "yearly": [],
                "segments": [],
                "evaluated": [],
            }

        earliest = min(dt for _, dt in evaluated_dt)
        latest = max(dt for _, dt in evaluated_dt)

        # Build month cutoffs up to latest
        months: list[str] = []
        cur = datetime(earliest.year, earliest.month, 1, tzinfo=timezone.utc)
        while cur <= latest:
            months.append(_period_month(cur))
            # next month
            if cur.month == 12:
                cur = datetime(cur.year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                cur = datetime(cur.year, cur.month + 1, 1, tzinfo=timezone.utc)

        monthly_rows = []
        for m in months:
            # month end: last day at 23:59:59-ish is enough; compare by year-month
            included = [rec for rec, dt in evaluated_dt if _period_month(dt) <= m]
            n = len(included)
            win = sum(1 for r in included if r["outcome"] == "win")
            lose = sum(1 for r in included if r["outcome"] == "lose")
            draw = sum(1 for r in included if r["outcome"] == "draw")
            baseline_hits = sum(int(r["baseline_strict"]) for r in included)
            shadow_hits = sum(int(r["shadow_strict"]) for r in included)
            strict_impr = shadow_hits - baseline_hits

            coverage_avg = (
                round(sum(float(r["coverage_score"]) for r in included) / n, 6) if n else 0.0
            )
            confidences = [float(r["confidence"]) for r in included if r.get("confidence") is not None]
            conf_dist = _confidence_dist(confidences)
            conf_p50 = float(conf_dist.get("p50") or 0.0)
            status = self._gate_status(
                n_tie=n,
                win=win,
                lose=lose,
                strict_impr=strict_impr,
                coverage_avg=coverage_avg,
                conf_p50=conf_p50,
            )
            strict_impr_rate = strict_impr / n if n else 0.0
            roi_change = strict_impr_rate
            monthly_rows.append(
                {
                    "month": m,
                    "tie_races": n,
                    "resolver_win": win,
                    "resolver_lose": lose,
                    "resolver_draw": draw,
                    "strict_improvement_rate": round(strict_impr_rate, 6),
                    "roi_change": round(roi_change, 6),
                    "confidence_p50": round(conf_p50, 6),
                    "gate_status": status,
                }
            )

        years: list[str] = []
        cury = datetime(earliest.year, 1, 1, tzinfo=timezone.utc)
        while cury.year <= latest.year:
            years.append(_period_year(cury))
            cury = datetime(cury.year + 1, 1, 1, tzinfo=timezone.utc)
        yearly_rows = []
        for y in years:
            included = [rec for rec, dt in evaluated_dt if _period_year(dt) <= y]
            n = len(included)
            win = sum(1 for r in included if r["outcome"] == "win")
            lose = sum(1 for r in included if r["outcome"] == "lose")
            draw = sum(1 for r in included if r["outcome"] == "draw")
            baseline_hits = sum(int(r["baseline_strict"]) for r in included)
            shadow_hits = sum(int(r["shadow_strict"]) for r in included)
            strict_impr = shadow_hits - baseline_hits
            coverage_avg = (
                round(sum(float(r["coverage_score"]) for r in included) / n, 6) if n else 0.0
            )
            confidences = [float(r["confidence"]) for r in included if r.get("confidence") is not None]
            conf_dist = _confidence_dist(confidences)
            conf_p50 = float(conf_dist.get("p50") or 0.0)
            status = self._gate_status(
                n_tie=n,
                win=win,
                lose=lose,
                strict_impr=strict_impr,
                coverage_avg=coverage_avg,
                conf_p50=conf_p50,
            )
            strict_impr_rate = strict_impr / n if n else 0.0
            yearly_rows.append(
                {
                    "year": y,
                    "tie_races": n,
                    "resolver_win": win,
                    "resolver_lose": lose,
                    "resolver_draw": draw,
                    "strict_improvement_rate": round(strict_impr_rate, 6),
                    "roi_change": round(strict_impr_rate, 6),
                    "confidence_p50": round(conf_p50, 6),
                    "gate_status": status,
                }
            )

        # Segment breakdown (final cumulative as-of latest)
        all_included = [rec for rec, _dt in evaluated_dt]
        seg_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for rec in all_included:
            meta = rec.get("race_meta") or {}
            for key in _segment_keys(meta):
                seg_map[key].append(rec)
        segments = []
        for key, items in sorted(seg_map.items(), key=lambda kv: -len(kv[1])):
            n = len(items)
            win = sum(1 for r in items if r["outcome"] == "win")
            lose = sum(1 for r in items if r["outcome"] == "lose")
            draw = sum(1 for r in items if r["outcome"] == "draw")
            baseline_hits = sum(int(r["baseline_strict"]) for r in items)
            shadow_hits = sum(int(r["shadow_strict"]) for r in items)
            strict_impr = shadow_hits - baseline_hits
            strict_impr_rate = strict_impr / n if n else 0.0
            roi_change = strict_impr_rate
            coverage_avg = round(sum(float(r["coverage_score"]) for r in items) / n, 6) if n else 0.0
            conf_dist = _confidence_dist([float(r["confidence"]) for r in items if r.get("confidence") is not None])
            segments.append(
                {
                    "segment": key,
                    "tie_races": n,
                    "resolver_win": win,
                    "resolver_lose": lose,
                    "resolver_draw": draw,
                    "strict_improvement_rate": round(strict_impr_rate, 6),
                    "roi_change": round(roi_change, 6),
                    "confidence_p50": conf_dist.get("p50"),
                }
            )

        return {
            "tie_races_evaluated": len(evaluated),
            "backfill_at": _now(),
            "monthly": monthly_rows,
            "yearly": yearly_rows,
            "segments": segments,
            "evaluated": evaluated,
        }


def write_backfill_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    latest = report["monthly"][-1] if report.get("monthly") else {}
    lines = [
        "# Version10.7 Research — Backfill Replay (Evidence-limited Governance)",
        "",
        f"**Date:** {report.get('backfill_at')}  ",
        "",
        "## 方式",
        "",
        "1. `predictions` を `created_at` の昇順で時系列再生",
        "2. Tie Race のみ対象（`model_rank` 最小グループが 2 頭以上。Ranking/Confidence の母数も Tie のみ）",
        "3. Evidence は `research_snapshot_features.observed_at <= prediction.created_at` を満たすものだけ使用",
        "4. その時点で Evidence Ranking（tiers / evidence_priority）を再計算",
        "5. Shadow Resolver を実行し、Shadow の Win/Lose/Draw と Confidence を算出",
        "6. Governance gate 判定（Shadow only / Production反映なし）",
        "",
        "## 出力の意味",
        "",
        "- `monthly/yearly` は **各月末・各年末時点の累積**（tie>=100 目標の現実的到達時期を示す）",
        "- `segments` は最終到達時点の内訳（全Tie / 年齢条件 / クラス / 芝ダート / 距離 / 競馬場）",
        "",
        "## 現状（バックフィル評価上限まで）",
        "",
        f"- Evaluated Tie races: `{report.get('tie_races_evaluated')}`",
        f"- Latest month cumulative: `{latest.get('month')}` / tie={latest.get('tie_races')}",
        "",
        "## カテゴリ別（最終到達時点の内訳）",
        "",
        "| Segment | Tie | Win | Lose | Draw | StrictImprovementRate | ROI | Confidence p50 |",
        "|---------|----:|----:|-----:|-----:|--------------------------:|---:|---------------:|",
    ]

    for seg in report.get("segments") or []:
        lines.append(
            f"| `{seg.get('segment')}` | {seg.get('tie_races')} | {seg.get('resolver_win')} | {seg.get('resolver_lose')} | {seg.get('resolver_draw')} | "
            f"{seg.get('strict_improvement_rate')} | {_pct(seg.get('roi_change'))} | {seg.get('confidence_p50')} |"
        )

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_governance_history_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version10.7 Research — Governance History (Monthly/Yearly)",
        "",
        f"**Date:** {report.get('backfill_at')}  ",
        "",
        "## Monthly (cumulative)",
        "",
        "| Month | Tie | Win | Lose | Draw | StrictImprovement | ROI | Confidence p50 | Gate |",
        "|------|----:|----:|-----:|-----:|------------------:|---:|----------------:|------|",
    ]
    for row in report.get("monthly") or []:
        lines.append(
            f"| `{row.get('month')}` | {row.get('tie_races')} | {row.get('resolver_win')} | {row.get('resolver_lose')} | {row.get('resolver_draw')} | "
            f"{row.get('strict_improvement_rate')} | { _pct(row.get('roi_change')) } | {row.get('confidence_p50')} | {row.get('gate_status')} |"
        )

    lines.extend(
        [
            "",
            "## Yearly (cumulative)",
            "",
            "| Year | Tie | Win | Lose | Draw | StrictImprovement | ROI | Confidence p50 | Gate |",
            "|------|----:|----:|-----:|-----:|------------------:|---:|----------------:|------|",
        ]
    )
    for row in report.get("yearly") or []:
        lines.append(
            f"| `{row.get('year')}` | {row.get('tie_races')} | {row.get('resolver_win')} | {row.get('resolver_lose')} | {row.get('resolver_draw')} | "
            f"{row.get('strict_improvement_rate')} | { _pct(row.get('roi_change')) } | {row.get('confidence_p50')} | {row.get('gate_status')} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_sample_expansion_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gate_month = None
    for row in report.get("monthly") or []:
        if row.get("gate_status") == "eligible":
            gate_month = row.get("month")
    lines = [
        "# Version10.7 Research — Sample Expansion Summary",
        "",
        f"**Date:** {report.get('backfill_at')}  ",
        "",
        f"- Evaluated Tie races: `{report.get('tie_races_evaluated')}`",
        f"- Eligible Month (first): `{gate_month or 'N/A'}`",
        "",
        "## Tie count expansion (monthly, cumulative)",
        "",
        "| Month | Tie | WinRate | LoseRate | StrictImprovementRate | Confidence p50 |",
        "|------|----:|--------:|---------:|--------------------------:|---------------:|",
    ]
    for row in report.get("monthly") or []:
        n = row.get("tie_races") or 0
        win_rate = (row.get("resolver_win") / n) if n else 0.0
        lose_rate = (row.get("resolver_lose") / n) if n else 0.0
        lines.append(
            f"| `{row.get('month')}` | {n} | {_pct(win_rate)} | {_pct(lose_rate)} | {row.get('strict_improvement_rate')} | {row.get('confidence_p50')} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write(
    *,
    backfill_md: Path | None = None,
    governance_history_md: Path | None = None,
    sample_expansion_md: Path | None = None,
    json_path: Path | None = None,
    perm_shuffles: int = 5,
    max_tie_races: int = V107_DEFAULT_MAX_TIE_RACES,
) -> dict[str, Any]:
    backfill = ResolverGovernanceBackfill(
        perm_shuffles=perm_shuffles, max_tie_races=max_tie_races
    )
    report = backfill.run()
    root = repo_root()
    evidence_out = evidence_root()
    backfill_md = backfill_md or (root / "docs/research/v107-backfill.md")
    governance_history_md = governance_history_md or (
        root / "docs/research/v107-governance-history.md"
    )
    sample_expansion_md = sample_expansion_md or (
        root / "docs/research/v107-sample-expansion.md"
    )
    json_path = json_path or (evidence_out / "reports" / "v107-governance-backfill.json")

    write_backfill_md(report, backfill_md)
    write_governance_history_md(report, governance_history_md)
    write_sample_expansion_md(report, sample_expansion_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "backfill_md": str(backfill_md),
        "governance_history_md": str(governance_history_md),
        "sample_expansion_md": str(sample_expansion_md),
        "json": str(json_path),
    }
    return report

