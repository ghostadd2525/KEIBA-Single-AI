# -*- coding: utf-8 -*-
"""Persist research horse-history RAW (JSONL, PK=horse_id)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_by_horse(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        hid = str(o.get("horse_id") or "")
        if hid:
            out[hid] = o
    return out


def save_by_horse(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(rows[k], ensure_ascii=False, separators=(",", ":"))
        for k in sorted(rows.keys())
    ]
    text = "\n".join(lines) + ("\n" if lines else "")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def upsert_horse_history(
    path: Path,
    *,
    horse_id: str,
    history_rows: list[dict[str, Any]],
    source: str,
    cache_path: str | None,
    parser: str = "pi_keibanet.netkeiba.horse_history",
) -> dict[str, Any]:
    rows = load_by_horse(path)
    valid = sum(
        1
        for r in history_rows
        if str(r.get("history_race_id") or "").isdigit()
        and len(str(r.get("history_race_id"))) == 12
    )
    now = _utc_iso()
    prev = rows.get(horse_id) or {}
    row = {
        "horse_id": horse_id,
        "history_rows": history_rows,
        "history_row_count": len(history_rows),
        "history_race_id_valid_count": valid,
        "source": source,
        "parser": parser,
        "cache_path": cache_path,
        "created_at": prev.get("created_at") or now,
        "updated_at": now,
    }
    rows[horse_id] = row
    save_by_horse(path, rows)
    return row
