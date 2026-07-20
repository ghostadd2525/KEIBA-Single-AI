# -*- coding: utf-8 -*-
"""Export FeatureRepository rows to compatibility CSV (DB is canonical source)."""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

from ..repository import FeatureRepository, RaceRepository


def _platform_data_root() -> Path | None:
    root = (os.environ.get("AI_PLATFORM_ROOT") or "").strip()
    if root:
        data = Path(root) / "data"
        if data.is_dir():
            return data
    return None


def _flatten_feature_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row.get("payload") or {})
    payload["race_id"] = row.get("race_id") or payload.get("race_id")
    if row.get("horse_number") is not None:
        payload["horse_number"] = row["horse_number"]
    if row.get("horse_id"):
        payload["horse_id"] = row["horse_id"]
    return payload


def export_features_for_date(race_date: str) -> dict[str, Any]:
    """
    Export DB features for ``race_date`` to daily + global compatibility CSV.
    Returns paths written and row counts.
    """
    data_root = _platform_data_root()
    if data_root is None:
        return {"ok": False, "reason": "platform_missing", "paths": []}

    races = RaceRepository().list(date=race_date, limit=500)
    core_ids = sorted(
        {
            str(r.get("core_race_id") or r.get("race_id") or "")
            for r in races
            if r.get("core_race_id") or r.get("race_id")
        }
    )

    repo = FeatureRepository()
    rows: list[dict[str, Any]] = []
    for core_id in core_ids:
        if not core_id:
            continue
        for feat in repo.list_for_race(core_id):
            rows.append(_flatten_feature_row(feat))

    if not rows:
        return {
            "ok": True,
            "reason": "no_features",
            "race_date": race_date,
            "paths": [],
            "row_count": 0,
        }

    fieldnames = sorted({k for row in rows for k in row.keys()})
    daily_dir = data_root / "demo_daily_outputs" / race_date
    daily_dir.mkdir(parents=True, exist_ok=True)
    daily_path = daily_dir / "demo_runners_pace_market_features.csv"
    _write_csv(daily_path, fieldnames, rows)

    global_path = data_root / "runners_pace_market_features.csv"
    merged = _merge_global_csv(global_path, rows, fieldnames)
    _write_csv(global_path, fieldnames, merged)

    return {
        "ok": True,
        "race_date": race_date,
        "row_count": len(rows),
        "paths": [str(daily_path), str(global_path)],
    }


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _merge_global_csv(
    path: Path,
    new_rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> list[dict[str, Any]]:
    existing: list[dict[str, Any]] = []
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as fh:
            existing = list(csv.DictReader(fh))

    replace_ids = {str(r.get("race_id") or "") for r in new_rows}
    kept = [r for r in existing if str(r.get("race_id") or "") not in replace_ids]
    merged = kept + new_rows
    all_fields = sorted({k for row in merged for k in row.keys()} | set(fieldnames))
    for row in merged:
        for key in all_fields:
            row.setdefault(key, "")
    return merged
