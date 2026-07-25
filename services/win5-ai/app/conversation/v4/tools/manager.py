# -*- coding: utf-8 -*-
"""
Tool Manager — Conversation Agent が利用する唯一の Tool 入口。

個別 Tool の直接呼び出しは禁止。Capability 一覧を保持し、選択・実行する。
前提: 呼び出し前に Security Guard を通過済み（Guard 自体は変更しない）。
"""
from __future__ import annotations

from typing import Any

from .base import Tool, ToolCapability, ToolResult
from .capabilities import (
    DEFAULT_CAPABILITIES,
    capability_catalog,
    select_tool_names,
)
from .help_tool import HelpTool
from .knowledge_tool import KnowledgeTool
from .prediction_tool import PredictionTool
from .race_info_tool import RaceInfoTool
from .statistics_tool import StatisticsTool


class ToolManager:
    """Agent ↔ Tools の単一窓口。"""

    def __init__(
        self,
        *,
        tools: dict[str, Tool] | None = None,
        capabilities: tuple[ToolCapability, ...] | None = None,
        prediction_tool: PredictionTool | None = None,
        knowledge_tool: KnowledgeTool | None = None,
    ) -> None:
        pred = prediction_tool or PredictionTool()
        knowledge = knowledge_tool or KnowledgeTool()
        default_tools: dict[str, Tool] = {
            "prediction": pred,
            "race_info": RaceInfoTool(),
            "statistics": StatisticsTool(),
            "help": HelpTool(),
            "knowledge": knowledge,
        }
        if tools:
            default_tools.update(tools)
        self._tools = default_tools
        self._capabilities = capabilities or DEFAULT_CAPABILITIES

    def capabilities(self) -> list[dict[str, object]]:
        """利用可能 Tool 一覧（Capability）。"""
        names = set(self._tools.keys())
        return [c for c in capability_catalog() if c["name"] in names]

    def list_tool_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def select(
        self,
        *,
        mode: str | None = None,
        intent: str | None = None,
        prefer_prediction: bool = False,
    ) -> list[str]:
        """Capability を参照して Tool 名を選択する。"""
        names = select_tool_names(
            mode=mode, intent=intent, prefer_prediction=prefer_prediction
        )
        return [n for n in names if n in self._tools]

    def call(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """名前付き Tool を実行（個別 Tool を Agent から直接触らせない）。"""
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(
                ok=False,
                tool=tool_name,
                error="tool_not_found",
                stub=False,
                read_only=True,
                mutated=False,
            )
        result = tool.invoke(**kwargs)
        if tool_name == "prediction":
            result.mutated = False
            meta = result.data.get("prediction_meta")
            if isinstance(meta, dict):
                meta["mutated"] = False
        return result

    def call_selected(
        self,
        *,
        mode: str | None = None,
        intent: str | None = None,
        prefer_prediction: bool = False,
        **kwargs: Any,
    ) -> dict[str, ToolResult]:
        """Capability 選択 → 一括実行。"""
        selected = self.select(
            mode=mode, intent=intent, prefer_prediction=prefer_prediction
        )
        return {name: self.call(name, **kwargs) for name in selected}

    def get_official_prediction(
        self, race_id: str | None
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """
        Review / Explain 用: Prediction Tool 経由で Official Prediction を取得。
        Agent 経路は Tool Manager のみ（個別 Tool 直接呼び出し禁止）。
        """
        result = self.call("prediction", race_id=race_id)
        data = result.data or {}
        official = data.get("official_prediction")
        meta = (
            dict(data["prediction_meta"])
            if isinstance(data.get("prediction_meta"), dict)
            else {}
        )
        meta["mutated"] = False
        meta["tool_layer"] = True
        meta["via"] = "tool_manager"
        if not result.ok:
            meta.setdefault("fail_open", True)
            meta.setdefault("connected", False)
            meta.setdefault("error", result.error)
        return (
            official if isinstance(official, dict) else None,
            meta,
        )

    def search_knowledge(
        self,
        query: str | None = None,
        *,
        category: str | None = None,
        limit: int = 5,
    ) -> ToolResult:
        """
        共通知識検索 — Tool Manager 経由のみ。
        Agent が Provider を直接呼ぶことは禁止。
        """
        return self.call(
            "knowledge",
            query=query,
            category=category,
            limit=limit,
        )


_default_manager: ToolManager | None = None


def get_tool_manager() -> ToolManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = ToolManager()
    return _default_manager


def reset_tool_manager_for_tests() -> None:
    global _default_manager
    _default_manager = None
