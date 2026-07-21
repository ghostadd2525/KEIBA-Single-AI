# -*- coding: utf-8 -*-
"""Data Availability Contract — artifact 公開タイミング (C-4)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, FrozenSet


# Availability windows
WEEKDAY = "WEEKDAY"  # 平日（開催日前の月〜金）
AFTER_DRAW = "AFTER_DRAW"  # 枠順確定後
RACE_DAY = "RACE_DAY"  # 開催日当日

# Update policy
ONCE = "ONCE"  # 取得後は再取得しない（SKIPPED 経路）
REFRESHABLE = "REFRESHABLE"  # 日次再取得可（DYNAMIC）

KIND_STATIC_CORE = "STATIC_CORE"
KIND_DYNAMIC = "DYNAMIC"


@dataclass(frozen=True)
class ArtifactAvailability:
    artifact_type: str
    kind: str
    availability: str
    prediction_required: bool
    update_policy: str
    priority: str
    description: str = ""


# Contract registry — Planner が知る全 artifact（取得実装は別）
AVAILABILITY_CONTRACT: dict[str, ArtifactAvailability] = {
    "race_meta": ArtifactAvailability(
        artifact_type="race_meta",
        kind=KIND_STATIC_CORE,
        availability=WEEKDAY,
        prediction_required=True,
        update_policy=ONCE,
        priority="P1",
        description="レースメタ — 平日取得可能",
    ),
    "entries_core": ArtifactAvailability(
        artifact_type="entries_core",
        kind=KIND_STATIC_CORE,
        availability=AFTER_DRAW,
        prediction_required=True,
        update_policy=ONCE,
        priority="P1",
        description="出走表コア — 枠順確定後のみ",
    ),
    "odds": ArtifactAvailability(
        artifact_type="odds",
        kind=KIND_DYNAMIC,
        availability=RACE_DAY,
        prediction_required=False,
        update_policy=REFRESHABLE,
        priority="P1",
        description="オッズ — 開催日のみ（DYNAMIC / C-6）",
    ),
    "track": ArtifactAvailability(
        artifact_type="track",
        kind=KIND_DYNAMIC,
        availability=RACE_DAY,
        prediction_required=False,
        update_policy=REFRESHABLE,
        priority="P1",
        description="馬場 — 開催日のみ（DYNAMIC / C-6）",
    ),
}

# C-4/C-6 で Queue 生成対象（取得実装あり）
# odds/track は RACE_DAY のみ is_available → enqueue
ENQUEUEABLE_ARTIFACTS: FrozenSet[str] = frozenset(
    {"race_meta", "entries_core", "odds", "track"}
)


@dataclass(frozen=True)
class AvailabilityContext:
    """
    現時点の公開状態。

    draw_confirmed:
      True = 枠順が確定済み（entries_core を enqueue 可）
      False = 未確定 → entries_core は「未生成」（ジョブを作らない）
    """

    as_of_date: str
    draw_confirmed: bool = False


def get_availability(artifact_type: str) -> ArtifactAvailability:
    spec = AVAILABILITY_CONTRACT.get(artifact_type)
    if not spec:
        raise KeyError(f"unknown artifact_type in Availability Contract: {artifact_type!r}")
    return spec


def is_available(
    artifact_type: str,
    *,
    context: AvailabilityContext,
    race_date: str,
) -> bool:
    """
    現在取得可能な artifact か。

    False の場合は SKIPPED ではなく「未生成」— Queue にジョブを作らない。
    """
    spec = get_availability(artifact_type)
    as_of = _parse_date(context.as_of_date)
    race = _parse_date(race_date)

    if spec.availability == WEEKDAY:
        # 平日（月〜金）かつ開催日以前
        return as_of.weekday() < 5 and as_of <= race

    if spec.availability == AFTER_DRAW:
        return bool(context.draw_confirmed)

    if spec.availability == RACE_DAY:
        return as_of == race

    return False


def available_enqueueable_artifacts(
    *,
    context: AvailabilityContext,
    race_date: str,
) -> list[ArtifactAvailability]:
    """Queue 生成対象のうち、現在取得可能なものだけ返す。"""
    out: list[ArtifactAvailability] = []
    for name in sorted(ENQUEUEABLE_ARTIFACTS):
        if is_available(name, context=context, race_date=race_date):
            out.append(get_availability(name))
    return out


def list_known_artifacts() -> list[ArtifactAvailability]:
    return list(AVAILABILITY_CONTRACT.values())


def _parse_date(value: str):
    return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
