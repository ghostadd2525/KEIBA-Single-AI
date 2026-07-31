# -*- coding: utf-8 -*-
"""Decision Layer service (ADR-008 / V91 M1).

Applies World-selected Decision policies without mutating Prediction.
"""
from __future__ import annotations

from typing import Any

from app.decision import flags
from app.decision.betting_params import BettingPolicyParams
from app.decision.dto import DecisionDTO, PredictionView
from app.decision.fingerprint import prediction_fingerprint, rank_fingerprint, score_fingerprint
from app.decision.policies import legacy_decision, merge_by_subflags, world_decision
from app.decision.policy_params import Rank7PolicyParams


def build_prediction_view(
    *,
    race_id: str,
    world_id: str,
    predicted_top1: str,
    winner_id: str,
    horses: list[dict[str, Any]],
    field_size: int | None = None,
) -> PredictionView:
    by_rank = tuple(sorted(horses, key=lambda h: int(h.get("model_rank") or 999)))
    horses_t = tuple(horses)
    return PredictionView(
        race_id=race_id,
        world_id=world_id,
        predicted_top1=predicted_top1,
        winner_id=winner_id,
        horses_by_rank=by_rank,
        horses=horses_t,
        field_size=int(field_size or len(horses)),
        rank_fingerprint=rank_fingerprint(horses),
        score_fingerprint=score_fingerprint(horses),
        prediction_fingerprint=prediction_fingerprint(race_id, predicted_top1, horses),
    )


def apply_decision(
    view: PredictionView,
    *,
    force_mode: str | None = None,
    rank7_params: Rank7PolicyParams | None = None,
    betting_params: BettingPolicyParams | None = None,
) -> DecisionDTO:
    """Apply Decision Layer.

    force_mode:
      None → respect env flags
      "OFF" → legacy always
      "ON"  → all decision axes ON (Shadow), ignoring env
    """
    if force_mode == "OFF":
        snap = {k: False for k in flags.snapshot_flags()}
        return legacy_decision(view, snap)

    if force_mode == "ON":
        snap = {k: True for k in flags.snapshot_flags()}
        snap["W_DECISION_LAYER_ENABLED"] = True
        return world_decision(
            view, snap, rank7_params=rank7_params, betting_params=betting_params
        )

    snap = flags.snapshot_flags()
    legacy = legacy_decision(view, snap)
    if not flags.decision_layer_enabled():
        return legacy

    full = world_decision(
        view, snap, rank7_params=rank7_params, betting_params=betting_params
    )
    return merge_by_subflags(
        legacy,
        full,
        ticket=flags.decision_ticket_enabled(),
        pool=flags.decision_pool_enabled(),
        explain=flags.decision_explain_enabled(),
        risk=flags.decision_risk_enabled(),
        conf=flags.decision_conf_display_enabled(),
    )


def dual_shadow(
    view: PredictionView,
    *,
    rank7_params: Rank7PolicyParams | None = None,
    betting_params: BettingPolicyParams | None = None,
) -> dict[str, DecisionDTO]:
    """Generate Decision OFF and ON against the same PredictionView."""
    return {
        "decision_off": apply_decision(view, force_mode="OFF"),
        "decision_on": apply_decision(
            view,
            force_mode="ON",
            rank7_params=rank7_params,
            betting_params=betting_params,
        ),
        "prediction_fingerprint": view.prediction_fingerprint,
        "rank_fingerprint": view.rank_fingerprint,
        "score_fingerprint": view.score_fingerprint,
    }
