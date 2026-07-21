# -*- coding: utf-8 -*-
"""
Dynamic Contract — odds / track (C-6 正本).

STATIC とは分離。Prediction Ready には影響しない。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import FrozenSet

from .availability import KIND_DYNAMIC, RACE_DAY, REFRESHABLE


# Stale conditions
STALE_INTERVAL = "interval_elapsed"  # refresh_interval 経過で STALE
STALE_ON_CHANGE = "on_change"  # 更新イベント時のみ STALE（自動タイマなし）


@dataclass(frozen=True)
class DynamicArtifactContract:
    artifact_type: str
    kind: str
    availability: str
    prediction_required: bool
    update_policy: str
    refresh_interval_sec: int | None
    stale_condition: str
    priority: str
    description: str = ""

    @property
    def auto_refresh(self) -> bool:
        return (
            self.stale_condition == STALE_INTERVAL
            and self.refresh_interval_sec is not None
            and self.refresh_interval_sec > 0
        )


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    return int(raw)


# Contract 正本 — odds.refresh_interval は環境変数で上書き可（既定 300s = 5分、5〜10分想定）
_ODDS_REFRESH_DEFAULT_SEC = 300


def _odds_contract() -> DynamicArtifactContract:
    return DynamicArtifactContract(
        artifact_type="odds",
        kind=KIND_DYNAMIC,
        availability=RACE_DAY,
        prediction_required=False,
        update_policy=REFRESHABLE,
        refresh_interval_sec=_env_int(
            "EXPECT_COLLECT_ODDS_REFRESH_SEC",
            _ODDS_REFRESH_DEFAULT_SEC,
        ),
        stale_condition=STALE_INTERVAL,
        priority="P1",
        description="オッズ — 開催日のみ。interval 経過で STALE_DYNAMIC",
    )


def _track_contract() -> DynamicArtifactContract:
    return DynamicArtifactContract(
        artifact_type="track",
        kind=KIND_DYNAMIC,
        availability=RACE_DAY,
        prediction_required=False,
        update_policy=REFRESHABLE,
        refresh_interval_sec=None,  # 更新時のみ
        stale_condition=STALE_ON_CHANGE,
        priority="P1",
        description="馬場 — 開催日のみ。更新イベント時のみ STALE",
    )


DYNAMIC_ARTIFACT_TYPES: FrozenSet[str] = frozenset({"odds", "track"})


def get_dynamic_contract(artifact_type: str) -> DynamicArtifactContract:
    if artifact_type == "odds":
        return _odds_contract()
    if artifact_type == "track":
        return _track_contract()
    raise KeyError(f"unknown dynamic artifact: {artifact_type!r}")


def list_dynamic_contracts() -> list[DynamicArtifactContract]:
    return [_odds_contract(), _track_contract()]


def is_dynamic_artifact(artifact_type: str) -> bool:
    return artifact_type in DYNAMIC_ARTIFACT_TYPES
