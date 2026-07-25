# -*- coding: utf-8 -*-
"""
Prediction Tool — Prediction API Read Only。

Conversation は Prediction を変更しない。mutated は常に false。
"""
from __future__ import annotations

from typing import Any

from ..prediction import ConversationPredictionAdapter, PredictionConnector
from .base import ToolResult


class PredictionTool:
    name = "prediction"
    read_only = True
    stub = False

    def __init__(
        self,
        *,
        connector: PredictionConnector | None = None,
        adapter: ConversationPredictionAdapter | None = None,
    ) -> None:
        self.connector = connector or PredictionConnector()
        self.adapter = adapter or ConversationPredictionAdapter()

    def invoke(self, **kwargs: Any) -> ToolResult:
        race_id = kwargs.get("race_id")
        rid = str(race_id).strip() if race_id else None
        fetch = self.connector.fetch(rid)
        official, meta = self.adapter.adapt(fetch)
        meta["mutated"] = False
        meta["via"] = "prediction_tool"
        return ToolResult(
            ok=bool(fetch.ok and official),
            tool=self.name,
            data={
                "official_prediction": official,
                "prediction_meta": meta,
                "fetch_error": fetch.error,
                "race_id": rid,
            },
            error=None if (fetch.ok and official) else (fetch.error or "prediction_unavailable"),
            stub=False,
            read_only=True,
            mutated=False,
        )
