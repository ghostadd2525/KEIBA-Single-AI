# -*- coding: utf-8 -*-
"""C4 target-level terminal / quarantine policy (separates SOURCE vs TARGET).

Empty-day policy:
- Do NOT classify races=[] + HTTP200 as NON_RACE without COMPLETE+NON_RACE_DAY evidence.
- Bound attempts; then PARTIAL_TERMINAL / quarantined (unresolved research coverage).
- Target incomplete must not alone mark global SourceHealth DEGRADED.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

TerminalKind = Literal[
    "race_day_complete",
    "non_race_day_confirmed",
    "partial_terminal",
    "quarantined",
    "retryable",
    "fetch_failed_retryable",
    "blocked",
    "malformed_retryable",
]

# Finite bound (config may override). Existing C4Config.max_attempts_per_date default=3.
DEFAULT_MAX_ATTEMPTS = 8

NO_FETCH_STATES = frozenset(
    {
        "race_day_complete",
        "non_race_day_confirmed",
        "partial_terminal",
        "quarantined",
    }
)

RETRYABLE_STATES = frozenset(
    {"pending", "partial", "fetch_failed", "blocked", "malformed"}
)


@dataclass(frozen=True)
class EmptyDayOutcome:
    state: str
    affect_source_health: bool
    reason: str


def classify_empty_day_result(
    *,
    http_ok: bool,
    parse_ok: bool,
    completeness_state: str | None,
    day_kind: str | None,
    listed_race_count: int,
    attempt_count: int,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> EmptyDayOutcome:
    """Map persist outcome → queue state + whether to touch SourceHealth."""
    if completeness_state == "COMPLETE" and day_kind == "RACE_DAY":
        return EmptyDayOutcome("race_day_complete", True, "complete_race_day")
    if completeness_state == "COMPLETE" and day_kind == "NON_RACE_DAY":
        return EmptyDayOutcome("non_race_day_confirmed", True, "complete_non_race")

    # Proven NON_RACE only via completeness evidence — never races=[] alone.
    if (
        http_ok
        and parse_ok
        and listed_race_count == 0
        and completeness_state == "COMPLETE"
        and day_kind == "NON_RACE_DAY"
    ):
        return EmptyDayOutcome("non_race_day_confirmed", True, "proven_non_race")

    # Uncertain empty / partial
    if attempt_count >= max_attempts:
        return EmptyDayOutcome(
            "partial_terminal",
            False,
            "max_attempts_uncertain_empty",
        )

    return EmptyDayOutcome(
        "partial",
        False,  # target-specific: do not degrade global source health
        "uncertain_partial_retryable",
    )


def should_fetch_target(row: dict[str, Any], *, max_attempts: int) -> bool:
    st = str(row.get("state") or "pending")
    if st in NO_FETCH_STATES:
        return False
    if st not in RETRYABLE_STATES:
        return False
    attempts = int(row.get("attempt_count") or 0)
    # attempt_count is incremented at fetch start; block when already at/above cap
    # for states that previously failed/partial.
    if st in ("partial", "fetch_failed", "malformed", "blocked") and attempts >= max_attempts:
        return False
    return True


def mark_terminal_if_exhausted(
    row: dict[str, Any],
    *,
    max_attempts: int,
) -> dict[str, Any]:
    """After a soft incomplete attempt, quarantine when bound reached."""
    out = dict(row)
    attempts = int(out.get("attempt_count") or 0)
    st = str(out.get("state") or "")
    if st in ("partial", "fetch_failed", "malformed") and attempts >= max_attempts:
        out["state"] = "partial_terminal"
        out["terminal_reason"] = "max_attempts_exceeded"
        # Keep unresolved research signal — do not fake NON_RACE.
        meta = dict(out.get("error_metadata") or {})
        meta["quarantine"] = True
        meta["resolved"] = False
        out["error_metadata"] = meta
    return out
