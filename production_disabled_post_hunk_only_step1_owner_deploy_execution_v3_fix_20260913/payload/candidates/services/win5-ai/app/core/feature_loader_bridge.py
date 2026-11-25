# -*- coding: utf-8 -*-
"""Bridge FeatureRepository (SQLite) into ai_platform FeatureLoader."""
from __future__ import annotations

from typing import Any

import pandas as pd

try:
    from ai_platform.core.features.feature_loader import FeatureLoadResult, register_db_provider
except Exception:  # ローカル/mock: platform 未配置でも GET/Conversation を起動可能
    FeatureLoadResult = None  # type: ignore[misc,assignment]
    register_db_provider = None


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


_unpinned_load_calls: list[str] = []


def unpinned_load_calls() -> list[str]:
    return list(_unpinned_load_calls)


def reset_unpinned_load_calls() -> None:
    _unpinned_load_calls.clear()


def _install_feature_pin() -> None:
    """POST 中のみピン済み FeatureLoadResult を返す。GET は未ピンで既存 load。"""
    try:
        from ai_platform.core.features.feature_loader import FeatureLoader
        from ..predictions.feature_pin import get_pinned_feature
    except Exception:
        return
    if getattr(FeatureLoader.load, "_prediction_pin_wrapped", False):
        return
    original = FeatureLoader.load

    def load(self, core_race_id: str):  # type: ignore[no-untyped-def]
        from ..predictions.feature_pin import FeatureLoadReloadForbidden
        from ..predictions.feature_pin import get_pinned_feature
        from ..predictions.feature_pin import persist_pin_required

        requested = str(core_race_id or "").strip()
        pinned = get_pinned_feature()
        if pinned is not None:
            if requested != str(pinned.core_race_id):
                raise FeatureLoadReloadForbidden(
                    "pinned FeatureLoadResult is for %s, not %s"
                    % (pinned.core_race_id, requested)
                )
            return pinned.result
        if persist_pin_required():
            raise FeatureLoadReloadForbidden(
                "persist POST must not reload FeatureLoader after confirm"
            )
        _unpinned_load_calls.append(requested)
        return original(self, core_race_id)

    load._prediction_pin_wrapped = True  # type: ignore[attr-defined]
    FeatureLoader.load = load  # type: ignore[method-assign]


def register() -> None:
    if register_db_provider is None:
        return
    register_db_provider(load_from_feature_repository)
    _install_feature_pin()


register()
