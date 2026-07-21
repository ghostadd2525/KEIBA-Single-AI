# -*- coding: utf-8 -*-
"""
Weekday Distribution — scheduled_for を月〜金へ計画分散 (C-8).

Budget 停止に頼らず、enqueue 時点で平日へ割り当てる。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Sequence

from .availability import AFTER_DRAW, RACE_DAY, get_availability


def parse_date(value: str | date) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()


def weekday_window_for_week(week_id: str) -> list[date]:
    """
    week_id（土曜基準）直前の月〜金を返す。

    例: week_id=2026-07-25 (Sat) → Mon 20 … Fri 24
    """
    saturday = parse_date(week_id)
    if saturday.weekday() != 5:
        saturday = saturday + timedelta(days=(5 - saturday.weekday()) % 7)
    monday = saturday - timedelta(days=5)
    return [monday + timedelta(days=i) for i in range(5)]


def friday_of_week(week_id: str) -> date:
    return weekday_window_for_week(week_id)[-1]


@dataclass(frozen=True)
class EnqueueSlot:
    artifact_type: str
    race_date: str


def plan_scheduled_dates(
    slots: Sequence[EnqueueSlot],
    *,
    week_id: str,
    context_as_of: str,
    daily_limit: int,
    fixed_scheduled_for: str | None = None,
) -> list[str]:
    """
    ジョブ列に対する scheduled_for 列を返す（slots と同じ順序）。

    アルゴリズム:
    1. fixed 指定 → 全ジョブその日
    2. RACE_DAY → race_date
    3. AFTER_DRAW → context_as_of
    4. WEEKDAY → 月〜金へ最小負荷優先で割当（1 日上限 = daily_limit、超過時は最小負荷日へ積み増し）
    """
    if fixed_scheduled_for:
        fixed = str(fixed_scheduled_for)[:10]
        return [fixed for _ in slots]

    days = weekday_window_for_week(week_id)
    loads = [0, 0, 0, 0, 0]
    cap = max(1, int(daily_limit))
    out: list[str] = []

    for slot in slots:
        spec = get_availability(slot.artifact_type)
        if spec.availability == RACE_DAY:
            out.append(str(slot.race_date)[:10])
            continue
        if spec.availability == AFTER_DRAW:
            out.append(str(context_as_of)[:10])
            continue

        # WEEKDAY: pick day with lowest load; prefer under-cap days
        under = [i for i in range(5) if loads[i] < cap]
        if under:
            day_i = min(under, key=lambda i: (loads[i], i))
        else:
            day_i = min(range(5), key=lambda i: (loads[i], i))
        loads[day_i] += 1
        out.append(days[day_i].isoformat())

    return out


def summarize_distribution(scheduled_dates: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in scheduled_dates:
        key = str(d)[:10]
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))
