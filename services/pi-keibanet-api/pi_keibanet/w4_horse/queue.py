# -*- coding: utf-8 -*-
"""W4 canonical horse queue (PK=horse_id). HTTP 0."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..page_a1_store import atomic_write_json

SUB_STATUSES = frozenset(
    {
        "pending",
        "cache_available",
        "complete",
        "partial",
        "blocked",
        "fetch_failed",
        "parse_failed",
    }
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_row(
    *,
    horse_id: str,
    horse_id_raw: str,
    horse_id_format: str,
    first_seen_race_id: str,
    first_seen_at: str,
    d1_status: str = "pending",
    d2_status: str = "pending",
    canonical_status: str = "pending",
    d1_cache_path: str | None = None,
    d2_cache_path: str | None = None,
) -> dict[str, Any]:
    now = _utc_iso()
    return {
        "horse_id": horse_id,
        "horse_id_raw": horse_id_raw,
        "horse_id_format": horse_id_format,
        "first_seen_race_id": first_seen_race_id,
        "first_seen_at": first_seen_at,
        "last_seen_race_id": first_seen_race_id,
        "last_seen_at": first_seen_at,
        "source_race_count": 1,
        "d1_status": d1_status,
        "d2_status": d2_status,
        "canonical_status": canonical_status,
        "d1_cache_path": d1_cache_path,
        "d2_cache_path": d2_cache_path,
        "created_at": now,
        "updated_at": now,
    }


def load_queue(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        hid = str(o.get("horse_id") or "")
        if hid:
            rows[hid] = o
    return rows


def save_queue(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(rows[k], ensure_ascii=False, separators=(",", ":"))
        for k in sorted(rows.keys())
    ]
    text = "\n".join(lines) + ("\n" if lines else "")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def load_provenance(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        hid = str(o.get("horse_id") or "")
        rid = str(o.get("race_id") or "")
        if hid and rid:
            out[(hid, rid)] = o
    return out


def save_provenance(path: Path, rows: dict[tuple[str, str], dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = [rows[k] for k in sorted(rows.keys(), key=lambda x: (x[0], x[1]))]
    lines = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in ordered]
    text = "\n".join(lines) + ("\n" if lines else "")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def _status_rank(status: str) -> int:
    order = {
        "pending": 0,
        "cache_available": 1,
        "partial": 2,
        "complete": 3,
        "fetch_failed": 1,
        "parse_failed": 1,
        "blocked": 2,
    }
    return order.get(status, 0)


def merge_seen(
    existing: dict[str, Any],
    *,
    race_id: str,
    seen_at: str,
    d1_status: str | None = None,
    d2_status: str | None = None,
    d1_cache_path: str | None = None,
    d2_cache_path: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Update last_seen / counts; never demote first_seen; never demote D1/D2 statuses."""
    out = dict(existing)
    # race set via provenance drives source_race_count; bump if new race
    prev_last = str(out.get("last_seen_race_id") or "")
    # Always refresh last_seen to latest scan ordering handled by caller timestamps
    out["last_seen_race_id"] = race_id
    out["last_seen_at"] = seen_at
    if not out.get("first_seen_race_id"):
        out["first_seen_race_id"] = race_id
        out["first_seen_at"] = seen_at
    # source_race_count recalculated by caller from provenance preferred;
    # here only ensure at least 1
    if int(out.get("source_race_count") or 0) < 1:
        out["source_race_count"] = 1

    for key, new_st, path_key, path_val in (
        ("d1_status", d1_status, "d1_cache_path", d1_cache_path),
        ("d2_status", d2_status, "d2_cache_path", d2_cache_path),
    ):
        if new_st:
            old = str(out.get(key) or "pending")
            if _status_rank(new_st) >= _status_rank(old):
                # allow pending → cache_available; never demote complete→pending
                if old in ("complete", "blocked") and new_st == "pending":
                    pass
                elif old == "cache_available" and new_st == "pending":
                    pass
                else:
                    out[key] = new_st
            if path_val and out.get(key) == "cache_available":
                out[path_key] = path_val

    # canonical_status: pending until both complete (future); for W4-A reflect cache
    d1 = str(out.get("d1_status") or "pending")
    d2 = str(out.get("d2_status") or "pending")
    if d1 == "cache_available" or d2 == "cache_available":
        if out.get("canonical_status") == "pending":
            out["canonical_status"] = "cache_available"
    out["updated_at"] = _utc_iso()
    action = "refreshed" if prev_last else "refreshed"
    return out, action


def queue_stats(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    from collections import Counter

    return {
        "canonical": dict(Counter(str(r.get("canonical_status") or "pending") for r in rows.values())),
        "d1": dict(Counter(str(r.get("d1_status") or "pending") for r in rows.values())),
        "d2": dict(Counter(str(r.get("d2_status") or "pending") for r in rows.values())),
        "format": dict(Counter(str(r.get("horse_id_format") or "") for r in rows.values())),
    }


def write_run_report(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload)
