# -*- coding: utf-8 -*-
"""V4 Conversation Feature Flags — 既定 OFF。"""
from __future__ import annotations

import os


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def conversation_enabled() -> bool:
    return _env_bool("F_V4_CONVERSATION_ENABLED", False)


def conversation_ollama_enabled() -> bool:
    """Ollama 呼び出し許可（Casual polish / Review 生成）。既定 OFF。"""
    return _env_bool("F_V4_CONVERSATION_OLLAMA", False)


def review_agent_enabled() -> bool:
    """Review Agent 有効。既定 OFF。"""
    return _env_bool("F_V4_REVIEW_AGENT", False)


def personal_chat_enabled() -> bool:
    """Personal Chat Agent（マイページ日常会話）有効。既定 OFF。"""
    return _env_bool("F_V4_PERSONAL_CHAT", False)


def tool_layer_enabled() -> bool:
    """Tool Layer（Tool Manager）有効。既定 OFF。"""
    return _env_bool("F_V4_TOOL_LAYER", False)


def knowledge_layer_enabled() -> bool:
    """Knowledge Layer（共通知識 RAG Foundation）有効。既定 OFF。"""
    return _env_bool("F_V4_KNOWLEDGE_LAYER", False)


def knowledge_integration_enabled() -> bool:
    """Knowledge Integration（Retriever / Adapter 配線）有効。既定 OFF。"""
    return _env_bool("F_V4_KNOWLEDGE_INTEGRATION", False)


def knowledge_runtime_enabled() -> bool:
    """V5 Knowledge Runtime（Retriever Runtime）有効。既定 OFF。"""
    return _env_bool("F_V5_KNOWLEDGE_RUNTIME", False)


def memory_enabled() -> bool:
    """V6 Memory Platform（Consent-only Long-term）有効。既定 OFF。"""
    return _env_bool("F_V6_MEMORY", False)


def v4_platform_active() -> bool:
    """Conversation Platform（Orchestrator）有効。Ollama Flag とは独立。"""
    return conversation_enabled()


def flag_snapshot() -> dict[str, bool]:
    return {
        "F_V4_CONVERSATION_ENABLED": conversation_enabled(),
        "F_V4_CONVERSATION_OLLAMA": conversation_ollama_enabled(),
        "F_V4_REVIEW_AGENT": review_agent_enabled(),
        "F_V4_PERSONAL_CHAT": personal_chat_enabled(),
        "F_V4_TOOL_LAYER": tool_layer_enabled(),
        "F_V4_KNOWLEDGE_LAYER": knowledge_layer_enabled(),
        "F_V4_KNOWLEDGE_INTEGRATION": knowledge_integration_enabled(),
        "F_V5_KNOWLEDGE_RUNTIME": knowledge_runtime_enabled(),
        "F_V6_MEMORY": memory_enabled(),
    }
