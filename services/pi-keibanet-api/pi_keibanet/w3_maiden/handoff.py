# -*- coding: utf-8 -*-
"""W3-A handoff: C4 RACE_DAY_COMPLETE → maiden canonical queue (HTTP 0)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..page_a1_store import load_index, listed_path
from .cache_probe import find_page_c_html
from .config import IDENTIFICATION_BASIS, MAIDEN_TOKEN, SOURCE_LABEL, W3AConfig
from .queue import (
    empty_row,
    is_valid_race_id,
    load_queue,
    merge_row,
    queue_stats,
    save_queue,
    write_run_report,
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class HandoffReport:
    started_at: str = ""
    finished_at: str = ""
    enabled: bool = True
    http_request_count: int = 0
    c4_complete_days_scanned: int = 0
    c4_complete_day_list: list[str] = field(default_factory=list)
    maidens_seen: int = 0
    maidens_enqueued_new: int = 0
    maidens_refreshed: int = 0
    maidens_skipped_non_maiden: int = 0
    maidens_skipped_invalid_race_id: int = 0
    maidens_skipped_missing_name: int = 0
    days_skipped_not_complete: int = 0
    days_skipped_partial: int = 0
    days_skipped_non_race: int = 0
    days_skipped_missing_listed: int = 0
    provenance_missing: int = 0
    duplicates_collapsed: int = 0
    queue_rows_total: int = 0
    queue_status_counts: dict[str, int] = field(default_factory=dict)
    cache_available: int = 0
    pending: int = 0
    errors: list[str] = field(default_factory=list)
    queue_path: str = ""
    run_report_path: str = ""
    dry_run: bool = False
    queue_written: bool = False
    supply_skipped_reason: str | None = None
    c4_source_health_state: str | None = None
    planned_new_race_ids: list[str] = field(default_factory=list)
    enqueue_capped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _c4_page_a1_health_state(cfg: W3AConfig) -> str:
    """Read-only raw C4 PAGE-A1 health state. Does not create or rewrite the file."""
    from ..c4_calendar.config import C4Config

    c4 = C4Config.from_env(data_root=cfg.data_root)
    path = c4.health_path
    if not path.is_file():
        return "UNAVAILABLE"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNAVAILABLE"
    if not isinstance(data, dict):
        return "UNKNOWN"
    raw = data.get("state")
    if raw is None or str(raw).strip() == "":
        return "UNKNOWN"
    return str(raw)


def _is_race_day_complete(index: dict[str, Any] | None) -> bool:
    if not index:
        return False
    return (
        index.get("completeness_state") == "COMPLETE"
        and (index.get("day_kind") or "") == "RACE_DAY"
    )


def _load_listed(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        races = data.get("races") or data.get("listed_races") or []
        if isinstance(races, list):
            return [x for x in races if isinstance(x, dict)]
    return []


def _discover_complete_dates(state_root: Path, c4_queue_path: Path) -> list[str]:
    """Union of COMPLETE+RACE_DAY indexes and c4 queue race_day_complete."""
    dates: set[str] = set()
    if state_root.is_dir():
        for child in state_root.iterdir():
            if not child.is_dir():
                continue
            d = child.name
            if len(d) != 10 or d[4] != "-" or d[7] != "-":
                continue
            idx = load_index(state_root, d)
            if _is_race_day_complete(idx):
                dates.add(d)
    if c4_queue_path.is_file():
        for line in c4_queue_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(o.get("state") or "") != "race_day_complete":
                continue
            d = str(o.get("kaisai_date") or o.get("date") or "")[:10]
            if not d:
                continue
            idx = load_index(state_root, d)
            # Only accept when index confirms COMPLETE+RACE_DAY (source-backed)
            if _is_race_day_complete(idx):
                dates.add(d)
    return sorted(dates)


def _needs_haron_hint(race_id: str, w2_index_path: Path | None) -> bool | None:
    """Optional metadata only — never mutates W2."""
    if w2_index_path is None or not w2_index_path.is_file():
        return None
    try:
        for line in w2_index_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(o.get("history_race_id") or "") == race_id:
                # Presence in W2 index implies haron was required historically
                return True
    except OSError:
        return None
    return None


def run_w3a_handoff(cfg: W3AConfig) -> HandoffReport:
    report = HandoffReport(
        started_at=_utc_iso(),
        enabled=cfg.enabled,
        queue_path=str(cfg.queue_path),
        dry_run=bool(cfg.w3a_handoff_dry_run),
    )
    if not cfg.enabled:
        report.finished_at = _utc_iso()
        report.errors.append("W3A_ENABLED=0")
        return report

    report.c4_source_health_state = _c4_page_a1_health_state(cfg)
    if report.c4_source_health_state != "HEALTHY":
        report.supply_skipped_reason = f"c4_not_healthy:{report.c4_source_health_state}"
        report.finished_at = _utc_iso()
        report.http_request_count = 0
        report.queue_written = False
        return report

    if not cfg.w3a_handoff_dry_run:
        cfg.w3_root.mkdir(parents=True, exist_ok=True)
        cfg.runs_dir.mkdir(parents=True, exist_ok=True)

    complete_dates = _discover_complete_dates(
        cfg.race_refresh_state_root, cfg.c4_queue_path
    )
    report.c4_complete_days_scanned = len(complete_dates)
    report.c4_complete_day_list = list(complete_dates)

    rows = load_queue(cfg.queue_path)
    seen_this_run: set[str] = set()
    cache_roots = cfg.cache_roots()
    w2_index = cfg.data_root / "var" / "layer_b_haron" / "canonical_index.jsonl"

    # Also scan non-complete dirs for skip counters (bounded to known date dirs)
    if cfg.race_refresh_state_root.is_dir():
        for child in cfg.race_refresh_state_root.iterdir():
            if not child.is_dir():
                continue
            d = child.name
            if len(d) != 10 or d[4] != "-" or d[7] != "-":
                continue
            if d in complete_dates:
                continue
            idx = load_index(cfg.race_refresh_state_root, d)
            if not idx:
                continue
            cs = idx.get("completeness_state")
            dk = idx.get("day_kind") or "UNKNOWN"
            if cs == "PARTIAL":
                report.days_skipped_partial += 1
            elif dk == "NON_RACE_DAY":
                report.days_skipped_non_race += 1
            elif cs != "COMPLETE" or dk != "RACE_DAY":
                report.days_skipped_not_complete += 1

    for kaisai_date in complete_dates:
        idx = load_index(cfg.race_refresh_state_root, kaisai_date)
        if not _is_race_day_complete(idx):
            report.days_skipped_not_complete += 1
            continue

        lp = listed_path(cfg.race_refresh_state_root, kaisai_date)
        listed = _load_listed(lp)
        if not listed:
            report.days_skipped_missing_listed += 1
            report.errors.append(f"missing_listed:{kaisai_date}")
            continue

        artifact_ref = str(lp)
        for race in listed:
            race_name = race.get("race_name")
            if race_name is None or str(race_name).strip() == "":
                report.maidens_skipped_missing_name += 1
                continue
            race_name_s = str(race_name)
            if MAIDEN_TOKEN not in race_name_s:
                report.maidens_skipped_non_maiden += 1
                continue

            rid = str(race.get("race_id") or "").strip()
            if not is_valid_race_id(rid):
                report.maidens_skipped_invalid_race_id += 1
                continue

            report.maidens_seen += 1
            if rid in seen_this_run:
                report.duplicates_collapsed += 1
                continue
            seen_this_run.add(rid)

            cache_path = find_page_c_html(rid, cache_roots)
            status = "cache_available" if cache_path is not None else "pending"

            provenance_ok = bool(
                artifact_ref
                and race_name_s
                and IDENTIFICATION_BASIS
                and kaisai_date
            )
            if not provenance_ok:
                report.provenance_missing += 1

            incoming = empty_row(
                race_id=rid,
                kaisai_date=kaisai_date,
                venue=str(race.get("venue") or ""),
                race_number=race.get("race_number")
                if isinstance(race.get("race_number"), int)
                else (
                    int(race["race_number"])
                    if str(race.get("race_number") or "").isdigit()
                    else None
                ),
                race_name=race_name_s,
                c4_day_status="RACE_DAY_COMPLETE",
                maiden_identification_basis=IDENTIFICATION_BASIS,
                source=SOURCE_LABEL,
                source_artifact_ref=artifact_ref,
                queue_status=status,
                needs_result=True,
                needs_haron=_needs_haron_hint(rid, w2_index if w2_index.is_file() else None),
                cache_html_path=str(cache_path) if cache_path else None,
            )
            # Extra provenance fields (Evidence, not Feature)
            incoming["provenance"] = {
                "c4_kaisai_date": kaisai_date,
                "listed_races_path": artifact_ref,
                "original_race_name": race_name_s,
                "identification_basis": IDENTIFICATION_BASIS,
                "index_completeness_state": (idx or {}).get("completeness_state"),
                "index_day_kind": (idx or {}).get("day_kind"),
            }

            existing = rows.get(rid)
            if existing is not None:
                # Do not rewrite existing rows (including result_complete).
                report.maidens_refreshed += 1
                continue

            if len(report.planned_new_race_ids) >= cfg.w3a_max_enqueue_per_run:
                report.enqueue_capped = True
                continue

            report.planned_new_race_ids.append(rid)
            if cfg.w3a_handoff_dry_run:
                continue

            merged, action = merge_row(existing, incoming)
            rows[rid] = merged
            if action == "inserted":
                report.maidens_enqueued_new += 1
            else:
                report.maidens_refreshed += 1

    if (not cfg.w3a_handoff_dry_run) and report.planned_new_race_ids:
        save_queue(cfg.queue_path, rows)
        report.queue_written = True
    stats = queue_stats(rows)
    report.queue_rows_total = len(rows)
    report.queue_status_counts = stats
    report.cache_available = int(stats.get("cache_available") or 0)
    report.pending = int(stats.get("pending") or 0)
    report.finished_at = _utc_iso()
    report.http_request_count = 0  # hard guarantee for W3-A

    if not cfg.w3a_handoff_dry_run:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_path = cfg.runs_dir / f"w3a_handoff_{stamp}.json"
        write_run_report(run_path, report.to_dict())
        report.run_report_path = str(run_path)
    return report
