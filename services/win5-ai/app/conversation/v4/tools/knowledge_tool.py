# -*- coding: utf-8 -*-
"""
Knowledge Tool — 共通知識検索。

Tool Manager からのみ呼び出すこと。
Agent が Knowledge Provider を直接呼ぶことは禁止。
"""
from __future__ import annotations

from typing import Any

from ..flags import knowledge_layer_enabled
from ..knowledge import KnowledgeProvider
from .base import ToolResult


class KnowledgeTool:
    name = "knowledge"
    read_only = True
    stub = True

    def __init__(self, provider: KnowledgeProvider | None = None) -> None:
        self.provider = provider or KnowledgeProvider()

    def invoke(self, **kwargs: Any) -> ToolResult:
        if not knowledge_layer_enabled():
            return ToolResult(
                ok=False,
                tool=self.name,
                data={
                    "stub": True,
                    "enabled": False,
                    "flag": "F_V4_KNOWLEDGE_LAYER",
                    "message": "Knowledge Layer はオフです（F_V4_KNOWLEDGE_LAYER）。",
                },
                error="knowledge_layer_disabled",
                stub=True,
                read_only=True,
                mutated=False,
            )

        query = kwargs.get("query") or kwargs.get("message") or kwargs.get("q")
        category = kwargs.get("category")
        limit = kwargs.get("limit", 5)
        payload = self.provider.search(
            str(query) if query is not None else None,
            category=str(category) if category else None,
            limit=int(limit) if limit is not None else 5,
        )
        # 不変条件の明示
        payload["via"] = "knowledge_tool"
        payload["enabled"] = True
        payload["user_private"] = False
        payload["prediction_rationale"] = False
        return ToolResult(
            ok=True,
            tool=self.name,
            data=payload,
            stub=True,
            read_only=True,
            mutated=False,
        )
