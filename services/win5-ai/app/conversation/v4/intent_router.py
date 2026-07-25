# -*- coding: utf-8 -*-
"""
Intent Router — Conversation Platform の中心。

Agent: casual | expert | review | chat
Mode: explain | review | chat | default
intent=chat のときのみ Chat Agent へルーティング。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from .modes import (
    MODE_CHAT,
    MODE_EXPLAIN,
    MODE_REVIEW,
    ConversationMode,
    normalize_mode,
)

AgentKind = Literal["casual", "expert", "review", "chat"]


@dataclass
class RoutedIntent:
    name: str
    agent: AgentKind
    confidence: float
    race_id: str | None = None
    mode: ConversationMode = "default"
    slots: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


# (intent, agent, keywords, confidence)
_RULES: list[tuple[str, AgentKind, tuple[str, ...], float]] = [
    # Personal Chat（マイページ日常会話 · KAOBA 非依存）
    (
        "chat",
        "chat",
        ("雑談", "おしゃべり", "日常会話", "personal chat", "マイページで話", "暇つぶし"),
        0.93,
    ),
    ("greeting", "casual", ("こんにちは", "こんばんは", "おはよう", "hello", "hi", "やあ"), 0.92),
    (
        "app_guide",
        "casual",
        ("使い方", "ヘルプ", "help", "何ができる", "どう使う", "ガイド", "案内"),
        0.9,
    ),
    (
        "refuse_predict",
        "casual",
        ("新しい予想", "本命を作って", "予測して作", "今から予想", "自分で予想", "生成して"),
        0.9,
    ),
    (
        "review_prediction",
        "review",
        ("相談", "レビュー", "review", "どう思う", "見てほしい", "意見を", "相談したい"),
        0.91,
    ),
    (
        "explain_pick",
        "expert",
        ("◎の理由", "本命の理由", "理由を聞く", "理由", "なぜ", "根拠", "why", "どうして", "選定", "説明して"),
        0.9,
    ),
    (
        "explain_confidence",
        "expert",
        ("信頼度", "confidence", "確信度", "どのくらい確か"),
        0.88,
    ),
    (
        "race_qa",
        "expert",
        ("レース", "出走", "枠順", "馬場", "距離", "発走", "何頭"),
        0.8,
    ),
    (
        "coverage_inquiry",
        "expert",
        ("カバレッジ", "coverage", "対応率", "データ状況"),
        0.88,
    ),
    (
        "diagnostics_inquiry",
        "expert",
        ("不足", "missing", "診断", "フォールバック", "mock"),
        0.88,
    ),
    (
        "list_races",
        "expert",
        ("レース一覧", "今日のレース", "開催一覧"),
        0.85,
    ),
    (
        "refuse_predict",
        "casual",
        ("予想して", "本命は", "印を", "予測して", "買い目を出して"),
        0.86,
    ),
]

_RACE_ID_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}|\d{8}_[a-z]+_\d{1,2})",
    re.I,
)


class IntentRouter:
    """Intent Router — Agent 責務分離の唯一の分岐点。"""

    def route(
        self,
        message: str,
        *,
        explicit_race_id: str | None = None,
        mode: ConversationMode | str | None = None,
    ) -> RoutedIntent:
        text = (message or "").strip()
        lower = text.lower()
        race_id = (explicit_race_id or "").strip() or None
        if not race_id:
            m = _RACE_ID_RE.search(text)
            if m:
                race_id = m.group(1)

        resolved_mode = normalize_mode(mode) if mode is not None else "default"

        # Mode 明示が最優先
        if resolved_mode == MODE_CHAT:
            return RoutedIntent(
                name="chat",
                agent="chat",
                confidence=0.95,
                race_id=None,  # Personal Chat はレース文脈を持たない
                mode=MODE_CHAT,
                slots={"from_mode": True, "kaoba_independent": True},
                reason="mode:chat",
            )
        if resolved_mode == MODE_REVIEW:
            return RoutedIntent(
                name="review_prediction",
                agent="review",
                confidence=0.95,
                race_id=race_id,
                mode=MODE_REVIEW,
                slots={"from_mode": True},
                reason="mode:review",
            )
        if resolved_mode == MODE_EXPLAIN:
            return RoutedIntent(
                name="explain_pick",
                agent="expert",
                confidence=0.95,
                race_id=race_id,
                mode=MODE_EXPLAIN,
                slots={"from_mode": True},
                reason="mode:explain",
            )

        if not text:
            return RoutedIntent(
                name="unknown",
                agent="casual",
                confidence=0.0,
                race_id=race_id,
                mode=resolved_mode,
                reason="empty_message",
            )

        for name, agent, keywords, conf in _RULES:
            if any(k in text or k.lower() in lower for k in keywords):
                # Chat Agent へは intent=chat のときのみ
                if name == "chat":
                    return RoutedIntent(
                        name="chat",
                        agent="chat",
                        confidence=conf,
                        race_id=None,
                        mode=MODE_CHAT,
                        slots={"matched": True, "kaoba_independent": True},
                        reason="keyword:chat",
                    )
                mode_out: ConversationMode = (
                    MODE_REVIEW
                    if agent == "review"
                    else MODE_EXPLAIN
                    if name == "explain_pick"
                    else resolved_mode
                )
                return RoutedIntent(
                    name=name,
                    agent=agent,
                    confidence=conf,
                    race_id=race_id,
                    mode=mode_out,
                    slots={"matched": True},
                    reason=f"keyword:{name}",
                )

        if race_id:
            return RoutedIntent(
                name="race_qa",
                agent="expert",
                confidence=0.7,
                race_id=race_id,
                mode=resolved_mode,
                reason="race_id_present",
            )

        return RoutedIntent(
            name="unknown",
            agent="casual",
            confidence=0.35,
            race_id=None,
            mode=resolved_mode,
            reason="no_match",
        )
