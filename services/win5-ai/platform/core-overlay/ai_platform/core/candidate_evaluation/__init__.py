# -*- coding: utf-8 -*-
"""Candidate Evaluation projection and race input resolution.

No Candidate Pool or Repick function is imported or called.  Every runner in
the probability input for the requested race is projected to CE.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from ai_platform.core.confidence import ConfidenceBuilder
from ai_platform.core.features import FeatureGenerator, FeatureLoader, FeatureLoadResult
from ai_platform.core.ranking import Ranker
from ai_platform.core.scoring import Scorer
from ai_platform.core.world import WorldClassifier


class CandidateEvaluationProjector:
    """Project frozen Rank/Confidence values into CE rows."""

    def project_candidates(
        self,
        ranking: dict[str, Any],
        confidence: dict[str, Any],
        world: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return CandidateEvaluation rows sorted by Rank."""
        world = world or {}
        per_horse = confidence.get("per_horse", {})
        candidates = [
            {
                "CandidateID": row["horse_name"],
                "Rank": int(row["rank"]),
                "Confidence": float(per_horse.get(row["horse_name"], row["score"])),
                "HorseNumber": row.get("horse_number"),
                "WorldMeta": world.get("world", ""),
                "SubWorldMeta": world.get("sub_world", ""),
            }
            for row in ranking.get("ranking", [])
        ]
        candidates.sort(key=lambda row: row["Rank"])
        return candidates


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
        candidates = self.projector.project_candidates(ranking, confidence, world)

        return {
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


__all__ = ["CandidateEvaluationProjector", "CorePipeline"]
