# -*- coding: utf-8 -*-
"""
V6 Phase 2 — Memory Platform（Long-term · Consent-only）.

Conversation History / Knowledge / Prediction / Security とは完全分離。
Tool Manager には登録しない（ADR-005: Knowledge Edge の非責務 = ユーザー Memory）。
"""
from __future__ import annotations

from .consent import ConsentManager
from .gateway import MemoryGateway, get_memory_gateway
from .manager import MemoryManager, get_memory_manager
from .policy import MemoryPolicy
from .retriever import MemoryRetriever
from .store import MemoryStore, get_memory_store
from .tool import MemoryTool

__all__ = [
    "ConsentManager",
    "MemoryGateway",
    "MemoryManager",
    "MemoryPolicy",
    "MemoryRetriever",
    "MemoryStore",
    "MemoryTool",
    "get_memory_gateway",
    "get_memory_manager",
    "get_memory_store",
]
