# -*- coding: utf-8 -*-
"""I1 HTTP handlers — Existing Site → Single API facade."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any
from urllib.parse import unquote

from app.consumer.core_client import InMemoryCoreClient
from app.consumer.decision_service.dto import version_info_dict
from app.consumer.flags import snapshot_all_flags
from app.consumer.single_api import ConsumerDisabledError, build_single_response
from app.site_integration.config import SiteIntegrationConfig
from app.site_integration.openapi import openapi_document
from app.site_integration.serialize import (
    envelope_err,
    envelope_ok,
    wrap_single_for_site,
)
from app.site_integration.validation import SiteValidationError, validate_site_single_request

HandlerResult = tuple[int, dict[str, Any]]
_EXEC = ThreadPoolExecutor(max_workers=8)


def handle_health(cfg: SiteIntegrationConfig | None = None) -> HandlerResult:
    cfg = cfg or SiteIntegrationConfig.from_env()
    return 200, envelope_ok(
        {
            "status": "ok" if cfg.http_enabled else "disabled",
            "service": cfg.service_name,
            "api_version": cfg.api_version,
            "http_enabled": cfg.http_enabled,
            "timeout_ms_default": cfg.default_timeout_ms,
            "flags": snapshot_all_flags(),
            "consumer_version": version_info_dict(),
            "platform": "CorePlatformVersion1",
            "single_ai": "SingleAIVersion1",
            "flow": "Site → HTTP → Single API → Core",
        }
    )


def handle_version(cfg: SiteIntegrationConfig | None = None) -> HandlerResult:
    cfg = cfg or SiteIntegrationConfig.from_env()
    return 200, envelope_ok(
        {
            "api_version": cfg.api_version,
            "schema": "site-integration/single/v1",
            "platform": "CorePlatformVersion1",
            "single_ai": "SingleAIVersion1",
            "consumer": version_info_dict(),
            "a1_service": "single-ai-http",
        }
    )


def handle_openapi(cfg: SiteIntegrationConfig | None = None) -> HandlerResult:
    return 200, openapi_document(cfg)


def _run_single(req: dict[str, Any], locale: str) -> dict[str, Any]:
    client = InMemoryCoreClient({req["race_id"]: req["core_payload"]})
    return build_single_response(
        client,
        req["race_id"],
        force=req["force"],
        include_tickets=req["include_tickets"],
        include_presentation=req["include_presentation"],
        locale=locale,
    )


def handle_site_single(
    body: dict[str, Any] | None,
    *,
    path_race_id: str | None = None,
    cfg: SiteIntegrationConfig | None = None,
    authorized: bool = True,
    header_timeout_ms: int | None = None,
) -> HandlerResult:
    cfg = cfg or SiteIntegrationConfig.from_env()

    if not cfg.http_enabled:
        return envelope_err("SERVICE_DISABLED", "SITE_SINGLE_HTTP_ENABLED is off", status=503)

    if cfg.require_api_key and not authorized:
        return envelope_err("UNAUTHORIZED", "X-AI-Key required", status=401)

    try:
        req = validate_site_single_request(
            body,
            path_race_id=path_race_id,
            default_timeout_ms=cfg.default_timeout_ms,
            max_timeout_ms=cfg.max_timeout_ms,
        )
    except SiteValidationError as e:
        return envelope_err(e.code, e.message, status=400)

    timeout_ms = req["timeout_ms"]
    if header_timeout_ms is not None:
        timeout_ms = min(max(100, int(header_timeout_ms)), cfg.max_timeout_ms)

    locale = req["locale"] or cfg.default_locale
    t0 = time.perf_counter()
    fut = _EXEC.submit(_run_single, req, locale)
    try:
        resp = fut.result(timeout=timeout_ms / 1000.0)
    except FuturesTimeout:
        return envelope_err(
            "TIMEOUT",
            f"Single API exceeded {timeout_ms}ms",
            status=504,
            details={"timeout_ms": timeout_ms, "race_id": req["race_id"]},
        )
    except ConsumerDisabledError as e:
        return envelope_err(
            "CONSUMER_DISABLED",
            str(e) or "W_CONSUMER_SINGLE_ENABLED is OFF (use force=true for Shadow)",
            status=503,
        )
    except Exception as e:  # noqa: BLE001
        return envelope_err("INTERNAL_ERROR", str(e), status=500)

    latency_ms = (time.perf_counter() - t0) * 1000
    data = wrap_single_for_site(resp, race_id=req["race_id"], api_version=cfg.api_version)
    return 200, envelope_ok(
        data,
        meta={
            "service": cfg.service_name,
            "api_version": cfg.api_version,
            "latency_ms": round(latency_ms, 3),
            "timeout_ms": timeout_ms,
            "race_meta": req["race_meta"],
            "platform": "CorePlatformVersion1",
            "single_ai": "SingleAIVersion1",
        },
    )


def try_dispatch_get(path: str, *, cfg: SiteIntegrationConfig | None = None) -> HandlerResult | None:
    if path == "/v1/site/health":
        return handle_health(cfg)
    if path == "/v1/site/version":
        return handle_version(cfg)
    if path == "/v1/site/openapi.json":
        return handle_openapi(cfg)
    return None


def try_dispatch_post(
    path: str,
    body: dict[str, Any] | None,
    *,
    authorized: bool,
    cfg: SiteIntegrationConfig | None = None,
    header_timeout_ms: int | None = None,
) -> HandlerResult | None:
    if path == "/v1/site/single":
        return handle_site_single(
            body,
            cfg=cfg,
            authorized=authorized,
            header_timeout_ms=header_timeout_ms,
        )
    prefix = "/v1/site/single/"
    if path.startswith(prefix) and path != prefix:
        race_id = unquote(path[len(prefix) :])
        if "/" in race_id:
            return None
        return handle_site_single(
            body,
            path_race_id=race_id,
            cfg=cfg,
            authorized=authorized,
            header_timeout_ms=header_timeout_ms,
        )
    return None
