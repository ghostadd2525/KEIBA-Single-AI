# -*- coding: utf-8 -*-
"""Single AI — shared response models (M2 skeleton).

Plain dict builders only. No inference, no computation.
Schema follows S-04 prediction_response_schema.csv (Bet items deferred to M3+).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ai_platform.single import PRODUCT_VERSION


def prediction_response(
    *,
    race_id: str,
    ranking: dict[str, Any] | None,
    confidence: dict[str, Any] | None,
    core_version: str,
    model_version: str = "core-delegated",
    warnings: list[str] | None = None,
    bets: dict[str, Any] | None = None,
    feature_source: str | None = None,
) -> dict[str, Any]:
    """Assemble the S-04 common response envelope (pass-through only)."""
    bets = bets or {}
    return {
        "RaceID": race_id,
        "GeneratedAt": datetime.now().isoformat(timespec="seconds"),
        "ModelVersion": model_version,
        "CoreVersion": core_version,
        "ProductVersion": PRODUCT_VERSION,
        "feature_source": feature_source,
        "ranking": (ranking or {}).get("ranking", []),
        "confidence": {
            k: v
            for k, v in (confidence or {}).items()
            if k in ("overall", "per_horse", "factors")
        },
        "items": list(bets.get("slips") or []),
        "warnings": (warnings or []) + list(bets.get("warnings") or []),
        "skipped": list(bets.get("skipped") or []),
    }


def error_response(*, race_id: str | None, error_code: str, message: str) -> dict[str, Any]:
    return {
        "RaceID": race_id,
        "error_code": error_code,
        "message": message,
        "ProductVersion": PRODUCT_VERSION,
    }
