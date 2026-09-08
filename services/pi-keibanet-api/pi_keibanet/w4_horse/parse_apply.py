# -*- coding: utf-8 -*-
"""Apply D1/D2 parsers to HTML on disk and update W4 queue (W4-B)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import W4Config
from .d1_parse import PARSER_VERSION as D1_VER
from .d1_parse import SOURCE_NAME as D1_SRC
from .d1_parse import decode_html_bytes, parse_d1_profile
from .d2_parse import PARSER_VERSION as D2_VER
from .d2_parse import SOURCE_NAME as D2_SRC
from .d2_parse import parse_d2_pedigree
from .id_format import find_d1_html, find_d2_html
from .raw_store import attach_provenance, upsert_raw


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except OSError:
        return None


def apply_d1_html(
    cfg: W4Config,
    *,
    horse_id: str,
    queue_row: dict[str, Any],
    html_path: Path,
    html: str | None = None,
) -> dict[str, Any]:
    if html is None:
        html = decode_html_bytes(html_path.read_bytes())
    parsed = parse_d1_profile(html, expected_horse_id=horse_id)
    status = "complete" if parsed.get("parse_ok") else "parse_failed"
    # partial if some fields missing but ok
    if parsed.get("parse_ok") and not parsed.get("profile_current_trainer_id"):
        status = "partial"
    row = attach_provenance(
        {k: v for k, v in parsed.items() if k not in ("reasons",)},
        source=D1_SRC,
        page_type="PAGE_D1",
        raw_html_reference=str(html_path),
        retrieved_at=_mtime_iso(html_path),
        parser_version=D1_VER,
        temporal_class="CURRENT_STATE_FOR_TRAINER_OWNER_AFFILIATION_STATIC_FOR_BIRTH_BREEDER",
    )
    row["parse_status"] = status
    row["parse_reasons"] = list(parsed.get("reasons") or [])
    if status in ("complete", "partial"):
        upsert_raw(cfg.profile_raw_path, row)
    queue_row["d1_status"] = status if status != "complete" else "complete"
    if status == "partial":
        queue_row["d1_status"] = "partial"
    if status == "parse_failed":
        queue_row["d1_status"] = "parse_failed"
    queue_row["d1_cache_path"] = str(html_path)
    queue_row["updated_at"] = _utc_iso()
    return {"status": queue_row["d1_status"], "parsed": parsed, "row": row}


def apply_d2_html(
    cfg: W4Config,
    *,
    horse_id: str,
    queue_row: dict[str, Any],
    html_path: Path,
    html: str | None = None,
) -> dict[str, Any]:
    if html is None:
        html = decode_html_bytes(html_path.read_bytes())
    parsed = parse_d2_pedigree(html, expected_horse_id=horse_id)
    if parsed.get("parse_ok") and parsed.get("broodmare_sire_id"):
        status = "complete"
    elif parsed.get("parse_ok"):
        status = "partial"
    else:
        status = "parse_failed"
    row = attach_provenance(
        {k: v for k, v in parsed.items() if k not in ("reasons",)},
        source=D2_SRC,
        page_type="PAGE_D2",
        raw_html_reference=str(html_path),
        retrieved_at=_mtime_iso(html_path),
        parser_version=D2_VER,
        temporal_class="STATIC_NEAR_STATIC",
    )
    row["parse_status"] = status
    row["parse_reasons"] = list(parsed.get("reasons") or [])
    if status in ("complete", "partial"):
        upsert_raw(cfg.pedigree_raw_path, row)
    queue_row["d2_status"] = status
    queue_row["d2_cache_path"] = str(html_path)
    queue_row["updated_at"] = _utc_iso()
    return {"status": status, "parsed": parsed, "row": row}


def refresh_canonical_status(queue_row: dict[str, Any]) -> None:
    d1 = str(queue_row.get("d1_status") or "pending")
    d2 = str(queue_row.get("d2_status") or "pending")
    if d1 == "complete" and d2 == "complete":
        queue_row["canonical_status"] = "complete"
    elif d1 in ("complete", "partial", "cache_available") or d2 in (
        "complete",
        "partial",
        "cache_available",
    ):
        if d1 == "parse_failed" and d2 == "parse_failed":
            queue_row["canonical_status"] = "parse_failed"
        elif d1 == "blocked" or d2 == "blocked":
            queue_row["canonical_status"] = "blocked"
        else:
            queue_row["canonical_status"] = "partial" if (
                d1 in ("complete", "partial") or d2 in ("complete", "partial")
            ) else "cache_available"
    elif d1 == "blocked" or d2 == "blocked":
        queue_row["canonical_status"] = "blocked"
    else:
        queue_row["canonical_status"] = "pending"


def try_parse_from_cache(cfg: W4Config, horse_id: str, queue_row: dict[str, Any]) -> dict[str, Any]:
    """W4-B: parse existing caches only (HTTP 0)."""
    result = {"d1": None, "d2": None}
    d1p = find_d1_html(horse_id, cfg.d1_cache_roots)
    if d1p is None and queue_row.get("d1_cache_path"):
        p = Path(str(queue_row["d1_cache_path"]))
        if p.is_file():
            d1p = p
    d2p = find_d2_html(horse_id, cfg.d2_cache_roots)
    if d2p is None and queue_row.get("d2_cache_path"):
        p = Path(str(queue_row["d2_cache_path"]))
        if p.is_file():
            d2p = p
    if d1p:
        result["d1"] = apply_d1_html(cfg, horse_id=horse_id, queue_row=queue_row, html_path=d1p)
    if d2p:
        result["d2"] = apply_d2_html(cfg, horse_id=horse_id, queue_row=queue_row, html_path=d2p)
    refresh_canonical_status(queue_row)
    return result
