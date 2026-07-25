# -*- coding: utf-8 -*-
"""Smoke test for Conversation Observability (ops layer)."""
from __future__ import annotations

from app.ops.conversation_observability import (
    ConversationObservability,
    evaluate_alerts,
    get_observability,
)


def test_record_and_snapshot_categories():
    obs = ConversationObservability(window=50)
    obs.record_response(
        {
            "orchestrator": True,
            "agent": "chat",
            "mode": "chat",
            "intent": {"name": "chat"},
            "reply": "hi",
            "llm": {"ollama_called": True, "used": True, "model": "qwen2.5:1.5b"},
            "tools_used": [],
        },
        latency_ms=12.5,
    )
    obs.record_response(
        {
            "orchestrator": True,
            "agent": "chat",
            "mode": "chat",
            "intent": {"name": "chat_blocked"},
            "fallback": "security_block",
            "reply": "blocked",
            "llm": {"ollama_called": False},
        },
        latency_ms=1.0,
    )
    snap = obs.snapshot()
    assert "conversation" in snap
    assert "ollama" in snap
    assert "knowledge" in snap
    assert "security" in snap
    assert snap["conversation"]["request_count"] == 2
    assert snap["conversation"]["chat_count"] == 2
    assert snap["security"]["block_count"] == 1
    assert snap["ollama"]["model_name"] == "qwen2.5:1.5b"


def test_alert_ids_stable():
    # empty window should not fire error-rate alert
    alerts = evaluate_alerts(
        {
            "overall_ok": True,
            "components": {
                "conversation_api": {"ok": True},
                "ollama": {"ok": True},
                "knowledge_runtime": {"ok": True},
                "tool_manager": {"ok": True},
                "prediction_connector": {"ok": True},
            },
        }
    )
    assert isinstance(alerts, list)
    # force health NG
    alerts_ng = evaluate_alerts(
        {
            "overall_ok": False,
            "components": {"ollama": {"ok": False}},
        }
    )
    ids = {a["id"] for a in alerts_ng}
    assert "ALT-C04" in ids
