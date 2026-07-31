# -*- coding: utf-8 -*-
"""
Memory Gateway — Conversation 入口での Consent フロー接続。

配線箇所は conversation/__init__.py のみ（V4 Orchestrator / Agents / History 非変更）。
F_V6_MEMORY=OFF 時は完全ノーオペ。
"""
from __future__ import annotations

import threading
from typing import Any
from uuid import uuid4

from .retriever import MemoryRetriever
from .tool import MemoryTool


def _resolve_user_id(body: dict[str, Any]) -> str:
    uid = body.get("_user_id") or body.get("user_id") or body.get("uid")
    if uid:
        return str(uid).strip()
    # 長期 Memory は session に紐づけないのが理想だが、未ログイン時は session キーで隔離
    sid = body.get("session_id")
    if sid:
        return f"session:{sid}"
    return "anonymous"


def _message_of(body: dict[str, Any]) -> str:
    for key in ("message", "text", "query", "prompt"):
        val = body.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


class MemoryGateway:
    """
    Conversation
      → Memory Candidate / Intent
      → User Consent（明示「覚えて」のみ書込）
      → Memory Store
      → Memory Retriever
      → Conversation Context（メッセージ先頭へ注入 · Agent 非改変）
    """

    version = "v6-phase2"

    def __init__(self, tool: MemoryTool | None = None) -> None:
        self.tool = tool or MemoryTool()
        self.retriever = MemoryRetriever(store=self.tool.manager.store)

    def maybe_handle(self, body: dict[str, Any] | None) -> dict[str, Any] | None:
        """
        Memory 操作を処理したら応答を返す。対象外 / Flag OFF は呼び出し側で判定。
        """
        raw = body if isinstance(body, dict) else {}
        message = _message_of(raw)
        if not message:
            return None

        user_id = _resolve_user_id(raw)
        result = self.tool.dispatch(user_id, message)
        if result is None:
            return None

        session_id = str(raw.get("session_id") or uuid4())
        reply = str(result.get("message") or "")
        return {
            "ok": bool(result.get("ok", True)),
            "reply": reply,
            "message": reply,
            "agent": "memory",
            "mode": raw.get("mode") or "chat",
            "session_id": session_id,
            "orchestrator": False,
            "platform": "v6-memory",
            "meta": {
                "memory": True,
                "memory_action": result.get("action"),
                "memory_saved": bool(result.get("saved")),
                "auto_save": False,
                "consent_required": True,
                "history_touched": False,
                "tool_manager": False,
                "memory_result": {
                    k: v
                    for k, v in result.items()
                    if k not in ("message",)
                },
            },
        }

    def enrich_body(self, body: dict[str, Any] | None) -> dict[str, Any]:
        """
        通常 Conversation 向けに Retriever 結果を Context として付与。
        History には書かない。Agent コードは変更せず message 先頭へ注入。
        """
        raw = dict(body) if isinstance(body, dict) else {}
        user_id = _resolve_user_id(raw)
        block = self.retriever.as_context_block(user_id)
        raw["_memory_user_id"] = user_id
        raw["_memory_context"] = block
        raw["_memory_snapshot"] = self.retriever.as_dict(user_id)

        if not block:
            return raw

        msg = _message_of(raw)
        if not msg:
            return raw

        # 二重注入防止
        if msg.startswith("[User Memory"):
            return raw

        enriched = (
            f"{block}\n\n"
            f"[Current user message]\n{msg}"
        )
        # 元メッセージキーを優先して上書き
        if "message" in raw or not any(k in raw for k in ("text", "query", "prompt")):
            raw["message"] = enriched
        elif "text" in raw:
            raw["text"] = enriched
        elif "query" in raw:
            raw["query"] = enriched
        else:
            raw["prompt"] = enriched
        return raw

    def attach_meta(self, response: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
        """通常応答に Memory meta を付与（History 非変更）。"""
        out = dict(response) if isinstance(response, dict) else {"ok": True, "reply": str(response)}
        meta = dict(out.get("meta") or {})
        snap = body.get("_memory_snapshot") if isinstance(body, dict) else None
        meta["memory"] = {
            "enabled": True,
            "auto_save": False,
            "injected": bool((body or {}).get("_memory_context")),
            "count": (snap or {}).get("count", 0) if isinstance(snap, dict) else 0,
            "history_separated": True,
        }
        out["meta"] = meta
        return out


_GATEWAY: MemoryGateway | None = None
_GATEWAY_LOCK = threading.Lock()


def get_memory_gateway() -> MemoryGateway:
    global _GATEWAY
    with _GATEWAY_LOCK:
        if _GATEWAY is None:
            _GATEWAY = MemoryGateway()
        return _GATEWAY


def reset_memory_gateway_for_tests(tool: MemoryTool | None = None) -> MemoryGateway:
    global _GATEWAY
    with _GATEWAY_LOCK:
        _GATEWAY = MemoryGateway(tool=tool) if tool is not None else MemoryGateway()
        return _GATEWAY
