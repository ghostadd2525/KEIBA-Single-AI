# -*- coding: utf-8 -*-
"""W5 canonical horse-history queue (PK=horse_id)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..page_a1_store import atomic_write_json

STATUSES = frozenset(
    {
        "pending",
        "cache_hit",
        "complete",
        "blocked",
        "fetch_failed",
        "parse_failed",
        "source_missing",
    }
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_row(
    *,
    horse_id: str,
    source: str,
    first_seen_race_id: str | None = None,
    target_race_ids: list[str] | None = None,
) -> dict[str, Any]:
    now = _utc_iso()
    return {
        "horse_id": horse_id,
        "queue_status": "pending",
        "source": source,
        "first_seen_race_id": first_seen_race_id,
        "target_race_ids": list(target_race_ids or ([first_seen_race_id] if first_seen_race_id else [])),
        "history_row_count": 0,
        "history_race_id_valid_count": 0,
        "attempt_count": 0,
        "last_attempt_at": None,
        "next_eligible_at": None,
        "error_code": None,
        "error_reason": None,
        "cache_path": None,
        "created_at": now,
        "updated_at": now,
    }


def load_queue(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
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


def queue_stats(rows: dict[str, dict[str, Any]]) -> dict[str, int]:
    from collections import Counter

    return dict(Counter(str(r.get("queue_status") or "pending") for r in rows.values()))


def write_run_report(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload)
