#!/usr/bin/env python3
"""Historical maiden dry-run from local C4 / race_refresh artifacts only.

Separates known / existing / missing. planned_new_race_ids is missing after
deterministic order + enqueue cap. Existing queue rows are never planned.
Unknown days stay unknown (not zero maidens). HTTP is forbidden.
"""
from __future__ import annotations

import json
import sys
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
from pi_keibanet.w3_maiden.queue import is_valid_race_id, load_queue

YEAR_START = "2024-01-01"
YEAR_END = "2026-12-31"
YEARS = ("2024", "2025", "2026")


def _load_json(path: Path) -> object | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _year_of(value: str) -> str:
    y = value[:4] if len(value) >= 4 else "unknown"
    return y if y in YEARS else "unknown"


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


def _existing_w3_ids(queue_path: Path) -> dict[str, list[str]]:
    by_year: dict[str, list[str]] = {y: [] for y in YEARS}
    for race_id, rec in load_queue(queue_path).items():
        if not is_valid_race_id(race_id):
            continue
        date_s = rec.get("kaisai_date") or rec.get("date") or race_id
        year = _year_of(str(date_s))
        if year in by_year:
            by_year[year].append(race_id)
    for year in YEARS:
        by_year[year] = sorted(set(by_year[year]))
    return by_year


def run_historical_dry_run(cfg: W3AConfig | None = None) -> dict:
    cfg = cfg or W3AConfig.from_env()
    c4_cfg = C4Config.from_env(data_root=cfg.data_root)
    known_complete = _discover_complete_dates(cfg.race_refresh_state_root, cfg.c4_queue_path)
    week_dates = _week_calendar_dates(c4_cfg.c4_root)

    known_by_year: dict[str, list[str]] = {y: [] for y in YEARS}
    known_order: list[str] = []
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
        for race in _load_listed(listed):
            name = str(race.get("race_name") or "")
            if MAIDEN_TOKEN not in name:
                continue
            race_id = str(race.get("race_id") or "").strip()
            if not is_valid_race_id(race_id):
                continue
            year = _year_of(date_s)
            if year in known_by_year and race_id not in known_by_year[year]:
                known_by_year[year].append(race_id)
            if race_id not in known_order:
                known_order.append(race_id)

    existing_by_year = _existing_w3_ids(cfg.queue_path)
    existing_all = {rid for ids in existing_by_year.values() for rid in ids}
    missing_order = [rid for rid in known_order if rid not in existing_all]
    missing_by_year: dict[str, list[str]] = {y: [] for y in YEARS}
    known_sets = {y: set(known_by_year[y]) for y in YEARS}
    existing_sets = {y: set(existing_by_year[y]) for y in YEARS}
    for year in YEARS:
        missing_by_year[year] = sorted(known_sets[year] - existing_sets[year])

    cap = int(cfg.w3a_max_enqueue_per_run)
    planned = missing_order[:cap]

    refresh_dirs: set[str] = set()
    if cfg.race_refresh_state_root.is_dir():
        for child in cfg.race_refresh_state_root.iterdir():
            if child.is_dir() and len(child.name) == 10 and child.name[4] == "-":
                refresh_dirs.add(child.name)
    week_only = [d for d in week_dates if d not in known_complete and d not in refresh_dirs]
    unknown = sorted(set(unknown_days + week_only))

    return {
        "ok": True,
        "http_calls": 0,
        "maiden_token": MAIDEN_TOKEN,
        "year_window": {"start": YEAR_START, "end": YEAR_END},
        "known_maiden_race_ids": known_by_year,
        "existing_w3_race_ids": existing_by_year,
        "missing_maiden_race_ids": missing_by_year,
        "known_maiden_count": {y: len(known_by_year[y]) for y in YEARS},
        "existing_w3_count": {y: len(existing_by_year[y]) for y in YEARS},
        "missing_maiden_count": {y: len(missing_by_year[y]) for y in YEARS},
        "unknown_days": unknown,
        "unknown_day_count": len(unknown),
        "missing_listed_days": missing_listed,
        "planned_new_race_ids": planned,
        "planned_new_count": len(planned),
        "enqueue_cap": cap,
        "note": "missing = known - existing; planned is missing after deterministic scan + cap; unknown days are not 0 maidens",
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
