# -*- coding: utf-8 -*-
"""Bridge FeatureRepository (SQLite) into ai_platform FeatureLoader."""
from __future__ import annotations

from typing import Any

import pandas as pd

from ai_platform.core.features.feature_loader import FeatureLoadResult, register_db_provider


def _rows_to_frame(rows: list[dict[str, Any]], core_race_id: str) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row.get("payload") or {})
        payload["race_id"] = core_race_id
        if row.get("horse_number") is not None:
            payload["horse_number"] = row["horse_number"]
        if row.get("horse_id"):
            payload["horse_id"] = row["horse_id"]
        records.append(payload)
    return pd.DataFrame(records)


def load_from_feature_repository(core_race_id: str) -> FeatureLoadResult | None:
    from ..data.repository import FeatureRepository

    rows = FeatureRepository().list_for_race(str(core_race_id))
    if not rows:
        return None
    frame = _rows_to_frame(rows, str(core_race_id))
    if frame.empty:
        return None
    return FeatureLoadResult(
        frame=frame,
        feature_source="db",
        metadata={
            "row_count": len(frame),
            "source_file": rows[0].get("source_file") if rows else None,
        },
    )


def register() -> None:
    register_db_provider(load_from_feature_repository)


register()
