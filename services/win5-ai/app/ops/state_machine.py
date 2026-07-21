# -*- coding: utf-8 -*-
"""Result Automation State Machine — Production only."""
from __future__ import annotations

from typing import FrozenSet

PENDING = "PENDING"
RESULT_SYNCING = "RESULT_SYNCING"
RESULT_SYNC_FAILED = "RESULT_SYNC_FAILED"
PREDICTION_MATCHING = "PREDICTION_MATCHING"
EVALUATING = "EVALUATING"
STATS_UPDATING = "STATS_UPDATING"
SELF_EVAL_UPDATING = "SELF_EVAL_UPDATING"
EVIDENCE_EXPORTING = "EVIDENCE_EXPORTING"
COMPLETED = "COMPLETED"
DEGRADED = "DEGRADED"
FAILED = "FAILED"
SUPERSEDED = "SUPERSEDED"

TERMINAL: FrozenSet[str] = frozenset({COMPLETED, DEGRADED, FAILED, SUPERSEDED})
ACTIVE: FrozenSet[str] = frozenset(
    {
        PENDING,
        RESULT_SYNCING,
        RESULT_SYNC_FAILED,
        PREDICTION_MATCHING,
        EVALUATING,
        STATS_UPDATING,
        SELF_EVAL_UPDATING,
        EVIDENCE_EXPORTING,
    }
)

# allowed transitions (from -> to)
TRANSITIONS: dict[str, FrozenSet[str]] = {
    PENDING: frozenset({RESULT_SYNCING, EVIDENCE_EXPORTING, FAILED, SUPERSEDED}),
    RESULT_SYNCING: frozenset({PREDICTION_MATCHING, RESULT_SYNC_FAILED, FAILED}),
    RESULT_SYNC_FAILED: frozenset({RESULT_SYNCING, FAILED, EVIDENCE_EXPORTING}),
    PREDICTION_MATCHING: frozenset({EVALUATING, FAILED}),
    EVALUATING: frozenset({STATS_UPDATING, FAILED}),
    STATS_UPDATING: frozenset({SELF_EVAL_UPDATING, FAILED}),
    SELF_EVAL_UPDATING: frozenset({EVIDENCE_EXPORTING, FAILED}),
    EVIDENCE_EXPORTING: frozenset({COMPLETED, DEGRADED, FAILED}),
}


def can_transition(current: str, nxt: str) -> bool:
    allowed = TRANSITIONS.get(current, frozenset())
    return nxt in allowed


def assert_transition(current: str, nxt: str) -> None:
    if not can_transition(current, nxt):
        raise ValueError(f"illegal transition {current} -> {nxt}")


# triggers
TRIGGER_SCHEDULED = "scheduled"
TRIGGER_RETRY = "retry"
TRIGGER_MANUAL = "manual"

VALID_TRIGGERS = frozenset({TRIGGER_SCHEDULED, TRIGGER_RETRY, TRIGGER_MANUAL})


def normalize_trigger(raw: str | None) -> str:
    t = (raw or TRIGGER_MANUAL).strip().lower()
    if t in ("test", "admin", "admin_api", "cli"):
        return TRIGGER_MANUAL
    if t in ("auto", "cron", "timer"):
        return TRIGGER_SCHEDULED
    if t in VALID_TRIGGERS:
        return t
    return TRIGGER_MANUAL
