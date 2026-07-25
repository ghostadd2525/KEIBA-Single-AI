# -*- coding: utf-8 -*-
"""
V4 Conversation Service facade.

実装本体は ConversationOrchestrator。
後方互換のため service.chat / health を公開する。
"""
from __future__ import annotations

from typing import Any

from .orchestrator import ConversationOrchestrator, chat, health

# 旧 Phase2 直呼び互換名
ConversationV4Service = ConversationOrchestrator

__all__ = [
    "ConversationOrchestrator",
    "ConversationV4Service",
    "chat",
    "health",
]


def get_service() -> ConversationOrchestrator:
    from .orchestrator import _orchestrator

    return _orchestrator


def chat_body(body: dict[str, Any] | None) -> dict[str, Any]:
    return chat(body)
