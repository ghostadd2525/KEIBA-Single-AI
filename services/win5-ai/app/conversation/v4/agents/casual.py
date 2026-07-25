# -*- coding: utf-8 -*-
"""
Casual Agent — 挨拶・ガイド・予測生成拒否・明確化。

Prediction / Expert Tool は呼ばない。
任意で Ollama による言い換えを使えるが、必須ではない（Platform 最小構成はテンプレ応答）。
"""
from __future__ import annotations

from typing import Any

from ..config import load_conversation_config
from ..flags import conversation_ollama_enabled
from ..intent_router import RoutedIntent


class CasualAgent:
    name = "casual"

    def __init__(self, ollama_client: Any | None = None) -> None:
        self._ollama = ollama_client

    def handle(self, message: str, routed: RoutedIntent) -> dict[str, Any]:
        cfg = load_conversation_config()
        intent = routed.name

        if intent == "greeting":
            reply = (
                "こんにちは！KAOBA だよ。"
                "使い方の案内や、レース画面の見方をガイドできるよ。"
                "予想そのものは Prediction AI が担当するから、ここでは説明と案内をするね。"
            )
        elif intent == "app_guide":
            reply = (
                "できること:\n"
                "・アプリの使い方ガイド\n"
                "・レース / 予測結果の見方の案内（Expert・現状 stub）\n"
                "・「なぜ？」などの説明リクエストの受付\n"
                "できないこと:\n"
                "・新しい本命・買い目の生成（Prediction AI の領域）"
            )
        elif intent == "refuse_predict":
            reply = (
                "新しい予想や本命は、ここでは作れないよ。"
                "Prediction AI の結果はレース画面で確認してね。"
                "『なぜその馬？』『信頼度は？』なら説明の担当に回せるよ。"
            )
            actions = [{"type": "open_race", "race_id": routed.race_id}] if routed.race_id else [
                {"type": "open_races"}
            ]
            return self._pack(intent, reply, routed, actions=actions, used_llm=False)

        elif intent == "unknown":
            reply = (
                "もう少し具体的に聞いてくれると助かるよ。"
                "例:「使い方」「なぜ軸？」「カバレッジは？」"
            )
        else:
            reply = "案内モードで受け取ったよ。使い方や画面の見方を聞いてね。"

        used_llm = False
        if conversation_ollama_enabled() and self._ollama is not None and intent in (
            "greeting",
            "app_guide",
            "unknown",
        ):
            try:
                enriched = self._maybe_ollama(message, reply)
                if enriched:
                    reply = enriched
                    used_llm = True
            except Exception:
                pass

        max_reply = int(cfg["limits"]["max_reply_chars"])
        if len(reply) > max_reply:
            reply = reply[:max_reply]

        return self._pack(intent, reply, routed, actions=[{"type": "help"}], used_llm=used_llm)

    def _maybe_ollama(self, user_message: str, draft: str) -> str | None:
        """テンプレを壊さない範囲の言い換え。失敗したら None。"""
        prompt = (
            "次の下書きを、競馬アプリの案内アシスタントとして自然な日本語に整えて。"
            "新しい予想は追加しない。下書きの意味は変えない。\n\n"
            f"ユーザー: {user_message}\n下書き: {draft}"
        )
        result = self._ollama.chat(
            model=load_conversation_config()["ollama"]["default_model"],
            message=prompt,
        )
        if getattr(result, "ok", False) and getattr(result, "reply", None):
            return str(result.reply).strip()
        return None

    def _pack(
        self,
        intent: str,
        reply: str,
        routed: RoutedIntent,
        *,
        actions: list[dict[str, Any]],
        used_llm: bool,
    ) -> dict[str, Any]:
        return {
            "agent": self.name,
            "intent": {
                "name": intent,
                "confidence": routed.confidence,
                "race_id": routed.race_id,
                "slots": routed.slots,
            },
            "reply": reply,
            "citations": [],
            "actions": actions,
            "tools_used": [],
            "prediction_meta": {
                "used": False,
                "prediction_available": False,
                "connected": False,
                "stub": True,
            },
            "llm": {"used": used_llm, "role": "casual_optional_polish"},
        }
