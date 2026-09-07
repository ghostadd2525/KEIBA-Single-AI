# -*- coding: utf-8 -*-
"""C4 Shadow configuration (bounded; no guessed safe rate)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..service import _resolve_prediction_data_root

SOURCE_KEY = "netkeiba_page_a1"
UNIVERSE_START = "2024-01-01"
UNIVERSE_AS_OF = "2026-08-10"

_DEFAULT_REPO = Path(__file__).resolve().parents[4]
_DEFAULT_DOCS = _DEFAULT_REPO / "docs" / "next-generation"
_DEFAULT_KNOWN = (
    _DEFAULT_DOCS
    / "_v2-ng-c4-historical-page-a1-feasibility-artifacts"
    / "known_jra_dates_page_a1_state.jsonl"
)


@dataclass
class C4Config:
    data_root: Path
    c4_root: Path
    lock_path: Path
    race_refresh_state_root: Path
    known_dates_path: Path
    domain_halt_path: Path
    universe_start: str = UNIVERSE_START
    universe_as_of: str = UNIVERSE_AS_OF
    max_dates_per_run: int = 2
    max_requests_per_run: int = 4
    max_runtime_sec: float = 120.0
    max_consecutive_failures: int = 3
    stop_on_block: bool = True
    cooldown_seconds: float = 86400.0
    fetch_failed_cooldown_sec: float = 3600.0
    min_interval_sec: float = 1.0
    max_attempts_per_date: int = 8
    fetch_enabled: bool = True
    dry_run: bool = False
    enabled: bool = True

    @classmethod
    def from_env(cls, *, data_root: Path | None = None) -> "C4Config":
        root = data_root or _resolve_prediction_data_root() or Path("/opt/expect-ai/platform/data")
        c4_root = Path(os.environ.get("C4_ROOT", str(root / "var" / "c4_calendar")))
        lock = Path(
            os.environ.get(
                "C4_P1_LOCK_PATH",
                os.environ.get(
                    "W2_P1_LOCK_PATH",
                    str(root / "var" / "locks" / "p1_refresh.lock.json"),
                ),
            )
        )
        state_raw = os.environ.get("PI_RACE_REFRESH_STATE_ROOT")
        state_root = Path(state_raw) if state_raw else root / "var" / "race_refresh"
        known = Path(os.environ.get("C4_KNOWN_DATES_PATH", str(_DEFAULT_KNOWN)))
        halt = Path(
            os.environ.get(
                "C4_DOMAIN_HALT_PATH",
                str(root / "var" / "locks" / "netkeiba_domain_halt.json"),
            )
        )
        return cls(
            data_root=root,
            c4_root=c4_root,
            lock_path=lock,
            race_refresh_state_root=state_root,
            known_dates_path=known,
            domain_halt_path=halt,
            universe_start=os.environ.get("C4_UNIVERSE_START", UNIVERSE_START),
            universe_as_of=os.environ.get("C4_UNIVERSE_AS_OF", UNIVERSE_AS_OF),
            max_dates_per_run=int(os.environ.get("C4_MAX_DATES_PER_RUN", "2")),
            max_requests_per_run=int(os.environ.get("C4_MAX_REQUESTS_PER_RUN", "4")),
            max_runtime_sec=float(os.environ.get("C4_MAX_RUNTIME_SEC", "120")),
            max_consecutive_failures=int(os.environ.get("C4_MAX_CONSECUTIVE_FAILURES", "3")),
            stop_on_block=os.environ.get("C4_STOP_ON_BLOCK", "1") not in ("0", "false", "False"),
            cooldown_seconds=float(os.environ.get("C4_COOLDOWN_SECONDS", "86400")),
            fetch_failed_cooldown_sec=float(
                os.environ.get("C4_FETCH_FAILED_COOLDOWN_SEC", "3600")
            ),
            min_interval_sec=float(
                os.environ.get("C4_MIN_INTERVAL_SEC")
                or os.environ.get("PI_NETKEIBA_MIN_INTERVAL_SEC", "1.0")
            ),
            # Finite persistent bound — prevents PARTIAL empty-day retry storms.
            # Default 8: allows short transient uncertainty without infinite retry.
            max_attempts_per_date=int(os.environ.get("C4_MAX_ATTEMPTS_PER_DATE", "8")),
            fetch_enabled=os.environ.get("C4_FETCH_ENABLED", "1") not in ("0", "false", "False"),
            dry_run=os.environ.get("C4_DRY_RUN", "0") in ("1", "true", "True"),
            enabled=os.environ.get("C4_ENABLED", "1") not in ("0", "false", "False"),
        )

    @property
    def queue_path(self) -> Path:
        return self.c4_root / "calendar_queue.jsonl"

    @property
    def health_path(self) -> Path:
        return self.c4_root / "source_health_netkeiba_page_a1.json"

    @property
    def runs_dir(self) -> Path:
        return self.c4_root / "runs"
