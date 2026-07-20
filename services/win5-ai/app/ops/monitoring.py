# -*- coding: utf-8 -*-
"""
Monitoring — ETL失敗率 / Coverage / fallback / エラー / API時間 / DBサイズ
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..data.coverage import get_coverage
from ..data.db import db_path
from ..data.repository.supply import SupplyRepository
from ..engine.adapters import prediction_adapter
from .performance import get_recorder


class MonitoringService:
    def collect(self) -> dict[str, Any]:
        return collect_metrics()


def collect_metrics() -> dict[str, Any]:
    supply = SupplyRepository()
    coverage = get_coverage(use_cache=False)
    perf = get_recorder().summarize()

    etl_runs = supply.list_runs(limit=100)
    etl_total = len(etl_runs)
    etl_failed = sum(1 for r in etl_runs if r.get("status") == "failed")
    etl_failure_rate = round((etl_failed / etl_total) * 100, 2) if etl_total else 0.0

    validations = supply.list_validations(limit=20)
    coverage_trend = [
        {
            "race_date": v.get("race_date"),
            "coverage": v.get("coverage"),
            "real_ai": v.get("real_ai"),
            "mock": v.get("mock"),
            "created_at": v.get("created_at"),
        }
        for v in reversed(validations)
    ]

    _, meta = prediction_adapter.list_with_meta()
    items = meta.get("items") or []
    fallback_trend: dict[str, int] = {}
    prediction_errors = 0
    for it in items:
        if it.get("engine_source") == "mock_fallback":
            reason = str(it.get("fallback_reason") or "unknown")
            fallback_trend[reason] = fallback_trend.get(reason, 0) + 1
        if it.get("fallback_reason") in ("exception", "prediction_failed", "timeout"):
            prediction_errors += 1

    db_file = db_path()
    db_bytes = db_file.stat().st_size if db_file.exists() else 0

    log_errors = _count_log_errors()

    return {
        "etl": {
            "total_runs": etl_total,
            "failed_runs": etl_failed,
            "failure_rate_pct": etl_failure_rate,
            "latest": supply.latest_run(),
        },
        "coverage": coverage,
        "coverage_trend": coverage_trend,
        "fallback_reason_trend": fallback_trend,
        "prediction_errors": prediction_errors,
        "api_performance": perf,
        "db": {
            "path": str(db_file),
            "size_bytes": db_bytes,
            "size_mb": round(db_bytes / (1024 * 1024), 3),
        },
        "log_errors": log_errors,
        "alerts": _build_alerts(
            etl_failure_rate=etl_failure_rate,
            coverage_pct=float(coverage.get("coverage") or 0),
            prediction_errors=prediction_errors,
            perf=perf,
            db_bytes=db_bytes,
        ),
    }


def _count_log_errors() -> int:
    try:
        from ..data.db import connect

        conn = connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM logs WHERE level IN ('error','critical')"
            ).fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()
    except Exception:
        return 0


def _build_alerts(
    *,
    etl_failure_rate: float,
    coverage_pct: float,
    prediction_errors: int,
    perf: dict[str, Any],
    db_bytes: int,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    if etl_failure_rate > 20:
        alerts.append(
            {
                "level": "warning",
                "code": "etl_high_failure_rate",
                "message": f"ETL failure rate {etl_failure_rate}% exceeds 20%",
            }
        )
    if coverage_pct < 5:
        alerts.append(
            {
                "level": "info",
                "code": "low_coverage",
                "message": f"Coverage {coverage_pct}% is below 5%",
            }
        )
    if prediction_errors > 0:
        alerts.append(
            {
                "level": "warning",
                "code": "prediction_errors",
                "message": f"{prediction_errors} prediction errors detected",
            }
        )
    for name, stats in (perf.get("by_name") or {}).items():
        if stats.get("p95_ms", 0) > 5000:
            alerts.append(
                {
                    "level": "warning",
                    "code": "slow_api",
                    "message": f"{name} p95={stats['p95_ms']}ms exceeds 5000ms",
                }
            )
    max_db = int(os.environ.get("EXPECT_AI_DB_MAX_MB") or "500") * 1024 * 1024
    if db_bytes > max_db:
        alerts.append(
            {
                "level": "warning",
                "code": "db_size",
                "message": f"DB size {db_bytes} exceeds limit {max_db}",
            }
        )
    return alerts
