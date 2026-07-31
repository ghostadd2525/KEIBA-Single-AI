# -*- coding: utf-8 -*-
"""Decision Layer DTOs (ADR-008).

Prediction ranks/scores are inputs only — never mutated by Decision.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TicketLeg:
    type: str  # "win"
    horse_id: str
    stake: float


@dataclass(frozen=True)
class ExplanationDTO:
    template: str
    text: str
    world_tag: str | None = None


@dataclass(frozen=True)
class ConfidenceDisplayDTO:
    value: float
    label: str
    suppressed: bool = False
    world_tag: str | None = None


@dataclass(frozen=True)
class RiskDisplayDTO:
    budget: float
    level: str
    skip: bool = False


@dataclass(frozen=True)
class DecisionDTO:
    """Decision Layer output. Does not contain mutable rank/score arrays."""

    mode: str  # "OFF" | "ON"
    action: str  # "BUY" | "SKIP"
    world_id: str | None
    tickets: tuple[TicketLeg, ...] = field(default_factory=tuple)
    pool: tuple[str, ...] = field(default_factory=tuple)
    explanation: ExplanationDTO | None = None
    confidence_display: ConfidenceDisplayDTO | None = None
    risk_display: RiskDisplayDTO | None = None
    # Read-only prediction fingerprint echoed for audit (not rewritten ranks)
    prediction_fingerprint: str | None = None
    flag_snapshot: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass(frozen=True)
class PredictionView:
    """Read-only projection of official prediction for Decision input."""

    race_id: str
    world_id: str
    predicted_top1: str
    winner_id: str
    horses_by_rank: tuple[dict[str, Any], ...]  # frozen logical order
    horses: tuple[dict[str, Any], ...]
    field_size: int
    rank_fingerprint: str
    score_fingerprint: str
    prediction_fingerprint: str
