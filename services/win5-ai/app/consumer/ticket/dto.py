# -*- coding: utf-8 -*-
"""Ticket DTO — Policy Resolver output (V109 C3).

No Reasoning / Reason generation. No Prediction mutation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


TICKET_SCHEMA = "ticket-plan/v1"


@dataclass(frozen=True)
class TicketLegDTO:
    type: str  # "win"
    horse_id: str
    stake: float
    odds: float | None = None  # from Market Resolver (display/audit only)


@dataclass(frozen=True)
class TicketTemplateRef:
    template_id: str
    policy_id: str
    action: str  # BUY | SKIP
    ticket_type: str
    top_n: int
    pool_size: int
    unit_stake: float
    stake_scale: float


@dataclass(frozen=True)
class TicketPlan:
    """Resolved ticket plan from template + read-only ranks + market."""

    schema: str = TICKET_SCHEMA
    policy_id: str = ""
    template_id: str = ""
    action: str = "SKIP"  # BUY | SKIP
    legs: tuple[TicketLegDTO, ...] = field(default_factory=tuple)
    pool: tuple[str, ...] = field(default_factory=tuple)
    budget: float = 0.0
    market_budget: float | None = None
    # Explicitly no reasoning payload
    reason: None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["reason"] = None
        return d
