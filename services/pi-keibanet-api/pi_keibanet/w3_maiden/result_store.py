# -*- coding: utf-8 -*-
"""W3-B Research RAW store (race_raw / runner_result_raw). No Feature/Prediction."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl_by_key(path: Path, key: str) -> dict[str, dict[str, Any]]:
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
        k = str(o.get(key) or "")
        if k:
            rows[k] = o
    return rows


def load_runner_jsonl(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Key = (race_id, horse_id or horse_number fallback)."""
    rows: dict[tuple[str, str], dict[str, Any]] = {}
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
        hid = str(o.get("horse_id") or "")
        if not rid:
            continue
        if hid:
            rows[(rid, hid)] = o
        else:
            hn = str(o.get("horse_number") or o.get("row_index") or "")
            rows[(rid, f"missing:{hn}")] = o
    return rows


def save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows
    ]
    text = "\n".join(lines) + ("\n" if lines else "")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def upsert_race_raw(
    path: Path,
    race_row: dict[str, Any],
) -> None:
    rows = load_jsonl_by_key(path, "race_id")
    rid = str(race_row.get("race_id") or "")
    if not rid:
        return
    prev = rows.get(rid)
    if prev and prev.get("created_at"):
        race_row = dict(race_row)
        race_row["created_at"] = prev["created_at"]
    rows[rid] = race_row
    ordered = [rows[k] for k in sorted(rows.keys())]
    save_jsonl(path, ordered)


def upsert_runners_for_race(
    path: Path,
    race_id: str,
    runner_rows: list[dict[str, Any]],
) -> None:
    """Replace all runners for race_id; leave other races intact. Idempotent."""
    existing = load_runner_jsonl(path)
    kept = {k: v for k, v in existing.items() if k[0] != race_id}
    for i, rr in enumerate(runner_rows):
        row = dict(rr)
        hid = str(row.get("horse_id") or "")
        key = (race_id, hid) if hid else (race_id, f"missing:{row.get('horse_number') or i}")
        prev = existing.get(key)
        if prev and prev.get("created_at"):
            row["created_at"] = prev["created_at"]
        kept[key] = row
    # stable order: race_id, finish_position, horse_number
    def sort_key(item: tuple[tuple[str, str], dict[str, Any]]) -> tuple:
        (_rid, _), o = item
        fp = o.get("finish_position")
        hn = o.get("horse_number")
        return (
            _rid,
            fp if isinstance(fp, int) else 999,
            hn if isinstance(hn, int) else 999,
            o.get("horse_id") or "",
        )

    ordered = [v for _, v in sorted(kept.items(), key=sort_key)]
    save_jsonl(path, ordered)


def attach_provenance(
    row: dict[str, Any],
    *,
    source: str,
    source_race_id: str,
    raw_html_reference: str,
    retrieved_at: str | None,
    parser_version: str,
    parsed_at: str | None = None,
) -> dict[str, Any]:
    out = dict(row)
    now = parsed_at or _utc_iso()
    if "created_at" not in out:
        out["created_at"] = now
    out["updated_at"] = now
    out["provenance"] = {
        "source": source,
        "source_race_id": source_race_id,
        "raw_html_reference": raw_html_reference,
        "retrieved_at": retrieved_at,
        "parser_version": parser_version,
        "parsed_at": now,
    }
    # flat mirrors for easy grep
    out["source"] = source
    out["source_race_id"] = source_race_id
    out["raw_html_reference"] = raw_html_reference
    out["retrieved_at"] = retrieved_at
    out["parser_version"] = parser_version
    out["parsed_at"] = now
    return out
