# -*- coding: utf-8 -*-
"""
Tool Capability 定義 — Tool Manager が保持する利用可能 Tool 一覧。
"""
from __future__ import annotations

from .base import ToolCapability

CAPABILITY_PREDICTION = ToolCapability(
    name="prediction",
    description="Official Prediction 取得（Read Only · Prediction API）",
    read_only=True,
    stub=False,
    intents=("explain_pick", "review_prediction", "explain_confidence"),
    modes=("explain", "review"),
)

CAPABILITY_RACE_INFO = ToolCapability(
    name="race_info",
    description="レース情報取得（Stub · 実接続禁止）",
    read_only=True,
    stub=True,
    intents=("race_qa", "list_races", "review_prediction", "explain_pick"),
    modes=("explain", "review", "default"),
)

CAPABILITY_STATISTICS = ToolCapability(
    name="statistics",
    description="統計取得（Stub · 実接続禁止）",
    read_only=True,
    stub=True,
    intents=("coverage_inquiry", "diagnostics_inquiry", "explain_confidence"),
    modes=("explain", "review", "default"),
)

CAPABILITY_HELP = ToolCapability(
    name="help",
    description="FAQ / ヘルプ（Stub）",
    read_only=True,
    stub=True,
    intents=("app_guide", "greeting", "refuse_predict"),
    modes=("default", "chat"),
)

CAPABILITY_KNOWLEDGE = ToolCapability(
    name="knowledge",
    description="共通知識検索（Knowledge Layer · Stub · ユーザー固有/予測根拠なし）",
    read_only=True,
    stub=True,
    intents=("app_guide", "greeting", "refuse_predict", "race_qa"),
    modes=("default", "chat", "explain", "review"),
)

DEFAULT_CAPABILITIES: tuple[ToolCapability, ...] = (
    CAPABILITY_PREDICTION,
    CAPABILITY_RACE_INFO,
    CAPABILITY_STATISTICS,
    CAPABILITY_HELP,
    CAPABILITY_KNOWLEDGE,
)


def capability_catalog() -> list[dict[str, object]]:
    return [
        {
            "name": c.name,
            "description": c.description,
            "read_only": c.read_only,
            "stub": c.stub,
            "intents": list(c.intents),
            "modes": list(c.modes),
        }
        for c in DEFAULT_CAPABILITIES
    ]


def select_tool_names(
    *,
    mode: str | None = None,
    intent: str | None = None,
    prefer_prediction: bool = False,
) -> list[str]:
    """
    Capability から利用 Tool 名を選択する。
    Review / Explain では Prediction を優先。
    """
    mode_s = (mode or "").strip().lower()
    intent_s = (intent or "").strip().lower()
    selected: list[str] = []

    for cap in DEFAULT_CAPABILITIES:
        by_mode = mode_s in cap.modes if mode_s else False
        by_intent = intent_s in cap.intents if intent_s else False
        if by_mode or by_intent:
            if cap.name not in selected:
                selected.append(cap.name)

    if prefer_prediction or mode_s in ("review", "explain") or intent_s in (
        "explain_pick",
        "review_prediction",
    ):
        if "prediction" not in selected:
            selected.insert(0, "prediction")
        else:
            selected = ["prediction"] + [n for n in selected if n != "prediction"]

    return selected
