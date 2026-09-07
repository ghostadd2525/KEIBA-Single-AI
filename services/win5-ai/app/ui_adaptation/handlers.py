# -*- coding: utf-8 -*-
"""UI1 HTTP handlers — View Mapper facade (no UI layout changes)."""
from __future__ import annotations

from typing import Any

from app.ui_adaptation.single_to_bundle import map_single_to_prediction_bundle

HandlerResult = tuple[int, dict[str, Any]]


def envelope_ok(data: Any, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": True, "data": data}
    if meta:
        out["meta"] = meta
    return out


def envelope_err(code: str, message: str, *, status: int = 400) -> HandlerResult:
    return status, {"ok": False, "error": {"code": code, "message": message, "details": None}}


def _resolve_source(body: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(body.get("single_response"), dict):
        return body["single_response"]
    if isinstance(body.get("single"), dict):
        # site wrap or consumer fragment
        if body.get("schema") == "site-integration/single/v1" or "single" in body:
            return body
        return body["single"]
    if body.get("schema") == "site-integration/single/v1":
        return body
    if isinstance(body.get("core_payload"), dict):
        return {
            "core_payload": body["core_payload"],
            "race_id": body.get("race_id") or body["core_payload"].get("race_id"),
        }
    if isinstance(body.get("prediction"), dict):
        return body
    return None


def handle_map_prediction_bundle(
    body: dict[str, Any] | None,
    *,
    authorized: bool = True,
    require_api_key: bool = True,
) -> HandlerResult:
    if require_api_key and not authorized:
        return envelope_err("UNAUTHORIZED", "X-AI-Key required", status=401)
    if not isinstance(body, dict):
        return envelope_err("BAD_REQUEST", "JSON object required")

    source = _resolve_source(body)
    if source is None:
        return envelope_err(
            "BAD_REQUEST",
            "single_response, single, core_payload, or prediction required",
        )

    race_info = body.get("race_info") if isinstance(body.get("race_info"), dict) else None
    base_bundle = body.get("base_bundle") if isinstance(body.get("base_bundle"), dict) else None
    race_id = body.get("race_id")

    try:
        bundle = map_single_to_prediction_bundle(
            source,
            race_id=str(race_id) if race_id else None,
            race_info=race_info,
            base_bundle=base_bundle,
        )
    except Exception as e:  # noqa: BLE001
        return envelope_err("MAP_ERROR", str(e), status=500)

    return 200, envelope_ok(
        bundle,
        meta={
            "service": "ui-adaptation",
            "phase": "UI1",
            "view": "prediction-bundle/2.0",
            "layout_changed": False,
            "internal_terms_exposed": False,
        },
    )


def try_dispatch_post(
    path: str,
    body: dict[str, Any] | None,
    *,
    authorized: bool,
) -> HandlerResult | None:
    if path == "/v1/ui/prediction-bundle":
        return handle_map_prediction_bundle(body, authorized=authorized)
    return None


def try_dispatch_get(path: str) -> HandlerResult | None:
    if path == "/v1/ui/health":
        return 200, envelope_ok(
            {
                "status": "ok",
                "phase": "UI1",
                "mapper": "single_to_prediction_bundle",
                "ui_layout_changed": False,
            }
        )
    return None
