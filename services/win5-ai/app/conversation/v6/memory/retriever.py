# -*- coding: utf-8 -*-
"""Memory Retriever — Store から Conversation Context 用の要約を返す。"""
from __future__ import annotations

from typing import Any

from .models import MemoryRecord
from .store import MemoryStore, get_memory_store


class MemoryRetriever:
    """Long-term Memory の読み出し専用。History / Knowledge は参照しない。"""

    version = "v6-phase2"

    def __init__(self, store: MemoryStore | None = None) -> None:
        self.store = store or get_memory_store()

    def retrieve(self, user_id: str, *, limit: int = 20) -> list[MemoryRecord]:
        records = self.store.list(user_id)
        return records[: max(1, int(limit))]

    def as_context_block(self, user_id: str, *, limit: int = 12) -> str:
        records = self.retrieve(user_id, limit=limit)
        if not records:
            return ""
        lines = ["[User Memory — consented long-term only]"]
        for r in records:
            lines.append(f"- ({r.category}) {r.key}: {r.value}")
        return "\n".join(lines)

    def as_dict(self, user_id: str, *, limit: int = 20) -> dict[str, Any]:
        records = self.retrieve(user_id, limit=limit)
        return {
            "ok": True,
            "user_id": user_id,
            "count": len(records),
            "memories": [r.to_dict() for r in records],
            "retriever": self.version,
            "source": "memory_store",
            "history": False,
            "knowledge": False,
        }
