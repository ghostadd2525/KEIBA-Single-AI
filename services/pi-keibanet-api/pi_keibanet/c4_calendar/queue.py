# -*- coding: utf-8 -*-
"""C4 calendar queue — one row per kaisai_date; Strategy C hybrid seed."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

from ..page_a1_store import atomic_write_json, load_index

# Queue states (lowercase per Owner spec)
TERMINAL_OK = frozenset({"race_day_complete", "non_race_day_confirmed"})
# partial_terminal / quarantined: unresolved research coverage; never re-fetch
NO_FETCH = frozenset(
    {
        "race_day_complete",
        "non_race_day_confirmed",
        "partial_terminal",
        "quarantined",
    }
)


def iter_calendar_dates(start: str, end: str) -> list[str]:
    a = date.fromisoformat(start)
    b = date.fromisoformat(end)
    out: list[str] = []
    cur = a
    while cur <= b:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def load_known_dates(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    known: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        d = o.get("kaisai_date") or o.get("date")
        if d:
            known.add(str(d)[:10])
    return known


def _row(
    kaisai_date: str,
    *,
    phase: int,
    state: str = "pending",
) -> dict[str, Any]:
    return {
        "kaisai_date": kaisai_date,
        "phase": phase,
        "state": state,
        "day_kind": "UNKNOWN",
        "attempt_count": 0,
        "last_attempt_at": None,
        "next_eligible_at": None,
        "raw_snapshot_ref": None,
        "error_metadata": None,
        "source_health_at_attempt": None,
    }


def classify_existing(
    state_root: Path,
    kaisai_date: str,
) -> str | None:
    """Return terminal/partial state from C1 index if present; else None."""
    idx = load_index(state_root, kaisai_date)
    if not idx:
        return None
    completeness = idx.get("completeness_state")
    day_kind = idx.get("day_kind") or "UNKNOWN"
    if completeness == "COMPLETE" and day_kind == "RACE_DAY":
        return "race_day_complete"
    if completeness == "COMPLETE" and day_kind == "NON_RACE_DAY":
        return "non_race_day_confirmed"
    # Legacy COMPLETE with race_count
    if completeness == "COMPLETE":
        n = int(idx.get("race_count") or 0)
        return "race_day_complete" if n >= 1 else "non_race_day_confirmed"
    if completeness == "PARTIAL":
        return "partial"
    return None


def seed_queue(
    *,
    universe_start: str,
    universe_as_of: str,
    known_dates: set[str],
    state_root: Path,
) -> dict[str, dict[str, Any]]:
    """Deterministic seed: 953 dates, exclude COMPLETE/VALID_EMPTY evidence."""
    rows: dict[str, dict[str, Any]] = {}
    for d in iter_calendar_dates(universe_start, universe_as_of):
        existing = classify_existing(state_root, d)
        phase = 1 if d in known_dates else 2
        if existing in TERMINAL_OK:
            rows[d] = _row(d, phase=phase, state=existing)
            idx = load_index(state_root, d) or {}
            rows[d]["day_kind"] = idx.get("day_kind") or (
                "RACE_DAY" if existing == "race_day_complete" else "NON_RACE_DAY"
            )
            continue
        if existing == "partial":
            rows[d] = _row(d, phase=phase, state="partial")
            continue
        rows[d] = _row(d, phase=phase, state="pending")
    return rows


def load_queue(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        d = str(o.get("kaisai_date") or "")
        if d:
            rows[d] = o
    return rows


def save_queue(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        for d in sorted(rows.keys()):
            f.write(json.dumps(rows[d], ensure_ascii=False) + "\n")
        f.flush()
    tmp.replace(path)


def merge_seed(existing: dict[str, dict[str, Any]], seeded: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Preserve runtime progress; never duplicate keys; do not demote terminal OK."""
    out = dict(seeded)
    for d, row in existing.items():
        if d not in out:
            out[d] = row
            continue
        prev = out[d]
        if row.get("state") in TERMINAL_OK:
            out[d] = row
            continue
        if prev.get("state") in TERMINAL_OK:
            continue
        # keep richer attempt metadata from existing
        merged = dict(prev)
        merged.update({k: v for k, v in row.items() if v is not None})
        # prefer higher attempt_count
        merged["attempt_count"] = max(
            int(prev.get("attempt_count") or 0),
            int(row.get("attempt_count") or 0),
        )
        if row.get("state") not in (None, "pending") or prev.get("state") == "pending":
            if row.get("state") in (
                "blocked",
                "fetch_failed",
                "malformed",
                "partial",
                "pending",
            ):
                # keep existing non-pending progress unless seeded terminal
                if prev.get("state") != "pending":
                    merged["state"] = prev["state"]
        out[d] = merged
    return out


def select_work(
    rows: dict[str, dict[str, Any]],
    *,
    max_dates: int,
    now_iso_eligible,
    max_attempts: int | None = None,
) -> list[dict[str, Any]]:
    """Phase1 then Phase2; pending/partial/fetch_failed/blocked(eligible) only."""
    from .target_policy import should_fetch_target

    candidates: list[dict[str, Any]] = []
    for phase in (1, 2):
        for d in sorted(k for k, r in rows.items() if int(r.get("phase") or 2) == phase):
            r = rows[d]
            st = r.get("state")
            if st in NO_FETCH:
                continue
            if st not in ("pending", "partial", "fetch_failed", "blocked", "malformed"):
                continue
            if max_attempts is not None and not should_fetch_target(r, max_attempts=max_attempts):
                continue
            if not now_iso_eligible(r):
                continue
            candidates.append(r)
            if len(candidates) >= max_dates:
                return candidates
    return candidates


def queue_stats(rows: dict[str, dict[str, Any]]) -> dict[str, int]:
    from collections import Counter

    c = Counter(str(r.get("state") or "unknown") for r in rows.values())
    return dict(c)
