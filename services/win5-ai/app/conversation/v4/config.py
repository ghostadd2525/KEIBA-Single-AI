# -*- coding: utf-8 -*-
"""V4 Conversation Platform 設定（最小）。"""
from __future__ import annotations

import os
from typing import Any


_DEFAULT_FAIL_OPEN = (
    "いま対話エンジンに接続できないよ。"
    "レース画面の AI 予測はそのまま見られるから、先にそちらを確認してみてね。"
)

_DEFAULT_DISABLED = (
    "Conversation Platform は現在オフです（F_V4_CONVERSATION_ENABLED）。"
)


def load_conversation_config() -> dict[str, Any]:
    return {
        "disabled_message": os.environ.get("CONVERSATION_DISABLED_MESSAGE") or _DEFAULT_DISABLED,
        "fail_open": {
            "enabled": (os.environ.get("CONVERSATION_FAIL_OPEN") or "true").lower()
            in ("1", "true", "yes", "on"),
            "message": os.environ.get("CONVERSATION_FAIL_OPEN_MESSAGE") or _DEFAULT_FAIL_OPEN,
        },
        "limits": {
            "max_message_chars": int(os.environ.get("CONVERSATION_MAX_MESSAGE_CHARS") or "2000"),
            "max_reply_chars": int(os.environ.get("CONVERSATION_MAX_REPLY_CHARS") or "1200"),
        },
        "history": {
            "max_messages": int(os.environ.get("CONVERSATION_HISTORY_MAX_MESSAGES") or "20"),
            "prompt_turns": int(os.environ.get("CONVERSATION_HISTORY_PROMPT_TURNS") or "8"),
            "persistent": False,
        },
        "ollama": {
            "base_url": os.environ.get("CONVERSATION_OLLAMA_BASE_URL")
            or "http://127.0.0.1:11434",
            "timeout_ms": int(os.environ.get("CONVERSATION_OLLAMA_TIMEOUT_MS") or "12000"),
            "default_model": os.environ.get("CONVERSATION_DEFAULT_MODEL") or "qwen3:8b",
            "chat_path": "/api/chat",
            "tags_path": "/api/tags",
        },
        "platform": {
            "prediction_api_connected": False,  # Hard: 本最小構成では接続しない
            "expert_tools": "stub",
        },
    }


def resolve_model(requested: str | None = None) -> str:
    cfg = load_conversation_config()
    allow = {
        "qwen3:8b",
        "gemma3:12b",
        "qwen2.5:1.5b",
        "qwen2.5:0.5b",
        "qwen2.5:3b",
        "tinyllama",
        cfg["ollama"]["default_model"],
    }
    if requested and requested in allow:
        return requested
    return str(cfg["ollama"]["default_model"])
