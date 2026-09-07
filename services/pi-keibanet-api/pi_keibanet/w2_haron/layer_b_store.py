# -*- coding: utf-8 -*-
"""Layer-B canonical index store (seal-preserving)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import PARSER_VERSION, SOURCE_NAME

CANONICAL_STATUSES = frozenset(
    {
        "cache_hit",
        "fetched",
        "source_missing",
        "blocked",
        "fetch_failed",
        "parse_failed",
        "pending",
        "invalid",
    }
)

# Statuses that must never be silently reclassified from seal.
SEAL_PRESERVE = frozenset({"cache_hit", "source_missing", "blocked", "fetch_failed"})


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_valid_race_id(rid: str | None) -> bool:
    return bool(rid) and isinstance(rid, str) and len(rid) == 12 and rid.isdigit()


def empty_row(history_race_id: str, *, status: str = "pending") -> dict[str, Any]:
    now = _utc_iso()
    return {
        "history_race_id": history_race_id,
        "source": SOURCE_NAME,
        "canonical_status": status,
        "raw_html_path": None,
        "raw_haron_present": False,
        "parsed_haron_present": False,
        "retrieved_at": None,
        "last_attempt_at": None,
        "parser_version": None,
        "error_code": None,
        "error_reason": None,
        "attempt_count": 0,
        "next_eligible_at": None,
        "created_at": now,
        "updated_at": now,
        "refetch_prohibited": status in ("cache_hit", "source_missing"),
    }


def load_index(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            rid = str(o.get("history_race_id") or "")
            if rid:
                rows[rid] = o
    return rows


def save_index(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for rid in sorted(rows.keys()):
            f.write(json.dumps(rows[rid], ensure_ascii=False) + "\n")
    tmp.replace(path)


def bootstrap_from_seal(
    runtime_path: Path,
    seal_path: Path,
    *,
    force: bool = False,
) -> dict[str, dict[str, Any]]:
    """Import sealed index once. Never reclassify sealed statuses."""
    if runtime_path.exists() and not force:
        return load_index(runtime_path)
    if not seal_path.exists():
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        save_index(runtime_path, {})
        return {}
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(seal_path, runtime_path)
    return load_index(runtime_path)


def upsert_pending(rows: dict[str, dict[str, Any]], race_ids: Iterable[str]) -> list[str]:
    """Register new valid race ids as pending. Existing rows untouched."""
    added: list[str] = []
    for rid in race_ids:
        if not is_valid_race_id(rid):
            continue
        if rid in rows:
            continue
        rows[rid] = empty_row(rid, status="pending")
        added.append(rid)
    return added


def find_cache_html(race_id: str, cache_roots: list[Path]) -> Path | None:
    for root in cache_roots:
        if not root:
            continue
        p = Path(root) / f"{race_id}.html"
        if p.is_file():
            return p
    return None


def try_promote_cache_hit_from_disk(
    row: dict[str, Any],
    *,
    cache_roots: list[Path],
    parse_fn,
) -> bool:
    """If usable Haron already on disk and row is pending/fetch_failed, promote to cache_hit.

    Never demotes seal cache_hit. Never refetches.
    """
    status = row.get("canonical_status")
    if status == "cache_hit":
        return False
    if status in ("source_missing", "blocked"):
        return False
    if row.get("refetch_prohibited") and status in SEAL_PRESERVE:
        return False
    rid = row.get("history_race_id")
    if not is_valid_race_id(rid):
        return False
    path = find_cache_html(str(rid), cache_roots)
    if path is None:
        return False
    try:
        html = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    parsed = parse_fn(html)
    if not parsed.get("parse_ok"):
        return False
    now = _utc_iso()
    row["canonical_status"] = "cache_hit"
    row["raw_html_path"] = str(path)
    row["raw_haron_present"] = True
    row["parsed_haron_present"] = True
    row["parser_version"] = PARSER_VERSION
    row["refetch_prohibited"] = True
    row["error_code"] = None
    row["error_reason"] = None
    row["updated_at"] = now
    row["sectional_sequence"] = parsed.get("sectional") or parsed.get("cumulative")
    return True


def mark_row(
    row: dict[str, Any],
    *,
    status: str,
    error_code: str | None = None,
    error_reason: str | None = None,
    raw_html_path: str | None = None,
    raw_haron_present: bool | None = None,
    parsed_haron_present: bool | None = None,
    sectional_sequence: Any = None,
    next_eligible_at: str | None = None,
    bump_attempt: bool = False,
    retrieved: bool = False,
) -> None:
    now = _utc_iso()
    row["canonical_status"] = status
    row["updated_at"] = now
    row["last_attempt_at"] = now
    if bump_attempt:
        row["attempt_count"] = int(row.get("attempt_count") or 0) + 1
    if error_code is not None:
        row["error_code"] = error_code
    if error_reason is not None:
        row["error_reason"] = error_reason
    if raw_html_path is not None:
        row["raw_html_path"] = raw_html_path
    if raw_haron_present is not None:
        row["raw_haron_present"] = raw_haron_present
    if parsed_haron_present is not None:
        row["parsed_haron_present"] = parsed_haron_present
    if sectional_sequence is not None:
        row["sectional_sequence"] = sectional_sequence
    if next_eligible_at is not None:
        row["next_eligible_at"] = next_eligible_at
    if retrieved:
        row["retrieved_at"] = now
        row["parser_version"] = PARSER_VERSION
    if status in ("cache_hit", "source_missing"):
        row["refetch_prohibited"] = True
