# -*- coding: utf-8 -*-
"""Intent 分類 — 自然言語からユーザー意図を構造化。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..data.race_resolver import RaceIdentity
from .context import ConversationContext


@dataclass
class IntentResult:
    intent: str
    race_id: str | None = None
    confidence: float = 0.0
    identity: RaceIdentity | None = None
    slots: dict[str, Any] = field(default_factory=dict)


_INTENT_RULES: list[tuple[str, tuple[str, ...], float]] = [
    ("greeting", ("こんにちは", "hello", "ヘルプ", "help", "使い方", "何ができる"), 0.9),
    (
        "coverage_inquiry",
        ("カバレッジ", "coverage", "real_ai", "データ状況", "何レース対応", "対応率"),
        0.88,
    ),
    (
        "diagnostics_inquiry",
        ("不足", "missing", "フォールバック", "mock", "なぜダミー", "データ欠", "診断"),
        0.88,
    ),
    ("list_races", ("レース一覧", "開催", "今日のレース", "レース教えて"), 0.85),
    ("explain_pick", ("理由", "なぜ", "根拠", "why", "どうして"), 0.9),
    ("find_upset", ("穴", "大穴", "穴馬", "狙い目"), 0.88),
    ("buy_advice", ("買い", "買う", "見送", "評価して", "馬券", "投資"), 0.85),
    ("predict_race", ("予想", "本命", "印", "予測", "分析して"), 0.85),
    ("follow_up", ("このレース", "さっき", "それ", "同じ", "もう一度", "続き", "先ほど"), 0.8),
]


class IntentClassifier:
    def classify(
        self,
        text: str,
        *,
        has_race: bool,
        ctx: ConversationContext | None = None,
    ) -> tuple[str, float, dict[str, Any]]:
        lower = text.lower()
        slots: dict[str, Any] = {}

        for intent, keywords, base_conf in _INTENT_RULES:
            if any(k in text or k in lower for k in keywords):
                conf = base_conf
                if intent == "follow_up" and ctx and ctx.active_race_id:
                    conf = 0.92
                    slots["follow_up"] = True
                if intent in ("explain_pick", "find_upset", "buy_advice", "predict_race"):
                    if has_race:
                        conf = min(0.95, conf + 0.05)
                return intent, conf, slots

        if has_race:
            return "predict_race", 0.75, slots

        if ctx and ctx.last_intent and ctx.active_race_id:
            if len(text) < 20:
                return ctx.last_intent, 0.65, {"inherited": True}

        return "unknown", 0.25, slots


class IntentParser:
    """Race Resolver + Context + IntentClassifier."""

    def __init__(self, context_manager) -> None:
        self.context_manager = context_manager

    def parse(
        self,
        message: str,
        ctx: ConversationContext,
        *,
        explicit_race_id: str | None = None,
    ) -> IntentResult:
        text = (message or "").strip()
        identity = self.context_manager.resolve_with_context(
            text, ctx, explicit_race_id=explicit_race_id
        )
        race_id = None
        if identity:
            race_id = identity.public_race_id or identity.catalog_race_id

        intent, confidence, slots = IntentClassifier().classify(
            text, has_race=bool(race_id), ctx=ctx
        )

        if intent == "follow_up" and ctx.last_intent:
            intent = ctx.last_intent
            slots["promoted_from"] = "follow_up"

        if intent == "unknown" and race_id:
            intent = "predict_race"
            confidence = max(confidence, 0.7)

        return IntentResult(
            intent=intent,
            race_id=race_id,
            confidence=confidence,
            identity=identity,
            slots=slots,
        )
