# -*- coding: utf-8 -*-
"""Decision Layer feature flags (ADR-008).

All default OFF. Sub-flags require W_DECISION_LAYER_ENABLED=true.
Does not affect Prediction Engine.
"""
from __future__ import annotations

import os
from typing import Any


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def decision_layer_enabled() -> bool:
    return _env_bool("W_DECISION_LAYER_ENABLED", False)


def decision_ticket_enabled() -> bool:
    return decision_layer_enabled() and _env_bool("W_DECISION_TICKET", False)


def decision_pool_enabled() -> bool:
    return decision_layer_enabled() and _env_bool("W_DECISION_POOL", False)


def decision_explain_enabled() -> bool:
    return decision_layer_enabled() and _env_bool("W_DECISION_EXPLAIN", False)


def decision_risk_enabled() -> bool:
    return decision_layer_enabled() and _env_bool("W_DECISION_RISK", False)


def decision_conf_display_enabled() -> bool:
    return decision_layer_enabled() and _env_bool("W_DECISION_CONF_DISPLAY", False)


def snapshot_flags() -> dict[str, bool]:
    return {
        "W_DECISION_LAYER_ENABLED": decision_layer_enabled(),
        "W_DECISION_TICKET": decision_ticket_enabled(),
        "W_DECISION_POOL": decision_pool_enabled(),
        "W_DECISION_EXPLAIN": decision_explain_enabled(),
        "W_DECISION_RISK": decision_risk_enabled(),
        "W_DECISION_CONF_DISPLAY": decision_conf_display_enabled(),
    }


def shadow_all_on_env() -> dict[str, str]:
    """Env overlay for Shadow Decision ON (research only; not Production)."""
    return {
        "W_DECISION_LAYER_ENABLED": "true",
        "W_DECISION_TICKET": "true",
        "W_DECISION_POOL": "true",
        "W_DECISION_EXPLAIN": "true",
        "W_DECISION_RISK": "true",
        "W_DECISION_CONF_DISPLAY": "true",
    }


def as_public_dict() -> dict[str, Any]:
    return {"decision_layer_flags": snapshot_flags(), "defaults_off": True}
