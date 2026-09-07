# -*- coding: utf-8 -*-
"""Presentation DTO — structured display only (V109 C2).

No Natural Explanation prose. No Ticket. No Prediction mutation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


PRESENTATION_SCHEMA = "presentation-bundle/v1"

# Fixed display order (Localization Contract)
DISPLAY_ORDER: tuple[str, ...] = (
    "world",
    "near_miss",
    "affinity",
    "explanation_confidence",
    "exclusion",
    "transition",
)


@dataclass(frozen=True)
class LabeledValue:
    key: str
    label: str
    value: Any = None
    kind: str = "text"  # text | score | list | map | null


@dataclass(frozen=True)
class WorldDisplay:
    world_id: str | None
    label: str
    label_key: str


@dataclass(frozen=True)
class NearMissDisplay:
    present: bool
    residual_class: str | None
    residual_label: str | None
    near_world: str | None
    near_world_label: str | None
    near_worlds: tuple[str, ...] = ()


@dataclass(frozen=True)
class AffinityDisplay:
    present: bool
    values: tuple[tuple[str, float], ...] = ()  # (world_id, score) sorted desc
    definition: str | None = None
    note_key: str = "affinity_display_only"  # not for ticket/skip


@dataclass(frozen=True)
class ExplanationConfidenceDisplay:
    present: bool
    semantic_confidence: float | None = None
    world_confidence: float | None = None
    near_miss_confidence: float | None = None
    trace_confidence: float | None = None
    explanation_confidence: float | None = None
    definition_version: str | None = None
    # ADR-010: never interpret as win probability
    not_win_probability: bool = True
    display_kind: str = "explanation_confidence"


@dataclass(frozen=True)
class ExclusionDisplay:
    present: bool
    by_world: tuple[tuple[str, tuple[str, ...]], ...] = ()


@dataclass(frozen=True)
class TransitionDisplay:
    present: bool
    transition: str | None = None
    trigger_path: str | None = None


@dataclass(frozen=True)
class PresentationBundle:
    """Structured Presentation — Natural Explanation forbidden (C2)."""

    schema: str = PRESENTATION_SCHEMA
    locale: str = "ja"
    display_order: tuple[str, ...] = DISPLAY_ORDER
    world: WorldDisplay | None = None
    near_miss: NearMissDisplay | None = None
    affinity: AffinityDisplay | None = None
    explanation_confidence: ExplanationConfidenceDisplay | None = None
    exclusion: ExclusionDisplay | None = None
    transition: TransitionDisplay | None = None
    # Explicitly absent in C2
    natural_explanation: None = None
    sections: tuple[LabeledValue, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["natural_explanation"] = None
        return d
