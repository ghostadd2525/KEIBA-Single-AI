# -*- coding: utf-8 -*-
"""
Result-day contract (Result Automation repair).

Authority for expected races = official day catalog (PI), not legacy predictions.
Prediction presence is NOT required for result acquisition.
Evaluation remains Prediction ∩ Result (handled elsewhere).
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

# Failure / terminal classes (retry policy)
CATALOG_NOT_DUE = "CATALOG_NOT_DUE"
SOURCE_PENDING = "SOURCE_PENDING"
TRANSIENT_HTTP = "TRANSIENT_HTTP"
PARSE_ERROR = "PARSE_ERROR"
IDENTITY_ERROR = "IDENTITY_ERROR"
PERMANENT_CONFIG_ERROR = "PERMANENT_CONFIG_ERROR"
NO_RACE_DAY = "NO_RACE_DAY"
NO_CATALOG_EXPECTED = "NO_CATALOG_EXPECTED"
CATALOG_EMPTY_ON_RACE_DAY = "CATALOG_EMPTY_ON_RACE_DAY"
RETRY_EXHAUSTED = "RETRY_EXHAUSTED"

NON_RETRIABLE = frozenset(
    {
        NO_RACE_DAY,
        NO_CATALOG_EXPECTED,
        PERMANENT_CONFIG_ERROR,
        IDENTITY_ERROR,
        RETRY_EXHAUSTED,
    }
)

TERMINAL_NO_RESULT_STATUSES = frozenset(
    {
        "cancelled",
        "canceled",
        "abandoned",
        "scrapped",
        "中止",
        "取消",
        "不成立",
    }
)

VALID_EXPECTED_STATUSES = frozenset(
    {
        "",
        "published",
        "scheduled",
        "open",
        "closed",
        "finished",
        "final",
        "result",
        "confirmed",
        "official",
    }
)

RESULT_TARGET_AUTHORITY = "official_day_catalog"
RESULT_EXPECTED_RACE_SOURCE = "PI_/v1/races?date= (published/valid); fallback readiness/final_predictions only if catalog unavailable"


@dataclass
class ExpectedRace:
    race_id: str
    numeric_race_id: str | None = None
    venue: str | None = None
    post_time: str | None = None
    status: str | None = None
    terminal_no_result: bool = False


@dataclass
class DaySettlement:
    race_date: str
    expected_race_ids: list[str]
    settled_race_ids: list[str]
    pending_race_ids: list[str]
    terminal_no_result_ids: list[str]
    EXPECTED_RACE_COUNT: int
    SETTLED_RACE_COUNT: int
    PENDING_RACE_COUNT: int
    TERMINAL_NO_RESULT_COUNT: int
    day_complete: bool
    authority: str = RESULT_TARGET_AUTHORITY
    source: str = "catalog"
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "race_date": self.race_date,
            "EXPECTED_RACE_COUNT": self.EXPECTED_RACE_COUNT,
            "SETTLED_RACE_COUNT": self.SETTLED_RACE_COUNT,
            "PENDING_RACE_COUNT": self.PENDING_RACE_COUNT,
            "TERMINAL_NO_RESULT_COUNT": self.TERMINAL_NO_RESULT_COUNT,
            "expected_race_ids": self.expected_race_ids,
            "settled_race_ids": self.settled_race_ids,
            "pending_race_ids": self.pending_race_ids,
            "terminal_no_result_ids": self.terminal_no_result_ids,
            "day_complete": self.day_complete,
            "authority": self.authority,
            "source": self.source,
            "notes": self.notes,
            # backward-compatible keys used by cadence UI
            "predictions": self.EXPECTED_RACE_COUNT,  # NOT legacy predictions table
            "results": self.SETTLED_RACE_COUNT,
            "unsettled": self.PENDING_RACE_COUNT,
            "unsettled_race_ids": self.pending_race_ids[:50],
        }


def _norm_status(raw: Any) -> str:
    return str(raw or "").strip().lower()


def expected_races_from_catalog(catalog_races: Iterable[dict[str, Any]]) -> list[ExpectedRace]:
    """Build expected set from official catalog rows (PI shape)."""
    out: list[ExpectedRace] = []
    seen: set[str] = set()
    for race in catalog_races or []:
        if not isinstance(race, dict):
            continue
        rid = str(race.get("race_id") or "").strip()
        if not rid or rid in seen:
            continue
        st = _norm_status(race.get("status") or race.get("race_status"))
        # Japanese status may be in race_status_label
        label = str(race.get("race_status_label") or race.get("status_label") or "").strip()
        terminal = st in TERMINAL_NO_RESULT_STATUSES or label in TERMINAL_NO_RESULT_STATUSES
        if st and st not in VALID_EXPECTED_STATUSES and not terminal:
            # unknown status: still include (fail-open for acquisition) unless clearly invalid
            if st in {"draft", "hidden", "test"}:
                continue
        seen.add(rid)
        out.append(
            ExpectedRace(
                race_id=rid,
                numeric_race_id=(
                    str(race.get("numeric_race_id") or "").strip() or None
                ),
                venue=(race.get("venue") or race.get("course") or None),
                post_time=(
                    str(race.get("post_time") or "").strip() or None
                ),
                status=st or None,
                terminal_no_result=terminal,
            )
        )
    return out


def fallback_expected_from_final_predictions(
    conn: Any, race_date: str
) -> list[ExpectedRace]:
    """Fallback when catalog unavailable: final_predictions race_ids only."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(final_predictions)").fetchall()]
    rid_col = "race_id" if "race_id" in cols else (
        "source_race_id" if "source_race_id" in cols else None
    )
    if not rid_col:
        return []
    rows = conn.execute(
        f"""
        SELECT DISTINCT [{rid_col}] AS race_id FROM final_predictions
        WHERE [{rid_col}] LIKE ? OR substr([{rid_col}],1,10)=?
        ORDER BY 1
        """,
        (race_date + "%", race_date),
    ).fetchall()
    out: list[ExpectedRace] = []
    for r in rows:
        rid = str(r["race_id"] if hasattr(r, "keys") else r[0])
        if rid:
            out.append(ExpectedRace(race_id=rid))
    return out


def settled_race_ids(conn: Any, race_date: str) -> set[str]:
    rows = conn.execute(
        "SELECT DISTINCT race_id FROM race_results WHERE race_date=?",
        (race_date,),
    ).fetchall()
    return {
        str(r["race_id"] if hasattr(r, "keys") else r[0])
        for r in rows
        if (r["race_id"] if hasattr(r, "keys") else r[0])
    }


def compute_settlement(
    race_date: str,
    expected: list[ExpectedRace],
    settled: set[str],
    *,
    source: str = "catalog",
    notes: list[str] | None = None,
) -> DaySettlement:
    expected_ids = [e.race_id for e in expected if not e.terminal_no_result]
    terminal_ids = [e.race_id for e in expected if e.terminal_no_result]
    expected_set = set(expected_ids)
    settled_in = sorted(expected_set & settled)
    pending = sorted(expected_set - settled)
    # terminal_no_result never pending
    day_complete = len(expected_ids) > 0 and len(pending) == 0
    # empty expected → not complete (avoid premature archive on empty)
    if len(expected_ids) == 0:
        day_complete = False
    return DaySettlement(
        race_date=race_date,
        expected_race_ids=expected_ids,
        settled_race_ids=settled_in,
        pending_race_ids=pending,
        terminal_no_result_ids=terminal_ids,
        EXPECTED_RACE_COUNT=len(expected_ids),
        SETTLED_RACE_COUNT=len(settled_in),
        PENDING_RACE_COUNT=len(pending),
        TERMINAL_NO_RESULT_COUNT=len(terminal_ids),
        day_complete=day_complete,
        source=source,
        notes=list(notes or []),
    )


def classify_empty_catalog(*, is_race_day: bool) -> str:
    if not is_race_day:
        return NO_RACE_DAY
    return CATALOG_EMPTY_ON_RACE_DAY


def default_max_attempts() -> int:
    try:
        return max(1, int(os.environ.get("EXPECT_RA_MAX_ATTEMPTS") or "5"))
    except ValueError:
        return 5


def parse_failure_class(error_json: Any, meta_json: Any = None) -> str | None:
    for blob in (meta_json, error_json):
        if not blob:
            continue
        try:
            doc = json.loads(blob) if isinstance(blob, str) else blob
        except (TypeError, json.JSONDecodeError):
            doc = {}
        if isinstance(doc, dict):
            fc = doc.get("failure_class") or doc.get("class")
            if fc:
                return str(fc)
            err = str(doc.get("error") or "")
            if "PI catalog empty" in err or "catalog empty" in err.lower():
                return CATALOG_EMPTY_ON_RACE_DAY
    return None


def retry_eligible(
    *,
    attempt: int,
    max_attempts: int,
    failure_class: str | None,
    status: str | None,
) -> tuple[bool, str]:
    """Return (eligible, reason)."""
    if status and status.upper() in {"COMPLETED"}:
        return False, "already_completed"
    if failure_class in NON_RETRIABLE:
        return False, f"non_retriable:{failure_class}"
    if attempt >= max_attempts:
        return False, RETRY_EXHAUSTED
    return True, "ok"


def should_skip_pre_post_time(
    post_time: str | None,
    *,
    now: datetime | None = None,
    race_date: str | None = None,
) -> bool:
    """
    Skip external fetch if current time is still before post_time.
    No invented grace — only strict now < post_time (existing env grace unused/absent).
    """
    if not post_time:
        return False
    now = now or datetime.now(JST)
    raw = post_time.strip()
    # accept HH:MM or HH:MM:SS
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            t = datetime.strptime(raw, fmt).time()
            break
        except ValueError:
            t = None
    if t is None:
        return False
    day = now.date()
    if race_date:
        try:
            day = datetime.strptime(race_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    post_dt = datetime.combine(day, t, tzinfo=JST)
    return now.astimezone(JST) < post_dt


CatalogLoader = Callable[[str], list[dict[str, Any]]]


def build_day_settlement(
    conn: Any,
    race_date: str,
    *,
    catalog_races: list[dict[str, Any]] | None = None,
    catalog_loader: CatalogLoader | None = None,
    is_race_day: bool | None = None,
) -> DaySettlement:
    """
    Preferred: catalog_races or catalog_loader(PI).
    Fallback: final_predictions (NOT legacy predictions).
    """
    notes: list[str] = []
    source = "catalog"
    races = catalog_races
    if races is None and catalog_loader is not None:
        try:
            races = catalog_loader(race_date)
        except Exception as exc:
            notes.append(f"catalog_loader_error:{exc}")
            races = []
    if races is None:
        races = []

    expected = expected_races_from_catalog(races)
    if not expected:
        # fallback to final_predictions
        try:
            expected = fallback_expected_from_final_predictions(conn, race_date)
            if expected:
                source = "final_predictions_fallback"
                notes.append("catalog_empty_used_final_predictions_fallback")
        except Exception as exc:
            notes.append(f"final_predictions_fallback_error:{exc}")

    if not expected and is_race_day is False:
        notes.append(NO_RACE_DAY)
    elif not expected and is_race_day is True:
        notes.append(CATALOG_EMPTY_ON_RACE_DAY)

    settled = settled_race_ids(conn, race_date)
    return compute_settlement(
        race_date, expected, settled, source=source, notes=notes
    )


def filter_pending_for_fetch(
    expected: list[ExpectedRace],
    pending_ids: set[str],
    *,
    now: datetime | None = None,
    race_date: str | None = None,
) -> list[ExpectedRace]:
    """Pending races only; skip pre-post_time."""
    out: list[ExpectedRace] = []
    for e in expected:
        if e.terminal_no_result:
            continue
        if e.race_id not in pending_ids:
            continue
        if should_skip_pre_post_time(e.post_time, now=now, race_date=race_date):
            continue
        out.append(e)
    return out


def connect_ro(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con
