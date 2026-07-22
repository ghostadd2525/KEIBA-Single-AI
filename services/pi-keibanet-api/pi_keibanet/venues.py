# -*- coding: utf-8 -*-
"""JRA netkeiba venue codes ↔ Japanese names."""

from __future__ import annotations

COURSE_CODE_TO_NAME: dict[str, str] = {
    "01": "札幌",
    "02": "函館",
    "03": "福島",
    "04": "新潟",
    "05": "東京",
    "06": "中山",
    "07": "中京",
    "08": "京都",
    "09": "阪神",
    "10": "小倉",
}

COURSE_NAME_TO_CODE: dict[str, str] = {v: k for k, v in COURSE_CODE_TO_NAME.items()}


def venue_from_race_id(race_id: str) -> str:
    if len(race_id) >= 6:
        return COURSE_CODE_TO_NAME.get(race_id[4:6], race_id[4:6])
    return ""


def race_no_from_race_id(race_id: str) -> int:
    if len(race_id) >= 2:
        try:
            return int(race_id[-2:])
        except ValueError:
            pass
    return 0


def collector_race_id(date: str, venue: str, race_no: int) -> str:
    token = date.replace("-", "")
    return f"{token}_{race_no:02d}_{venue}"


def win5_pipeline_race_id(date: str, label_no: int, race_no: int) -> str:
    """Win5AI legacy runners.csv race_id format (e.g. 2026-07-19-01-10)."""
    return f"{date}-{int(label_no):02d}-{int(race_no):02d}"
