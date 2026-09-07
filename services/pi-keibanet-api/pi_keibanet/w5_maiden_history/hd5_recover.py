# -*- coding: utf-8 -*-
"""HD-5 recovery: reuse existing horse_history_raw if history_race_id already valid.

Without raw HTML href cells, reconstructing race_id from names/dates is forbidden.
If CSV already has 12-digit history_race_id (W1 contract), copy into W5 research store.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import W5Config
from .queue import empty_row, load_queue, save_queue
from .store import upsert_horse_history

HD5_HORSES = [
    "2021100387",
    "2021104112",
    "2021104362",
    "2021105765",
    "2021105895",
    "2021106942",
]


@dataclass
class Hd5Report:
    scanned_files: int = 0
    horses_checked: int = 0
    recovered: int = 0
    unrecovered: int = 0
    recovered_horse_ids: list[str] = field(default_factory=list)
    unrecovered_horse_ids: list[str] = field(default_factory=list)
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _iter_history_csvs(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root:
            continue
        if root.is_file() and root.name == "horse_history_raw.csv":
            out.append(root)
            continue
        if root.is_dir():
            out.extend(sorted(root.rglob("horse_history_raw.csv")))
    return out


def recover_hd5_from_existing_raw(
    cfg: W5Config,
    *,
    horse_ids: list[str] | None = None,
) -> Hd5Report:
    targets = list(horse_ids or HD5_HORSES)
    report = Hd5Report(horses_checked=len(targets))
    cfg.w5_root.mkdir(parents=True, exist_ok=True)
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)

    by_horse: dict[str, list[dict[str, Any]]] = {h: [] for h in targets}
    files = _iter_history_csvs(cfg.horse_history_raw_roots or [])
    report.scanned_files = len(files)
    for path in files:
        if path.stat().st_size < 1000:
            continue
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "horse_id" not in reader.fieldnames:
                continue
            has_rid = "history_race_id" in (reader.fieldnames or [])
            for row in reader:
                hid = str(row.get("horse_id") or "").strip()
                if hid not in by_horse:
                    continue
                if not has_rid:
                    continue
                rid = str(row.get("history_race_id") or "").strip()
                if rid.isdigit() and len(rid) == 12:
                    # Keep research-relevant history fields only
                    by_horse[hid].append(dict(row))

    queue = load_queue(cfg.queue_path)
    for hid in targets:
        rows = by_horse.get(hid) or []
        # Deduplicate by history_race_id
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for r in rows:
            rid = str(r.get("history_race_id") or "")
            if rid in seen:
                continue
            seen.add(rid)
            deduped.append(r)
        detail = {
            "horse_id": hid,
            "rows_with_valid_history_race_id": len(deduped),
        }
        if deduped:
            upsert_horse_history(
                cfg.raw_path,
                horse_id=hid,
                history_rows=deduped,
                source="hd5_recover_existing_horse_history_raw",
                cache_path=None,
            )
            if hid not in queue:
                queue[hid] = empty_row(horse_id=hid, source="hd5_recover")
            queue[hid]["queue_status"] = "complete"
            queue[hid]["history_row_count"] = len(deduped)
            queue[hid]["history_race_id_valid_count"] = len(deduped)
            queue[hid]["updated_at"] = queue[hid].get("updated_at")
            report.recovered += 1
            report.recovered_horse_ids.append(hid)
            detail["status"] = "recovered"
        else:
            report.unrecovered += 1
            report.unrecovered_horse_ids.append(hid)
            detail["status"] = "unrecovered_needs_fetch"
            detail["reason"] = (
                "no_12digit_history_race_id_in_existing_csv_href_reconstruction_forbidden_without_html"
            )
        report.details.append(detail)

    save_queue(cfg.queue_path, queue)
    return report
