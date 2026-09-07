# -*- coding: utf-8 -*-
"""W5 handoff: W3 maiden runners + gap universe → history queue (HTTP 0)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import W5Config
from .queue import empty_row, load_queue, queue_stats, save_queue, write_run_report
from .store import load_by_horse


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class HandoffReport:
    started_at: str = ""
    finished_at: str = ""
    enabled: bool = True
    http_request_count: int = 0
    w3_runners_scanned: int = 0
    seed_horses: int = 0
    new_rows: int = 0
    refreshed_rows: int = 0
    skipped_complete: int = 0
    queue_total: int = 0
    queue_stats: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    run_report_path: str = ""
    feature_consumer: bool = False
    prediction_consumer: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            out.append(o)
    return out


def run_w5_handoff(
    cfg: W5Config,
    *,
    seed_horse_ids: list[str] | None = None,
    include_w3_runners: bool = True,
) -> HandoffReport:
    report = HandoffReport(started_at=_utc_iso(), enabled=cfg.enabled)
    if not cfg.enabled:
        report.finished_at = _utc_iso()
        report.errors.append("W5_ENABLED=0")
        return report

    cfg.w5_root.mkdir(parents=True, exist_ok=True)
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)

    # Always load W3 runners for target_race_id metadata; expand seeds only when include_w3_runners.
    runners = _load_jsonl(cfg.w3_runner_raw_path)
    report.w3_runners_scanned = len(runners)
    queue = load_queue(cfg.queue_path)
    raw_done = load_by_horse(cfg.raw_path)

    # Build horse -> race_ids from W3
    horse_races: dict[str, set[str]] = {}
    for r in runners:
        hid = str(r.get("horse_id") or "").strip()
        rid = str(r.get("race_id") or "").strip()
        if not hid:
            continue
        horse_races.setdefault(hid, set())
        if rid:
            horse_races[hid].add(rid)

    seeds = set(seed_horse_ids or [])
    if include_w3_runners:
        seeds |= set(horse_races.keys())
    report.seed_horses = len(seeds)

    def _research_complete(hid: str) -> bool:
        raw = raw_done.get(hid)
        if not raw:
            return False
        src = str(raw.get("source") or "")
        # HD-5 recover or any persisted research history with valid race ids
        if src.startswith("hd5"):
            return True
        return int(raw.get("history_race_id_valid_count") or 0) > 0 or (
            int(raw.get("history_row_count") or 0) == 0 and src.startswith("w5_")
        )

    for hid in sorted(seeds):
        races = sorted(horse_races.get(hid) or [])
        first_race = races[0] if races else None
        done = _research_complete(hid)

        if hid not in queue:
            st = "complete" if done else "pending"
            queue[hid] = empty_row(
                horse_id=hid,
                source="w3_handoff" if hid in horse_races else "seed_universe",
                first_seen_race_id=first_race,
                target_race_ids=races,
            )
            queue[hid]["queue_status"] = st
            if st == "complete":
                queue[hid]["history_row_count"] = int(
                    raw_done[hid].get("history_row_count") or 0
                )
                queue[hid]["history_race_id_valid_count"] = int(
                    raw_done[hid].get("history_race_id_valid_count") or 0
                )
                report.skipped_complete += 1
            report.new_rows += 1
        else:
            row = queue[hid]
            existing = set(row.get("target_race_ids") or [])
            existing |= set(races)
            row["target_race_ids"] = sorted(existing)
            if not row.get("first_seen_race_id") and first_race:
                row["first_seen_race_id"] = first_race
            if done and row.get("queue_status") == "pending":
                row["queue_status"] = "complete"
                row["history_row_count"] = int(raw_done[hid].get("history_row_count") or 0)
                row["history_race_id_valid_count"] = int(
                    raw_done[hid].get("history_race_id_valid_count") or 0
                )
                report.skipped_complete += 1
            row["updated_at"] = _utc_iso()
            queue[hid] = row
            report.refreshed_rows += 1

    save_queue(cfg.queue_path, queue)
    report.queue_total = len(queue)
    report.queue_stats = queue_stats(queue)
    report.http_request_count = 0
    report.finished_at = _utc_iso()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = cfg.runs_dir / f"w5_handoff_{stamp}.json"
    write_run_report(path, report.to_dict())
    report.run_report_path = str(path)
    return report
