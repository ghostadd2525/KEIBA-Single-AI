# -*- coding: utf-8 -*-
"""A1 HTTP handlers — Application facade over Consumer library."""
from __future__ import annotations

import time
from typing import Any, Callable

from app.consumer.core_client import InMemoryCoreClient
from app.consumer.decision_service.dto import version_info_dict
from app.consumer.flags import snapshot_all_flags
from app.consumer.single_api import ConsumerDisabledError, build_single_response
from app.service_integration.config import SingleServiceConfig
from app.service_integration.logging_util import log_event
from app.service_integration.metrics import METRICS
from app.service_integration.openapi import openapi_document
from app.service_integration.serialize import envelope_err, envelope_ok, serialize_single_response
from app.service_integration.validation import RequestValidationError, validate_single_response_request


HandlerResult = tuple[int, dict[str, Any]]


def handle_health(cfg: SingleServiceConfig | None = None) -> HandlerResult:
    cfg = cfg or SingleServiceConfig.from_env()
    return 200, envelope_ok(
        {
            "status": "ok" if cfg.http_enabled else "disabled",
            "service": cfg.service_name,
            "version": cfg.service_version,
            "http_enabled": cfg.http_enabled,
            "flags": snapshot_all_flags(),
            "consumer_version": version_info_dict(),
            "platform": "CorePlatformVersion1",
            "single_ai": "SingleAIVersion1",
        }
    )


def handle_metrics() -> HandlerResult:
    return 200, envelope_ok(METRICS.snapshot())


def handle_openapi(cfg: SingleServiceConfig | None = None) -> HandlerResult:
    # Raw OpenAPI document (no ok/data envelope) for tooling compatibility.
    return 200, openapi_document(cfg)


def handle_single_response(
    body: dict[str, Any] | None,
    *,
    cfg: SingleServiceConfig | None = None,
    authorized: bool = True,
) -> HandlerResult:
    cfg = cfg or SingleServiceConfig.from_env()
    path = "/v1/single/response"
    t0 = time.perf_counter()

    if not cfg.http_enabled:
        status, err = envelope_err("SERVICE_DISABLED", "SINGLE_AI_HTTP_ENABLED is off", status=503)
        METRICS.record(path, ok=False, latency_ms=(time.perf_counter() - t0) * 1000)
        log_event("response_disabled")
        return status, err

    if cfg.require_api_key and not authorized:
        status, err = envelope_err("UNAUTHORIZED", "X-AI-Key required", status=401)
        METRICS.record(path, ok=False, latency_ms=(time.perf_counter() - t0) * 1000)
        log_event("response_unauthorized")
        return status, err

    try:
        req = validate_single_response_request(body)
    except RequestValidationError as e:
        status, err = envelope_err(e.code, e.message, status=400)
        METRICS.record(path, ok=False, latency_ms=(time.perf_counter() - t0) * 1000)
        log_event("response_validation_error", code=e.code, message=e.message)
        return status, err

    locale = req["locale"] or cfg.default_locale
    client = InMemoryCoreClient({req["race_id"]: req["core_payload"]})

    try:
        resp = build_single_response(
            client,
            req["race_id"],
            force=req["force"],
            include_tickets=req["include_tickets"],
            include_presentation=req["include_presentation"],
            locale=locale,
        )
        data = serialize_single_response(resp)
        latency_ms = (time.perf_counter() - t0) * 1000
        METRICS.record(path, ok=True, latency_ms=latency_ms)
        log_event(
            "response_ok",
            race_id=req["race_id"],
            latency_ms=round(latency_ms, 3),
            include_tickets=req["include_tickets"],
            include_presentation=req["include_presentation"],
        )
        return 200, envelope_ok(
            data,
            meta={
                "service": cfg.service_name,
                "service_version": cfg.service_version,
                "latency_ms": round(latency_ms, 3),
            },
        )
    except ConsumerDisabledError as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        METRICS.record(path, ok=False, latency_ms=latency_ms)
        log_event("response_consumer_disabled", race_id=req["race_id"])
        return envelope_err(
            "CONSUMER_DISABLED",
            str(e) or "W_CONSUMER_SINGLE_ENABLED is OFF (use force=true for Shadow)",
            status=503,
        )
    except Exception as e:  # noqa: BLE001 — Application boundary
        latency_ms = (time.perf_counter() - t0) * 1000
        METRICS.record(path, ok=False, latency_ms=latency_ms)
        log_event("response_error", error=str(e), race_id=req["race_id"])
        return envelope_err("INTERNAL_ERROR", str(e), status=500)


def try_dispatch_get(
    path: str,
    *,
    cfg: SingleServiceConfig | None = None,
) -> HandlerResult | None:
    """Return HandlerResult if path is owned by service_integration, else None."""
    if path == "/v1/single/health":
        return handle_health(cfg)
    if path == "/v1/single/metrics":
        return handle_metrics()
    if path == "/v1/single/openapi.json":
        return handle_openapi(cfg)
    return None


def try_dispatch_post(
    path: str,
    body: dict[str, Any] | None,
    *,
    authorized: bool,
    cfg: SingleServiceConfig | None = None,
) -> HandlerResult | None:
    if path == "/v1/single/response":
        return handle_single_response(body, cfg=cfg, authorized=authorized)
    return None


# Typing helper for main.py wiring
DispatchGet = Callable[[str], HandlerResult | None]
DispatchPost = Callable[[str, dict[str, Any] | None, bool], HandlerResult | None]
