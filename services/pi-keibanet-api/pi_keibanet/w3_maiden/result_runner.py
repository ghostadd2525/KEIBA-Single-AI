# -*- coding: utf-8 -*-
"""W3-B runner — parse cache_available PAGE-C HTML only (HTTP 0)."""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cache_probe import find_page_c_html
from .config import W3AConfig
from .queue import load_queue, queue_stats, save_queue, write_run_report
from .result_apply import apply_html_result_parse
from .result_store import load_runner_jsonl


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ParseReport:
    started_at: str = ""
    finished_at: str = ""
    enabled: bool = True
    http_request_count: int = 0
    cache_available_input: int = 0
    parsed_races: int = 0
    result_complete: int = 0
    partial: int = 0
    parse_failed: int = 0
    skipped_not_cache_available: int = 0
    total_runners: int = 0
    unique_horse_ids: int = 0
    horse_id_missing: int = 0
    trainer_present: int = 0
    trainer_missing: int = 0
    body_weight_present: int = 0
    body_weight_missing: int = 0
    odds_present: int = 0
    odds_missing: int = 0
    w4_candidate_unique_horses: int = 0
    errors: list[str] = field(default_factory=list)
    race_ids_processed: list[str] = field(default_factory=list)
    queue_status_counts: dict[str, int] = field(default_factory=dict)
    queue_path: str = ""
    race_raw_path: str = ""
    runner_raw_path: str = ""
    run_report_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _tally_runners(report: ParseReport, runners: list[dict[str, Any]]) -> None:
    for rrow in runners:
        hid = rrow.get("horse_id")
        if hid:
            has_tr = bool(
                rrow.get("race_time_trainer_id") or rrow.get("race_time_trainer_name")
            )
            report.trainer_present += 1 if has_tr else 0
            report.trainer_missing += 0 if has_tr else 1
            report.body_weight_present += 1 if rrow.get("body_weight") is not None else 0
            report.body_weight_missing += 0 if rrow.get("body_weight") is not None else 1
            report.odds_present += 1 if rrow.get("odds") is not None else 0
            report.odds_missing += 0 if rrow.get("odds") is not None else 1
        else:
            report.horse_id_missing += 1
            report.trainer_missing += 1
            report.body_weight_missing += 1
            report.odds_missing += 1


def run_w3b_parse(cfg: W3AConfig) -> ParseReport:
    report = ParseReport(
        started_at=_utc_iso(),
        queue_path=str(cfg.queue_path),
        race_raw_path=str(cfg.race_raw_path),
        runner_raw_path=str(cfg.runner_raw_path),
    )
    enabled = os.environ.get("W3B_ENABLED", "1") not in ("0", "false", "False")
    report.enabled = enabled
    if not enabled:
        report.finished_at = _utc_iso()
        report.errors.append("W3B_ENABLED=0")
        return report

    cfg.w3_root.mkdir(parents=True, exist_ok=True)
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)

    rows = load_queue(cfg.queue_path)
    cache_roots = cfg.cache_roots()
    targets = [
        (rid, row)
        for rid, row in sorted(rows.items())
        if str(row.get("queue_status") or "") == "cache_available"
    ]
    report.cache_available_input = len(targets)
    report.skipped_not_cache_available = len(rows) - len(targets)

    for rid, row in targets:
        html_path: Path | None = None
        cached = row.get("cache_html_path")
        if cached and Path(str(cached)).is_file():
            html_path = Path(str(cached))
        if html_path is None:
            html_path = find_page_c_html(rid, cache_roots)
        if html_path is None or not html_path.is_file():
            report.parse_failed += 1
            report.errors.append(f"cache_html_missing:{rid}")
            row["queue_status"] = "parse_failed"
            row["parse_error"] = "cache_html_missing"
            row["updated_at"] = _utc_iso()
            rows[rid] = row
            continue

        try:
            applied = apply_html_result_parse(
                cfg, race_id=rid, queue_row=row, html_path=html_path
            )
        except OSError as exc:
            report.parse_failed += 1
            report.errors.append(f"read_failed:{rid}:{exc}")
            row["queue_status"] = "parse_failed"
            row["parse_error"] = "read_failed"
            row["updated_at"] = _utc_iso()
            rows[rid] = row
            continue

        status = str(applied["queue_status"])
        if applied["parse_ok"]:
            report.parsed_races += 1
            report.total_runners += int(applied["runner_count"])
            report.race_ids_processed.append(rid)
            _tally_runners(report, applied["runners"])
        if status == "result_complete":
            report.result_complete += 1
        elif status == "partial":
            report.partial += 1
        else:
            report.parse_failed += 1
        rows[rid] = row

    save_queue(cfg.queue_path, rows)

    stored_runners = load_runner_jsonl(cfg.runner_raw_path)
    uniq = {
        k[1]
        for k, v in stored_runners.items()
        if v.get("horse_id") and not str(k[1]).startswith("missing:")
    }
    report.unique_horse_ids = len(uniq)
    report.w4_candidate_unique_horses = len(uniq)
    report.queue_status_counts = queue_stats(rows)
    report.http_request_count = 0
    report.finished_at = _utc_iso()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = cfg.runs_dir / f"w3b_parse_{stamp}.json"
    write_run_report(run_path, report.to_dict())
    report.run_report_path = str(run_path)
    return report
