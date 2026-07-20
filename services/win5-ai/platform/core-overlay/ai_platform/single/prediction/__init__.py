# -*- coding: utf-8 -*-
"""Single AI — Prediction (M3).

RaceID -> Core Facade (Ranking/Confidence)
       -> Bet Strategy (Bet Plan) -> Bet Builder (slips)
       -> JSON response.
Prediction layer itself only assembles/dispatches (no inference, S-04).
"""
from __future__ import annotations

from typing import Any

from ai_platform.core.facade import (
    CORE_FACADE_VERSION,
    predict_confidence,
    predict_ranking,
)
from ai_platform.single.bet_builder import build_bets
from ai_platform.single.bet_strategy import build_bet_plan
from ai_platform.single.models import error_response, prediction_response


def predict(
    race_id: str,
    bet_types: list[str] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full Single AI pipeline for one race (S-09/S-10 canonical path)."""
    rid = str(race_id or "").strip()
    if not rid:
        return error_response(race_id=None, error_code="missing_race_id", message="--race is required")

    ranking = predict_ranking(rid)
    if ranking is None:
        return error_response(
            race_id=rid,
            error_code="race_not_resolved",
            message=f"race_id={rid!r} could not be resolved by AI Core",
        )
    confidence = predict_confidence(rid)

    plan_result = build_bet_plan(ranking, confidence, bet_types=bet_types, options=options)
    bets = build_bets(plan_result)

    resp = prediction_response(
        race_id=rid,
        ranking=ranking,
        confidence=confidence,
        core_version=CORE_FACADE_VERSION,
        bets=bets,
        feature_source=ranking.get("feature_source") if isinstance(ranking, dict) else None,
    )
    resp["bet_plans"] = plan_result.get("plans", [])
    return resp
