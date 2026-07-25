# -*- coding: utf-8 -*-
"""Expert Tools — Stub only（Prediction API 実接続なし）。"""
from __future__ import annotations

from typing import Any


class ExpertToolStub:
    """
    Expert Agent が使う Tool 面。
    本最小構成ではすべて Stub。将来 Read-only Prediction 接続に差し替える。
    """

    connected_to_prediction_api = False

    def prediction_snapshot(self, race_id: str | None) -> dict[str, Any]:
        return {
            "tool": "prediction_snapshot",
            "stub": True,
            "race_id": race_id,
            "prediction_available": False,
            "engine_source": None,
            "message": "Prediction API は未接続（stub）。実データは取得していません。",
            "summary": None,
            "top_runners": [],
        }

    def explain_projection(self, race_id: str | None) -> dict[str, Any]:
        return {
            "tool": "explain_projection",
            "stub": True,
            "race_id": race_id,
            "available": False,
            "summary": "説明用の Prediction / explain データはまだ接続されていません。",
            "factor_lines": [],
        }

    def coverage(self) -> dict[str, Any]:
        return {
            "tool": "coverage",
            "stub": True,
            "race_total": None,
            "real_ai": None,
            "message": "カバレッジ Tool は stub です。",
        }

    def diagnostics(self) -> dict[str, Any]:
        return {
            "tool": "diagnostics",
            "stub": True,
            "summary": "診断 Tool は stub です。不足データの実集計は行いません。",
            "missing_tables": [],
        }

    def race_list(self) -> dict[str, Any]:
        return {
            "tool": "race_list",
            "stub": True,
            "races": [],
            "message": "レース一覧 Tool は stub です。",
        }

    def execute(self, intent: str, *, race_id: str | None = None) -> dict[str, Any]:
        if intent in ("explain_pick", "explain_confidence", "race_qa"):
            return {
                "intent": intent,
                "sources": ["stub:prediction_snapshot", "stub:explain_projection"],
                "prediction": self.prediction_snapshot(race_id),
                "explain": self.explain_projection(race_id),
            }
        if intent == "coverage_inquiry":
            return {
                "intent": intent,
                "sources": ["stub:coverage"],
                "coverage": self.coverage(),
            }
        if intent == "diagnostics_inquiry":
            return {
                "intent": intent,
                "sources": ["stub:diagnostics"],
                "diagnostics": self.diagnostics(),
            }
        if intent == "list_races":
            return {
                "intent": intent,
                "sources": ["stub:race_list"],
                "races": self.race_list(),
            }
        return {
            "intent": intent,
            "sources": ["stub:noop"],
            "note": "no stub tool for intent",
        }
