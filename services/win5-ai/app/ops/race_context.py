# -*- coding: utf-8 -*-
"""Race context extraction — surface / distance / going for stats & heatmaps."""
from __future__ import annotations

from typing import Any

from ..stats.evaluator import normalize_going


_GOING_KEYS = (
    "going",
    "track_condition",
    "condition",
    "baba",
    "track",
    "馬場",
)
_SURFACE_KEYS = ("surface", "target_surface", "race_surface")
_DISTANCE_KEYS = ("distance", "target_distance", "race_distance")


def _first_value(sources: list[dict[str, Any]], keys: tuple[str, ...]) -> Any:
    for src in sources:
        if not isinstance(src, dict):
            continue
        for key in keys:
            val = src.get(key)
            if val not in (None, "", "unknown", "Unknown"):
                return val
    return None


def _parse_distance(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        d = int(float(value))
    except (TypeError, ValueError):
        return None
    return d if d > 0 else None


def extract_race_context(
    *,
    result: dict[str, Any] | None = None,
    bundle: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge race context from result row, CSV extras, and PredictionBundle."""
    info = (bundle or {}).get("race_info") or {}
    explain = (bundle or {}).get("explain") or {}
    meta = explain.get("meta") or {}
    result_json = {}
    if result and result.get("result_json"):
        raw = result.get("result_json")
        if isinstance(raw, dict):
            result_json = raw
        elif isinstance(raw, str):
            try:
                import json

                result_json = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                result_json = {}

    sources = [
        result or {},
        result_json,
        extra or {},
        info,
        meta,
        explain,
        bundle or {},
    ]

    surface = _first_value(sources, _SURFACE_KEYS)
    distance = _parse_distance(_first_value(sources, _DISTANCE_KEYS))
    going_raw = _first_value(sources, _GOING_KEYS)
    going = normalize_going(going_raw)

    out: dict[str, Any] = {}
    if surface not in (None, ""):
        out["surface"] = surface
    if distance is not None:
        out["distance"] = distance
    if going:
        out["going"] = going
    return out


def apply_context_to_result_row(row: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    merged = dict(row)
    for key in ("surface", "distance", "going"):
        if merged.get(key) in (None, "", "unknown"):
            if ctx.get(key) not in (None, ""):
                merged[key] = ctx[key]
    return merged
