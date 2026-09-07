# -*- coding: utf-8 -*-
"""Research Evidence Platform configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


SCHEMA_VERSION = "expect-prediction-snapshot/1.1"
JOB_SCHEMA_VERSION = "expect-research-collect-job/1.0"

# Legacy Phase1 market features
PHASE1_MARKET_FEATURES = (
    "popularity",
    "win_odds",
    "expected_popularity",
    "trainer",
)

# V10.3 Horse Intelligence
HORSE_FEATURES = (
    "sire",
    "damsire",
    "breeder",
    "owner",
    "sale_price",
)

WORKOUT_FEATURES = (
    "oikiri_time",
    "oikiri_rating",
)

# All features stored on snapshot runners / indexed
PHASE1_FEATURES = PHASE1_MARKET_FEATURES + HORSE_FEATURES + WORKOUT_FEATURES

P0_FEATURES = frozenset({"popularity", "win_odds", "expected_popularity"})
P0B_FEATURES = frozenset({"trainer"})
# Coverage gate targets for V10.3 (exclude sale_price — often legitimately "-")
V103_COVERAGE_FEATURES = (
    "sire",
    "damsire",
    "breeder",
    "oikiri_time",
    "oikiri_rating",
)


def repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in [p, *p.parents]:
        if (parent / "public").is_dir() and (parent / "services").is_dir():
            return parent
    return p.parents[4]


def evidence_root() -> Path:
    env = (os.environ.get("RESEARCH_EVIDENCE_ROOT") or "").strip()
    if env:
        return Path(env)
    return repo_root() / "evidence" / "research"


def snapshot_root() -> Path:
    return evidence_root() / "prediction-snapshots"


def report_root() -> Path:
    return evidence_root() / "reports" / "weekly"


@dataclass(frozen=True)
class CollectorSettings:
    enabled: bool
    poll_interval_sec: float
    job_timeout_sec: float
    max_attempts: int
    deadline_minutes: int
    pi_base_url: str
    pi_timeout_sec: float

    @classmethod
    def from_env(cls) -> CollectorSettings:
        raw = (os.environ.get("RESEARCH_EVIDENCE_COLLECTOR") or "1").strip().lower()
        enabled = raw not in ("0", "false", "no", "off")
        base = (
            os.environ.get("EXPECT_KEIBANET_BASE_URL")
            or os.environ.get("PI_BASE_URL")
            or os.environ.get("EXPECT_PI_BASE_URL")
            or ""
        ).strip().rstrip("/")
        return cls(
            enabled=enabled,
            poll_interval_sec=float(os.environ.get("RESEARCH_COLLECTOR_POLL_SEC", "15")),
            job_timeout_sec=float(os.environ.get("RESEARCH_COLLECTOR_TIMEOUT_SEC", "25")),
            max_attempts=int(os.environ.get("RESEARCH_COLLECTOR_MAX_ATTEMPTS", "5")),
            deadline_minutes=int(os.environ.get("RESEARCH_COLLECTOR_DEADLINE_MIN", "15")),
            pi_base_url=base,
            pi_timeout_sec=float(os.environ.get("RESEARCH_PI_TIMEOUT_SEC", "20")),
        )
