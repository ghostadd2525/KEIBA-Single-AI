# -*- coding: utf-8 -*-
"""Web GUI race catalog helpers (display identity for venue → race selection)."""
from __future__ import annotations

import re
from typing import Any, Optional

from .venues import COURSE_NAME_TO_CODE, win5_pipeline_race_id

# Preferred venue order for label_no assignment (Win5-compatible).
DEFAULT_VENUE_ORDER = (
    "札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉",
)

_WIN5_RACE_ID_RE = re.compile(
    r"^(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})-(?P<label>\d{2})-(?P<rno>\d{2})$"
)
_COLLECTOR_RACE_ID_RE = re.compile(
    r"^(?P<ymd>\d{8})_(?P<rno>\d{2})_(?P<venue>.+)$"
)


def race_label(course: str, race_number: int) -> str:
    """Human-readable label for GUI, e.g. 新潟6R."""
    return f"{course}{int(race_number)}R"


def build_race_summary(
    *,
    race_id: str,
    race_date: str,
    course: str,
    race_number: int,
    race_name: str = "",
    numeric_race_id: str = "",
    status: str = "published",
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Canonical race identity payload for Web + Prediction.

    - race_id: Prediction key (Win5 format preferred)
    - course / race_number: selection & display (never drop)
    - race_label: GUI string
    - venue / race_no: aliases for Collector / older clients
    """
    payload: dict[str, Any] = {
        "race_id": race_id,
        "race_date": race_date,
        "date": race_date,
        "course": course,
        "venue": course,
        "race_number": int(race_number),
        "race_no": int(race_number),
        "race_label": race_label(course, race_number),
        "race_name": race_name or "",
        "numeric_race_id": numeric_race_id or "",
        "status": status,
    }
    if extra:
        payload.update(extra)
    return payload


def assign_venue_label_nos(
    venues: list[str],
    *,
    preferred_order: list[str] | None = None,
) -> dict[str, int]:
    """
    Assign 1-based label_no per venue for Win5 race_id.

    preferred_order: meeting order from race_list (stable with pipeline / GUI).
    Falls back to DEFAULT_VENUE_ORDER for any remaining venues.
    """
    ordered: list[str] = []
    seen: set[str] = set()
    for v in preferred_order or []:
        if v in venues and v not in seen:
            ordered.append(v)
            seen.add(v)
    rest = sorted(
        [v for v in venues if v not in seen],
        key=lambda x: (
            DEFAULT_VENUE_ORDER.index(x) if x in DEFAULT_VENUE_ORDER else 999,
            x,
        ),
    )
    ordered.extend(rest)
    return {v: i + 1 for i, v in enumerate(ordered)}


def make_win5_race_id(date: str, course: str, race_number: int, venue_labels: dict[str, int]) -> str:
    label_no = venue_labels.get(course, 1)
    return win5_pipeline_race_id(date, label_no, race_number)


def parse_race_id_ref(race_id: str) -> dict[str, Any]:
    """
    Parse Win5 or collector race_id into structured parts.

    Win5:      2026-07-25-01-06
    Collector: 20260725_06_新潟
    """
    rid = str(race_id or "").strip()
    m = _WIN5_RACE_ID_RE.match(rid)
    if m:
        return {
            "format": "win5",
            "race_id": rid,
            "race_date": f"{m.group('y')}-{m.group('m')}-{m.group('d')}",
            "label_no": int(m.group("label")),
            "race_number": int(m.group("rno")),
            "course": "",
        }
    m = _COLLECTOR_RACE_ID_RE.match(rid)
    if m:
        ymd = m.group("ymd")
        return {
            "format": "collector",
            "race_id": rid,
            "race_date": f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}",
            "label_no": None,
            "race_number": int(m.group("rno")),
            "course": m.group("venue"),
        }
    raise ValueError(f"unsupported race_id format: {rid!r}")


def group_races_by_course(
    races: list[dict[str, Any]],
    *,
    preferred_order: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build venues[] tree for GET /v1/races?date=..."""
    by_course: dict[str, list[dict[str, Any]]] = {}
    for race in races:
        course = str(race.get("course") or race.get("venue") or "")
        by_course.setdefault(course, []).append(race)

    order_index = {v: i for i, v in enumerate(preferred_order or [])}
    venues_out: list[dict[str, Any]] = []
    for course in sorted(
        by_course.keys(),
        key=lambda v: (
            order_index.get(v, 1000 + (
                DEFAULT_VENUE_ORDER.index(v) if v in DEFAULT_VENUE_ORDER else 999
            )),
            v,
        ),
    ):
        items = sorted(by_course[course], key=lambda r: int(r.get("race_number") or 0))
        venues_out.append({
            "course": course,
            "venue": course,
            "races": items,
        })
    return venues_out
