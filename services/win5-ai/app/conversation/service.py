# -*- coding: utf-8 -*-
"""
Conversation Layer — 意図解析 / Prediction 連携 / 応答組み立て

チャット UI は後付け。ここでは API・サービス境界のみ。
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from ..data.repository import ConversationRepository, PredictionRepository
from ..engine.adapters import prediction_adapter


@dataclass
class IntentResult:
    intent: str
    race_id: str | None = None
    confidence: float = 0.0
    slots: dict[str, Any] | None = None


_VENUE_ALIASES = {
    "福島": "fukushima",
    "函館": "hakodate",
    "阪神": "hanshin",
    "東京": "tokyo",
    "中山": "nakayama",
    "京都": "kyoto",
    "中京": "chukyo",
    "新潟": "niigata",
    "小倉": "kokura",
    "札幌": "sapporo",
}


def parse_intent(message: str) -> IntentResult:
    text = (message or "").strip()
    lower = text.lower()

    race_id = _extract_race_id(text)
    if any(k in text for k in ("理由", "なぜ", "根拠", "why")):
        return IntentResult("explain_pick", race_id=race_id, confidence=0.8)
    if any(k in text for k in ("穴", "大穴", "穴馬")):
        return IntentResult("find_upset", race_id=race_id, confidence=0.85)
    if any(k in text for k in ("買い", "買う", "見送", "評価して")):
        return IntentResult("buy_advice", race_id=race_id, confidence=0.75)
    if any(k in text for k in ("予想", "本命", "印", "予測")) or race_id:
        return IntentResult("predict_race", race_id=race_id, confidence=0.8 if race_id else 0.55)
    return IntentResult("unknown", race_id=race_id, confidence=0.2)


def _extract_race_id(text: str) -> str | None:
    m = re.search(r"(20\d{6}_[a-z]+_\d{1,2})", text, re.I)
    if m:
        return m.group(1).lower()
    # 「今日の福島11R」→ catalog から解決（簡易）
    m = re.search(r"(福島|函館|阪神|東京|中山|京都|中京|新潟|小倉|札幌)\s*(\d{1,2})\s*R?", text)
    if not m:
        return None
    venue_ja, race_no = m.group(1), int(m.group(2))
    key = _VENUE_ALIASES.get(venue_ja)
    catalog = prediction_adapter.list_bundles()
    for b in catalog:
        info = b.get("race_info") or {}
        if info.get("venue") == venue_ja and int(info.get("race_no") or 0) == race_no:
            return str(b.get("race_id"))
        rid = str(b.get("race_id") or "")
        if key and key in rid and rid.endswith(f"_{race_no}"):
            return rid
    # 合成 slug（データが無い場合のヒント）
    if key:
        return f"20260719_{key}_{race_no}"
    return None


class ResponseBuilder:
    """Prediction / Analysis 結果 → 会話応答テキスト + 構造化ペイロード."""

    def build(self, intent: IntentResult, bundle: dict[str, Any] | None) -> dict[str, Any]:
        if not bundle:
            return {
                "reply": "対象レースの予想データが見つかりませんでした。race_id を指定してください。",
                "citations": [],
                "actions": [{"type": "list_races"}],
            }
        runners = ((bundle.get("evaluation") or {}).get("runners")) or []
        top = runners[:3]
        conf = (bundle.get("ai_confidence") or {}).get("score")
        narrative = ((bundle.get("explain") or {}).get("narrative")) or ""
        race_id = bundle.get("race_id")

        if intent.intent == "explain_pick":
            reasons = (bundle.get("explain") or {}).get("reasons") or []
            bullets = []
            for r in reasons[:3]:
                bullets.extend(r.get("bullets") or [])
            reply = "選定理由:\n- " + "\n- ".join(bullets[:5]) if bullets else (narrative or "理由テキストがありません。")
        elif intent.intent == "find_upset":
            ana = next((r for r in runners if r.get("mark") == "ana"), None)
            if ana:
                reply = f"穴候補は {ana.get('horse_number')}番 {ana.get('horse_name') or ''} です。"
            else:
                reply = "穴印の馬は現データにありません。下位人気の上位評価を確認してください。"
        elif intent.intent == "buy_advice":
            honmei = next((r for r in runners if r.get("mark") == "honmei"), top[0] if top else None)
            if honmei:
                reply = (
                    f"本命は {honmei.get('horse_number')}番。確信度={conf}。"
                    "点数を抑えるなら軸寄せ、広げるなら相手を増やしてください。"
                )
            else:
                reply = "買い目の軸候補を特定できませんでした。"
        else:  # predict_race / unknown with bundle
            names = " / ".join(
                f"{r.get('horse_number')}{r.get('horse_name') or ''}" for r in top
            )
            reply = f"{race_id} の上位評価: {names}。{narrative}"

        return {
            "reply": reply,
            "race_id": race_id,
            "intent": intent.intent,
            "top_runners": top,
            "ai_confidence": conf,
            "citations": [{"type": "prediction_bundle", "race_id": race_id}],
            "actions": [{"type": "open_race", "race_id": race_id}],
        }


class ConversationService:
    """
    Conversation API → Intent → Prediction API → Response Builder

    Kaoba（既存）とは分離。将来 LLM 差し替えは Intent/Response 境界で行う。
    """

    def __init__(self) -> None:
        self.history = ConversationRepository()
        self.predictions_store = PredictionRepository()
        self.builder = ResponseBuilder()

    def chat(self, body: dict[str, Any]) -> dict[str, Any]:
        message = str(body.get("message") or body.get("text") or "").strip()
        session_id = str(body.get("session_id") or uuid.uuid4())
        explicit_race = body.get("race_id")

        self.history.append(
            session_id=session_id,
            role="user",
            content=message,
            race_id=explicit_race,
        )

        intent = parse_intent(message)
        if explicit_race:
            intent.race_id = str(explicit_race)

        bundle = None
        meta = None
        if intent.race_id:
            bundle, meta = prediction_adapter.get_with_meta(intent.race_id)
            if bundle and meta:
                self.predictions_store.save(
                    race_id=str(intent.race_id),
                    bundle=bundle,
                    engine_source=str(meta.get("engine_source") or "unknown"),
                    fallback_reason=meta.get("fallback_reason"),
                    core_race_id=meta.get("core_race_id"),
                    model_version=meta.get("model_version"),
                )

        built = self.builder.build(intent, bundle)
        self.history.append(
            session_id=session_id,
            role="assistant",
            content=built["reply"],
            intent=intent.intent,
            race_id=intent.race_id,
            meta={
                "engine_source": (meta or {}).get("engine_source"),
                "fallback_reason": (meta or {}).get("fallback_reason"),
            },
        )

        return {
            "session_id": session_id,
            "intent": {
                "name": intent.intent,
                "confidence": intent.confidence,
                "race_id": intent.race_id,
            },
            "prediction_meta": {
                "engine_source": (meta or {}).get("engine_source"),
                "fallback_reason": (meta or {}).get("fallback_reason"),
                "core_race_id": (meta or {}).get("core_race_id"),
            }
            if meta
            else None,
            **built,
        }


_service = ConversationService()


def chat(body: dict[str, Any]) -> dict[str, Any]:
    return _service.chat(body)
