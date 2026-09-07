# -*- coding: utf-8 -*-
"""W3 maiden-result canonical queue (PK=race_id). HTTP 0."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..page_a1_store import atomic_write_json

# Terminal / protected statuses — never demote on re-handoff
PROTECTED = frozenset(
    {
        "cache_available",
        "result_complete",
        "partial",
        "blocked",
        "fetch_failed",
        "parse_failed",
    }
)

VALID_STATUSES = frozenset(
    {
        "pending",
        "cache_available",
        "result_complete",
        "partial",
        "blocked",
        "fetch_failed",
        "parse_failed",
    }
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_valid_race_id(rid: str | None) -> bool:
    return bool(rid) and isinstance(rid, str) and len(rid) == 12 and rid.isdigit()


def empty_row(
    *,
    race_id: str,
    kaisai_date: str,
    venue: str,
    race_number: int | None,
    race_name: str,
    c4_day_status: str,
    maiden_identification_basis: str,
    source: str,
    source_artifact_ref: str,
    queue_status: str,
    needs_result: bool = True,
    needs_haron: bool | None = None,
    cache_html_path: str | None = None,
) -> dict[str, Any]:
    now = _utc_iso()
    return {
        "race_id": race_id,
        "kaisai_date": kaisai_date,
        "venue": venue,
        "race_number": race_number,
        "race_name": race_name,
        "c4_day_status": c4_day_status,
        "maiden_identification_basis": maiden_identification_basis,
        "source": source,
        "source_artifact_ref": source_artifact_ref,
        "queue_status": queue_status,
        "needs_result": needs_result,
        "needs_maiden_result": True,
        "needs_haron": needs_haron,
        "cache_html_path": cache_html_path,
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
        rid = str(o.get("race_id") or "")
        if rid:
            rows[rid] = o
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


def merge_row(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """Idempotent merge. Never demote protected statuses. Returns (row, action)."""
    if existing is None:
        return incoming, "inserted"

    out = dict(existing)
    prev_status = str(existing.get("queue_status") or "pending")
    new_status = str(incoming.get("queue_status") or "pending")

    # Refresh provenance / listing fields (non-status)
    for key in (
        "kaisai_date",
        "venue",
        "race_number",
        "race_name",
        "c4_day_status",
        "maiden_identification_basis",
        "source",
        "source_artifact_ref",
    ):
        if incoming.get(key) is not None:
            out[key] = incoming[key]

    out["needs_maiden_result"] = True
    if incoming.get("needs_result") is not None:
        out["needs_result"] = incoming["needs_result"]
    # Do not overwrite needs_haron True→False; only set if newly known
    if incoming.get("needs_haron") is True:
        out["needs_haron"] = True
    elif out.get("needs_haron") is None and incoming.get("needs_haron") is not None:
        out["needs_haron"] = incoming["needs_haron"]

    # Status policy: never demote protected; pending→cache_available upgrade OK
    if prev_status in PROTECTED:
        # allow cache path refresh if still cache_available
        if prev_status == "cache_available" and incoming.get("cache_html_path"):
            out["cache_html_path"] = incoming["cache_html_path"]
        out["updated_at"] = _utc_iso()
        return out, "unchanged_protected"

    if prev_status == "pending" and new_status == "cache_available":
        out["queue_status"] = "cache_available"
        out["cache_html_path"] = incoming.get("cache_html_path")
        out["updated_at"] = _utc_iso()
        return out, "upgraded_cache"

    if prev_status == new_status:
        if new_status == "cache_available" and incoming.get("cache_html_path"):
            out["cache_html_path"] = incoming["cache_html_path"]
        out["updated_at"] = _utc_iso()
        return out, "refreshed"

    # Do not initialize away from pending to pending unnecessarily
    out["updated_at"] = _utc_iso()
    return out, "refreshed"


def queue_stats(rows: dict[str, dict[str, Any]]) -> dict[str, int]:
    from collections import Counter

    c = Counter(str(r.get("queue_status") or "pending") for r in rows.values())
    return dict(c)


def write_run_report(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload)
