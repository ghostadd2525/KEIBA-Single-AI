# -*- coding: utf-8 -*-
"""W4 horse Research config (W4-A queue / W4-B parse / W4-C/D acquire)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ..service import _resolve_prediction_data_root

_DEFAULT_REPO = Path(__file__).resolve().parents[4]
_DEFAULT_DOCS = _DEFAULT_REPO / "docs" / "next-generation"


@dataclass
class W4Config:
    data_root: Path
    w4_root: Path
    w3_root: Path
    d1_cache_roots: list[Path] = field(default_factory=list)
    d2_cache_roots: list[Path] = field(default_factory=list)
    p1_lock_path: Path | None = None
    page_c_health_path: Path | None = None
    db_horse_health_path: Path | None = None
    enabled: bool = True  # W4-A
    # W4-C/D bounds
    w4cd_enabled: bool = True
    w4cd_fetch_enabled: bool = True
    w4cd_dry_run: bool = False
    max_horses_per_run: int = 2
    max_requests_per_run: int = 4  # D1+D2 per horse worst case
    max_runtime_sec: float = 120.0
    max_consecutive_failures: int = 3
    stop_on_block: bool = True
    cooldown_seconds: float = 86400.0
    fetch_failed_cooldown_sec: float = 3600.0
    min_interval_sec: float = 1.0
    fetch_d1: bool = True
    fetch_d2: bool = True

    @classmethod
    def from_env(cls, *, data_root: Path | None = None) -> "W4Config":
        root = data_root or _resolve_prediction_data_root() or Path("/opt/expect-ai/platform/data")
        w4 = Path(os.environ.get("W4_ROOT", str(root / "var" / "w4_horse")))
        w3 = Path(os.environ.get("W3_ROOT", str(root / "var" / "w3_maiden")))
        d1_extra = os.environ.get("W4_D1_CACHE_ROOTS", "")
        d2_extra = os.environ.get("W4_D2_CACHE_ROOTS", "")
        d1_roots = [
            w4 / "cache" / "d1",
            Path(_DEFAULT_DOCS) / "_v2-ng-horse-profile-cache",
        ]
        d2_roots = [
            w4 / "cache" / "d2",
            Path(_DEFAULT_DOCS) / "_v2-ng-horse-pedigree-cache",
        ]
        if d1_extra.strip():
            d1_roots.extend(Path(p.strip()) for p in d1_extra.split(os.pathsep) if p.strip())
        if d2_extra.strip():
            d2_roots.extend(Path(p.strip()) for p in d2_extra.split(os.pathsep) if p.strip())
        lock = Path(
            os.environ.get(
                "W4_P1_LOCK_PATH",
                os.environ.get(
                    "W2_P1_LOCK_PATH",
                    str(root / "var" / "locks" / "p1_refresh.lock.json"),
                ),
            )
        )
        page_c_health = Path(
            os.environ.get(
                "W4_PAGE_C_HEALTH_PATH",
                str(root / "var" / "layer_b_haron" / "source_health_netkeiba_page_c.json"),
            )
        )
        db_health = Path(
            os.environ.get(
                "W4_DB_HORSE_HEALTH_PATH",
                str(w4 / "source_health_netkeiba_db_horse.json"),
            )
        )
        return cls(
            data_root=root,
            w4_root=w4,
            w3_root=w3,
            d1_cache_roots=d1_roots,
            d2_cache_roots=d2_roots,
            p1_lock_path=lock,
            page_c_health_path=page_c_health,
            db_horse_health_path=db_health,
            enabled=os.environ.get("W4A_ENABLED", "1") not in ("0", "false", "False"),
            w4cd_enabled=os.environ.get("W4CD_ENABLED", "1") not in ("0", "false", "False"),
            w4cd_fetch_enabled=os.environ.get("W4CD_FETCH_ENABLED", "1")
            not in ("0", "false", "False"),
            w4cd_dry_run=os.environ.get("W4CD_DRY_RUN", "0") in ("1", "true", "True"),
            max_horses_per_run=int(os.environ.get("W4_MAX_HORSES_PER_RUN", "2")),
            max_requests_per_run=int(os.environ.get("W4_MAX_REQUESTS_PER_RUN", "4")),
            max_runtime_sec=float(os.environ.get("W4_MAX_RUNTIME_SEC", "120")),
            max_consecutive_failures=int(os.environ.get("W4_MAX_CONSECUTIVE_FAILURES", "3")),
            stop_on_block=os.environ.get("W4_STOP_ON_BLOCK", "1") not in ("0", "false", "False"),
            cooldown_seconds=float(os.environ.get("W4_COOLDOWN_SECONDS", "86400")),
            fetch_failed_cooldown_sec=float(
                os.environ.get("W4_FETCH_FAILED_COOLDOWN_SEC", "3600")
            ),
            min_interval_sec=float(
                os.environ.get("W4_MIN_INTERVAL_SEC")
                or os.environ.get("PI_NETKEIBA_MIN_INTERVAL_SEC", "1.0")
            ),
            fetch_d1=os.environ.get("W4_FETCH_D1", "1") not in ("0", "false", "False"),
            fetch_d2=os.environ.get("W4_FETCH_D2", "1") not in ("0", "false", "False"),
        )

    @property
    def queue_path(self) -> Path:
        return self.w4_root / "horse_canonical_queue.jsonl"

    @property
    def provenance_path(self) -> Path:
        return self.w4_root / "horse_race_provenance.jsonl"

    @property
    def runs_dir(self) -> Path:
        return self.w4_root / "runs"

    @property
    def raw_dir(self) -> Path:
        return self.w4_root / "raw"

    @property
    def profile_raw_path(self) -> Path:
        return self.raw_dir / "horse_profile_raw.jsonl"

    @property
    def pedigree_raw_path(self) -> Path:
        return self.raw_dir / "horse_pedigree_raw.jsonl"

    @property
    def d1_cache_dir(self) -> Path:
        return self.w4_root / "cache" / "d1"

    @property
    def d2_cache_dir(self) -> Path:
        return self.w4_root / "cache" / "d2"

    @property
    def w3_runner_raw_path(self) -> Path:
        return self.w3_root / "raw" / "runner_result_raw.jsonl"

    @property
    def w3_queue_path(self) -> Path:
        return self.w3_root / "maiden_result_queue.jsonl"
