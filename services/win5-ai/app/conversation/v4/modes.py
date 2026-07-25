# -*- coding: utf-8 -*-
"""
Conversation Mode 定義（UI 連携契約 · UI 実装は別 Round）。

「KAOBAに◎の理由を聞く」→ Explain Mode
「KAOBAに相談」        → Review Mode
「マイページ日常会話」  → Chat Mode（KAOBA 非依存 · Personal Chat）
"""
from __future__ import annotations

from typing import Any, Literal

ConversationMode = Literal["explain", "review", "chat", "default"]

MODE_EXPLAIN: ConversationMode = "explain"
MODE_REVIEW: ConversationMode = "review"
MODE_CHAT: ConversationMode = "chat"
MODE_DEFAULT: ConversationMode = "default"

# UI ラベル（実装はしない · 契約のみ）
UI_MODE_TRIGGERS = {
    MODE_EXPLAIN: {
        "label_ja": "KAOBAに◎の理由を聞く",
        "intent": "explain_pick",
        "agent": "expert",
        "prompt": "explain",
    },
    MODE_REVIEW: {
        "label_ja": "KAOBAに相談",
        "intent": "review_prediction",
        "agent": "review",
        "prompt": "review",
    },
    MODE_CHAT: {
        "label_ja": "マイページ日常会話",
        "intent": "chat",
        "agent": "chat",
        "prompt": "chat",
        "kaoba_independent": True,
    },
}


def normalize_mode(raw: Any) -> ConversationMode:
    if raw is None:
        return MODE_DEFAULT
    s = str(raw).strip().lower()
    if s in ("explain", "explain_mode", "explain_pick"):
        return MODE_EXPLAIN
    if s in ("review", "review_mode", "consult", "相談"):
        return MODE_REVIEW
    if s in ("chat", "personal_chat", "mypage_chat", "日常会話"):
        return MODE_CHAT
    return MODE_DEFAULT


def resolve_mode_from_body(body: dict[str, Any] | None) -> ConversationMode:
    """request.mode / context.mode / context.type から Mode を決定。"""
    body = body if isinstance(body, dict) else {}
    if body.get("mode") is not None:
        return normalize_mode(body.get("mode"))
    ctx = body.get("context") if isinstance(body.get("context"), dict) else {}
    if ctx.get("mode") is not None:
        return normalize_mode(ctx.get("mode"))
    ctype = str(ctx.get("type") or "").lower()
    if ctype in ("explain", "explain_pick", "honmei_reason"):
        return MODE_EXPLAIN
    if ctype in ("review", "consult", "strategy_review"):
        return MODE_REVIEW
    if ctype in ("chat", "personal_chat", "mypage_chat"):
        return MODE_CHAT
    return MODE_DEFAULT
