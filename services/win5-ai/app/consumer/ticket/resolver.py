# -*- coding: utf-8 -*-
"""Ticket Resolver — policy_id → TicketPlan (V109 C3).

Policy Resolver only (not Reasoning Engine).
Reads prediction ranks; never mutates Core / Prediction / Policy.
Does not generate Reasons.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from app.consumer.ticket.dto import TicketLegDTO, TicketPlan, TicketTemplateRef
from app.consumer.ticket.market import MarketResolver, MarketSnapshot, NullMarketResolver
from app.consumer.ticket.templates import (
    declining_weights,
    equal_weights,
    get_template,
)


def _ranks_from_prediction(prediction: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(prediction, Mapping):
        return []
    ranks = prediction.get("ranks")
    if isinstance(ranks, (list, tuple)) and ranks:
        return [str(x) for x in ranks]
    top1 = prediction.get("top1")
    if top1 is not None and str(top1):
        return [str(top1)]
    return []


def resolve_ticket(
    policy_id: str,
    *,
    race_id: str,
    prediction: Mapping[str, Any] | None,
    market: MarketResolver | None = None,
) -> TicketPlan:
    """Fill Ticket Template using read-only prediction ranks + market.

    MUST NOT:
      - mutate prediction / core
      - change policy_id meaning
      - generate reason text
    """
    # Defense copy — never write back
    pred_view = copy.deepcopy(dict(prediction or {}))
    ranks = _ranks_from_prediction(pred_view)
    tpl = get_template(policy_id)
    mres = market or NullMarketResolver()
    snap: MarketSnapshot = mres.resolve(race_id)

    warnings: list[str] = []
    if not ranks and tpl.action == "BUY":
        warnings.append("missing_ranks_skip")
        return TicketPlan(
            policy_id=policy_id,
            template_id=tpl.template_id,
            action="SKIP",
            legs=(),
            pool=(),
            budget=0.0,
            market_budget=snap.budget,
            reason=None,
            warnings=tuple(warnings),
        )

    if tpl.action == "SKIP":
        pool = tuple(ranks[: max(1, tpl.pool_size)]) if ranks else ()
        return TicketPlan(
            policy_id=policy_id,
            template_id=tpl.template_id,
            action="SKIP",
            legs=(),
            pool=pool,
            budget=0.0,
            market_budget=snap.budget,
            reason=None,
            warnings=tuple(warnings),
        )

    n_avail = len(ranks)
    top_n = max(0, min(int(tpl.top_n), n_avail))
    pool_n = max(top_n, min(int(tpl.pool_size), n_avail)) if n_avail else 0
    buy_ids = ranks[:top_n]
    pool = tuple(ranks[:pool_n])

    if tpl.weight_mode == "declining":
        weights = declining_weights(top_n)
    else:
        weights = equal_weights(top_n)

    base_budget = float(tpl.unit_stake) * float(tpl.stake_scale)
    if snap.budget is not None:
        base_budget = float(snap.budget) * float(tpl.stake_scale)

    odds_map = dict(snap.odds_by_horse or {})
    legs: list[TicketLegDTO] = []
    for hid, wt in zip(buy_ids, weights):
        odds = odds_map.get(hid)
        if odds is not None:
            try:
                odds_f: float | None = float(odds)
            except (TypeError, ValueError):
                odds_f = None
                warnings.append(f"bad_odds:{hid}")
        else:
            odds_f = None
        legs.append(
            TicketLegDTO(
                type=tpl.ticket_type,
                horse_id=hid,
                stake=base_budget * float(wt),
                odds=odds_f,
            )
        )

    return TicketPlan(
        policy_id=policy_id,
        template_id=tpl.template_id,
        action="BUY",
        legs=tuple(legs),
        pool=pool,
        budget=base_budget,
        market_budget=snap.budget,
        reason=None,
        warnings=tuple(warnings),
    )


def template_ref(policy_id: str) -> TicketTemplateRef:
    tpl = get_template(policy_id)
    return TicketTemplateRef(
        template_id=tpl.template_id,
        policy_id=policy_id,
        action=tpl.action,
        ticket_type=tpl.ticket_type,
        top_n=tpl.top_n,
        pool_size=tpl.pool_size,
        unit_stake=tpl.unit_stake,
        stake_scale=tpl.stake_scale,
    )
