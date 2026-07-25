# -*- coding: utf-8 -*-
"""
V4 Conversation Platform — minimal package.

Conversation API = Conversation Orchestrator（Ollama Wrapper ではない）
  Intent Router → Casual Agent | Expert Agent
Expert Tools は Stub。Prediction API 実接続なし。
"""
from .orchestrator import ConversationOrchestrator, chat, health

__all__ = [
    "ConversationOrchestrator",
    "chat",
    "health",
]
