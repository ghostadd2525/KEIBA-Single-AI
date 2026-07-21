# -*- coding: utf-8 -*-
"""Planner contract — collect_targets (Source of Truth: 開催カレンダー)."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "collect-target/1.0"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_VENUE_RE = re.compile(r"^[\u3040-\u9fff\u30a0-\u30ffA-Za-z0-9\-]+$")


@dataclass(frozen=True)
class CollectTarget:
    """
    Planner output row derived from 開催カレンダー (Source of Truth).

    One calendar row = (race_date, venue, race_no).
    """

    week_id: str
    calendar_version: str
    race_date: str
    venue: str
    race_no: int
    race_id: str | None = None
    public_race_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def target_key(self) -> tuple[str, str, str, int]:
        return (self.week_id, self.race_date, self.venue, self.race_no)


def validate_collect_target(raw: dict[str, Any] | CollectTarget) -> CollectTarget:
    if isinstance(raw, CollectTarget):
        _validate_fields(raw.week_id, raw.calendar_version, raw.race_date, raw.venue, raw.race_no)
        return raw

    week_id = str(raw.get("week_id") or "").strip()
    calendar_version = str(raw.get("calendar_version") or "").strip()
    race_date = str(raw.get("race_date") or "").strip()[:10]
    venue = str(raw.get("venue") or "").strip()
    race_no = int(raw.get("race_no") or 0)
    race_id = (raw.get("race_id") or None)
    public_race_id = (raw.get("public_race_id") or None)
    if race_id is not None:
        race_id = str(race_id).strip() or None
    if public_race_id is not None:
        public_race_id = str(public_race_id).strip() or None

    _validate_fields(week_id, calendar_version, race_date, venue, race_no)
    return CollectTarget(
        week_id=week_id,
        calendar_version=calendar_version,
        race_date=race_date,
        venue=venue,
        race_no=race_no,
        race_id=race_id,
        public_race_id=public_race_id,
    )


def validate_collect_targets(rows: list[dict[str, Any]]) -> list[CollectTarget]:
    seen: set[tuple[str, str, str, int]] = set()
    out: list[CollectTarget] = []
    for row in rows:
        target = validate_collect_target(row)
        key = target.target_key
        if key in seen:
            raise ValueError(f"duplicate collect_target: {key}")
        seen.add(key)
        out.append(target)
    return out


def _validate_fields(
    week_id: str,
    calendar_version: str,
    race_date: str,
    venue: str,
    race_no: int,
) -> None:
    if not week_id or not _DATE_RE.match(week_id):
        raise ValueError(f"invalid week_id: {week_id!r}")
    if not calendar_version:
        raise ValueError("calendar_version is required")
    if not race_date or not _DATE_RE.match(race_date):
        raise ValueError(f"invalid race_date: {race_date!r}")
    if not venue or not _VENUE_RE.match(venue):
        raise ValueError(f"invalid venue: {venue!r}")
    if race_no < 1 or race_no > 12:
        raise ValueError(f"race_no must be 1..12, got {race_no}")


class PlannerContract:
    """
    Planner responsibility (C-0 contract only — no KeibaNet / enqueue impl).

    Generate collect_targets from 開催カレンダー; do not derive targets from
    Collector, ETL, or SQLite catalog counts.
    """

    SOURCE_OF_TRUTH = "race_calendar"

    @staticmethod
    def validate_targets_from_calendar(
        *,
        calendar_version: str,
        week_id: str,
        targets: list[dict[str, Any]],
    ) -> list[CollectTarget]:
        validated = validate_collect_targets(targets)
        for t in validated:
            if t.calendar_version != calendar_version:
                raise ValueError(
                    f"collect_target calendar_version mismatch: {t.calendar_version!r} != {calendar_version!r}"
                )
            if t.week_id != week_id:
                raise ValueError(f"collect_target week_id mismatch: {t.week_id!r} != {week_id!r}")
        return validated
