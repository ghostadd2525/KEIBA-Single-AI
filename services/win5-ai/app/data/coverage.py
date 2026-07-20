# -*- coding: utf-8 -*-
"""Coverage metrics — real_ai / mock / missing 集計。"""
from __future__ import annotations

from typing import Any

from ..engine.adapters import prediction_adapter
from .repository.supply import SupplyRepository

_FEATURE_REASONS = frozenset(
    {
        "feature_csv_missing",
        "market_feature_missing",
        "feature_missing",
    }
)


def compute_coverage(
    items: list[dict[str, Any]] | None = None,
    *,
    race_date: str | None = None,
) -> dict[str, Any]:
    """
    カタログ全レースのカバレッジを算出。
    items 未指定時は prediction_adapter.list_with_meta() を使用。
    """
    if items is None:
        date_filter = race_date or ""
        _, meta = prediction_adapter.list_with_meta(date=date_filter)
        items = meta.get("items") or []

    total = len(items)
    real = sum(1 for i in items if i.get("engine_source") == "real_ai")
    mock = sum(1 for i in items if i.get("engine_source") == "mock_fallback")
    missing_races = sum(
        1 for i in items if i.get("fallback_reason") == "race_not_found"
    )
    missing_features = sum(
        1 for i in items if i.get("fallback_reason") in _FEATURE_REASONS
    )
    coverage_pct = round((real / total) * 100, 1) if total else 0.0

    by_reason: dict[str, int] = {}
    for it in items:
        if it.get("engine_source") != "mock_fallback":
            continue
        reason = str(it.get("fallback_reason") or "unknown")
        by_reason[reason] = by_reason.get(reason, 0) + 1

    return {
        "race_total": total,
        "real_ai": real,
        "mock": mock,
        "coverage": coverage_pct,
        "missing_features": missing_features,
        "missing_races": missing_races,
        "by_reason": by_reason,
    }


def get_coverage(*, race_date: str | None = None, use_cache: bool = True) -> dict[str, Any]:
    """最新 validation スナップショットがあれば返し、なければ live 計算。"""
    if use_cache and race_date:
        cached = SupplyRepository().latest_validation(race_date)
        if cached:
            return {
                "race_total": cached["race_total"],
                "real_ai": cached["real_ai"],
                "mock": cached["mock"],
                "coverage": cached["coverage"],
                "missing_features": cached["missing_features"],
                "missing_races": cached["missing_races"],
                "by_reason": cached.get("by_reason") or {},
                "source": "validation_cache",
                "validation_id": cached["id"],
            }
    live = compute_coverage(race_date=race_date)
    live["source"] = "live"
    return live
