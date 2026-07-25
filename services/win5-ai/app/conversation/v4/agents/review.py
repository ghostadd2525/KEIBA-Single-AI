# -*- coding: utf-8 -*-
"""
Review Agent — Prediction 結果のレビュー文章のみ生成。

公開 API: review(context: ReviewContext) のみ。
個別 payload を直接受け取らない。
Flow: ReviewContext → Prompt Builder → Ollama
"""
from __future__ import annotations

import re
from typing import Any

from ..config import load_conversation_config, resolve_model
from ..context.review_context import ReviewContext
from ..flags import conversation_ollama_enabled, review_agent_enabled
from ..ollama_client import OllamaClient
from ..prompts.builder import PromptBuilder

_REWRITE_RE = re.compile(
    r"(本命を|印を|順位を|買い目を).{0,8}(変更|変え|差し替|修正)|"
    r"(別の本命|代わりに|おすすめは\d+番|私なら|買い目提案)",
    re.I,
)

_TEMPLATE_REVIEW = """## 予想の強み
Prediction AI の印・順位を前提にすると、軸候補の一貫性が読み取りやすいよ。

## リスク
展開や相手関係で着順が入れ替わる可能性は常にあるよ。数値の自信度もあわせて見てね。

## 展開の注目点
ペース配分と位置取りが、想定どおりか発走前後の気配で確認するのがポイントだよ。

## 初心者向けアドバイス
印や買い目は変えず、まずは Prediction の結果をレース画面で確認してから相談内容を深掘りしよう。
※ Review Agent は予測を変更しません。Prediction AI が唯一の正解です。
"""


class ReviewAgent:
    name = "review"

    def __init__(
        self,
        *,
        prompts: PromptBuilder | None = None,
        ollama: OllamaClient | None = None,
    ) -> None:
        self.prompts = prompts or PromptBuilder()
        self._ollama = ollama

    def review(self, context: ReviewContext) -> dict[str, Any]:
        """Review Agent の唯一の公開入口。ReviewContext のみ受け取る。"""
        if not isinstance(context, ReviewContext):
            raise TypeError("ReviewAgent.review requires ReviewContext")

        cfg = load_conversation_config()
        req = context.request or {}
        race_id = context.race_id

        if not review_agent_enabled():
            return {
                "agent": self.name,
                "mode": context.mode or "review",
                "intent": {
                    "name": "review_disabled",
                    "confidence": req.get("intent_confidence") or 0.0,
                    "race_id": race_id,
                    "slots": req.get("slots") or {},
                },
                "reply": "Review Agent は現在オフです（F_V4_REVIEW_AGENT）。",
                "citations": [],
                "actions": [],
                "tools_used": [],
                "prediction_meta": {
                    **(context.prediction_meta or {}),
                    "used": False,
                    "mutated": False,
                    "connected": False,
                    "source": "none",
                },
                "llm": {"used": False, "role": "review"},
                "fallback": "flag_off",
                "context_keys": list(context.to_dict().keys()),
            }

        prompt = self.prompts.build_review(context)
        reply, llm_meta, fallback = self._generate(prompt, cfg)
        reply = self._guard_output(reply)

        max_reply = int(cfg["limits"]["max_reply_chars"])
        if len(reply) > max_reply:
            reply = reply[:max_reply]

        actions: list[dict[str, Any]] = []
        if race_id:
            actions.append({"type": "open_race", "race_id": race_id})

        # prediction_meta は Context 由来を維持し、mutated は常に false
        meta = dict(context.prediction_meta or {})
        meta["mutated"] = False
        meta["connected"] = False

        pred = context.prediction
        return {
            "agent": self.name,
            "mode": context.mode or "review",
            "intent": {
                "name": req.get("intent") or "review_prediction",
                "confidence": req.get("intent_confidence") or 0.0,
                "race_id": race_id,
                "slots": {
                    **(req.get("slots") or {}),
                    "review_rules": "no_mutate_prediction",
                    "input": "ReviewContext",
                },
            },
            "reply": reply,
            "citations": [
                {
                    "type": "prediction_readonly",
                    "race_id": race_id,
                    "engine_source": meta.get("engine_source")
                    or ((pred or {}).get("engine_source") if pred else None),
                }
            ]
            if pred
            else [],
            "actions": actions,
            "tools_used": [],
            "prompt_kind": prompt.get("kind"),
            "prediction_meta": meta,
            "llm": llm_meta,
            "fallback": fallback,
            "review_sections": ["strengths", "risks", "pace_focus", "beginner_advice"],
            "context_keys": list(context.to_dict().keys()),
            "history_used": len(context.history or []),
        }

    def _generate(
        self, prompt: dict[str, str], cfg: dict[str, Any]
    ) -> tuple[str, dict[str, Any], str | None]:
        model = resolve_model(None)
        if not conversation_ollama_enabled():
            return _TEMPLATE_REVIEW, {"used": False, "role": "review_template"}, "template_no_ollama_flag"

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
                {"used": True, "role": "review", "model": result.model or model, "provider": "ollama"},
                None,
            )
        return (
            _TEMPLATE_REVIEW,
            {"used": False, "role": "review_fail_open", "model": model},
            result.error_reason or "ollama_error",
        )

    def _guard_output(self, reply: str) -> str:
        text = str(reply or "").strip() or _TEMPLATE_REVIEW
        if _REWRITE_RE.search(text):
            return (
                _TEMPLATE_REVIEW
                + "\n\n（出力ガード: 順位・印・買い目の変更表現を検出し、レビュー定型に差し替えました。）"
            )
        return text
