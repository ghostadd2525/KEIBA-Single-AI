# -*- coding: utf-8 -*-
"""
Consent Manager — 明示同意（「覚えて」等）の検出のみ。

同意なしの候補は保存しない。自動保存は禁止。
"""
from __future__ import annotations

import re
from typing import Any


# 明示的な保存許可フレーズ
_CONSENT_PATTERNS = (
    re.compile(r"覚えて(?:おいて|てください|下さい|てね|てよ|て)?", re.I),
    re.compile(r"記憶して(?:おいて|てください|下さい|てね|て)?", re.I),
    re.compile(r"メモして(?:おいて|てください|下さい|てね|て)?", re.I),
    re.compile(r"\bremember(?:\s+this|\s+that)?\b", re.I),
)

# 削除 · 一覧 · 全削除（同意フローとは別操作）
_FORGET_ONE = re.compile(
    r"(?:を)?(?:忘れて(?:ください|下さい|ね|よ)?|忘れろ|削除して(?:ください|下さい)?)",
    re.I,
)
_FORGET_ALL = re.compile(
    r"(?:全部|すべて|全て)(?:を)?(?:忘れて|忘れろ|削除して)|メモリー?(?:を)?全削除",
    re.I,
)
_LIST = re.compile(
    r"(?:私について)?(?:何を|なにを)?覚えて(?:る|いる|ますか|る\?|る？)|"
    r"記憶一覧|覚えていること|what\s+do\s+you\s+remember",
    re.I,
)


class ConsentManager:
    """User Consent 検出。"""

    version = "v6-phase2"

    def has_explicit_remember_consent(self, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        # 一覧・全削除は「覚えて」を含むが保存同意ではない
        if self.is_list_intent(text) or self.is_forget_all_intent(text):
            return False
        return any(p.search(text) for p in _CONSENT_PATTERNS)

    def is_forget_one_intent(self, message: str) -> bool:
        text = str(message or "").strip()
        if self.is_forget_all_intent(text):
            return False
        return bool(_FORGET_ONE.search(text))

    def is_forget_all_intent(self, message: str) -> bool:
        return bool(_FORGET_ALL.search(str(message or "")))

    def is_list_intent(self, message: str) -> bool:
        return bool(_LIST.search(str(message or "")))

    def classify_intent(self, message: str) -> str:
        """
        Returns: remember | forget_one | forget_all | list | none
        """
        text = str(message or "").strip()
        if not text:
            return "none"
        if self.is_forget_all_intent(text):
            return "forget_all"
        if self.is_list_intent(text):
            return "list"
        if self.is_forget_one_intent(text):
            return "forget_one"
        if self.has_explicit_remember_consent(text):
            return "remember"
        return "none"

    def meta(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "auto_save": False,
            "consent_required_for_write": True,
        }
