# -*- coding: utf-8 -*-
"""Apply W3-B PAGE-C result parser to one race (shared by W3-B / W3-C)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import W3AConfig
from .result_parse import PARSER_VERSION, SOURCE_NAME, parse_page_c_result
from .result_store import attach_provenance, upsert_race_raw, upsert_runners_for_race


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _file_mtime_iso(path: Path) -> str | None:
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return None


def apply_html_result_parse(
    cfg: W3AConfig,
    *,
    race_id: str,
    queue_row: dict[str, Any],
    html_path: Path,
    html: str | None = None,
) -> dict[str, Any]:
    """Parse PAGE-C HTML with W3-B parser; persist Research RAW; mutate queue_row.

    Returns dict with queue_status, runner_count, horse_id_missing, runners, race, reasons.
    """
    if html is None:
        html = html_path.read_text(encoding="utf-8", errors="replace")

    parsed = parse_page_c_result(html, expected_race_id=race_id)
    status = str(parsed["queue_status"])
    race = dict(parsed["race"])
    if not race.get("race_date") and queue_row.get("kaisai_date"):
        race["race_date"] = queue_row.get("kaisai_date")
    if not race.get("venue") and queue_row.get("venue"):
        race["venue"] = queue_row.get("venue")
    if race.get("race_number") is None and queue_row.get("race_number") is not None:
        race["race_number"] = queue_row.get("race_number")
    if not race.get("race_name") and queue_row.get("race_name"):
        race["race_name"] = queue_row.get("race_name")

    retrieved_at = _file_mtime_iso(html_path)
    race_row = attach_provenance(
        race,
        source=SOURCE_NAME,
        source_race_id=race_id,
        raw_html_reference=str(html_path),
        retrieved_at=retrieved_at,
        parser_version=PARSER_VERSION,
    )
    race_row["parse_status"] = status
    race_row["parse_reasons"] = list(parsed.get("reasons") or [])

    runner_rows: list[dict[str, Any]] = []
    for rr in parsed["runners"]:
        runner_rows.append(
            attach_provenance(
                dict(rr),
                source=SOURCE_NAME,
                source_race_id=race_id,
                raw_html_reference=str(html_path),
                retrieved_at=retrieved_at,
                parser_version=PARSER_VERSION,
            )
        )

    if status in ("result_complete", "partial"):
        cfg.raw_dir.mkdir(parents=True, exist_ok=True)
        upsert_race_raw(cfg.race_raw_path, race_row)
        upsert_runners_for_race(cfg.runner_raw_path, race_id, runner_rows)

    now = _utc_iso()
    queue_row["queue_status"] = status
    queue_row["cache_html_path"] = str(html_path)
    queue_row["raw_html_reference"] = str(html_path)
    queue_row["parser_version"] = PARSER_VERSION
    queue_row["parsed_at"] = now
    queue_row["parse_status"] = status
    queue_row["parse_reasons"] = list(parsed.get("reasons") or [])
    queue_row["runner_count"] = len(runner_rows)
    queue_row["horse_id_missing_count"] = int(parsed.get("horse_id_missing") or 0)
    queue_row["needs_result"] = status != "result_complete"
    queue_row["updated_at"] = now

    return {
        "queue_status": status,
        "runner_count": len(runner_rows),
        "horse_id_missing": int(parsed.get("horse_id_missing") or 0),
        "runners": runner_rows,
        "race": race_row,
        "reasons": list(parsed.get("reasons") or []),
        "parse_ok": status in ("result_complete", "partial"),
    }
