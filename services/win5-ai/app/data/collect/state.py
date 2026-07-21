# -*- coding: utf-8 -*-
"""Collector job / artifact state machine — Contract 1.1."""
from __future__ import annotations

from typing import FrozenSet

PENDING = "PENDING"
RUNNING = "RUNNING"
READY = "READY"
PARTIAL = "PARTIAL"
FAILED = "FAILED"
SKIPPED = "SKIPPED"
STALE_DYNAMIC = "STALE_DYNAMIC"

KIND_DYNAMIC = "DYNAMIC"
STATIC_KINDS: FrozenSet[str] = frozenset(
    {
        "STATIC_CORE",
        "STATIC_PROFILE",
        "STATIC_HISTORY",
    }
)

ALL_STATUSES: FrozenSet[str] = frozenset(
    {
        PENDING,
        RUNNING,
        READY,
        PARTIAL,
        FAILED,
        SKIPPED,
        STALE_DYNAMIC,
    }
)

TERMINAL: FrozenSet[str] = frozenset({SKIPPED})

TRANSITIONS: dict[str, FrozenSet[str]] = {
    PENDING: frozenset({RUNNING}),
    RUNNING: frozenset({READY, PARTIAL, FAILED, SKIPPED}),
    PARTIAL: frozenset({PENDING}),
    FAILED: frozenset({PENDING}),
    READY: frozenset({STALE_DYNAMIC}),
    STALE_DYNAMIC: frozenset({PENDING}),
    SKIPPED: frozenset(),
}


def is_dynamic_kind(kind: str | None) -> bool:
    return str(kind or "").strip().upper() == KIND_DYNAMIC


def can_transition(current: str, nxt: str, *, kind: str | None = None) -> bool:
    if current not in ALL_STATUSES:
        return False
    if nxt not in ALL_STATUSES:
        return False
    if nxt not in TRANSITIONS.get(current, frozenset()):
        return False
    if current == READY and nxt == STALE_DYNAMIC:
        return is_dynamic_kind(kind)
    return True


def assert_transition(current: str, nxt: str, *, kind: str | None = None) -> None:
    if not can_transition(current, nxt, kind=kind):
        if current == READY and nxt == STALE_DYNAMIC and not is_dynamic_kind(kind):
            raise ValueError(
                f"illegal collect transition {current!r} -> {nxt!r}: "
                f"only kind={KIND_DYNAMIC!r} may stale (got {kind!r})"
            )
        raise ValueError(f"illegal collect job transition {current!r} -> {nxt!r}")


def is_terminal(status: str) -> bool:
    return status in TERMINAL
