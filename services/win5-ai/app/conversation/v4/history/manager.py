# -*- coding: utf-8 -*-
"""
History Manager — セッション単位 Conversation History（メモリ FIFO · 非永続）。

Personal Chat / Review / Explain 共通。
Security Guard 通過後の内容のみ append すること（呼び出し側責務）。
"""
from __future__ import annotations

import os
import threading
from typing import Any

from .models import ConversationHistory, HistoryMessage, Role


def _default_max_messages() -> int:
    return int(os.environ.get("CONVERSATION_HISTORY_MAX_MESSAGES") or "20")


def _default_prompt_turns() -> int:
    return int(os.environ.get("CONVERSATION_HISTORY_PROMPT_TURNS") or "8")


class HistoryManager:
    """
    プロセス内メモリのみ。再起動で消える。DB / ディスク書き込みなし。
    """

    def __init__(
        self,
        *,
        max_messages: int | None = None,
        prompt_turns: int | None = None,
    ) -> None:
        self.max_messages = max_messages if max_messages is not None else _default_max_messages()
        self.prompt_turns = prompt_turns if prompt_turns is not None else _default_prompt_turns()
        self._sessions: dict[str, ConversationHistory] = {}
        self._lock = threading.RLock()

    def get_or_create(self, session_id: str) -> ConversationHistory:
        sid = str(session_id or "").strip() or "anonymous"
        with self._lock:
            hist = self._sessions.get(sid)
            if hist is None:
                hist = ConversationHistory(
                    session_id=sid,
                    messages=[],
                    max_messages=self.max_messages,
                )
                self._sessions[sid] = hist
            else:
                # 設定変更に追従
                hist.max_messages = self.max_messages
                hist._trim()
            return hist

    def append_user(self, session_id: str, content: str) -> ConversationHistory:
        return self._append(session_id, "user", content)

    def append_assistant(self, session_id: str, content: str) -> ConversationHistory:
        return self._append(session_id, "assistant", content)

    def _append(self, session_id: str, role: Role, content: str) -> ConversationHistory:
        with self._lock:
            hist = self.get_or_create(session_id)
            hist.append(role, content)
            return hist

    def prompt_history(self, session_id: str) -> list[dict[str, str]]:
        with self._lock:
            hist = self.get_or_create(session_id)
            return hist.for_prompt(max_turns=self.prompt_turns)

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(str(session_id), None)

    def snapshot(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            return self.get_or_create(session_id).to_dict()


# プロセス共有の既定マネージャ（永続化なし）
_default_manager: HistoryManager | None = None


def get_history_manager() -> HistoryManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = HistoryManager()
    return _default_manager


def reset_history_manager_for_tests() -> HistoryManager:
    """テスト用にメモリをリセット。"""
    global _default_manager
    _default_manager = HistoryManager()
    return _default_manager
