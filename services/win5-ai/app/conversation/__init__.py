# -*- coding: utf-8 -*-
from typing import Any

from .context import ContextManager, ConversationContext
from .intent import IntentClassifier, IntentParser, IntentResult
from .reason_builder import ReasonBuilder, ReasonPayload
from .service import ConversationService
from .service import chat as legacy_chat
from .tools import ConversationTools


def chat(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Conversation 入口。
    F_V4_CONVERSATION_ENABLED=ON → V4 Conversation Orchestrator
    OFF → 既存 ConversationService（互換）
    """
    from .v4.flags import v4_platform_active

    if v4_platform_active():
        from .v4 import chat as v4_chat

        return v4_chat(body if isinstance(body, dict) else {})
    return legacy_chat(body if isinstance(body, dict) else {})


__all__ = [
    "ConversationService",
    "ConversationContext",
    "ContextManager",
    "IntentParser",
    "IntentClassifier",
    "IntentResult",
    "ReasonBuilder",
    "ReasonPayload",
    "ConversationTools",
    "chat",
]
