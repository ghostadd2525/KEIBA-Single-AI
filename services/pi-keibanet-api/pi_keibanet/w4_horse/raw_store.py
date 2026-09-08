# -*- coding: utf-8 -*-
"""W4 Research RAW store: horse_profile_raw / horse_pedigree_raw."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_by_key(path: Path, key: str = "horse_id") -> dict[str, dict[str, Any]]:
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


def save_by_key(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(rows[k], ensure_ascii=False, separators=(",", ":"))
        for k in sorted(rows.keys())
    ]
    text = "\n".join(lines) + ("\n" if lines else "")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def upsert_raw(
    path: Path,
    row: dict[str, Any],
    *,
    key: str = "horse_id",
) -> None:
    rows = load_by_key(path, key)
    k = str(row.get(key) or "")
    if not k:
        return
    prev = rows.get(k)
    now = _utc_iso()
    if prev and prev.get("created_at"):
        row = dict(row)
        row["created_at"] = prev["created_at"]
    else:
        row = dict(row)
        row.setdefault("created_at", now)
    row["updated_at"] = now
    rows[k] = row
    save_by_key(path, rows)


def attach_provenance(
    row: dict[str, Any],
    *,
    source: str,
    page_type: str,
    raw_html_reference: str,
    retrieved_at: str | None,
    parser_version: str,
    temporal_class: str,
) -> dict[str, Any]:
    out = dict(row)
    now = _utc_iso()
    out["provenance"] = {
        "source": source,
        "page_type": page_type,
        "raw_html_reference": raw_html_reference,
        "retrieved_at": retrieved_at,
        "parser_version": parser_version,
        "parsed_at": now,
        "temporal_class": temporal_class,
    }
    out["source"] = source
    out["page_type"] = page_type
    out["raw_html_reference"] = raw_html_reference
    out["retrieved_at"] = retrieved_at
    out["parser_version"] = parser_version
    out["temporal_class"] = temporal_class
    out["parsed_at"] = now
    return out
