#!/usr/bin/env python3
"""Historical maiden dry-run from local C4 / race_refresh artifacts only.

Uses real page_a1_store paths (kaisai_day_index.json + page_a1/listed_races.json)
and the real W3 JSONL queue. Does not invent race IDs.
Unknown days stay unknown (not zero maidens). HTTP is forbidden.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.c4_calendar.config import C4Config
from pi_keibanet.page_a1_store import listed_path, load_index
from pi_keibanet.w3_maiden.config import MAIDEN_TOKEN, W3AConfig
from pi_keibanet.w3_maiden.handoff import (
    _discover_complete_dates,
    _is_race_day_complete,
    _load_listed,
)
from pi_keibanet.w3_maiden.queue import load_queue

YEAR_START = "2024-01-01"
YEAR_END = "2026-12-31"


def _load_json(path: Path) -> object | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _year_of(date_s: str) -> str:
    return date_s[:4] if len(date_s) >= 4 else "unknown"


def _week_calendar_dates(c4_root: Path) -> dict[str, str]:
    dates: dict[str, str] = {}
    weeks_dir = c4_root / "weeks"
    if not weeks_dir.is_dir():
        return dates
    for week_dir in sorted(p for p in weeks_dir.iterdir() if p.is_dir()):
        cal = _load_json(week_dir / "calendar.json")
        if not isinstance(cal, dict):
            continue
        days = cal.get("days")
        if not isinstance(days, list):
            continue
        for day in days:
            if not isinstance(day, dict):
                continue
            date_s = day.get("date")
            if not isinstance(date_s, str):
                continue
            if date_s < YEAR_START or date_s > YEAR_END:
                continue
            dates[date_s] = "week_calendar"
    return dates


def _maiden_ids_from_listed(path: Path) -> list[str]:
    ids: list[str] = []
    for race in _load_listed(path):
        name = str(race.get("race_name") or "")
        if MAIDEN_TOKEN not in name:
            continue
        race_id = str(race.get("race_id") or "").strip()
        if race_id:
            ids.append(race_id)
    return ids


def _existing_w3_years(queue_path: Path) -> dict[str, int]:
    counts: dict[str, int] = {"2024": 0, "2025": 0, "2026": 0}
    for race_id, rec in load_queue(queue_path).items():
        date_s = rec.get("kaisai_date") or rec.get("date")
        if isinstance(date_s, str) and date_s[:4] in counts:
            counts[date_s[:4]] += 1
            continue
        if isinstance(race_id, str) and race_id[:4] in counts:
            counts[race_id[:4]] += 1
    return counts


def run_historical_dry_run(cfg: W3AConfig | None = None) -> dict:
    cfg = cfg or W3AConfig.from_env()
    c4_cfg = C4Config.from_env(data_root=cfg.data_root)
    known_complete = _discover_complete_dates(cfg.race_refresh_state_root, cfg.c4_queue_path)
    week_dates = _week_calendar_dates(c4_cfg.c4_root)

    planned_by_year: Counter[str] = Counter()
    planned_ids: list[str] = []
    missing_listed: list[str] = []
    unknown_days: list[str] = []

    for date_s in known_complete:
        if date_s < YEAR_START or date_s > YEAR_END:
            continue
        idx = load_index(cfg.race_refresh_state_root, date_s)
        if not _is_race_day_complete(idx):
            unknown_days.append(date_s)
            continue
        listed = listed_path(cfg.race_refresh_state_root, date_s)
        if not listed.is_file():
            missing_listed.append(date_s)
            continue
        ids = _maiden_ids_from_listed(listed)
        planned_ids.extend(ids)
        planned_by_year[_year_of(date_s)] += len(ids)

    refresh_dirs: set[str] = set()
    if cfg.race_refresh_state_root.is_dir():
        for child in cfg.race_refresh_state_root.iterdir():
            if child.is_dir() and len(child.name) == 10 and child.name[4] == "-":
                refresh_dirs.add(child.name)

    week_only = [
        d
        for d in week_dates
        if d not in known_complete and d not in refresh_dirs
    ]
    unknown = sorted(set(unknown_days + week_only))
    existing = _existing_w3_years(cfg.queue_path)

    return {
        "ok": True,
        "http_calls": 0,
        "maiden_token": MAIDEN_TOKEN,
        "year_window": {"start": YEAR_START, "end": YEAR_END},
        "known_complete_dates": list(known_complete),
        "known_complete_count": len(known_complete),
        "planned_maiden_race_ids": planned_ids,
        "planned_maiden_count": len(planned_ids),
        "planned_by_year": {
            "2024": planned_by_year.get("2024", 0),
            "2025": planned_by_year.get("2025", 0),
            "2026": planned_by_year.get("2026", 0),
        },
        "existing_w3_queue_by_year": existing,
        "unknown_days": unknown,
        "unknown_day_count": len(unknown),
        "missing_listed_races": missing_listed,
        "note": "unknown days are not treated as 0 maidens; no race-id brute force",
        "artifacts_used": [
            "PI_RACE_REFRESH_STATE_ROOT/*/kaisai_day_index.json",
            "PI_RACE_REFRESH_STATE_ROOT/*/page_a1/listed_races.json",
            "C4 calendar_queue.jsonl",
            "C4 weeks/*/calendar.json",
            "W3 maiden_result_queue.jsonl",
        ],
    }


def main() -> int:
    report = run_historical_dry_run()
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
