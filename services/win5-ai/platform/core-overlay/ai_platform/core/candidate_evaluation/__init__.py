# -*- coding: utf-8 -*-
"""Candidate Evaluation projection and race input resolution.

No Candidate Pool or Repick function is imported or called.  Every runner in
the probability input for the requested race is projected to CE.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from ai_platform.core.confidence import ConfidenceBuilder
from ai_platform.core.explain import build_explain_payload, is_explain_v2_enabled
from ai_platform.core.features import FeatureGenerator, FeatureLoader, FeatureLoadResult
from ai_platform.core.ranking import Ranker
from ai_platform.core.scoring import Scorer
from ai_platform.core.world import WorldClassifier


class CandidateEvaluationProjector:
    """Project frozen Rank/Confidence values into CE rows."""

    # 馬の能力寄り特徴量（0–1 想定）。評価内訳用に CE へ透過する。
    ABILITY_FEATURE_KEYS = (
        "history_score",
        "distance_score",
        "style_confidence",
        "front_rate",
        "style_distance_fit_weight",
        "pace_collapse_risk_v2",
        "gate_risk_score",
        "inside_traffic_risk",
        "style_disadvantage_score",
    )

    def project_candidates(
        self,
        ranking: dict[str, Any],
        confidence: dict[str, Any],
        world: dict[str, Any] | None = None,
        runners_frame: pd.DataFrame | None = None,
    ) -> list[dict[str, Any]]:
        """Return CandidateEvaluation rows sorted by Rank."""
        world = world or {}
        per_horse = confidence.get("per_horse", {})
        ability_by_key = self._ability_index(runners_frame)
        candidates = []
        for row in ranking.get("ranking", []):
            horse_name = row["horse_name"]
            horse_number = row.get("horse_number")
            ability = self._lookup_ability(ability_by_key, horse_number, horse_name)
            cand = {
                "CandidateID": horse_name,
                "Rank": int(row["rank"]),
                "Confidence": float(per_horse.get(horse_name, row["score"])),
                "HorseNumber": horse_number,
                "WorldMeta": world.get("world", ""),
                "SubWorldMeta": world.get("sub_world", ""),
            }
            if ability:
                cand["AbilityScores"] = ability
            candidates.append(cand)
        candidates.sort(key=lambda row: row["Rank"])
        return candidates

    def _ability_index(
        self, runners_frame: pd.DataFrame | None
    ) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        if runners_frame is None or runners_frame.empty:
            return out
        for _, row in runners_frame.iterrows():
            ability: dict[str, float] = {}
            for key in self.ABILITY_FEATURE_KEYS:
                if key not in runners_frame.columns:
                    continue
                val = row.get(key)
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    continue
                try:
                    ability[key] = float(val)
                except (TypeError, ValueError):
                    continue
            if not ability:
                continue
            name = str(row.get("horse_name") or "").strip()
            num = row.get("horse_number")
            if name:
                out[f"name:{name}"] = ability
            if num is not None and str(num) != "" and not (isinstance(num, float) and pd.isna(num)):
                try:
                    out[f"num:{int(num)}"] = ability
                except (TypeError, ValueError):
                    out[f"num:{num}"] = ability
        return out

    def _lookup_ability(
        self,
        ability_by_key: dict[str, dict[str, float]],
        horse_number: Any,
        horse_name: Any,
    ) -> dict[str, float]:
        if horse_number is not None and str(horse_number) != "":
            try:
                hit = ability_by_key.get(f"num:{int(horse_number)}")
            except (TypeError, ValueError):
                hit = ability_by_key.get(f"num:{horse_number}")
            if hit:
                return dict(hit)
        name = str(horse_name or "").strip()
        if name and f"name:{name}" in ability_by_key:
            return dict(ability_by_key[f"name:{name}"])
        return {}


class CorePipeline:
    """Feature-to-CE orchestration with no Product or Win5 selection stages."""

    def __init__(self, *, loader: FeatureLoader | None = None) -> None:
        self.loader = loader or FeatureLoader()
        self.features = FeatureGenerator()
        self.scoring = Scorer()
        self.ranking = Ranker()
        self.confidence = ConfidenceBuilder()
        self.world = WorldClassifier()
        self.projector = CandidateEvaluationProjector()

    def load_race_input(self, race_id: str) -> FeatureLoadResult | None:
        """Load runner features via FeatureLoader (DB → daily CSV → global CSV)."""
        return self.loader.load(str(race_id))

    def evaluate(self, race_id: str, **opts: Any) -> dict[str, Any] | None:
        """Run the migrated existing Core stages and return CorePublicBundle."""
        loaded = self.load_race_input(str(race_id))
        if loaded is None:
            return None
        runners = loaded.frame
        feature_matrix = self.features.build_feature_matrix(runners)
        scores = self.scoring.score_candidates(feature_matrix)

        scored_frame = scores["_source_frame"].copy()
        scored_frame["base_model_score"] = scores["base_model_score"]
        scored_frame["adjusted_model_score"] = scores["adjusted_model_score"]
        scored_frame["win_prob"] = scores["win_prob"]

        ranking = self.ranking.build_ranking(scores)
        rank_by_id = {
            row["horse_name"]: row["rank"] for row in ranking["ranking"]
        }
        scored_frame["model_rank"] = (
            scored_frame.get("horse_name", pd.Series("", index=scored_frame.index))
            .fillna("")
            .astype(str)
            .map(rank_by_id)
        )

        meta = self.world.build_race_meta(scored_frame)
        meta["race_id"] = str(race_id)
        confidence = self.confidence.build_confidence(scores, meta)
        world = self.world.classify_world(confidence, meta)
        candidates = self.projector.project_candidates(
            ranking, confidence, world, runners_frame=scored_frame
        )

        result: dict[str, Any] = {
            "race_id": str(race_id),
            "candidates": candidates,
            "context": {
                "source": loaded.metadata.get("path") or loaded.feature_source,
                "feature_source": loaded.feature_source,
                "feature_metadata": loaded.metadata,
                "field_size": int(len(runners)),
            },
            "world": world["world"],
            "sub_world": world["sub_world"],
            "overall_confidence": confidence["overall"],
            "confidence_factors": confidence["factors"],
            "meta": meta,
            "core_version": "ai-core-migrated/1.0-phase1",
        }
        # Version 2 Explainability Phase 1 — Flag OFF ≡ omit key (v1.1 identical)
        if is_explain_v2_enabled():
            payload = build_explain_payload(
                candidates=candidates,
                world=world,
                confidence=confidence,
                meta=meta,
                core_version=result["core_version"],
            )
            if payload is not None:
                result["explain_payload"] = payload
        return result


__all__ = ["CandidateEvaluationProjector", "CorePipeline"]
