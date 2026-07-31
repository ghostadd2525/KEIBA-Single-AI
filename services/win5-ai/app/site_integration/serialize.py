# -*- coding: utf-8 -*-
"""I1 Response serialization + site error envelope."""
from __future__ import annotations

from typing import Any


SITE_SCHEMA = "site-integration/single/v1"


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
) -> tuple[int, dict[str, Any]]:
    return status, {
        "ok": False,
        "error": {"code": code, "message": message, "details": details},
    }


def wrap_single_for_site(
    consumer_resp: dict[str, Any],
    *,
    race_id: str,
    api_version: str,
) -> dict[str, Any]:
    """Pass-through Consumer response with site envelope fields. No semantic rewrite."""
    out = dict(consumer_resp)
    out["natural_explanation"] = None
    out["decision_reason"] = None
    out.setdefault("race_id", race_id)
    return {
        "schema": SITE_SCHEMA,
        "race_id": race_id,
        "api_version": api_version,
        "single": out,
    }
