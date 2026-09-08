# -*- coding: utf-8 -*-
"""W4-A handoff: W3 runner_result_raw → canonical horse queue (HTTP 0)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import W4Config
from .id_format import classify_horse_id, find_d1_html, find_d2_html
from .queue import (
    empty_row,
    load_provenance,
    load_queue,
    merge_seen,
    queue_stats,
    save_provenance,
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
    w3_runner_rows_scanned: int = 0
    w3_unique_horse_ids_input: int = 0
    w3_result_complete_races: int = 0
    w4_canonical_horses: int = 0
    new_rows: int = 0
    refreshed_rows: int = 0
    deduped_references: int = 0
    invalid_ids: int = 0
    non_standard_ids: int = 0
    d1_pending: int = 0
    d2_pending: int = 0
    d1_cache_available: int = 0
    d2_cache_available: int = 0
    audit_baseline_unique: int = 127
    delta_vs_audit_baseline: int = 0
    provenance_rows: int = 0
    errors: list[str] = field(default_factory=list)
    queue_stats: dict[str, Any] = field(default_factory=dict)
    queue_path: str = ""
    provenance_path: str = ""
    run_report_path: str = ""
    feature_consumer: bool = False
    prediction_consumer: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_runner_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _count_result_complete(w3_queue_path: Path) -> int:
    if not w3_queue_path.is_file():
        return 0
    n = 0
    for line in w3_queue_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(o.get("queue_status") or "") == "result_complete":
            n += 1
    return n


def _seen_at_for_row(row: dict[str, Any], race_order: dict[str, int]) -> str:
    # Prefer provenance parsed_at / retrieved_at if present
    for key in ("parsed_at", "retrieved_at", "updated_at", "created_at"):
        prov = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        val = row.get(key) or (prov.get(key) if prov else None)
        if val:
            return str(val)
    rid = str(row.get("race_id") or "")
    # deterministic synthetic stamp from race_id order
    return f"order:{race_order.get(rid, 0):06d}"


def run_w4a_handoff(cfg: W4Config) -> HandoffReport:
    report = HandoffReport(
        started_at=_utc_iso(),
        enabled=cfg.enabled,
        queue_path=str(cfg.queue_path),
        provenance_path=str(cfg.provenance_path),
    )
    if not cfg.enabled:
        report.finished_at = _utc_iso()
        report.errors.append("W4A_ENABLED=0")
        return report

    try:
        cfg.w4_root.mkdir(parents=True, exist_ok=True)
        cfg.runs_dir.mkdir(parents=True, exist_ok=True)

        runners = _load_runner_rows(cfg.w3_runner_raw_path)
        report.w3_runner_rows_scanned = len(runners)
        report.w3_result_complete_races = _count_result_complete(cfg.w3_queue_path)

        # Sort for deterministic first_seen: by race_id then horse_number
        def sort_key(r: dict[str, Any]) -> tuple:
            rid = str(r.get("race_id") or "")
            hn = r.get("horse_number")
            fp = r.get("finish_position")
            return (
                rid,
                hn if isinstance(hn, int) else 999,
                fp if isinstance(fp, int) else 999,
                str(r.get("horse_id") or ""),
            )

        runners_sorted = sorted(runners, key=sort_key)
        race_ids_ordered = sorted({str(r.get("race_id") or "") for r in runners if r.get("race_id")})
        race_order = {rid: i for i, rid in enumerate(race_ids_ordered)}

        queue = load_queue(cfg.queue_path)
        provenance = load_provenance(cfg.provenance_path)

        unique_input: set[str] = set()
        for row in runners_sorted:
            raw_hid = row.get("horse_id")
            hid, fmt = classify_horse_id(None if raw_hid is None else str(raw_hid))
            if not hid or fmt == "invalid":
                report.invalid_ids += 1
                continue
            unique_input.add(hid)

            race_id = str(row.get("race_id") or "").strip()
            if not race_id:
                report.errors.append(f"missing_race_id_for_horse:{hid}")
                continue

            seen_at = _seen_at_for_row(row, race_order)
            prov_key = (hid, race_id)
            is_new_pair = prov_key not in provenance
            if is_new_pair:
                provenance[prov_key] = {
                    "horse_id": hid,
                    "race_id": race_id,
                    "horse_name": row.get("horse_name"),
                    "first_recorded_at": seen_at,
                    "source": "w3_runner_result_raw",
                    "created_at": _utc_iso(),
                }
            else:
                report.deduped_references += 1

            d1_path = find_d1_html(hid, cfg.d1_cache_roots)
            d2_path = find_d2_html(hid, cfg.d2_cache_roots)
            d1_st = "cache_available" if d1_path else "pending"
            d2_st = "cache_available" if d2_path else "pending"

            if hid not in queue:
                if fmt == "netkeiba_other_canonical":
                    report.non_standard_ids += 1
                canon = "cache_available" if (d1_st == "cache_available" or d2_st == "cache_available") else "pending"
                queue[hid] = empty_row(
                    horse_id=hid,
                    horse_id_raw=str(raw_hid).strip(),
                    horse_id_format=fmt,
                    first_seen_race_id=race_id,
                    first_seen_at=seen_at,
                    d1_status=d1_st,
                    d2_status=d2_st,
                    canonical_status=canon,
                    d1_cache_path=str(d1_path) if d1_path else None,
                    d2_cache_path=str(d2_path) if d2_path else None,
                )
                report.new_rows += 1
            else:
                existing = queue[hid]
                # preserve first_seen
                merged, _ = merge_seen(
                    existing,
                    race_id=race_id,
                    seen_at=seen_at,
                    d1_status=d1_st,
                    d2_status=d2_st,
                    d1_cache_path=str(d1_path) if d1_path else None,
                    d2_cache_path=str(d2_path) if d2_path else None,
                )
                # never overwrite first_seen_*
                merged["first_seen_race_id"] = existing.get("first_seen_race_id")
                merged["first_seen_at"] = existing.get("first_seen_at")
                merged["created_at"] = existing.get("created_at")
                if existing.get("horse_id_format") == "netkeiba_other_canonical":
                    merged["horse_id_format"] = "netkeiba_other_canonical"
                queue[hid] = merged
                report.refreshed_rows += 1

        # Recompute source_race_count from provenance
        from collections import Counter

        race_counts = Counter(hid for (hid, _rid) in provenance.keys())
        for hid, row in queue.items():
            row["source_race_count"] = int(race_counts.get(hid) or row.get("source_race_count") or 0)

        # last_seen: for each horse, max race_id by race_order among provenance
        for hid, row in queue.items():
            races = [rid for (h, rid) in provenance.keys() if h == hid]
            if not races:
                continue
            # prefer chronological via race_id sort (YYYY embedded) then order map
            best = max(races, key=lambda rid: (race_order.get(rid, -1), rid))
            row["last_seen_race_id"] = best
            # keep last_seen_at if already set for that race via runner; else leave
            row["updated_at"] = _utc_iso()

        save_queue(cfg.queue_path, queue)
        save_provenance(cfg.provenance_path, provenance)

        report.w3_unique_horse_ids_input = len(unique_input)
        report.w4_canonical_horses = len(queue)
        report.provenance_rows = len(provenance)
        report.delta_vs_audit_baseline = report.w4_canonical_horses - report.audit_baseline_unique
        report.non_standard_ids = sum(
            1 for r in queue.values() if r.get("horse_id_format") == "netkeiba_other_canonical"
        )
        report.d1_pending = sum(1 for r in queue.values() if r.get("d1_status") == "pending")
        report.d2_pending = sum(1 for r in queue.values() if r.get("d2_status") == "pending")
        report.d1_cache_available = sum(
            1 for r in queue.values() if r.get("d1_status") == "cache_available"
        )
        report.d2_cache_available = sum(
            1 for r in queue.values() if r.get("d2_status") == "cache_available"
        )
        report.queue_stats = queue_stats(queue)
        report.http_request_count = 0
        report.finished_at = _utc_iso()

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_path = cfg.runs_dir / f"w4a_handoff_{stamp}.json"
        write_run_report(run_path, report.to_dict())
        report.run_report_path = str(run_path)
        return report
    except Exception as exc:  # noqa: BLE001 — never propagate to W3
        report.errors.append(f"w4a_failed:{type(exc).__name__}:{exc}")
        report.http_request_count = 0
        report.finished_at = _utc_iso()
        return report
