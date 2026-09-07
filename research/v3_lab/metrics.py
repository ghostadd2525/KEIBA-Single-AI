# -*- coding: utf-8 -*-
"""Version 3 Lab — measurement points (no Accuracy intervention)."""
from __future__ import annotations

from typing import Any


METRIC_POINTS = (
    "lab.pipeline.start",
    "lab.pipeline.end",
    "lab.stage.representation",
    "lab.stage.admission",
    "lab.stage.selection",
    "lab.stage.evaluation",
    "lab.stage.purchase",
    "lab.identity",
    "lab.representation.enabled",
    "lab.representation.feature_count",
    "lab.representation.embedding_dim",
    "lab.representation.runner_count",
    "lab.admission.enabled",
    "lab.admission.pool_size",
    "lab.admission.capacity_max",
    "lab.admission.admitted_count",
    "lab.admission.rejected_count",
    "lab.admission.deep_extra",
    "lab.selection.enabled",
    "lab.selection.selected_size",
    "lab.selection.pool_size",
    "lab.selection.swap_count",
    "lab.selection.size_invariant",
    "lab.selection.pool_external_adds",
    "lab.evaluation.enabled",
    "lab.evaluation.ranked_size",
    "lab.evaluation.policy_id",
    "lab.ab.control_hit",
    "lab.ab.treatment_hit",
    "lab.ab.churn_hit",
    "lab.ab.a02.hit",
)


class MetricsSink:
    """In-memory counter / event sink for Lab runs."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.counters: dict[str, int] = {}

    def emit(self, name: str, **payload: Any) -> None:
        self.events.append({"name": name, **payload})
        self.counters[name] = self.counters.get(name, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": dict(self.counters),
            "event_count": len(self.events),
            "points": list(METRIC_POINTS),
        }

    def reset(self) -> None:
        self.events.clear()
        self.counters.clear()


_GLOBAL = MetricsSink()


def get_metrics_sink() -> MetricsSink:
    return _GLOBAL


def reset_metrics() -> None:
    _GLOBAL.reset()


__all__ = ["METRIC_POINTS", "MetricsSink", "get_metrics_sink", "reset_metrics"]
