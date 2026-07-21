# -*- coding: utf-8 -*-
"""Collect OPS Monitor — Manifest + DYNAMIC 状態 (C-6)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import state as sm
from .manifest_store import read_manifest
from .repository import CollectJobRepository

# Prediction / Complete dimension (C-5)
NOT_READY = "NOT_READY"
PREDICTION_READY = "PREDICTION_READY"
COMPLETE_READY = "COMPLETE_READY"

# DYNAMIC dimension (C-6) — Prediction Ready と独立
STATIC_READY = "STATIC_READY"
DYNAMIC_REFRESHING = "DYNAMIC_REFRESHING"
DYNAMIC_READY = "DYNAMIC_READY"


@dataclass(frozen=True)
class CollectOpsState:
    week_id: str
    state: str
    dynamic_state: str
    prediction_ready: bool
    complete_ready: bool
    dynamic_ready: bool
    dynamic_stale: bool
    prediction_ready_races: int
    total_races_expected: int
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "week_id": self.week_id,
            "state": self.state,
            "dynamic_state": self.dynamic_state,
            "prediction_ready": self.prediction_ready,
            "complete_ready": self.complete_ready,
            "dynamic_ready": self.dynamic_ready,
            "dynamic_stale": self.dynamic_stale,
            "prediction_ready_races": self.prediction_ready_races,
            "total_races_expected": self.total_races_expected,
            "detail": self.detail,
        }


def classify_ops_state(
    *,
    prediction_ready: bool,
    complete_ready: bool,
) -> str:
    if complete_ready:
        return COMPLETE_READY
    if prediction_ready:
        return PREDICTION_READY
    return NOT_READY


def classify_dynamic_state(
    *,
    dynamic_ready: bool,
    dynamic_stale: bool,
    refreshing: bool = False,
) -> str:
    """
    STATIC_READY      — DYNAMIC 非活性 / 静的供給フォーカス
    DYNAMIC_REFRESHING — STALE / PENDING / RUNNING など更新中
    DYNAMIC_READY      — DYNAMIC 全 READY
    """
    if refreshing or dynamic_stale:
        return DYNAMIC_REFRESHING
    if dynamic_ready:
        return DYNAMIC_READY
    return STATIC_READY


def evaluate_collect_ops(week_id: str) -> CollectOpsState:
    """
    Manifest を正本として週次供給状態を判定。

    Prediction: NOT_READY / PREDICTION_READY / COMPLETE_READY
    Dynamic:    STATIC_READY / DYNAMIC_REFRESHING / DYNAMIC_READY
    """
    manifest = read_manifest(week_id)
    if not manifest:
        return CollectOpsState(
            week_id=week_id,
            state=NOT_READY,
            dynamic_state=STATIC_READY,
            prediction_ready=False,
            complete_ready=False,
            dynamic_ready=False,
            dynamic_stale=False,
            prediction_ready_races=0,
            total_races_expected=0,
            detail="manifest_missing",
        )

    status = manifest.get("status") or {}
    races = manifest.get("races") or {}
    prediction_ready = bool(status.get("prediction_ready"))
    complete_ready = bool(status.get("complete_ready"))
    dynamic_ready = bool(status.get("dynamic_ready"))
    dynamic_stale = bool(status.get("dynamic_stale"))

    refreshing = False
    try:
        dyn_jobs = CollectJobRepository().list_dynamic_jobs(week_id)
        refreshing = any(
            j.get("status")
            in (sm.STALE_DYNAMIC, sm.PENDING, sm.RUNNING, sm.PARTIAL, sm.FAILED)
            for j in dyn_jobs
        )
    except Exception:
        refreshing = dynamic_stale

    state = classify_ops_state(
        prediction_ready=prediction_ready,
        complete_ready=complete_ready,
    )
    dynamic_state = classify_dynamic_state(
        dynamic_ready=dynamic_ready,
        dynamic_stale=dynamic_stale,
        refreshing=refreshing,
    )
    return CollectOpsState(
        week_id=week_id,
        state=state,
        dynamic_state=dynamic_state,
        prediction_ready=prediction_ready,
        complete_ready=complete_ready,
        dynamic_ready=dynamic_ready,
        dynamic_stale=dynamic_stale,
        prediction_ready_races=int(races.get("prediction_ready_races") or 0),
        total_races_expected=int(races.get("total_races_expected") or 0),
        detail="",
    )
