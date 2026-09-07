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

    F_V6_MEMORY=ON 時のみ Memory Gateway を入口前段に接続する。
    （V4 Orchestrator / History / Tool Manager / Agents は変更しない）
    """
    from .v4.flags import memory_enabled, v4_platform_active

    raw = body if isinstance(body, dict) else {}

    if memory_enabled():
        from .v6.memory.gateway import get_memory_gateway

        gateway = get_memory_gateway()
        handled = gateway.maybe_handle(raw)
        if handled is not None:
            return handled
        raw = gateway.enrich_body(raw)

    if v4_platform_active():
        from .v4 import chat as v4_chat

        response = v4_chat(raw)
        if memory_enabled():
            from .v6.memory.gateway import get_memory_gateway

            return get_memory_gateway().attach_meta(response, raw)
        return response
    return legacy_chat(raw)


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
