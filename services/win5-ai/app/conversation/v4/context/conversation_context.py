# -*- coding: utf-8 -*-
"""
ConversationContext (V4) — セッション文脈 + Conversation History 紐付け。

Personal Chat / Review / Explain 共通。履歴は短期・非永続。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..history.manager import HistoryManager, get_history_manager
from ..history.models import ConversationHistory


@dataclass
class ConversationContext:
    session_id: str
    mode: str | None = None
    turn: int = 0
    last_intent: str | None = None
    last_agent: str | None = None
    race_id: str | None = None
    # HistoryManager 経由の参照（永続しない）
    _history_manager: HistoryManager | None = field(default=None, repr=False, compare=False)

    def history_manager(self) -> HistoryManager:
        return self._history_manager or get_history_manager()

    def history(self) -> ConversationHistory:
        return self.history_manager().get_or_create(self.session_id)

    def prompt_history(self) -> list[dict[str, str]]:
        return self.history_manager().prompt_history(self.session_id)

    def append_user(self, content: str) -> None:
        self.history_manager().append_user(self.session_id, content)
        self.turn = len(self.history().messages)

    def append_assistant(self, content: str) -> None:
        self.history_manager().append_assistant(self.session_id, content)
        self.turn = len(self.history().messages)

    def as_meta(self) -> dict[str, Any]:
        hist = self.history()
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "turn": self.turn or len(hist.messages),
            "last_intent": self.last_intent,
            "last_agent": self.last_agent,
            "race_id": self.race_id,
            "history_count": len(hist.messages),
            "history_persistent": False,
        }
