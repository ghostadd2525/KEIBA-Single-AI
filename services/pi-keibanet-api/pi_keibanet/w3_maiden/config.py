# -*- coding: utf-8 -*-
"""W3 maiden Research config (W3-A handoff / W3-B parse / W3-C acquisition)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ..service import _resolve_prediction_data_root
from ..w2_haron.config import RESULT_URL, SOURCE_KEY

MAIDEN_TOKEN = "未勝利"
IDENTIFICATION_BASIS = "race_name_contains_literal_maiden"
SOURCE_LABEL = "c4_page_a1_listed_races"
PAGE_C_SOURCE_KEY = SOURCE_KEY  # netkeiba_page_c — shared with W2
PAGE_C_RESULT_URL = RESULT_URL

_DEFAULT_REPO = Path(__file__).resolve().parents[4]
_DEFAULT_DOCS = _DEFAULT_REPO / "docs" / "next-generation"


@dataclass
class W3AConfig:
    data_root: Path
    w3_root: Path
    race_refresh_state_root: Path
    c4_queue_path: Path
    hbf_cache_root: Path
    extsrc_cache_root: Path
    w2_raw_root: Path
    # W3-C / shared PAGE-C
    p1_lock_path: Path | None = None
    page_c_health_path: Path | None = None
    extra_cache_roots: list[Path] = field(default_factory=list)
    enabled: bool = True  # W3-A
    # W3-A supply bounds / fail-closed (new; systemd does not set these)
    w3a_handoff_dry_run: bool = True
    w3a_max_enqueue_per_run: int = 2
    # W3-C bounds (safe defaults — never bulk 56)
    w3c_enabled: bool = True
    w3c_fetch_enabled: bool = True
    w3c_dry_run: bool = False
    max_races_per_run: int = 2
    max_requests_per_run: int = 2
    max_runtime_sec: float = 120.0
    max_consecutive_failures: int = 3
    max_attempts_per_race: int = 2
    stop_on_block: bool = True
    cooldown_seconds: float = 86400.0
    fetch_failed_cooldown_sec: float = 3600.0
    min_interval_sec: float = 1.0

    @classmethod
    def from_env(cls, *, data_root: Path | None = None) -> "W3AConfig":
        root = data_root or _resolve_prediction_data_root() or Path("/opt/expect-ai/platform/data")
        w3 = Path(os.environ.get("W3_ROOT", str(root / "var" / "w3_maiden")))
        state_raw = os.environ.get("PI_RACE_REFRESH_STATE_ROOT")
        state = Path(state_raw) if state_raw else root / "var" / "race_refresh"
        c4q = Path(
            os.environ.get(
                "W3_C4_QUEUE_PATH",
                str(root / "var" / "c4_calendar" / "calendar_queue.jsonl"),
            )
        )
        hbf = Path(
            os.environ.get(
                "W3_HBF_CACHE_ROOT",
                os.environ.get(
                    "W2_HBF_CACHE_ROOT",
                    str(_DEFAULT_DOCS / "_v2-ng-hbf-harontime-cache" / "result"),
                ),
            )
        )
        extsrc = Path(
            os.environ.get(
                "W3_EXTSRC_CACHE_ROOT",
                os.environ.get(
                    "W2_EXTSRC_CACHE_ROOT",
                    str(_DEFAULT_DOCS / "_v2-ng-extsrc-backfill-cache" / "result"),
                ),
            )
        )
        w2_raw = Path(
            os.environ.get(
                "W3_W2_RAW_ROOT",
                str(root / "var" / "layer_b_haron" / "raw"),
            )
        )
        lock = Path(
            os.environ.get(
                "W3_P1_LOCK_PATH",
                os.environ.get(
                    "W2_P1_LOCK_PATH",
                    str(root / "var" / "locks" / "p1_refresh.lock.json"),
                ),
            )
        )
        health = Path(
            os.environ.get(
                "W3_PAGE_C_HEALTH_PATH",
                str(root / "var" / "layer_b_haron" / "source_health_netkeiba_page_c.json"),
            )
        )
        extra: list[Path] = []
        raw_extra = os.environ.get("W3_EXTRA_CACHE_ROOTS", "")
        if raw_extra.strip():
            extra = [Path(p.strip()) for p in raw_extra.split(os.pathsep) if p.strip()]
        return cls(
            data_root=root,
            w3_root=w3,
            race_refresh_state_root=state,
            c4_queue_path=c4q,
            hbf_cache_root=hbf,
            extsrc_cache_root=extsrc,
            w2_raw_root=w2_raw,
            p1_lock_path=lock,
            page_c_health_path=health,
            extra_cache_roots=extra,
            enabled=os.environ.get("W3A_ENABLED", "1") not in ("0", "false", "False"),
            w3a_handoff_dry_run=os.environ.get("W3A_HANDOFF_DRY_RUN", "1")
            not in ("0", "false", "False"),
            w3a_max_enqueue_per_run=int(os.environ.get("W3A_MAX_ENQUEUE_PER_RUN", "2")),
            w3c_enabled=os.environ.get("W3C_ENABLED", "1") not in ("0", "false", "False"),
            w3c_fetch_enabled=os.environ.get("W3C_FETCH_ENABLED", "1")
            not in ("0", "false", "False"),
            w3c_dry_run=os.environ.get("W3C_DRY_RUN", "0") in ("1", "true", "True"),
            max_races_per_run=int(os.environ.get("W3C_MAX_RACES_PER_RUN", "2")),
            max_requests_per_run=int(os.environ.get("W3C_MAX_REQUESTS_PER_RUN", "2")),
            max_runtime_sec=float(os.environ.get("W3C_MAX_RUNTIME_SEC", "120")),
            max_consecutive_failures=int(
                os.environ.get("W3C_MAX_CONSECUTIVE_FAILURES", "3")
            ),
            max_attempts_per_race=int(os.environ.get("W3C_MAX_ATTEMPTS_PER_RACE", "2")),
            stop_on_block=os.environ.get("W3C_STOP_ON_BLOCK", "1")
            not in ("0", "false", "False"),
            cooldown_seconds=float(os.environ.get("W3C_COOLDOWN_SECONDS", "86400")),
            fetch_failed_cooldown_sec=float(
                os.environ.get("W3C_FETCH_FAILED_COOLDOWN_SEC", "3600")
            ),
            min_interval_sec=float(
                os.environ.get("W3C_MIN_INTERVAL_SEC")
                or os.environ.get("W2_MIN_INTERVAL_SEC")
                or os.environ.get("PI_NETKEIBA_MIN_INTERVAL_SEC", "1.0")
            ),
        )

    @property
    def queue_path(self) -> Path:
        return self.w3_root / "maiden_result_queue.jsonl"

    @property
    def runs_dir(self) -> Path:
        return self.w3_root / "runs"

    @property
    def raw_dir(self) -> Path:
        return self.w3_root / "raw"

    @property
    def race_raw_path(self) -> Path:
        return self.raw_dir / "race_raw.jsonl"

    @property
    def runner_raw_path(self) -> Path:
        return self.raw_dir / "runner_result_raw.jsonl"

    @property
    def page_c_cache_dir(self) -> Path:
        """W3-owned PAGE-C HTML mirror (also written to shared W2 raw on fetch)."""
        return self.w3_root / "page_c_cache"

    def cache_roots(self) -> list[Path]:
        roots = [
            self.page_c_cache_dir,
            self.hbf_cache_root,
            self.extsrc_cache_root,
            self.w2_raw_root,
            *self.extra_cache_roots,
        ]
        out: list[Path] = []
        seen: set[str] = set()
        for r in roots:
            key = str(r)
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
        return out
