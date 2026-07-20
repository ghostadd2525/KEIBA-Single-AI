# -*- coding: utf-8 -*-
"""
Reason Builder — Prediction 結果から会話用根拠・説明を組み立て。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ReasonPayload:
    summary: str
    bullets: list[str]
    top_runners: list[dict[str, Any]]
    ai_confidence: float | None
    citations: list[dict[str, Any]]
    narrative: str


class ReasonBuilder:
    """Prediction bundle + intent → 構造化 reason。"""

    def build(
        self,
        intent: str,
        bundle: dict[str, Any] | None,
        *,
        race_id: str | None = None,
    ) -> ReasonPayload:
        if not bundle:
            return ReasonPayload(
                summary="対象レースの予想データが見つかりませんでした。",
                bullets=["race_id を指定してください。"],
                top_runners=[],
                ai_confidence=None,
                citations=[],
                narrative="",
            )

        runners = ((bundle.get("evaluation") or {}).get("runners")) or []
        top = runners[:3]
        conf = (bundle.get("ai_confidence") or {}).get("score")
        narrative = ((bundle.get("explain") or {}).get("narrative")) or ""
        rid = race_id or bundle.get("race_id")

        if intent == "explain_pick":
            reasons = (bundle.get("explain") or {}).get("reasons") or []
            bullets: list[str] = []
            for r in reasons[:3]:
                bullets.extend(r.get("bullets") or [])
            summary = "選定理由を整理しました。"
            if not bullets:
                bullets = [narrative or "理由テキストがありません。"]
        elif intent == "find_upset":
            ana = next((r for r in runners if r.get("mark") == "ana"), None)
            if ana:
                summary = f"穴候補は {ana.get('horse_number')}番 {ana.get('horse_name') or ''} です。"
                bullets = ["穴印に基づく候補"]
            else:
                summary = "穴印の馬は現データにありません。"
                bullets = ["下位人気の上位評価を確認してください。"]
        elif intent == "buy_advice":
            honmei = next((r for r in runners if r.get("mark") == "honmei"), top[0] if top else None)
            if honmei:
                summary = f"本命は {honmei.get('horse_number')}番。確信度={conf}。"
                bullets = ["軸寄せなら本命中心", "広げるなら相手を増やす"]
            else:
                summary = "買い目の軸候補を特定できませんでした。"
                bullets = []
        else:
            names = " / ".join(
                f"{r.get('horse_number')}{r.get('horse_name') or ''}" for r in top
            )
            summary = f"{rid} の上位評価: {names}。"
            bullets = [narrative] if narrative else []

        return ReasonPayload(
            summary=summary,
            bullets=[b for b in bullets if b],
            top_runners=top,
            ai_confidence=conf if isinstance(conf, (int, float)) else None,
            citations=[{"type": "prediction_bundle", "race_id": rid}],
            narrative=narrative,
        )
