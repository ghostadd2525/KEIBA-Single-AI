# -*- coding: utf-8 -*-
"""Anti-leak guard: observed_at must be <= prediction_created_at."""
from __future__ import annotations

from datetime import datetime
from typing import Any


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    s = str(ts).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def anti_leak_ok(*, observed_at: str | None, prediction_created_at: str) -> bool:
    obs = parse_iso(observed_at)
    pred = parse_iso(prediction_created_at)
    if obs is None or pred is None:
        return False
    return obs <= pred


def reject_reason(*, observed_at: str | None, prediction_created_at: str) -> str:
    if not observed_at:
        return "anti_leak_rejected"
    obs = parse_iso(observed_at)
    pred = parse_iso(prediction_created_at)
    if obs is None or pred is None:
        return "anti_leak_rejected"
    if obs > pred:
        return "anti_leak_rejected"
    return ""


def accept_observation(
    *,
    value: Any,
    observed_at: str | None,
    prediction_created_at: str,
) -> tuple[Any, str | None, str | None]:
    """Return (value, observed_at, missing_reason). Rejects leak violations."""
    if value is None:
        return None, None, "source_unavailable"
    if not anti_leak_ok(observed_at=observed_at, prediction_created_at=prediction_created_at):
        return None, None, reject_reason(
            observed_at=observed_at,
            prediction_created_at=prediction_created_at,
        ) or "anti_leak_rejected"
    return value, observed_at, None
