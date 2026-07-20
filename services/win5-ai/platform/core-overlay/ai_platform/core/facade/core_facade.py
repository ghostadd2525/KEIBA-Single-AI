# -*- coding: utf-8 -*-
"""AI Core public facade — SINGLE-04 Phase 1.

Canonical public boundary:
    evaluate_candidates(race_id) -> CorePublicBundle | None

Compatibility views are projections from CE.  This module does not call
Candidate Pool, Repick, Purchase, Delete, Optimizer, Ticket, V2 or V4.
"""
from __future__ import annotations

from typing import Any

from ai_platform.core.candidate_evaluation import CorePipeline

CORE_FACADE_VERSION = "ai-core-migrated/1.0-phase1"


def _pipeline() -> CorePipeline:
    """Create a stateless Phase-1 Core pipeline."""
    return CorePipeline()


def evaluate_candidates(race_id: str, **opts: Any) -> dict[str, Any] | None:
    """Return the frozen CorePublicBundle for ``race_id``.

    Required CE fields remain CandidateID, Rank and Confidence.  Unresolved
    races return ``None``.  No Product-stage selection is performed.
    """
    return _pipeline().evaluate(str(race_id), **opts)


def _ranking_rows_from_ce(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build the frozen compatibility Ranking view from CE."""
    return [
        {
            "horse_name": candidate["CandidateID"],
            "horse_number": candidate.get("HorseNumber"),
            "rank": candidate["Rank"],
            "score": candidate["Confidence"],
        }
        for candidate in candidates
    ]


def resolve_core(race_id: str) -> dict[str, Any] | None:
    """Return the S-01 compatibility bundle assembled from canonical CE."""
    ce = evaluate_candidates(race_id)
    if ce is None:
        return None
    return {
        "race_id": ce["race_id"],
        "context": ce.get("context", {}),
        "world": ce.get("world", ""),
        "sub_world": ce.get("sub_world", ""),
        "features": None,
        "ranking": _ranking_rows_from_ce(ce["candidates"]),
        "confidence": {
            "overall": ce.get("overall_confidence", 0.0),
            "per_horse": {
                candidate["CandidateID"]: candidate["Confidence"]
                for candidate in ce["candidates"]
            },
            "factors": ce.get("confidence_factors", []),
        },
        "meta": ce.get("meta", {}),
        "core_version": ce.get("core_version", CORE_FACADE_VERSION),
    }


def predict_ranking(race_id: str, **opts: Any) -> dict[str, Any] | None:
    """Return the compatibility RankingResult projected from CE."""
    ce = evaluate_candidates(race_id, **opts)
    if ce is None:
        return None
    ctx = ce.get("context") or {}
    return {
        "race_id": ce["race_id"],
        "ranking": _ranking_rows_from_ce(ce["candidates"]),
        "core_version": ce.get("core_version", CORE_FACADE_VERSION),
        "feature_source": ctx.get("feature_source"),
    }


def predict_confidence(
    race_id: str,
    ranking: dict[str, Any] | None = None,
    **opts: Any,
) -> dict[str, Any] | None:
    """Return the compatibility ConfidenceResult projected from CE."""
    del ranking
    ce = evaluate_candidates(race_id, **opts)
    if ce is None:
        return None
    return {
        "race_id": ce["race_id"],
        "overall": ce.get("overall_confidence", 0.0),
        "per_horse": {
            candidate["CandidateID"]: candidate["Confidence"]
            for candidate in ce["candidates"]
        },
        "factors": ce.get("confidence_factors", []),
        "core_version": ce.get("core_version", CORE_FACADE_VERSION),
    }


__all__ = [
    "CORE_FACADE_VERSION",
    "evaluate_candidates",
    "predict_ranking",
    "predict_confidence",
    "resolve_core",
]
