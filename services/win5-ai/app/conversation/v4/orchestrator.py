# -*- coding: utf-8 -*-
"""
Conversation Orchestrator — Conversation API の実装本体。

Intent Router → Casual | Expert | Review | Chat Agent
Chat: Personal Chat（マイページ日常会話 · KAOBA 非依存）
Review / Explain: ReviewContextBuilder → Prediction API（Read Only）→ ReviewContext
Review: ReviewAgent.review(context) のみ（Prediction 改変なし）
Explain: ExpertAgent.explain(context)
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from .agents.casual import CasualAgent
from .agents.chat import ChatAgent
from .agents.expert import ExpertAgent
from .agents.review import ReviewAgent
from .config import load_conversation_config, resolve_model
from .context import ConversationContext, ReviewContextBuilder
from .flags import (
    conversation_ollama_enabled,
    flag_snapshot,
    knowledge_integration_enabled,
    knowledge_layer_enabled,
    personal_chat_enabled,
    review_agent_enabled,
    tool_layer_enabled,
    v4_platform_active,
)
from .history import HistoryManager, get_history_manager
from .intent_router import IntentRouter
from .logging_util import log_conversation_event
from .modes import resolve_mode_from_body
from .ollama_client import OllamaClient
from .prediction import FAIL_OPEN_MESSAGE
from .security import SecurityGuard
from .tools.stub import ExpertToolStub


class ConversationOrchestrator:
    """Conversation Platform Orchestrator（Casual / Expert / Review / Chat）。"""

    def __init__(
        self,
        *,
        router: IntentRouter | None = None,
        casual: CasualAgent | None = None,
        expert: ExpertAgent | None = None,
        review: ReviewAgent | None = None,
        chat_agent: ChatAgent | None = None,
        ollama: OllamaClient | None = None,
        review_context_builder: ReviewContextBuilder | None = None,
        security_guard: SecurityGuard | None = None,
        history_manager: HistoryManager | None = None,
    ) -> None:
        self.router = router or IntentRouter()
        self._ollama = ollama
        self.casual = casual or CasualAgent(ollama_client=None)
        self.expert = expert or ExpertAgent(tools=ExpertToolStub())
        self.review = review or ReviewAgent(ollama=ollama)
        self.chat_agent = chat_agent or ChatAgent(ollama=ollama)
        self.review_context_builder = review_context_builder or ReviewContextBuilder()
        self.security_guard = security_guard or SecurityGuard()
        self.history_manager = history_manager or get_history_manager()

    def _conversation_context(self, session_id: str, mode: str | None) -> ConversationContext:
        cfg = load_conversation_config()
        hist_cfg = cfg.get("history") or {}
        # マネージャ設定を config に同期（永続化はしない）
        self.history_manager.max_messages = int(hist_cfg.get("max_messages") or 20)
        self.history_manager.prompt_turns = int(hist_cfg.get("prompt_turns") or 8)
        return ConversationContext(
            session_id=session_id,
            mode=mode,
            _history_manager=self.history_manager,
        )

    def _append_turn_if_allowed(
        self,
        conv: ConversationContext,
        *,
        user_message: str,
        assistant_reply: str | None,
        store_user: bool,
    ) -> None:
        """Security Guard 通過済みの内容のみ履歴へ。"""
        if store_user and user_message:
            conv.append_user(user_message)
        if assistant_reply:
            conv.append_assistant(assistant_reply)
    def _ensure_casual_ollama(self) -> CasualAgent:
        if not conversation_ollama_enabled():
            return self.casual
        if self.casual._ollama is not None:
            return self.casual
        cfg = load_conversation_config()
        client = self._ollama or OllamaClient(
            base_url=cfg["ollama"]["base_url"],
            timeout_ms=int(cfg["ollama"]["timeout_ms"]),
            chat_path=cfg["ollama"]["chat_path"],
            tags_path=cfg["ollama"]["tags_path"],
        )
        return CasualAgent(ollama_client=client)

    def _review_agent(self) -> ReviewAgent:
        if self._ollama is not None and self.review._ollama is None:
            return ReviewAgent(ollama=self._ollama)
        return self.review

    def _chat_agent(self) -> ChatAgent:
        if self._ollama is not None and self.chat_agent._ollama is None:
            return ChatAgent(ollama=self._ollama)
        return self.chat_agent

    def _platform_meta(self) -> dict[str, Any]:
        return {
            "prediction_api_connected": True,
            "prediction_read_only": True,
            "tool_layer": tool_layer_enabled(),
            "knowledge_layer": knowledge_layer_enabled(),
            "knowledge_integration": knowledge_integration_enabled(),
            "expert_tools": "stub",
            "review_agent": review_agent_enabled(),
            "personal_chat": personal_chat_enabled(),
            "security_guard": True,
            "security_guard_always_on": True,
            "history_persistent": False,
        }

    def _fail_open_prediction(
        self,
        *,
        routed: Any,
        review_ctx: Any,
        request_id: str,
        session_id: str,
        started: float,
        conv: Any,
    ) -> dict[str, Any]:
        """Prediction API 不可時 — 固定文。Platform は停止しない。"""
        ms = (time.perf_counter() - started) * 1000
        meta = dict(getattr(review_ctx, "prediction_meta", None) or {})
        meta["mutated"] = False
        meta["fail_open"] = True
        agent_name = "review" if routed.agent == "review" else "expert"
        log_conversation_event(
            request_id=request_id,
            agent=agent_name,
            intent=routed.name,
            mode=routed.mode,
            tools_used=[],
            response_time_ms=ms,
            error_reason="prediction_api_fail_open",
        )
        return {
            "session_id": session_id,
            "disabled": False,
            "orchestrator": True,
            "agent": agent_name,
            "mode": routed.mode,
            "intent": {
                "name": routed.name,
                "confidence": routed.confidence,
                "race_id": routed.race_id,
                "slots": routed.slots,
            },
            "reply": FAIL_OPEN_MESSAGE,
            "citations": [],
            "actions": (
                [{"type": "open_race", "race_id": routed.race_id}]
                if routed.race_id
                else [{"type": "list_races"}]
            ),
            "tools_used": [],
            "prediction_meta": meta,
            "fallback": "prediction_api_fail_open",
            "llm": {"used": False, "role": "none"},
            "router": {
                "agent": routed.agent,
                "reason": routed.reason,
                "mode": routed.mode,
            },
            "request_id": request_id,
            "response_time": round(ms, 2),
            "conversation": conv.as_meta(),
            "platform": self._platform_meta(),
        }

    def health(self) -> dict[str, Any]:
        started = time.perf_counter()
        request_id = str(uuid.uuid4())
        cfg = load_conversation_config()
        flags = flag_snapshot()
        model = resolve_model(None)

        if not v4_platform_active():
            ms = (time.perf_counter() - started) * 1000
            return {
                "status": "disabled",
                "message": cfg["disabled_message"],
                "flags": flags,
                "platform": {
                    "orchestrator": True,
                    "prediction_api_connected": True,
                    "prediction_read_only": True,
                    "tool_layer": tool_layer_enabled(),
                    "knowledge_layer": knowledge_layer_enabled(),
                    "knowledge_integration": knowledge_integration_enabled(),
                    "expert_tools": "stub",
                    "review_agent": review_agent_enabled(),
                    "personal_chat": personal_chat_enabled(),
                },
                "request_id": request_id,
                "response_time": round(ms, 2),
            }

        ollama_info: dict[str, Any] = {"checked": False, "enabled": conversation_ollama_enabled()}
        if conversation_ollama_enabled():
            client = self._ollama or OllamaClient(
                base_url=cfg["ollama"]["base_url"],
                timeout_ms=int(cfg["ollama"]["timeout_ms"]),
            )
            ollama_info = {**client.health(), "checked": True, "enabled": True}

        ms = (time.perf_counter() - started) * 1000
        return {
            "status": "ok",
            "flags": flags,
            "selected_model": model,
            "platform": {
                "orchestrator": True,
                "intent_router": True,
                "agents": ["casual", "expert", "review", "chat"],
                "modes": ["explain", "review", "chat"],
                "prediction_api_connected": True,
                "prediction_read_only": True,
                "tool_layer": tool_layer_enabled(),
                "knowledge_layer": knowledge_layer_enabled(),
                "knowledge_integration": knowledge_integration_enabled(),
                "expert_tools": "stub",
                "review_agent": review_agent_enabled(),
                "personal_chat": personal_chat_enabled(),
            },
            "ollama": ollama_info,
            "request_id": request_id,
            "response_time": round(ms, 2),
        }

    def chat(self, body: dict[str, Any] | None) -> dict[str, Any]:
        started = time.perf_counter()
        request_id = str(uuid.uuid4())
        cfg = load_conversation_config()
        body = body if isinstance(body, dict) else {}
        session_id = str(body.get("session_id") or uuid.uuid4())

        if not v4_platform_active():
            ms = (time.perf_counter() - started) * 1000
            log_conversation_event(
                request_id=request_id,
                agent=None,
                intent=None,
                error_reason="disabled",
                response_time_ms=ms,
            )
            return {
                "session_id": session_id,
                "reply": cfg["disabled_message"],
                "disabled": True,
                "orchestrator": True,
                "agent": None,
                "intent": {"name": "disabled", "confidence": 0.0, "race_id": None},
                "citations": [],
                "actions": [],
                "fallback": None,
                "request_id": request_id,
                "response_time": round(ms, 2),
                "platform": {
                    "prediction_api_connected": True,
                    "prediction_read_only": True,
                    "expert_tools": "stub",
                    "review_agent": False,
                    "personal_chat": False,
                },
            }

        message = str(body.get("message") or body.get("text") or "").strip()
        max_chars = int(cfg["limits"]["max_message_chars"])
        if len(message) > max_chars:
            message = message[:max_chars]

        mode = resolve_mode_from_body(body)
        conv = self._conversation_context(session_id, mode)

        # Personal Chat: Orchestrator → Security Guard → Intent Router
        # Block 時は固定文のみ。履歴にも載せない。Ollama は呼ばない。
        if mode == "chat":
            pre_guard = self.security_guard.check(message)
            if pre_guard.blocked:
                blocked = self.security_guard.block_response(guard=pre_guard)
                ms = (time.perf_counter() - started) * 1000
                log_conversation_event(
                    request_id=request_id,
                    agent="chat",
                    intent="chat_blocked",
                    mode="chat",
                    tools_used=[],
                    response_time_ms=ms,
                    error_reason="security_block",
                )
                return {
                    "session_id": session_id,
                    "disabled": False,
                    "orchestrator": True,
                    "router": {"agent": None, "reason": "security_guard_pre_router", "mode": "chat"},
                    "request_id": request_id,
                    "response_time": round(ms, 2),
                    "conversation": conv.as_meta(),
                    "platform": self._platform_meta(),
                    **blocked,
                }

        # Chat / Review / Explain 共通: Guard 通過後のみ user を履歴へ
        guard_for_history = self.security_guard.check(message)
        history_allowed = not guard_for_history.blocked
        prompt_history = conv.prompt_history()

        explicit_race = body.get("race_id")
        routed = self.router.route(
            message,
            explicit_race_id=str(explicit_race) if explicit_race else None,
            mode=mode,
        )
        conv.last_intent = routed.name
        conv.race_id = routed.race_id

        # intent=chat のときのみ Chat Agent（Review / Explain / Prediction 非関与）
        if routed.agent == "chat" or routed.name == "chat":
            agent_out = self._chat_agent().chat(
                message, routed, history=prompt_history
            )
        elif routed.agent == "review":
            if review_agent_enabled():
                review_ctx = self.review_context_builder.build(
                    body,
                    routed,
                    message=message,
                    history=prompt_history,
                )
                # Official Prediction 不可 → fail-open（Platform は継続）
                if review_ctx.prediction_meta.get("fail_open") and not review_ctx.prediction:
                    fo = self._fail_open_prediction(
                        routed=routed,
                        review_ctx=review_ctx,
                        request_id=request_id,
                        session_id=session_id,
                        started=started,
                        conv=conv,
                    )
                    if history_allowed:
                        self._append_turn_if_allowed(
                            conv,
                            user_message=message,
                            assistant_reply=str(fo.get("reply") or ""),
                            store_user=True,
                        )
                        fo["conversation"] = conv.as_meta()
                    return fo
                agent_out = self._review_agent().review(review_ctx)
            else:
                from .intent_router import RoutedIntent

                fallback_route = RoutedIntent(
                    name="app_guide",
                    agent="casual",
                    confidence=0.5,
                    race_id=routed.race_id,
                    mode=routed.mode,
                    reason="review_flag_off",
                )
                agent_out = self._ensure_casual_ollama().handle(
                    "Review Agent はオフです。使い方を教えて",
                    fallback_route,
                )
                agent_out = {
                    **agent_out,
                    "fallback": "review_flag_off",
                    "mode": "review",
                }
        elif routed.agent == "expert":
            if routed.name == "explain_pick" or routed.mode == "explain":
                review_ctx = self.review_context_builder.build(
                    body,
                    routed,
                    message=message,
                    history=prompt_history,
                    mode="explain",
                )
                if review_ctx.prediction_meta.get("fail_open") and not review_ctx.prediction:
                    fo = self._fail_open_prediction(
                        routed=routed,
                        review_ctx=review_ctx,
                        request_id=request_id,
                        session_id=session_id,
                        started=started,
                        conv=conv,
                    )
                    if history_allowed:
                        self._append_turn_if_allowed(
                            conv,
                            user_message=message,
                            assistant_reply=str(fo.get("reply") or ""),
                            store_user=True,
                        )
                        fo["conversation"] = conv.as_meta()
                    return fo
                agent_out = self.expert.explain(review_ctx)
            else:
                # その他 Expert Intent は Tool Stub（本 Phase 対象外）
                agent_out = self.expert.handle(
                    message, routed, history=prompt_history
                )
            agent_out.setdefault("mode", routed.mode)
        else:
            agent_out = self._ensure_casual_ollama().handle(message, routed)
            agent_out.setdefault("mode", routed.mode)

        # 履歴更新: Security Guard 通過 + Block 応答以外
        store_user = history_allowed and not agent_out.get("blocked")
        assistant_reply = None
        if store_user and not agent_out.get("blocked"):
            assistant_reply = str(agent_out.get("reply") or "")
        self._append_turn_if_allowed(
            conv,
            user_message=message,
            assistant_reply=assistant_reply if store_user else None,
            store_user=store_user,
        )
        conv.last_agent = agent_out.get("agent")
        conv.turn = len(conv.history().messages)

        ms = (time.perf_counter() - started) * 1000
        log_conversation_event(
            request_id=request_id,
            agent=agent_out.get("agent"),
            intent=(agent_out.get("intent") or {}).get("name"),
            mode=agent_out.get("mode") or routed.mode,
            tools_used=agent_out.get("tools_used") or [],
            response_time_ms=ms,
            error_reason=None,
        )

        out = {
            "session_id": session_id,
            "disabled": False,
            "orchestrator": True,
            "router": {
                "agent": routed.agent,
                "reason": routed.reason,
                "mode": routed.mode,
            },
            "request_id": request_id,
            "response_time": round(ms, 2),
            "conversation": conv.as_meta(),
            "platform": self._platform_meta(),
            **agent_out,
        }
        if "fallback" not in out:
            out["fallback"] = None
        return out


_orchestrator = ConversationOrchestrator()


def health() -> dict[str, Any]:
    return _orchestrator.health()


def chat(body: dict[str, Any] | None) -> dict[str, Any]:
    return _orchestrator.chat(body)
