# -*- coding: utf-8 -*-
"""Intake new history_race_id values from W1 horse_history_raw.csv (read-only)."""
from __future__ import annotations

import csv
from pathlib import Path

from .layer_b_store import is_valid_race_id


def collect_history_race_ids_from_csv(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.is_file():
        return ids
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "history_race_id" not in reader.fieldnames:
            return ids
        for row in reader:
            rid = (row.get("history_race_id") or "").strip()
            if is_valid_race_id(rid):
                ids.add(rid)
    return ids


def collect_new_ids_from_state(
    state_root: Path,
    *,
    date: str | None = None,
    lookback_days: int = 7,
) -> set[str]:
    """Scan race_refresh state for history_race_id (incremental; not full 10k enqueue)."""
    ids: set[str] = set()
    if date:
        ids |= collect_history_race_ids_from_csv(state_root / date / "horse_history_raw.csv")
        return ids
    if not state_root.is_dir():
        return ids
    # Prefer recent day dirs by name (YYYY-MM-DD).
    day_dirs = sorted(
        [p for p in state_root.iterdir() if p.is_dir() and len(p.name) == 10],
        key=lambda p: p.name,
        reverse=True,
    )
    for p in day_dirs[: max(1, lookback_days)]:
        ids |= collect_history_race_ids_from_csv(p / "horse_history_raw.csv")
    return ids
