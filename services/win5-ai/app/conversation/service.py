# -*- coding: utf-8 -*-
"""
Conversation AI — 自然言語で競馬 AI を利用する統合レイヤー。

Resolver → Tools (Prediction/Coverage/Diagnostics) → Reason Builder → Response
複数ターン会話は ContextManager が session 状態を維持。
"""
from __future__ import annotations

import uuid
from typing import Any

from ..data.race_resolver import RaceResolver
from ..data.repository import ConversationRepository, PredictionRepository
from .context import ContextManager, ConversationContext
from .intent import IntentParser, IntentResult
from .reason_builder import ReasonBuilder, ReasonPayload
from .tools import ConversationTools


class ResponseBuilder:
    def build(
        self,
        intent: IntentResult,
        reason: ReasonPayload,
        *,
        ctx: ConversationContext,
        meta: dict[str, Any] | None = None,
        tool_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not reason.summary and not reason.bullets:
            return {
                "reply": "ご質問の意図を特定できませんでした。レース名や「カバレッジを教えて」などとお試しください。",
                "citations": [],
                "actions": [{"type": "list_races"}, {"type": "help"}],
            }

        parts: list[str] = [reason.summary]
        if reason.bullets:
            if intent.intent in ("explain_pick", "diagnostics_inquiry", "greeting", "list_races"):
                parts.append("\n".join(f"・{b}" for b in reason.bullets[:8]))
            elif intent.intent == "predict_race" and reason.narrative:
                parts.append(reason.narrative)
            elif len(reason.bullets) == 1:
                parts.append(reason.bullets[0])
            else:
                parts.append("\n".join(f"・{b}" for b in reason.bullets[:5]))

        reply = "\n".join(p for p in parts if p)

        actions: list[dict[str, Any]] = []
        if intent.race_id:
            actions.append({"type": "open_race", "race_id": intent.race_id})
        if intent.intent == "coverage_inquiry":
            actions.append({"type": "open_coverage"})
        if intent.intent == "diagnostics_inquiry":
            actions.append({"type": "open_diagnostics"})
        if not actions:
            actions.append({"type": "list_races"})

        return {
            "reply": reply,
            "race_id": intent.race_id,
            "top_runners": reason.top_runners,
            "ai_confidence": reason.ai_confidence,
            "citations": reason.citations,
            "sections": reason.sections,
            "actions": actions,
            "resolved": intent.identity.as_meta() if intent.identity else None,
            "context": ctx.as_meta(),
            "sources": (tool_data or {}).get("sources") or [],
        }


class ConversationService:
    def __init__(self) -> None:
        self.resolver = RaceResolver()
        self.history = ConversationRepository()
        self.predictions_store = PredictionRepository()
        self.context_manager = ContextManager(self.history, self.resolver)
        self.intent_parser = IntentParser(self.context_manager)
        self.tools = ConversationTools()
        self.reason_builder = ReasonBuilder()
        self.response_builder = ResponseBuilder()

    def chat(self, body: dict[str, Any]) -> dict[str, Any]:
        message = str(body.get("message") or body.get("text") or "").strip()
        session_id = str(body.get("session_id") or uuid.uuid4())
        explicit_race = body.get("race_id")

        ctx = self.context_manager.load(session_id)
        ctx.turn += 1

        self.history.append(
            session_id=session_id,
            role="user",
            content=message,
            race_id=explicit_race,
        )

        intent = self.intent_parser.parse(message, ctx, explicit_race_id=explicit_race)
        if intent.identity:
            ctx.update_from_identity(intent.identity)
        ctx.last_intent = intent.intent

        tool_data = self.tools.execute(intent.intent, race_id=intent.race_id)

        pred_block = tool_data.get("prediction") or {}
        bundle = pred_block.get("bundle")
        meta = pred_block.get("meta")
        if bundle and meta and intent.race_id:
            self.predictions_store.save(
                race_id=str(intent.race_id),
                bundle=bundle,
                engine_source=str(meta.get("engine_source") or "unknown"),
                fallback_reason=meta.get("fallback_reason"),
                core_race_id=meta.get("core_race_id"),
                model_version=meta.get("model_version"),
            )

        reason = self.reason_builder.build(
            intent.intent,
            tool_data,
            race_id=intent.race_id,
            prediction_meta=meta,
        )
        built = self.response_builder.build(
            intent, reason, ctx=ctx, meta=meta, tool_data=tool_data
        )

        user_id = body.get("_user_id")
        if user_id:
            from ..user import get_service

            get_service().persist_chat_turn(
                user_id=str(user_id),
                session_id=session_id,
                user_message=message,
                assistant_reply=built.get("reply") or "",
                race_id=intent.race_id,
                intent=intent.intent,
                meta={
                    "engine_source": (meta or {}).get("engine_source"),
                    "fallback_reason": (meta or {}).get("fallback_reason"),
                },
            )

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
                "context": built.get("context"),
                "sources": built.get("sources"),
            },
        )

        return {
            "session_id": session_id,
            "turn": ctx.turn,
            "intent": {
                "name": intent.intent,
                "confidence": intent.confidence,
                "race_id": intent.race_id,
                "slots": intent.slots,
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
