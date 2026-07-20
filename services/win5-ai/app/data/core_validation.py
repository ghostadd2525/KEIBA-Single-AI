# -*- coding: utf-8 -*-
"""Core validation and deployment gate for real_ai_rate."""
from __future__ import annotations

from typing import Any

from ..engine.adapters import prediction_adapter
from .coverage import compute_coverage
from .repository.supply import SupplyRepository


def validate_core(
    *,
    run_id: int | None = None,
    race_date: str | None = None,
) -> dict[str, Any]:
    """
    Core 推論診断 — prediction_adapter 経由で real_ai_rate を算出。
    FeatureLoader 統一経路で診断・推論が一致する。
    """
    date_filter = race_date or ""
    _, meta = prediction_adapter.list_with_meta(date=date_filter)
    items = meta.get("items") or []
    coverage = compute_coverage(items)

    total = int(coverage.get("race_total") or 0)
    real = int(coverage.get("real_ai") or 0)
    real_ai_rate = round(real / total, 4) if total else 0.0

    feature_sources: dict[str, int] = {}
    for it in items:
        if it.get("engine_source") != "real_ai":
            continue
        src = str(it.get("feature_source") or "unknown")
        feature_sources[src] = feature_sources.get(src, 0) + 1

    return {
        "run_id": run_id,
        "race_date": race_date or "",
        "race_total": total,
        "real_ai": real,
        "mock_fallback": int(coverage.get("mock") or 0),
        "real_ai_rate": real_ai_rate,
        "coverage_pct": coverage.get("coverage"),
        "by_reason": coverage.get("by_reason") or {},
        "feature_sources": feature_sources,
        "items": items,
    }


def check_deployment_gate(
    core_result: dict[str, Any],
    *,
    race_date: str | None = None,
    min_rate: float | None = None,
) -> dict[str, Any]:
    """
    real_ai_rate が前回 validation より低下した場合 Deployment NG。
    """
    current_rate = float(core_result.get("real_ai_rate") or 0.0)
    previous = SupplyRepository().latest_validation(race_date)
    previous_rate: float | None = None
    if previous and previous.get("race_total"):
        previous_rate = round(
            float(previous.get("real_ai") or 0) / float(previous["race_total"]),
            4,
        )

    floor = min_rate
    if floor is None and previous_rate is not None:
        floor = previous_rate

    ok = True
    reason = "ok"
    if floor is not None and current_rate < floor:
        ok = False
        reason = "real_ai_rate_regressed"
    elif current_rate < 1.0 and int(core_result.get("race_total") or 0) > 0:
        # カタログ全件 real_ai 未達も NG（初回除く previous 無しは許容）
        if previous_rate is not None and current_rate < previous_rate:
            ok = False
            reason = "real_ai_rate_regressed"

    return {
        "ok": ok,
        "reason": reason,
        "current_real_ai_rate": current_rate,
        "previous_real_ai_rate": previous_rate,
        "min_required_rate": floor,
        "deployment": "ok" if ok else "ng",
    }
