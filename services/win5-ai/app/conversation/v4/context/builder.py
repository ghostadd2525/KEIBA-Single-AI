# -*- coding: utf-8 -*-
"""
Review Context Builder — Official Prediction → ReviewContext。

F_V4_TOOL_LAYER=ON 時:
  ReviewContextBuilder → Tool Manager → Prediction Tool → Prediction API

F_V4_TOOL_LAYER=OFF 時（既定）:
  ReviewContextBuilder → Prediction Connector → Prediction API（Phase 7 互換）

Review / Explain Agent は変更せず、本 Builder 経由でのみ Tool Manager を利用する。
Prediction は Read Only。request payload の prediction は根拠にしない。
"""
from __future__ import annotations

from typing import Any

from ..flags import tool_layer_enabled
from ..intent_router import RoutedIntent
from ..modes import MODE_EXPLAIN, MODE_REVIEW
from ..prediction import ConversationPredictionAdapter, PredictionConnector
from ..tools.manager import ToolManager
from ..tools.prediction_tool import PredictionTool
from .review_context import ReviewContext


def _stub_race(race_id: str | None) -> dict[str, Any]:
    return {
        "stub": True,
        "race_id": race_id,
        "connected": False,
        "message": "race context stub（未接続）",
    }


def _stub_horse() -> dict[str, Any]:
    return {
        "stub": True,
        "connected": False,
        "message": "horse context stub（未接続）",
    }


def _stub_buy_strategy() -> dict[str, Any]:
    return {
        "stub": True,
        "connected": False,
        "message": "buy_strategy context stub（未接続）",
    }


def _stub_user(body: dict[str, Any]) -> dict[str, Any]:
    uid = body.get("_user_id") or body.get("user_id")
    return {
        "stub": True,
        "connected": False,
        "user_id": str(uid) if uid else None,
        "message": "user context stub（未接続）",
    }


class ReviewContextBuilder:
    """Official Prediction を取得して ReviewContext を構築する。"""

    def __init__(
        self,
        *,
        connector: PredictionConnector | None = None,
        adapter: ConversationPredictionAdapter | None = None,
        tool_manager: ToolManager | None = None,
    ) -> None:
        self.connector = connector or PredictionConnector()
        self.adapter = adapter or ConversationPredictionAdapter()
        self._tool_manager = tool_manager

    def _manager(self) -> ToolManager:
        if self._tool_manager is None:
            self._tool_manager = ToolManager(
                prediction_tool=PredictionTool(
                    connector=self.connector,
                    adapter=self.adapter,
                )
            )
        return self._tool_manager

    def _resolve_prediction(
        self,
        race_id: str | None,
        *,
        mode: str,
        intent: str | None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any], list[str]]:
        """
        returns: official, prediction_meta, tools_selected
        Tool Layer ON → Tool Manager のみ（個別 Tool 直接禁止）。
        """
        if tool_layer_enabled():
            manager = self._manager()
            selected = manager.select(
                mode=mode, intent=intent, prefer_prediction=True
            )
            official, meta = manager.get_official_prediction(race_id)
            meta["mutated"] = False
            meta["tool_layer"] = True
            meta["tools_selected"] = selected
            if "race_info" in selected:
                race_res = manager.call("race_info", race_id=race_id)
                meta["race_info_stub"] = bool(race_res.stub)
            return official, meta, list(selected)

        fetch = self.connector.fetch(race_id)
        official, prediction_meta = self.adapter.adapt(fetch)
        prediction_meta["mutated"] = False
        prediction_meta["tool_layer"] = False
        return official, prediction_meta, []

    def build(
        self,
        body: dict[str, Any] | None,
        routed: RoutedIntent,
        *,
        message: str | None = None,
        history: list[dict[str, str]] | None = None,
        mode: str | None = None,
    ) -> ReviewContext:
        body = body if isinstance(body, dict) else {}
        text = (
            message
            if message is not None
            else str(body.get("message") or body.get("text") or "")
        ).strip()
        race_id = routed.race_id or (
            str(body.get("race_id")).strip() if body.get("race_id") else None
        )

        resolved_mode = mode or (
            MODE_REVIEW
            if routed.mode == MODE_REVIEW or routed.agent == "review"
            else MODE_EXPLAIN
            if routed.mode == MODE_EXPLAIN or routed.name == "explain_pick"
            else str(routed.mode or "review")
        )

        official, prediction_meta, tools_selected = self._resolve_prediction(
            race_id,
            mode=resolved_mode,
            intent=routed.name,
        )
        prediction_meta["mutated"] = False

        race_ctx = _stub_race(race_id)
        if tool_layer_enabled():
            race_res = self._manager().call("race_info", race_id=race_id)
            if race_res.ok and isinstance(race_res.data, dict):
                race_ctx = {**race_ctx, **race_res.data, "via": "tool_manager"}

        slots = dict(routed.slots or {})
        if tools_selected:
            slots["tools_used"] = tools_selected
            slots["tool_layer"] = True

        return ReviewContext(
            mode=resolved_mode,
            prediction=official,
            prediction_meta=prediction_meta,
            buy_strategy=_stub_buy_strategy(),
            race=race_ctx,
            horse=_stub_horse(),
            user=_stub_user(body),
            request={
                "message": text,
                "race_id": race_id,
                "session_id": body.get("session_id"),
                "intent": routed.name,
                "intent_confidence": routed.confidence,
                "router_reason": routed.reason,
                "slots": slots,
            },
            history=list(history or []),
        )
