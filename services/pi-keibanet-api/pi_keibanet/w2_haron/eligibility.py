# -*- coding: utf-8 -*-
"""Queue eligibility (cache-first / P1 / SourceHealth / cooldown)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .layer_b_store import is_valid_race_id
from .p1_lock import P1Lock
from .source_health import SourceHealth, allows_mainline_fetch


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(timezone.utc)


def row_time_eligible(row: dict[str, Any], *, now: datetime | None = None) -> bool:
    now = _now(now)
    nxt = _parse_iso(row.get("next_eligible_at"))
    return nxt is None or now >= nxt


def is_request_eligible(
    row: dict[str, Any],
    *,
    health: SourceHealth,
    p1: P1Lock,
    max_attempts: int,
    now: datetime | None = None,
    recovering_probe_only: bool = False,
) -> bool:
    """Return True if PAGE-C HTTP request is allowed for this row."""
    now = _now(now)
    rid = row.get("history_race_id")
    if not is_valid_race_id(rid):
        return False
    if p1.state != "IDLE":
        return False
    if not allows_mainline_fetch(health):
        return False
    if not row_time_eligible(row, now=now):
        return False

    status = row.get("canonical_status")
    if status in ("cache_hit", "source_missing", "invalid", "fetched"):
        return False
    if status == "parse_failed":
        return False  # HTTP re-fetch prohibited; offline reparse only

    attempts = int(row.get("attempt_count") or 0)

    if status == "pending":
        if health.state == "RECOVERING" and recovering_probe_only:
            return True
        if health.state in ("HEALTHY", "DEGRADED"):
            return True
        if health.state == "RECOVERING":
            return True
        return False

    if status == "fetch_failed":
        if attempts >= max_attempts:
            return False
        return health.state in ("HEALTHY", "DEGRADED", "RECOVERING")

    if status == "blocked":
        # Only after cooldown (next_eligible_at) and Health allows.
        if health.state == "RECOVERING":
            return True
        if health.state in ("HEALTHY", "DEGRADED") and row_time_eligible(row, now=now):
            return attempts < max_attempts
        return False

    return False


def select_eligible_race_ids(
    rows: dict[str, dict[str, Any]],
    *,
    health: SourceHealth,
    p1: P1Lock,
    max_attempts: int,
    max_races: int,
    now: datetime | None = None,
) -> list[str]:
    """Deterministic order: pending first, then fetch_failed, then blocked (probe)."""
    now = _now(now)
    pending: list[str] = []
    failed: list[str] = []
    blocked: list[str] = []
    for rid in sorted(rows.keys()):
        row = rows[rid]
        if not is_request_eligible(
            row, health=health, p1=p1, max_attempts=max_attempts, now=now
        ):
            continue
        st = row.get("canonical_status")
        if st == "pending":
            pending.append(rid)
        elif st == "fetch_failed":
            failed.append(rid)
        elif st == "blocked":
            blocked.append(rid)

    ordered = pending + failed + blocked
    if health.state == "RECOVERING":
        # Single probe per run while recovering.
        return ordered[:1]
    return ordered[: max(0, max_races)]
