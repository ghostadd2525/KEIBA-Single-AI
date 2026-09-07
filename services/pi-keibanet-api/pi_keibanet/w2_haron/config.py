# -*- coding: utf-8 -*-
"""W2 Shadow configuration (bounded work; no guessed safe rate)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ..service import _resolve_prediction_data_root

PARSER_VERSION = "haron-w2-shadow-v1"
RESULT_URL = "https://race.netkeiba.com/race/result.html?race_id={race_id}"
SOURCE_KEY = "netkeiba_page_c"
SOURCE_NAME = "netkeiba_result"

# Default research cache roots (dual-root cache-first).
_DEFAULT_REPO = Path(__file__).resolve().parents[4]  # KEIBA-Single-AI
_DEFAULT_DOCS = _DEFAULT_REPO / "docs" / "next-generation"


@dataclass
class W2Config:
    data_root: Path
    layer_b_root: Path
    lock_path: Path
    race_refresh_state_root: Path
    seal_index_path: Path
    hbf_cache_root: Path
    extsrc_cache_root: Path
    max_races_per_run: int = 5
    max_consecutive_failures: int = 3
    max_runtime_sec: float = 300.0
    stop_on_block: bool = True
    max_attempts_per_race: int = 2
    fetch_failed_cooldown_sec: float = 3600.0
    source_cooldown_sec: float = 86400.0
    min_interval_sec: float = 1.0
    fetch_enabled: bool = True
    dry_run: bool = False
    enabled: bool = True
    extra_cache_roots: list[Path] = field(default_factory=list)

    @classmethod
    def from_env(cls, *, data_root: Path | None = None) -> "W2Config":
        root = data_root or _resolve_prediction_data_root() or Path("/opt/expect-ai/platform/data")
        layer_b = Path(os.environ.get("W2_LAYER_B_ROOT", str(root / "var" / "layer_b_haron")))
        lock = Path(
            os.environ.get(
                "W2_P1_LOCK_PATH",
                str(root / "var" / "locks" / "p1_refresh.lock.json"),
            )
        )
        state_raw = os.environ.get("PI_RACE_REFRESH_STATE_ROOT")
        state_root = Path(state_raw) if state_raw else root / "var" / "race_refresh"
        seal = Path(
            os.environ.get(
                "W2_SEAL_INDEX_PATH",
                str(
                    _DEFAULT_DOCS
                    / "_v2-ng-w2-layer-b-canonical-index-seal"
                    / "layer_b_canonical_index.sealed.jsonl"
                ),
            )
        )
        hbf = Path(
            os.environ.get(
                "W2_HBF_CACHE_ROOT",
                str(_DEFAULT_DOCS / "_v2-ng-hbf-harontime-cache" / "result"),
            )
        )
        extsrc = Path(
            os.environ.get(
                "W2_EXTSRC_CACHE_ROOT",
                str(_DEFAULT_DOCS / "_v2-ng-extsrc-backfill-cache" / "result"),
            )
        )
        return cls(
            data_root=root,
            layer_b_root=layer_b,
            lock_path=lock,
            race_refresh_state_root=state_root,
            seal_index_path=seal,
            hbf_cache_root=hbf,
            extsrc_cache_root=extsrc,
            max_races_per_run=int(os.environ.get("W2_MAX_RACES_PER_RUN", "5")),
            max_consecutive_failures=int(os.environ.get("W2_MAX_CONSECUTIVE_FAILURES", "3")),
            max_runtime_sec=float(os.environ.get("W2_MAX_RUNTIME_SEC", "300")),
            stop_on_block=os.environ.get("W2_STOP_ON_BLOCK", "1") not in ("0", "false", "False"),
            max_attempts_per_race=int(os.environ.get("W2_MAX_ATTEMPTS_PER_RACE", "2")),
            fetch_failed_cooldown_sec=float(
                os.environ.get("W2_FETCH_FAILED_COOLDOWN_SEC", "3600")
            ),
            source_cooldown_sec=float(os.environ.get("W2_SOURCE_COOLDOWN_SEC", "86400")),
            min_interval_sec=float(
                os.environ.get("W2_MIN_INTERVAL_SEC")
                or os.environ.get("PI_NETKEIBA_MIN_INTERVAL_SEC", "1.0")
            ),
            fetch_enabled=os.environ.get("W2_FETCH_ENABLED", "1") not in ("0", "false", "False"),
            dry_run=os.environ.get("W2_DRY_RUN", "0") in ("1", "true", "True"),
            enabled=os.environ.get("W2_ENABLED", "1") not in ("0", "false", "False"),
        )

    @property
    def index_path(self) -> Path:
        return self.layer_b_root / "canonical_index.jsonl"

    @property
    def health_path(self) -> Path:
        return self.layer_b_root / "source_health_netkeiba_page_c.json"

    @property
    def raw_dir(self) -> Path:
        return self.layer_b_root / "raw"

    @property
    def parsed_dir(self) -> Path:
        return self.layer_b_root / "parsed"

    @property
    def runs_dir(self) -> Path:
        return self.layer_b_root / "runs"

    def cache_roots(self) -> list[Path]:
        roots = [self.raw_dir, self.hbf_cache_root, self.extsrc_cache_root]
        roots.extend(self.extra_cache_roots)
        return roots
