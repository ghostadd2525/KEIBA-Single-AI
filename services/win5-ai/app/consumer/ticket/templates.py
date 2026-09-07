# -*- coding: utf-8 -*-
"""Ticket Template Registry — static templates by policy_id (V109 C3).

Policy Resolver data only. Does not change Decision Registry policies.
Does not generate Reasons.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.consumer.registry import FALLBACK_POLICY, PURE_RESIDUAL_POLICY

TEMPLATE_REGISTRY_VERSION = "ticket-template-registry/v1"
UNIT = 100.0


@dataclass(frozen=True)
class TicketTemplate:
    template_id: str
    action: str  # BUY | SKIP
    ticket_type: str  # win
    top_n: int
    pool_size: int
    unit_stake: float = UNIT
    stake_scale: float = 1.0
    # equal | declining (fixed weights pattern — not EV reasoning)
    weight_mode: str = "equal"


def _t(
    template_id: str,
    *,
    action: str,
    top_n: int,
    pool_size: int,
    stake_scale: float = 1.0,
    weight_mode: str = "equal",
) -> TicketTemplate:
    return TicketTemplate(
        template_id=template_id,
        action=action,
        ticket_type="win",
        top_n=top_n,
        pool_size=pool_size,
        unit_stake=UNIT,
        stake_scale=stake_scale,
        weight_mode=weight_mode,
    )


_NEAR_MISS_POLICY_IDS: tuple[str, ...] = (
    "policy_near_miss_core_conservative",
    "policy_near_miss_midupper_conservative",
    "policy_near_miss_midhole_conservative",
    "policy_near_miss_rank7_conservative",
)

# Static map: policy_id → template (V88/V95 structural defaults, not reasoning)
_TEMPLATES: dict[str, TicketTemplate] = {
    "policy_rank7_ready": _t(
        "tpl_rank7_top5_pool7",
        action="BUY",
        top_n=5,
        pool_size=7,
        stake_scale=1.0,
        weight_mode="declining",
    ),
    "policy_midhole_partial": _t(
        "tpl_midhole_top1_pool3",
        action="BUY",
        top_n=1,
        pool_size=3,
        stake_scale=0.8,
        weight_mode="equal",
    ),
    "policy_unsatisfied_conservative": _t(
        "tpl_unsatisfied_baseline_top1",
        action="BUY",
        top_n=1,
        pool_size=1,
        stake_scale=1.0,
        weight_mode="equal",
    ),
    PURE_RESIDUAL_POLICY: _t(
        "tpl_pure_residual_baseline_top1",
        action="BUY",
        top_n=1,
        pool_size=1,
        stake_scale=1.0,
        weight_mode="equal",
    ),
    "policy_blocked_provisional": _t(
        "tpl_blocked_skip",
        action="SKIP",
        top_n=0,
        pool_size=1,
        stake_scale=0.0,
    ),
    "policy_blocked": _t(
        "tpl_blocked_skip",
        action="SKIP",
        top_n=0,
        pool_size=1,
        stake_scale=0.0,
    ),
    "policy_blocked_exception": _t(
        "tpl_blocked_skip",
        action="SKIP",
        top_n=0,
        pool_size=1,
        stake_scale=0.0,
    ),
    FALLBACK_POLICY: _t(
        "tpl_legacy_top1",
        action="BUY",
        top_n=1,
        pool_size=1,
        stake_scale=1.0,
        weight_mode="equal",
    ),
}

# Near Miss: conservative baseline only — never copy Ready rank7 diversify (V95 / DL-C6)
for _pid in _NEAR_MISS_POLICY_IDS:
    _TEMPLATES[_pid] = _t(
        "tpl_near_miss_conservative_top1",
        action="BUY",
        top_n=1,
        pool_size=1,
        stake_scale=0.5,
        weight_mode="equal",
    )


def get_template(policy_id: str) -> TicketTemplate:
    """Resolve policy_id → template. Unknown → legacy fallback template."""
    tpl = _TEMPLATES.get(policy_id)
    if tpl is not None:
        return tpl
    return _TEMPLATES[FALLBACK_POLICY]


def list_templates() -> Mapping[str, TicketTemplate]:
    return dict(_TEMPLATES)


def template_registry_meta() -> dict[str, object]:
    return {
        "schema": TEMPLATE_REGISTRY_VERSION,
        "policy_ids": sorted(_TEMPLATES.keys()),
        "rules": [
            "Templates are static — no Reasoning Engine",
            "Near Miss never uses Ready diversify templates",
            "No Reason / Natural Explanation fields",
            "Does not modify Decision Registry policy_id meanings",
        ],
    }


def declining_weights(n: int) -> tuple[float, ...]:
    """Fixed structural weights (not EV optimization)."""
    if n <= 0:
        return ()
    if n == 1:
        return (1.0,)
    # Simple declining: n, n-1, ... normalized
    raw = [float(n - i) for i in range(n)]
    s = sum(raw)
    return tuple(x / s for x in raw)


def equal_weights(n: int) -> tuple[float, ...]:
    if n <= 0:
        return ()
    w = 1.0 / float(n)
    return tuple(w for _ in range(n))
