# -*- coding: utf-8 -*-
"""
Version7.1 ResultAutomation cadence helpers (REPAIR).

Expected races = official day catalog (not legacy predictions).
Day complete iff settled_result_races == expected_result_races.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from ..data import db as app_db
from . import state_machine as sm
from .result_automation import archive_root
from .result_day_contract import (
    RESULT_TARGET_AUTHORITY,
    build_day_settlement,
    CatalogLoader,
)

JST = ZoneInfo("Asia/Tokyo")

ACTIVE_MIN_INTERVAL_SEC = int(os.environ.get("EXPECT_RA_ACTIVE_INTERVAL_SEC") or 120)
IDLE_MIN_INTERVAL_SEC = int(os.environ.get("EXPECT_RA_IDLE_INTERVAL_SEC") or 1800)
STATE_FILE = Path(
    os.environ.get("EXPECT_RA_CADENCE_STATE")
    or str(Path("/opt/expect-ai/shared/ra-cadence-v71.json"))
)

# Optional injectable catalog loader (tests / runner).
_catalog_loader: CatalogLoader | None = None


def set_catalog_loader(loader: CatalogLoader | None) -> None:
    global _catalog_loader
    _catalog_loader = loader


def _default_catalog_loader(race_date: str) -> list[dict[str, Any]]:
    from .netkeiba_results import fetch_pi_race_catalog

    return fetch_pi_race_catalog(race_date)


def _now() -> datetime:
    return datetime.now(JST)


def _read_state() -> dict[str, Any]:
    try:
        if STATE_FILE.is_file():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _write_state(doc: dict[str, Any]) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(STATE_FILE)
    except OSError:
        pass


def count_unsettled_races(
    race_date: str,
    *,
    is_race_day: bool | None = None,
    catalog_races: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Settlement snapshot for cadence.

    LEGACY_PREDICTIONS_USED_FOR_COMPLETION = NO
    Uses catalog (+ final_predictions fallback), never predictions table.
    """
    app_db.migrate()
    conn = app_db.connect()
    try:
        loader = _catalog_loader or _default_catalog_loader
        settlement = build_day_settlement(
            conn,
            race_date,
            catalog_races=catalog_races,
            catalog_loader=None if catalog_races is not None else loader,
            is_race_day=is_race_day,
        )
        d = settlement.as_dict()
        d["authority"] = RESULT_TARGET_AUTHORITY
        d["LEGACY_PREDICTIONS_USED_FOR_COMPLETION"] = False
        return d
    finally:
        conn.close()


def is_day_result_complete(
    race_date: str,
    *,
    is_race_day: bool | None = None,
    catalog_races: list[dict[str, Any]] | None = None,
) -> bool:
    snap = count_unsettled_races(
        race_date, is_race_day=is_race_day, catalog_races=catalog_races
    )
    return bool(snap.get("day_complete"))


def has_terminal_success(race_date: str) -> bool:
    """True only when day result acquisition is complete (not mere COMPLETED/DEGRADED row)."""
    return is_day_result_complete(race_date)


def has_day_completed_run(race_date: str) -> bool:
    """DB run marked COMPLETED for date (optional signal; cadence prefers day_complete)."""
    conn = app_db.connect()
    try:
        row = conn.execute(
            """
            SELECT id FROM result_automation_runs
            WHERE race_date=? AND status=?
            ORDER BY id DESC LIMIT 1
            """,
            (race_date, sm.COMPLETED),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def archive_exists(race_date: str) -> bool:
    return (archive_root() / f"{race_date}.json").is_file()


def decide_today_run(race_date: str, *, is_race_day: bool) -> dict[str, Any]:
    """
    Returns { run: bool, reason, cadence, unsettled, ... }.
    meeting_complete requires day_complete + archive (not legacy predictions).
    """
    unsettled = count_unsettled_races(race_date, is_race_day=is_race_day)
    state = _read_state()
    last_iso = (state.get("last_run") or {}).get(race_date)
    last_dt = None
    if last_iso:
        try:
            last_dt = datetime.fromisoformat(str(last_iso))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=JST)
        except ValueError:
            last_dt = None
    elapsed = None
    if last_dt is not None:
        elapsed = (_now() - last_dt.astimezone(JST)).total_seconds()

    day_complete = bool(unsettled.get("day_complete"))
    meeting_done = (
        day_complete
        and int(unsettled.get("EXPECTED_RACE_COUNT") or 0) > 0
        and archive_exists(race_date)
    )

    if not is_race_day and day_complete:
        return {
            "run": False,
            "reason": "not_race_day_and_settled",
            "cadence": "stop",
            "unsettled": unsettled,
            "elapsed_sec": elapsed,
        }

    if not is_race_day and int(unsettled.get("EXPECTED_RACE_COUNT") or 0) == 0:
        return {
            "run": False,
            "reason": "no_race_day",
            "cadence": "stop",
            "unsettled": unsettled,
            "elapsed_sec": elapsed,
        }

    if meeting_done:
        if elapsed is not None and elapsed < IDLE_MIN_INTERVAL_SEC:
            return {
                "run": False,
                "reason": "idle_interval_not_elapsed",
                "cadence": "idle_30m",
                "unsettled": unsettled,
                "elapsed_sec": elapsed,
                "min_interval_sec": IDLE_MIN_INTERVAL_SEC,
            }
        return {
            "run": False,
            "reason": "meeting_complete_archived",
            "cadence": "stop",
            "unsettled": unsettled,
            "elapsed_sec": elapsed,
        }

    # Incomplete day: never treat as meeting_complete even if old archive exists
    if elapsed is not None and elapsed < ACTIVE_MIN_INTERVAL_SEC - 15:
        return {
            "run": False,
            "reason": "active_interval_not_elapsed",
            "cadence": "active_5m",
            "unsettled": unsettled,
            "elapsed_sec": elapsed,
            "min_interval_sec": ACTIVE_MIN_INTERVAL_SEC,
        }

    return {
        "run": True,
        "reason": "unsettled_or_in_progress",
        "cadence": "active_5m",
        "unsettled": unsettled,
        "elapsed_sec": elapsed,
        "min_interval_sec": ACTIVE_MIN_INTERVAL_SEC,
    }


def mark_ran(race_date: str, meta: dict[str, Any] | None = None) -> None:
    state = _read_state()
    last = state.get("last_run") if isinstance(state.get("last_run"), dict) else {}
    last[race_date] = _now().isoformat()
    state["last_run"] = last
    if meta:
        state["last_meta"] = meta
    state["updated_at"] = _now().isoformat()
    _write_state(state)


def collect_v71_ops_metrics(race_date: str | None = None) -> dict[str, Any]:
    """Ops Dashboard metrics — settlement uses catalog authority."""
    app_db.migrate()
    day = race_date or _now().date().isoformat()
    unsettled = count_unsettled_races(day, is_race_day=True)
    conn = app_db.connect()
    try:
        active = conn.execute(
            f"""
            SELECT COUNT(*) AS n FROM result_automation_runs
            WHERE status IN ({",".join("?" * len(sm.ACTIVE))})
            """,
            tuple(sm.ACTIVE),
        ).fetchone()
        archive_q = 0
        if (
            int(unsettled.get("SETTLED_RACE_COUNT") or 0) > 0
            and unsettled.get("day_complete")
            and not archive_exists(day)
        ):
            archive_q = 1
        archive_count = 0
        try:
            root = archive_root()
            if root.is_dir():
                archive_count = len(list(root.glob("*.json")))
        except OSError:
            archive_count = 0
        return {
            "schema_version": "expect-v73-ops-metrics/1.1-ra-repair",
            "race_date": day,
            "result_automation_pending": int((active["n"] if active else 0) or 0),
            "race_results_waiting": unsettled.get("PENDING_RACE_COUNT"),
            "result_automation_queue": int((active["n"] if active else 0) or 0),
            "archive_queue": archive_q,
            "archive_count": archive_count,
            "unsettled": unsettled,
            "cadence": decide_today_run(day, is_race_day=True),
            "RESULT_TARGET_AUTHORITY": RESULT_TARGET_AUTHORITY,
        }
    finally:
        conn.close()
