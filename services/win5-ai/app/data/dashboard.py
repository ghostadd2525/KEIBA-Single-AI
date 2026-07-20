# -*- coding: utf-8 -*-
"""Admin dashboard — Coverage / ETL / Import / Fallback / Missing 集約。"""
from __future__ import annotations

import json
from typing import Any

from ..diagnostics.missing_collector import collect_missing_report
from ..engine.adapters import prediction_adapter
from .coverage import get_coverage
from .repository.supply import SupplyRepository
from .sources import list_sources


class DashboardService:
    def __init__(self) -> None:
        self.supply = SupplyRepository()

    def coverage(self, *, race_date: str | None = None) -> dict[str, Any]:
        return get_coverage(race_date=race_date)

    def etl_status(self, *, race_date: str | None = None) -> dict[str, Any]:
        run = self.supply.latest_run(race_date)
        if not run:
            return {"status": "none", "message": "no ETL runs yet"}
        steps = self.supply.steps_for_run(int(run["id"]))
        d = dict(run)
        d["missing_data"] = json.loads(d.pop("missing_data_json") or "{}")
        d["result"] = json.loads(d.pop("result_json") or "{}")
        d["steps"] = steps
        return d

    def import_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.supply.list_import_history(limit=limit)

    def fallback_reasons(self) -> dict[str, Any]:
        _, meta = prediction_adapter.list_with_meta()
        items = meta.get("items") or []
        by_reason: dict[str, list[dict[str, Any]]] = {}
        for it in items:
            if it.get("engine_source") != "mock_fallback":
                continue
            reason = str(it.get("fallback_reason") or "unknown")
            by_reason.setdefault(reason, []).append(
                {
                    "race_id": it.get("race_id"),
                    "core_race_id": it.get("core_race_id"),
                    "detail": it.get("detail"),
                }
            )
        return {
            "total_mock": sum(len(v) for v in by_reason.values()),
            "by_reason": {k: {"count": len(v), "items": v[:50]} for k, v in by_reason.items()},
        }

    def missing_data(self) -> dict[str, Any]:
        _, meta = prediction_adapter.list_with_meta()
        items = meta.get("items") or []
        return collect_missing_report(items)

    def summary(self, *, race_date: str | None = None) -> dict[str, Any]:
        return {
            "coverage": self.coverage(race_date=race_date),
            "etl_status": self.etl_status(race_date=race_date),
            "sources": list_sources(),
            "import_history": self.import_history(limit=5),
            "fallback_reasons": self.fallback_reasons(),
            "missing_summary": self.missing_data().get("summary"),
        }
