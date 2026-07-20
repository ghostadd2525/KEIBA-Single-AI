# -*- coding: utf-8 -*-
"""Auto validation — ETL 後に全レースを検証しスナップショット保存。"""
from __future__ import annotations

from typing import Any

from ..diagnostics.missing_collector import collect_missing_report
from ..engine.adapters import prediction_adapter
from .core_validation import check_deployment_gate, validate_core
from .coverage import compute_coverage
from .repository.supply import SupplyRepository


def validate_all_races(
    *,
    run_id: int | None = None,
    race_date: str | None = None,
) -> dict[str, Any]:
    """
    全カタログレースを推論診断し、coverage / reason を生成して DB 保存。
    """
    date_filter = race_date or ""
    _, meta = prediction_adapter.list_with_meta(date=date_filter)
    items = meta.get("items") or []

    coverage = compute_coverage(items)
    by_reason = coverage.pop("by_reason", {})

    detailed_items = []
    for it in items:
        detailed_items.append(
            {
                "race_id": it.get("race_id"),
                "engine_source": it.get("engine_source"),
                "fallback_reason": it.get("fallback_reason"),
                "core_race_id": it.get("core_race_id"),
            }
        )

    missing_report = collect_missing_report(items)

    core_validation = validate_core(run_id=run_id, race_date=race_date or date_filter or None)
    deployment_gate = check_deployment_gate(
        core_validation,
        race_date=race_date or date_filter or None,
    )

    validation_id = SupplyRepository().save_validation(
        run_id=run_id,
        race_date=race_date or "",
        coverage=coverage,
        items=detailed_items,
        by_reason=by_reason,
    )

    return {
        "validation_id": validation_id,
        "coverage": coverage,
        "by_reason": by_reason,
        "items": detailed_items,
        "missing_report_summary": missing_report.get("summary"),
        "core_validation": core_validation,
        "deployment_gate": deployment_gate,
    }
