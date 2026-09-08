# -*- coding: utf-8 -*-
"""W4-B — Parse D1/D2 HTML already on disk (HTTP 0)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .config import W4Config
from .parse_apply import try_parse_from_cache
from .queue import load_queue, queue_stats, save_queue, write_run_report
from .raw_store import load_by_key


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ParseReport:
    started_at: str = ""
    finished_at: str = ""
    enabled: bool = True
    http_request_count: int = 0
    horses_scanned: int = 0
    d1_parsed_ok: int = 0
    d1_partial: int = 0
    d1_parse_failed: int = 0
    d1_no_cache: int = 0
    d2_parsed_ok: int = 0
    d2_partial: int = 0
    d2_parse_failed: int = 0
    d2_no_cache: int = 0
    profile_raw_rows: int = 0
    pedigree_raw_rows: int = 0
    errors: list[str] = field(default_factory=list)
    queue_stats: dict[str, Any] = field(default_factory=dict)
    run_report_path: str = ""
    feature_consumer: bool = False
    prediction_consumer: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_w4b_parse(cfg: W4Config, *, horse_ids: list[str] | None = None) -> ParseReport:
    report = ParseReport(started_at=_utc_iso(), enabled=cfg.enabled)
    if not cfg.enabled:
        report.finished_at = _utc_iso()
        report.errors.append("W4A_ENABLED=0")
        return report

    cfg.w4_root.mkdir(parents=True, exist_ok=True)
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)

    queue = load_queue(cfg.queue_path)
    targets = horse_ids or sorted(queue.keys())
    for hid in targets:
        row = queue.get(hid)
        if row is None:
            report.errors.append(f"missing_queue_row:{hid}")
            continue
        report.horses_scanned += 1
        before_d1 = str(row.get("d1_status") or "pending")
        before_d2 = str(row.get("d2_status") or "pending")
        try:
            result = try_parse_from_cache(cfg, hid, row)
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"parse_exc:{hid}:{type(exc).__name__}:{exc}")
            continue
        if result.get("d1") is None and before_d1 in ("pending", "cache_available"):
            report.d1_no_cache += 1
        elif result.get("d1"):
            st = result["d1"]["status"]
            if st == "complete":
                report.d1_parsed_ok += 1
            elif st == "partial":
                report.d1_partial += 1
            else:
                report.d1_parse_failed += 1
        if result.get("d2") is None and before_d2 in ("pending", "cache_available"):
            report.d2_no_cache += 1
        elif result.get("d2"):
            st = result["d2"]["status"]
            if st == "complete":
                report.d2_parsed_ok += 1
            elif st == "partial":
                report.d2_partial += 1
            else:
                report.d2_parse_failed += 1
        queue[hid] = row

    save_queue(cfg.queue_path, queue)
    report.profile_raw_rows = len(load_by_key(cfg.profile_raw_path))
    report.pedigree_raw_rows = len(load_by_key(cfg.pedigree_raw_path))
    report.queue_stats = queue_stats(queue)
    report.http_request_count = 0
    report.finished_at = _utc_iso()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = cfg.runs_dir / f"w4b_parse_{stamp}.json"
    write_run_report(run_path, report.to_dict())
    report.run_report_path = str(run_path)
    return report
