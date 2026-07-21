# -*- coding: utf-8 -*-
"""開催カレンダー input contract — Planner Source of Truth (C-2)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class RaceCalendarDay:
    race_date: str
    venues: dict[str, int]
    venue_races: dict[str, tuple[int, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class RaceCalendar:
    """
    開催カレンダー正本 — Planner の唯一入力。

    全開催場 × 土日全レースを展開する。Win5 絞り込みは禁止。
    """

    calendar_version: str
    week_id: str
    days: tuple[RaceCalendarDay, ...] = field(default_factory=tuple)

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> RaceCalendar:
        calendar_version = str(raw.get("calendar_version") or "").strip()
        week_id = str(raw.get("week_id") or "").strip()[:10]
        if not calendar_version:
            raise ValueError("calendar_version is required")
        if not week_id or not _DATE_RE.match(week_id):
            raise ValueError(f"invalid week_id: {week_id!r}")

        days_raw = raw.get("days") or raw.get("weekend") or []
        if not isinstance(days_raw, list) or not days_raw:
            raise ValueError("calendar days/weekend is required")

        days: list[RaceCalendarDay] = []
        for item in days_raw:
            race_date = str(item.get("race_date") or "").strip()[:10]
            venues_raw = item.get("venues") or {}
            if not race_date or not _DATE_RE.match(race_date):
                raise ValueError(f"invalid race_date in calendar: {race_date!r}")
            if not isinstance(venues_raw, dict) or not venues_raw:
                raise ValueError(f"venues required for race_date {race_date!r}")
            venues: dict[str, int] = {}
            venue_races: dict[str, tuple[int, ...]] = {}
            venue_races_raw = item.get("venue_races") or {}
            for name, count in venues_raw.items():
                venue = str(name).strip()
                races = int(count)
                if not venue:
                    raise ValueError("venue name must not be empty")
                if races < 1 or races > 12:
                    raise ValueError(f"venue {venue!r} race count must be 1..12, got {races}")
                venues[venue] = races
                if venue in venue_races_raw:
                    nums = venue_races_raw[venue]
                    if not isinstance(nums, list) or not nums:
                        raise ValueError(f"venue_races[{venue!r}] must be non-empty list")
                    parsed = tuple(sorted({int(n) for n in nums}))
                    for n in parsed:
                        if n < 1 or n > 12:
                            raise ValueError(f"venue_races[{venue!r}] invalid race_no {n}")
                    venue_races[venue] = parsed
            _assert_weekend_date(week_id, race_date)
            days.append(
                RaceCalendarDay(
                    race_date=race_date,
                    venues=venues,
                    venue_races=venue_races,
                )
            )

        return RaceCalendar(
            calendar_version=calendar_version,
            week_id=week_id,
            days=tuple(days),
        )

    def race_count_per_venue(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for day in self.days:
            for venue, max_r in day.venues.items():
                if venue in day.venue_races:
                    out.setdefault(day.race_date, {})[venue] = len(day.venue_races[venue])
                else:
                    out.setdefault(day.race_date, {})[venue] = max_r
        return out

    def venue_count(self) -> int:
        venues: set[str] = set()
        for day in self.days:
            venues.update(day.venues.keys())
        return len(venues)

    def total_races_expected(self) -> int:
        total = 0
        for day in self.days:
            for venue in day.venues:
                if venue in day.venue_races:
                    total += len(day.venue_races[venue])
                else:
                    total += day.venues[venue]
        return total


def _assert_weekend_date(week_id: str, race_date: str) -> None:
    anchor = datetime.strptime(week_id, "%Y-%m-%d").date()
    if anchor.weekday() != 5:
        raise ValueError(f"week_id must be Saturday, got {week_id!r}")
    sunday = anchor + timedelta(days=1)
    allowed = {anchor.isoformat(), sunday.isoformat()}
    if race_date not in allowed:
        raise ValueError(
            f"race_date {race_date!r} must be weekend of week_id {week_id!r} ({allowed})"
        )


def expand_calendar_targets(calendar: RaceCalendar) -> list[dict[str, Any]]:
    """Expand calendar to collect_targets rows (all venues × all R)."""
    rows: list[dict[str, Any]] = []
    for day in calendar.days:
        for venue, max_r in day.venues.items():
            race_numbers = day.venue_races.get(venue) or tuple(range(1, max_r + 1))
            for race_no in race_numbers:
                race_id = _synthetic_race_id(day.race_date, venue, race_no)
                rows.append(
                    {
                        "week_id": calendar.week_id,
                        "calendar_version": calendar.calendar_version,
                        "race_date": day.race_date,
                        "venue": venue,
                        "race_no": race_no,
                        "race_id": race_id,
                    }
                )
    return rows


def _synthetic_race_id(race_date: str, venue: str, race_no: int) -> str:
    compact = race_date.replace("-", "")
    venue_key = venue.replace(" ", "")
    return f"{compact}_{race_no:02d}_{venue_key}"
