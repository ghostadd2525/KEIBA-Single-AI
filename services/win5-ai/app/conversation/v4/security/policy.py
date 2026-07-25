# -*- coding: utf-8 -*-
"""
Security Policy — Personal Chat 情報漏洩防止（無効化不可）。

許可: 日常会話 / 相談 / 学習 / 雑談 / 一般知識
禁止: 内部システム・秘密情報の照会・開示要求
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# Security Guard は無効化できない
SECURITY_GUARD_ALWAYS_ON: Final[bool] = True

BLOCK_FIXED_MESSAGE: Final[str] = (
    "その内容にはお答えできません。"
    "内部の仕組みや秘密情報についてはお話しできないよ。"
    "日常の雑談や一般的な相談なら、どうぞ！"
)

ALLOWED_TOPICS: Final[tuple[str, ...]] = (
    "日常会話",
    "相談",
    "学習",
    "雑談",
    "一般知識",
)


@dataclass(frozen=True)
class SecurityPolicy:
    """Personal Chat 向け Security Policy（常時適用）。"""

    always_on: bool = True
    block_message: str = BLOCK_FIXED_MESSAGE
    allowed_topics: tuple[str, ...] = ALLOWED_TOPICS

    def is_enabled(self) -> bool:
        """無効化不可 — 常に True。"""
        return True


DEFAULT_SECURITY_POLICY = SecurityPolicy()
