# -*- coding: utf-8 -*-
"""W5 Research — Historical maiden horse-history acquisition (lowest priority)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..service import _resolve_prediction_data_root


@dataclass
class W5Config:
    data_root: Path
    w5_root: Path
    w3_root: Path
    p1_lock_path: Path | None = None
    health_path: Path | None = None
    horse_history_raw_roots: list[Path] | None = None
    enabled: bool = True
    fetch_enabled: bool = True
    dry_run: bool = False
    max_horses_per_run: int = 2
    max_requests_per_run: int = 4
    max_runtime_sec: float = 120.0
    max_consecutive_failures: int = 3
    stop_on_block: bool = True
    cooldown_seconds: float = 86400.0
    fetch_failed_cooldown_sec: float = 3600.0
    min_interval_sec: float = 1.0

    @classmethod
    def from_env(cls, *, data_root: Path | None = None) -> "W5Config":
        root = data_root or _resolve_prediction_data_root() or Path("/opt/expect-ai/platform/data")
        w5 = Path(os.environ.get("W5_ROOT", str(root / "var" / "w5_maiden_history")))
        w3 = Path(os.environ.get("W3_ROOT", str(root / "var" / "w3_maiden")))
        hist_roots = [
            root / "var" / "race_refresh",
        ]
        extra = os.environ.get("W5_HORSE_HISTORY_RAW_ROOTS", "")
        if extra.strip():
            hist_roots.extend(Path(p.strip()) for p in extra.split(os.pathsep) if p.strip())
        return cls(
            data_root=root,
            w5_root=w5,
            w3_root=w3,
            p1_lock_path=Path(
                os.environ.get(
                    "W5_P1_LOCK_PATH",
                    str(root / "var" / "locks" / "p1_refresh.lock.json"),
                )
            ),
            health_path=Path(
                os.environ.get(
                    "W5_HEALTH_PATH",
                    str(w5 / "source_health_netkeiba_horse_history.json"),
                )
            ),
            horse_history_raw_roots=hist_roots,
            enabled=os.environ.get("W5_ENABLED", "1") not in ("0", "false", "False"),
            fetch_enabled=os.environ.get("W5_FETCH_ENABLED", "1")
            not in ("0", "false", "False"),
            dry_run=os.environ.get("W5_DRY_RUN", "0") in ("1", "true", "True"),
            max_horses_per_run=int(os.environ.get("W5_MAX_HORSES_PER_RUN", "2")),
            max_requests_per_run=int(os.environ.get("W5_MAX_REQUESTS_PER_RUN", "4")),
            max_runtime_sec=float(os.environ.get("W5_MAX_RUNTIME_SEC", "120")),
            max_consecutive_failures=int(os.environ.get("W5_MAX_CONSECUTIVE_FAILURES", "3")),
            stop_on_block=os.environ.get("W5_STOP_ON_BLOCK", "1") not in ("0", "false", "False"),
            cooldown_seconds=float(os.environ.get("W5_COOLDOWN_SECONDS", "86400")),
            fetch_failed_cooldown_sec=float(
                os.environ.get("W5_FETCH_FAILED_COOLDOWN_SEC", "3600")
            ),
            min_interval_sec=float(
                os.environ.get("W5_MIN_INTERVAL_SEC")
                or os.environ.get("PI_NETKEIBA_MIN_INTERVAL_SEC", "1.0")
            ),
        )

    @property
    def queue_path(self) -> Path:
        return self.w5_root / "horse_history_queue.jsonl"

    @property
    def raw_path(self) -> Path:
        return self.w5_root / "raw" / "horse_history_research.jsonl"

    @property
    def cache_dir(self) -> Path:
        return self.w5_root / "cache" / "ajax"

    @property
    def runs_dir(self) -> Path:
        return self.w5_root / "runs"

    @property
    def w3_runner_raw_path(self) -> Path:
        return self.w3_root / "raw" / "runner_result_raw.jsonl"

    @property
    def w3_race_raw_path(self) -> Path:
        return self.w3_root / "raw" / "race_raw.jsonl"

    @property
    def w3_queue_path(self) -> Path:
        return self.w3_root / "maiden_result_queue.jsonl"
