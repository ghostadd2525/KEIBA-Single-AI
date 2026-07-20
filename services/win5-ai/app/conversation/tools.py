# -*- coding: utf-8 -*-
"""Conversation Tools — Prediction / Coverage / Diagnostics 等を統合取得。"""
from __future__ import annotations

from typing import Any

from ..data.coverage import get_coverage
from ..data.dashboard import DashboardService
from ..diagnostics.missing_collector import collect_missing_report
from ..engine import data as engine_data
from ..engine.adapters import prediction_adapter


class ConversationTools:
    """Intent に応じたデータ取得。Prediction 以外もここ経由。"""

    def fetch_prediction(self, race_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        return prediction_adapter.get_with_meta(race_id)

    def fetch_coverage(self) -> dict[str, Any]:
        return get_coverage(use_cache=False)

    def fetch_diagnostics(self) -> dict[str, Any]:
        _, meta = prediction_adapter.list_with_meta()
        items = meta.get("items") or []
        report = collect_missing_report(items)
        return {
            "summary": report.get("summary"),
            "missing_tables": report.get("missing_tables"),
            "how_to_reach_real_ai": (report.get("how_to_reach_real_ai") or [])[:5],
            "by_reason_counts": (report.get("summary") or {}).get("by_reason"),
        }

    def fetch_race_list(self, *, date: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
        catalog = engine_data.load_races()
        races = list(catalog.get("races") or [])
        if date:
            races = [r for r in races if r.get("date") == date]
        return races[:limit]

    def fetch_fallback_summary(self) -> dict[str, Any]:
        return DashboardService().fallback_reasons()

    def execute(self, intent: str, *, race_id: str | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {"intent": intent, "sources": []}

        if intent in ("predict_race", "explain_pick", "find_upset", "buy_advice", "follow_up"):
            if race_id:
                bundle, meta = self.fetch_prediction(race_id)
                out["prediction"] = {"bundle": bundle, "meta": meta}
                out["sources"].append("prediction")
            return out

        if intent == "coverage_inquiry":
            out["coverage"] = self.fetch_coverage()
            out["sources"].append("coverage")
            return out

        if intent == "diagnostics_inquiry":
            out["diagnostics"] = self.fetch_diagnostics()
            out["fallback"] = self.fetch_fallback_summary()
            out["sources"].extend(["diagnostics", "fallback"])
            return out

        if intent == "list_races":
            out["races"] = self.fetch_race_list()
            out["sources"].append("catalog")
            return out

        if intent == "greeting":
            out["help"] = {
                "capabilities": [
                    "レース予想（例: 今日の福島11Rを予想して）",
                    "選定理由・穴馬・買い目アドバイス",
                    "データカバレッジ / 不足診断の確認",
                    "複数ターン会話（このレース / さっきの続き）",
                ]
            }
            out["sources"].append("help")
            return out

        return out
