# -*- coding: utf-8 -*-
"""
Conversation History — セッション単位の短期履歴（非永続）。

User / Assistant メッセージのみ。FIFO。Database 禁止。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

Role = Literal["user", "assistant"]


@dataclass
class HistoryMessage:
    role: Role
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class ConversationHistory:
    """1 セッション分の短期履歴（メモリのみ）。"""

    session_id: str
    messages: list[HistoryMessage]
    max_messages: int

    def __post_init__(self) -> None:
        if self.messages is None:
            self.messages = []
        self._trim()

    def append(self, role: Role, content: str) -> None:
        text = str(content or "").strip()
        if not text:
            return
        if role not in ("user", "assistant"):
            raise ValueError("role must be user or assistant")
        self.messages.append(HistoryMessage(role=role, content=text))
        self._trim()

    def _trim(self) -> None:
        max_n = max(1, int(self.max_messages))
        if len(self.messages) > max_n:
            self.messages = self.messages[-max_n:]

    def for_prompt(self, *, max_turns: int | None = None) -> list[dict[str, str]]:
        """Prompt に載せる必要最小限の履歴（直近）。"""
        limit = max_turns if max_turns is not None else self.max_messages
        limit = max(0, int(limit))
        if limit <= 0:
            return []
        return [m.to_dict() for m in self.messages[-limit:]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "max_messages": self.max_messages,
            "count": len(self.messages),
            "messages": [m.to_dict() for m in self.messages],
            "persistent": False,
        }
