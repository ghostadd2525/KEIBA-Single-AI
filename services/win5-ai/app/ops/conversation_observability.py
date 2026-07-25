# -*- coding: utf-8 -*-
"""
Conversation Observability (V5 Production) — ops layer only.

Does NOT modify Conversation Platform / Agents / Knowledge Runtime /
Security Guard / Prediction API. Metrics are recorded at the API boundary
(main.py) and via read-only health probes.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _ops_dir() -> Path:
    env = (os.environ.get("EXPECT_AI_OPS_DIR") or "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "var" / "ops"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 2)
    idx = min(len(sorted_vals) - 1, max(0, int(round((p / 100.0) * (len(sorted_vals) - 1)))))
    return round(sorted_vals[idx], 2)


class ConversationObservability:
    """In-process rolling metrics + JSONL persistence."""

    def __init__(self, *, window: int = 500) -> None:
        self._lock = threading.Lock()
        self._window = max(50, window)
        self._latencies: deque[float] = deque(maxlen=self._window)
        self._ollama_latencies: deque[float] = deque(maxlen=self._window)
        self._knowledge_latencies: deque[float] = deque(maxlen=self._window)
        self._counts = {
            "request_count": 0,
            "success_count": 0,
            "error_count": 0,
            "review_count": 0,
            "explain_count": 0,
            "chat_count": 0,
            "ollama_timeout_count": 0,
            "ollama_error_count": 0,
            "knowledge_search_count": 0,
            "knowledge_retrieval_hit": 0,
            "knowledge_retrieval_miss": 0,
            "security_block_count": 0,
            "security_allow_count": 0,
        }
        self._tokens_in = 0
        self._tokens_out = 0
        self._last_model: str | None = None
        self._block_reasons: dict[str, int] = {}
        self._last_health: dict[str, Any] | None = None
        self._path = _ops_dir() / "conversation_metrics.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _append_jsonl(self, row: dict[str, Any]) -> None:
        try:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def record_response(self, result: dict[str, Any] | None, *, latency_ms: float) -> None:
        result = result if isinstance(result, dict) else {}
        agent = str(result.get("agent") or "")
        mode = str(result.get("mode") or "")
        intent = result.get("intent") if isinstance(result.get("intent"), dict) else {}
        intent_name = str((intent or {}).get("name") or "")
        llm = result.get("llm") if isinstance(result.get("llm"), dict) else {}
        tools = result.get("tools_used") if isinstance(result.get("tools_used"), list) else []
        fallback = str(result.get("fallback") or "")
        error_reason = result.get("error_reason")
        pred_meta = result.get("prediction_meta") if isinstance(result.get("prediction_meta"), dict) else {}

        is_block = (
            intent_name.endswith("_blocked")
            or fallback == "security_block"
            or error_reason == "security_block"
            or str(result.get("security_status") or "") == "blocked"
        )
        is_error = bool(
            result.get("disabled") is False
            and (
                error_reason
                or fallback in ("fail_open", "prediction_api_fail_open")
                or (pred_meta.get("error") and not result.get("orchestrator"))
            )
            and not is_block
        )
        # treat orchestrated replies as success unless explicit error/block
        if result.get("orchestrator") and not is_block and not error_reason:
            is_error = False
        if result.get("reply") and not is_block:
            is_error = False if result.get("orchestrator") else is_error

        with self._lock:
            self._counts["request_count"] += 1
            self._latencies.append(float(latency_ms))
            if is_block:
                self._counts["security_block_count"] += 1
                reason = str(
                    (result.get("security") or {}).get("reason")
                    if isinstance(result.get("security"), dict)
                    else error_reason or intent_name or "blocked"
                )
                self._block_reasons[reason] = self._block_reasons.get(reason, 0) + 1
            else:
                self._counts["security_allow_count"] += 1
                if is_error:
                    self._counts["error_count"] += 1
                else:
                    self._counts["success_count"] += 1

            if agent == "review" or mode == "review":
                self._counts["review_count"] += 1
            if agent in ("expert", "explain") or mode == "explain":
                self._counts["explain_count"] += 1
            if agent == "chat" or mode == "chat":
                self._counts["chat_count"] += 1

            if llm.get("ollama_called"):
                self._ollama_latencies.append(float(latency_ms))
                model = llm.get("model")
                if model:
                    self._last_model = str(model)
                tin = llm.get("tokens_input")
                tout = llm.get("tokens_output")
                if isinstance(tin, (int, float)):
                    self._tokens_in += int(tin)
                if isinstance(tout, (int, float)):
                    self._tokens_out += int(tout)
            if llm.get("error") or str(llm.get("error_reason") or "").startswith("timeout"):
                self._counts["ollama_error_count"] += 1
            if "timeout" in str(llm.get("error_reason") or "").lower() or fallback == "ollama_timeout":
                self._counts["ollama_timeout_count"] += 1

            knowledge_obj = (
                result.get("knowledge") if isinstance(result.get("knowledge"), dict) else {}
            )
            used_knowledge = any(
                str(t).lower() in ("knowledge", "knowledge_tool", "knowledge_api") for t in tools
            ) or bool(knowledge_obj.get("used"))
            if used_knowledge:
                self._counts["knowledge_search_count"] += 1
                self._knowledge_latencies.append(float(latency_ms))
                hits = knowledge_obj.get("hit_count")
                if hits is None and isinstance(result.get("citations"), list):
                    hits = len(result["citations"])
                if hits is not None and int(hits) > 0:
                    self._counts["knowledge_retrieval_hit"] += 1
                else:
                    self._counts["knowledge_retrieval_miss"] += 1

            row = {
                "ts": _now_iso(),
                "event": "conversation.observability",
                "latency_ms": round(float(latency_ms), 2),
                "agent": agent,
                "mode": mode,
                "intent": intent_name,
                "error": is_error,
                "security_block": is_block,
                "ollama_called": bool(llm.get("ollama_called")),
                "model": llm.get("model"),
                "tools_used": tools,
            }
        self._append_jsonl(row)

    def record_knowledge_probe(
        self,
        *,
        latency_ms: float,
        hit_count: int,
        top_k: int,
        ok: bool,
    ) -> None:
        with self._lock:
            self._counts["knowledge_search_count"] += 1
            self._knowledge_latencies.append(float(latency_ms))
            if ok and hit_count > 0:
                self._counts["knowledge_retrieval_hit"] += 1
            else:
                self._counts["knowledge_retrieval_miss"] += 1
            self._append_jsonl(
                {
                    "ts": _now_iso(),
                    "event": "conversation.observability.knowledge_probe",
                    "latency_ms": round(float(latency_ms), 2),
                    "hit_count": hit_count,
                    "top_k": top_k,
                    "ok": ok,
                }
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            lat = sorted(self._latencies)
            ollama_lat = sorted(self._ollama_latencies)
            know_lat = sorted(self._knowledge_latencies)
            req = self._counts["request_count"]
            err = self._counts["error_count"]
            error_rate = round(err / req, 4) if req else 0.0
            return {
                "generated_at": _now_iso(),
                "window": self._window,
                "conversation": {
                    "request_count": req,
                    "success_count": self._counts["success_count"],
                    "error_count": err,
                    "error_rate": error_rate,
                    "latency_ms": {
                        "p50": _percentile(lat, 50),
                        "p95": _percentile(lat, 95),
                        "p99": _percentile(lat, 99),
                        "samples": len(lat),
                    },
                    "review_count": self._counts["review_count"],
                    "explain_count": self._counts["explain_count"],
                    "chat_count": self._counts["chat_count"],
                },
                "ollama": {
                    "response_time_ms": {
                        "p50": _percentile(ollama_lat, 50),
                        "p95": _percentile(ollama_lat, 95),
                        "p99": _percentile(ollama_lat, 99),
                        "samples": len(ollama_lat),
                    },
                    "timeout_count": self._counts["ollama_timeout_count"],
                    "error_count": self._counts["ollama_error_count"],
                    "tokens_input": self._tokens_in,
                    "tokens_output": self._tokens_out,
                    "tokens_available": False,
                    "model_name": self._last_model,
                },
                "knowledge": {
                    "search_count": self._counts["knowledge_search_count"],
                    "search_latency_ms": {
                        "p50": _percentile(know_lat, 50),
                        "p95": _percentile(know_lat, 95),
                        "p99": _percentile(know_lat, 99),
                        "samples": len(know_lat),
                    },
                    "retrieval_hit": self._counts["knowledge_retrieval_hit"],
                    "retrieval_miss": self._counts["knowledge_retrieval_miss"],
                    "top_k": int(os.environ.get("CONVERSATION_KNOWLEDGE_TOP_K") or "5"),
                },
                "security": {
                    "block_count": self._counts["security_block_count"],
                    "allow_count": self._counts["security_allow_count"],
                    "block_reason": dict(self._block_reasons),
                },
            }


_default: ConversationObservability | None = None


def get_observability() -> ConversationObservability:
    global _default
    if _default is None:
        _default = ConversationObservability()
    return _default


def build_component_health() -> dict[str, Any]:
    """
    Extended Conversation Health — read-only probes.
    Does not mutate Platform / Prediction / Knowledge internals.
    """
    from ..conversation.v4 import health as v4_health
    from ..conversation.v4.flags import (
        knowledge_layer_enabled,
        knowledge_runtime_enabled,
        tool_layer_enabled,
        v4_platform_active,
    )

    started = time.perf_counter()
    base = v4_health()
    components: dict[str, Any] = {}

    # 1) Conversation API (this process answering health)
    components["conversation_api"] = {
        "ok": base.get("status") in ("ok", "disabled"),
        "status": base.get("status"),
        "detail": "orchestrator_health",
    }

    # 2) Ollama
    ollama = base.get("ollama") if isinstance(base.get("ollama"), dict) else {}
    if ollama.get("enabled"):
        components["ollama"] = {
            "ok": bool(ollama.get("reachable") or ollama.get("ok")),
            "reachable": ollama.get("reachable"),
            "models": ollama.get("models") or [],
            "error_reason": ollama.get("error_reason"),
        }
    else:
        components["ollama"] = {
            "ok": True,
            "skipped": True,
            "reason": "F_V4_CONVERSATION_OLLAMA off",
        }

    # 3) Knowledge Runtime (read-only search probe)
    top_k = int(os.environ.get("CONVERSATION_KNOWLEDGE_TOP_K") or "5")
    if knowledge_runtime_enabled() or knowledge_layer_enabled():
        t0 = time.perf_counter()
        try:
            from ..conversation.v4.knowledge.provider import KnowledgeProvider

            provider = KnowledgeProvider()
            out = provider.search("ops health probe", limit=top_k)
            ms = (time.perf_counter() - t0) * 1000
            hit_count = int(out.get("hit_count") or 0)
            get_observability().record_knowledge_probe(
                latency_ms=ms, hit_count=hit_count, top_k=top_k, ok=True
            )
            components["knowledge_runtime"] = {
                "ok": True,
                "enabled": knowledge_runtime_enabled(),
                "layer": knowledge_layer_enabled(),
                "search_latency_ms": round(ms, 2),
                "hit_count": hit_count,
                "top_k": top_k,
                "knowledge_runtime": bool(out.get("knowledge_runtime")),
            }
        except Exception as exc:
            ms = (time.perf_counter() - t0) * 1000
            get_observability().record_knowledge_probe(
                latency_ms=ms, hit_count=0, top_k=top_k, ok=False
            )
            components["knowledge_runtime"] = {
                "ok": False,
                "error": type(exc).__name__,
                "search_latency_ms": round(ms, 2),
            }
    else:
        components["knowledge_runtime"] = {
            "ok": True,
            "skipped": True,
            "reason": "knowledge flags off",
        }

    # 4) Tool Manager (flag surface — no structure change)
    components["tool_manager"] = {
        "ok": True if not v4_platform_active() else tool_layer_enabled(),
        "enabled": tool_layer_enabled(),
        "detail": "flag F_V4_TOOL_LAYER",
    }

    # 5) Prediction Connector (read-only soft check)
    pred_ok = True
    pred_detail: dict[str, Any] = {"read_only": True}
    try:
        from ..conversation.v4.prediction import PredictionConnector

        connector = PredictionConnector()
        # Prefer metadata/health if present; otherwise mark connected via platform claim
        if hasattr(connector, "health"):
            ph = connector.health()  # type: ignore[attr-defined]
            pred_detail["probe"] = ph
            pred_ok = bool(ph.get("ok", True)) if isinstance(ph, dict) else True
        else:
            plat = base.get("platform") if isinstance(base.get("platform"), dict) else {}
            pred_detail["prediction_api_connected"] = plat.get("prediction_api_connected")
            pred_detail["prediction_read_only"] = plat.get("prediction_read_only", True)
            pred_ok = True
    except Exception as exc:
        pred_ok = False
        pred_detail["error"] = type(exc).__name__
    components["prediction_connector"] = {"ok": pred_ok, **pred_detail}

    overall_ok = all(bool(c.get("ok")) for c in components.values())
    payload = {
        "status": "ok" if overall_ok else "degraded",
        "overall_ok": overall_ok,
        "components": components,
        "platform_health": base,
        "metrics": get_observability().snapshot(),
        "response_time_ms": round((time.perf_counter() - started) * 1000, 2),
        "generated_at": _now_iso(),
    }
    get_observability()._last_health = payload
    return payload


def evaluate_alerts(health: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Alert policy evaluation (ops layer)."""
    obs = get_observability().snapshot()
    health = health or get_observability()._last_health or build_component_health()
    alerts: list[dict[str, Any]] = []

    err_rate_thr = _env_float("CONV_ALERT_ERROR_RATE", 0.2)
    timeout_thr = int(_env_float("CONV_ALERT_OLLAMA_TIMEOUT", 3))

    ollama_timeouts = int((obs.get("ollama") or {}).get("timeout_count") or 0)
    if ollama_timeouts >= timeout_thr:
        alerts.append(
            {
                "id": "ALT-C01",
                "severity": "warning",
                "title": "Ollama timeout",
                "detail": f"timeout_count={ollama_timeouts}",
                "runbook": "docs/ops/conversation-observability-runbook.md#alt-c01",
            }
        )

    conv = obs.get("conversation") or {}
    err_rate = float(conv.get("error_rate") or 0)
    req = int(conv.get("request_count") or 0)
    if req >= 10 and err_rate >= err_rate_thr:
        alerts.append(
            {
                "id": "ALT-C02",
                "severity": "critical",
                "title": "Conversation error rate",
                "detail": f"error_rate={err_rate} threshold={err_rate_thr}",
                "runbook": "docs/ops/conversation-observability-runbook.md#alt-c02",
            }
        )

    kr = (health.get("components") or {}).get("knowledge_runtime") or {}
    if kr.get("ok") is False and not kr.get("skipped"):
        alerts.append(
            {
                "id": "ALT-C03",
                "severity": "warning",
                "title": "Knowledge Runtime failure",
                "detail": str(kr.get("error") or "knowledge probe failed"),
                "runbook": "docs/ops/conversation-observability-runbook.md#alt-c03",
            }
        )

    if health.get("overall_ok") is False:
        bad = [
            name
            for name, c in (health.get("components") or {}).items()
            if isinstance(c, dict) and c.get("ok") is False
        ]
        alerts.append(
            {
                "id": "ALT-C04",
                "severity": "critical",
                "title": "Conversation health check NG",
                "detail": "components=" + ",".join(bad) if bad else "overall degraded",
                "runbook": "docs/ops/conversation-observability-runbook.md#alt-c04",
            }
        )

    return alerts


def dashboard_payload() -> dict[str, Any]:
    health = build_component_health()
    metrics = get_observability().snapshot()
    alerts = evaluate_alerts(health)
    return {
        "schema": "expect-conversation-observability/1.0",
        "categories": {
            "conversation": metrics["conversation"],
            "ollama": metrics["ollama"],
            "knowledge": metrics["knowledge"],
            "security": metrics["security"],
        },
        "health": health,
        "alerts": alerts,
        "generated_at": _now_iso(),
    }
