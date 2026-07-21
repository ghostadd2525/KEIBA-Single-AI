# -*- coding: utf-8 -*-
"""Improvement Evidence Builder registry."""
from __future__ import annotations

from typing import Any, Protocol

from .feature_missing_builder import FeatureMissingEvidenceBuilder
from .miss_builder import MissEvidenceBuilder
from .prediction_failed_builder import PredictionFailedEvidenceBuilder
from .result_sync_failed_builder import ResultSyncFailedEvidenceBuilder


class EvidenceBuilder(Protocol):
    event_type: str

    def build(self, ctx: dict[str, Any]) -> dict[str, Any] | None: ...


_REGISTRY: dict[str, EvidenceBuilder] = {
    "miss": MissEvidenceBuilder(),
    "feature_missing": FeatureMissingEvidenceBuilder(),
    "prediction_failed": PredictionFailedEvidenceBuilder(),
    "result_sync_failed": ResultSyncFailedEvidenceBuilder(),
}


def get_builder(event_type: str) -> EvidenceBuilder:
    b = _REGISTRY.get(event_type)
    if not b:
        raise KeyError(f"unknown event_type: {event_type}")
    return b


def build_event(event_type: str, ctx: dict[str, Any]) -> dict[str, Any] | None:
    return get_builder(event_type).build(ctx)


def registered_types() -> list[str]:
    return sorted(_REGISTRY.keys())
