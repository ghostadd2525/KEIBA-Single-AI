# -*- coding: utf-8 -*-
"""
Memory Tool — ユーザー操作の実行面。

Tool Manager / Capability には登録しない（V4 Platform 非侵食）。
Memory Manager への薄いファサード。
"""
from __future__ import annotations

from typing import Any

from .consent import ConsentManager
from .manager import MemoryManager, get_memory_manager


class MemoryTool:
    """覚えて / 忘れて / 一覧 / 全削除。"""

    name = "memory"
    version = "v6-phase2"
    registered_in_tool_manager = False

    def __init__(self, manager: MemoryManager | None = None) -> None:
        self.manager = manager or get_memory_manager()
        self.consent = self.manager.consent

    def dispatch(self, user_id: str, message: str) -> dict[str, Any] | None:
        """
        Memory 操作なら結果 dict、対象外なら None。
        """
        intent = self.consent.classify_intent(message)
        if intent == "none":
            return None
        if intent == "remember":
            return self.remember(user_id, message)
        if intent == "forget_one":
            return self.forget(user_id, message)
        if intent == "forget_all":
            return self.forget_all(user_id)
        if intent == "list":
            return self.list(user_id)
        return None

    def remember(self, user_id: str, message: str) -> dict[str, Any]:
        return self.manager.remember(user_id, message)

    def forget(self, user_id: str, message: str) -> dict[str, Any]:
        return self.manager.forget(user_id, message)

    def forget_all(self, user_id: str) -> dict[str, Any]:
        return self.manager.forget_all(user_id)

    def list(self, user_id: str) -> dict[str, Any]:
        return self.manager.list_memories(user_id)

    def meta(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "registered_in_tool_manager": self.registered_in_tool_manager,
            "auto_save": False,
        }
