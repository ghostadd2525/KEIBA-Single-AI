# -*- coding: utf-8 -*-
"""
Chat Agent — マイページ専用の日常会話 AI。

KAOBA / Review / Explain / Prediction とは独立。
公開: chat(message) → Security Guard → Chat Prompt → Ollama
Security Guard 通過前に Ollama は呼ばない。
"""
from __future__ import annotations

from typing import Any

from ..config import load_conversation_config, resolve_model
from ..flags import conversation_ollama_enabled, personal_chat_enabled
from ..intent_router import RoutedIntent
from ..ollama_client import OllamaClient
from ..prompts.builder import PromptBuilder
from ..security import SecurityGuard

_TEMPLATE_CHAT = (
    "こんにちは。マイページの日常会話パートナーだよ。"
    "競馬の予想や印の話ではなく、気軽な会話ならなんでもどうぞ。"
    "（※ Personal Chat · KAOBA / Prediction とは別系統です）"
)


class ChatAgent:
    """Personal Chat Agent（KAOBA 非依存）。"""

    name = "chat"

    def __init__(
        self,
        *,
        prompts: PromptBuilder | None = None,
        ollama: OllamaClient | None = None,
        security_guard: SecurityGuard | None = None,
    ) -> None:
        self.prompts = prompts or PromptBuilder()
        self._ollama = ollama
        self.security_guard = security_guard or SecurityGuard()

    def chat(
        self,
        message: str,
        routed: RoutedIntent | None = None,
        *,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        cfg = load_conversation_config()
        routed = routed or RoutedIntent(
            name="chat",
            agent="chat",
            confidence=1.0,
            mode="chat",
        )

        if not personal_chat_enabled():
            return {
                "agent": self.name,
                "mode": "chat",
                "intent": {
                    "name": "chat_disabled",
                    "confidence": routed.confidence,
                    "race_id": None,
                    "slots": {},
                },
                "reply": "Personal Chat は現在オフです（F_V4_PERSONAL_CHAT）。",
                "citations": [],
                "actions": [],
                "tools_used": [],
                "prediction_meta": None,
                "llm": {"used": False, "role": "personal_chat", "ollama_called": False},
                "fallback": "flag_off",
                "kaoba_independent": True,
            }

        text = str(message or "").strip() or "こんにちは"

        # Ollama 呼び出し前に必ず Security Guard（無効化不可）
        guard = self.security_guard.check(text)
        if guard.blocked:
            return self.security_guard.block_response(guard=guard)

        prompt = self.prompts.build_chat(message=text, history=history)
        reply, llm_meta, fallback = self._generate(prompt, cfg)

        max_reply = int(cfg["limits"]["max_reply_chars"])
        if len(reply) > max_reply:
            reply = reply[:max_reply]

        return {
            "agent": self.name,
            "mode": "chat",
            "intent": {
                "name": "chat",
                "confidence": routed.confidence,
                "race_id": None,
                "slots": {**(routed.slots or {}), "domain": "personal_chat"},
            },
            "reply": reply,
            "citations": [],
            "actions": [{"type": "mypage_chat"}],
            "tools_used": [],
            "prompt_kind": prompt.get("kind"),
            "prediction_meta": None,
            "llm": llm_meta,
            "fallback": fallback,
            "blocked": False,
            "security": guard.to_dict(),
            "history_used": len(history or []),
            "kaoba_independent": True,
            "involves_prediction": False,
            "involves_review": False,
            "involves_explain": False,
        }

    def _generate(
        self, prompt: dict[str, str], cfg: dict[str, Any]
    ) -> tuple[str, dict[str, Any], str | None]:
        model = resolve_model(None)
        if not conversation_ollama_enabled():
            return (
                _TEMPLATE_CHAT,
                {"used": False, "role": "personal_chat_template", "ollama_called": False},
                "template_no_ollama_flag",
            )

        client = self._ollama or OllamaClient(
            base_url=cfg["ollama"]["base_url"],
            timeout_ms=int(cfg["ollama"]["timeout_ms"]),
            chat_path=cfg["ollama"]["chat_path"],
            tags_path=cfg["ollama"]["tags_path"],
        )
        combined = f"{prompt['system']}\n\n{prompt['user']}"
        result = client.chat(model=model, message=combined)
        if result.ok and result.reply:
            return (
                result.reply,
                {
                    "used": True,
                    "role": "personal_chat",
                    "model": result.model or model,
                    "provider": "ollama",
                    "ollama_called": True,
                },
                None,
            )
        return (
            _TEMPLATE_CHAT,
            {
                "used": False,
                "role": "personal_chat_fail_open",
                "model": model,
                "ollama_called": True,
            },
            result.error_reason or "ollama_error",
        )
