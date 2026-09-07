# -*- coding: utf-8 -*-
"""A1 Response serialization + error envelope."""
from __future__ import annotations

from typing import Any


def envelope_ok(data: Any, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": True, "data": data}
    if meta:
        out["meta"] = meta
    return out


def envelope_err(
    code: str,
    message: str,
    *,
    status: int = 400,
    details: Any = None,
    trace_id: str | None = None,
) -> tuple[int, dict[str, Any]]:
    err: dict[str, Any] = {"code": code, "message": message, "details": details}
    if trace_id:
        err["trace_id"] = trace_id
    return status, {"ok": False, "error": err}


def serialize_single_response(resp: dict[str, Any]) -> dict[str, Any]:
    """Pass-through JSON-serializable Consumer response (no semantic rewrite)."""
    # Ensure forbidden fields stay null if present
    out = dict(resp)
    out["natural_explanation"] = None
    out["decision_reason"] = None
    return out
