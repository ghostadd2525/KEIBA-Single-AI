# -*- coding: utf-8 -*-
"""Consumer-layer feature flags (ADR-011 / V109 C1).

Defaults OFF. Does not affect Prediction Engine or Core Contract.
"""
from __future__ import annotations

import os
from typing import Any

from app.decision.flags import snapshot_flags as decision_snapshot_flags


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def consumer_single_enabled() -> bool:
    return _env_bool("W_CONSUMER_SINGLE_ENABLED", False)


def consumer_presentation_enabled() -> bool:
    """Structured Presentation — default OFF; Shadow via force."""
    return _env_bool("W_CONSUMER_PRESENTATION_ENABLED", False)


def consumer_ticket_enabled() -> bool:
    """Ticket Policy Resolver — default OFF; Shadow via force_ticket."""
    return _env_bool("W_CONSUMER_TICKET_ENABLED", False)


def core_payload_v103_enabled() -> bool:
    """PROMOTE fields visibility — separate Gate; default OFF."""
    return _env_bool("W_CORE_PAYLOAD_V103", False)


def snapshot_consumer_flags() -> dict[str, bool]:
    return {
        "W_CONSUMER_SINGLE_ENABLED": consumer_single_enabled(),
        "W_CONSUMER_PRESENTATION_ENABLED": consumer_presentation_enabled(),
        "W_CONSUMER_TICKET_ENABLED": consumer_ticket_enabled(),
        "W_CORE_PAYLOAD_V103": core_payload_v103_enabled(),
    }


def snapshot_all_flags() -> dict[str, bool]:
    out = snapshot_consumer_flags()
    out.update(decision_snapshot_flags())
    return out


def as_public_dict() -> dict[str, Any]:
    return {
        "consumer_flags": snapshot_consumer_flags(),
        "decision_layer_flags": decision_snapshot_flags(),
        "defaults_off": True,
    }
