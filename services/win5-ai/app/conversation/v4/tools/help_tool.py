# -*- coding: utf-8 -*-
"""Help Tool — FAQ / ヘルプ Stub。"""
from __future__ import annotations

from typing import Any

from .base import ToolResult

_FAQ = (
    {
        "q": "KAOBAとは？",
        "a": "Expect ～ KEIBA AI ～ の会話アシスタントだよ。予想の作成・変更はしないよ。",
    },
    {
        "q": "予想は変えられる？",
        "a": "いいえ。Prediction AI が唯一の公式結果で、Conversation は説明・相談のみ。",
    },
    {
        "q": "◎の理由を聞くには？",
        "a": "レース画面の「KAOBAに◎の理由を聞く」（Explain Mode）を使ってね。",
    },
)


class HelpTool:
    name = "help"
    read_only = True
    stub = True

    def invoke(self, **kwargs: Any) -> ToolResult:
        query = str(kwargs.get("query") or kwargs.get("message") or "").strip()
        return ToolResult(
            ok=True,
            tool=self.name,
            data={
                "stub": True,
                "connected": False,
                "query": query or None,
                "faq": list(_FAQ),
                "message": "Help Tool は stub です。FAQ 固定応答のみ。",
            },
            stub=True,
            read_only=True,
            mutated=False,
        )
