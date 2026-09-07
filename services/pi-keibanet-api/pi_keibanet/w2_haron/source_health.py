# -*- coding: utf-8 -*-
"""SourceHealth for netkeiba PAGE-C (restriction compliance, not bypass)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from .config import SOURCE_KEY

HealthState = Literal["HEALTHY", "DEGRADED", "BLOCKED", "RECOVERING", "UNAVAILABLE"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


@dataclass
class SourceHealth:
    source: str = SOURCE_KEY
    state: HealthState = "UNAVAILABLE"
    last_success_at: str | None = None
    last_failure_at: str | None = None
    consecutive_failures: int = 0
    last_http_status: int | None = None
    reason: str | None = None
    cooldown_until: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "state": self.state,
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "consecutive_failures": self.consecutive_failures,
            "last_http_status": self.last_http_status,
            "reason": self.reason,
            "cooldown_until": self.cooldown_until,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SourceHealth":
        state = d.get("state") or "UNAVAILABLE"
        valid = ("HEALTHY", "DEGRADED", "BLOCKED", "RECOVERING", "UNAVAILABLE")
        if state not in valid:
            state = "UNAVAILABLE"
        return cls(
            source=str(d.get("source") or SOURCE_KEY),
            state=state,  # type: ignore[arg-type]
            last_success_at=d.get("last_success_at"),
            last_failure_at=d.get("last_failure_at"),
            consecutive_failures=int(d.get("consecutive_failures") or 0),
            last_http_status=d.get("last_http_status"),
            reason=d.get("reason"),
            cooldown_until=d.get("cooldown_until"),
            updated_at=d.get("updated_at"),
        )


def load_health(path: Path) -> SourceHealth:
    if not path.exists():
        return SourceHealth(state="UNAVAILABLE", reason="no_health_file_yet")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return SourceHealth.from_dict(data if isinstance(data, dict) else {})
    except (OSError, json.JSONDecodeError):
        return SourceHealth(state="UNAVAILABLE", reason="health_file_corrupt")


def save_health(path: Path, health: SourceHealth) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    health.updated_at = _iso(_utc_now())
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(health.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def ensure_boot_health(path: Path) -> SourceHealth:
    """First boot: UNAVAILABLE until first successful fetch or explicit enable → HEALTHY on first run prep."""
    h = load_health(path)
    if path.exists():
        return h
    # Shadow first run: allow attempts from HEALTHY until block evidence appears.
    h = SourceHealth(state="HEALTHY", reason="shadow_boot_default")
    save_health(path, h)
    return h


def prepare_run_health(health: SourceHealth, *, now: datetime | None = None) -> SourceHealth:
    """Apply BLOCKED→RECOVERING when cooldown elapsed (scheduled resume)."""
    now = now or _utc_now()
    if health.state == "BLOCKED":
        until = _parse_iso(health.cooldown_until)
        if until is not None and now >= until:
            health.state = "RECOVERING"
            health.reason = "cooldown_elapsed_probe"
        elif until is None:
            # No cooldown set: stay BLOCKED (do not auto-recover)
            pass
    return health


def record_success(health: SourceHealth) -> SourceHealth:
    now = _utc_now()
    health.last_success_at = _iso(now)
    health.consecutive_failures = 0
    health.last_http_status = 200
    if health.state in ("RECOVERING", "DEGRADED", "HEALTHY", "UNAVAILABLE"):
        health.state = "HEALTHY"
    health.reason = "fetch_ok"
    health.cooldown_until = None
    return health


def record_soft_failure(
    health: SourceHealth,
    *,
    http_status: int | None,
    degraded_after: int,
) -> SourceHealth:
    now = _utc_now()
    health.last_failure_at = _iso(now)
    health.consecutive_failures = int(health.consecutive_failures or 0) + 1
    health.last_http_status = http_status
    health.reason = "fetch_failed"
    if health.state == "RECOVERING":
        # Soft fail during probe does not auto-HEALTHY; stay RECOVERING until success or block
        pass
    elif health.consecutive_failures >= degraded_after and health.state == "HEALTHY":
        health.state = "DEGRADED"
        health.reason = "repeated_failures"
    return health


def record_block(
    health: SourceHealth,
    *,
    http_status: int | None,
    cooldown_sec: float,
    reason: str = "HTTP_400_HARD_STOP",
) -> SourceHealth:
    now = _utc_now()
    health.state = "BLOCKED"
    health.last_failure_at = _iso(now)
    health.consecutive_failures = int(health.consecutive_failures or 0) + 1
    health.last_http_status = http_status
    health.reason = reason
    health.cooldown_until = _iso(now + timedelta(seconds=cooldown_sec))
    return health


def allows_mainline_fetch(health: SourceHealth) -> bool:
    return health.state in ("HEALTHY", "DEGRADED", "RECOVERING")
