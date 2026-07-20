# -*- coding: utf-8 -*-
"""
Conversation Layer — Resolver → Prediction → Reason Builder → Response

Prediction を直接呼ばず、Race Resolver で race_id を正規化してから推論する。
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from ..data.race_resolver import RaceIdentity, RaceResolver
from ..data.repository import ConversationRepository, PredictionRepository
from ..engine.adapters import prediction_adapter
from .reason_builder import ReasonBuilder


@dataclass
class IntentResult:
    intent: str
    race_id: str | None = None
    confidence: float = 0.0
    identity: RaceIdentity | None = None
    slots: dict[str, Any] | None = None


class IntentParser:
    def __init__(self, resolver: RaceResolver) -> None:
        self.resolver = resolver

    def parse(self, message: str, *, explicit_race_id: str | None = None) -> IntentResult:
        text = (message or "").strip()
        identity: RaceIdentity | None = None
        race_id: str | None = None

        if explicit_race_id:
            identity = self.resolver.resolve(str(explicit_race_id))
            race_id = identity.public_race_id if identity else str(explicit_race_id)
        else:
            identity = self._resolve_from_message(text)
            if identity:
                race_id = identity.public_race_id or identity.catalog_race_id

        intent = self._classify_intent(text, bool(race_id))
        confidence = 0.85 if race_id else 0.55 if intent != "unknown" else 0.2
        return IntentResult(
            intent=intent,
            race_id=race_id,
            confidence=confidence,
            identity=identity,
        )

    def _resolve_from_message(self, text: str) -> RaceIdentity | None:
        embedded = re.search(r"(20\d{6}_[a-z0-9]+_\d+)", text.lower())
        if embedded:
            return self.resolver.resolve(embedded.group(1))

        core = re.search(r"(20\d{2}-\d{2}-\d{2}-\d{2}-\d+)", text)
        if core:
            return self.resolver.resolve(core.group(1))

        catalog = re.search(
            r"(20\d{2}-\d{2}-\d{2}-(?:札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)-\d+)",
            text,
        )
        if catalog:
            return self.resolver.resolve(catalog.group(1))

        ui = re.search(
            r"(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)\s*(\d{1,2})\s*R?",
            text,
        )
        if ui:
            return self.resolver.parse_ui_label(text)

        return None

    def _classify_intent(self, text: str, has_race: bool) -> str:
        if any(k in text for k in ("理由", "なぜ", "根拠", "why")):
            return "explain_pick"
        if any(k in text for k in ("穴", "大穴", "穴馬")):
            return "find_upset"
        if any(k in text for k in ("買い", "買う", "見送", "評価して")):
            return "buy_advice"
        if any(k in text for k in ("予想", "本命", "印", "予測")) or has_race:
            return "predict_race"
        return "unknown"


class ResponseBuilder:
    """ReasonBuilder 出力 → 会話応答テキスト + actions。"""

    def build(
        self,
        intent: IntentResult,
        reason: Any,
        *,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not reason.bullets and not reason.summary:
            return {
                "reply": "対象レースの予想データが見つかりませんでした。race_id を指定してください。",
                "citations": [],
                "actions": [{"type": "list_races"}],
            }

        if intent.intent == "explain_pick" and reason.bullets:
            reply = "選定理由:\n- " + "\n- ".join(reason.bullets[:5])
        else:
            reply = reason.summary
            if reason.narrative and intent.intent == "predict_race":
                reply = f"{reply}{reason.narrative}"

        actions = [{"type": "open_race", "race_id": intent.race_id}] if intent.race_id else [
            {"type": "list_races"}
        ]
        return {
            "reply": reply,
            "race_id": intent.race_id,
            "intent": intent.intent,
            "top_runners": reason.top_runners,
            "ai_confidence": reason.ai_confidence,
            "citations": reason.citations,
            "actions": actions,
            "resolved": intent.identity.as_meta() if intent.identity else None,
        }


class ConversationService:
    """
    Resolver → Prediction → Reason Builder → Response
    """

    def __init__(self) -> None:
        self.resolver = RaceResolver()
        self.intent_parser = IntentParser(self.resolver)
        self.reason_builder = ReasonBuilder()
        self.response_builder = ResponseBuilder()
        self.history = ConversationRepository()
        self.predictions_store = PredictionRepository()

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

        intent = self.intent_parser.parse(message, explicit_race_id=explicit_race)

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

        reason = self.reason_builder.build(intent.intent, bundle, race_id=intent.race_id)
        built = self.response_builder.build(intent, reason, meta=meta)

        self.history.append(
            session_id=session_id,
            role="assistant",
            content=built["reply"],
            intent=intent.intent,
            race_id=intent.race_id,
            meta={
                "engine_source": (meta or {}).get("engine_source"),
                "fallback_reason": (meta or {}).get("fallback_reason"),
                "resolved": built.get("resolved"),
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
