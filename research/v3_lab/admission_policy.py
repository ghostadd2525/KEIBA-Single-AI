# -*- coding: utf-8 -*-
"""Version 3 Lab — Admission Policy (P3).

AP-V3-A Banded Deep Admit: capacity-aware candidate pool from anonymous
signals (model_rank / win_prob / field_size) plus optional Representation
features/embeddings when present.

No result / payout / finish columns.
"""
from __future__ import annotations

import math
from typing import Any

POLICY_ID = "AP-V3-A-banded-deep"
ADMISSION_ID = "v3-adm-p3-v1"
CONTRACT_ID = "v3-lab-admission/2.0"
DEEP_K_MAX = 2


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        n = float(v)
        if not math.isfinite(n):
            return default
        return n
    except Exception:
        return default


def _i(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def _rank(runner: dict[str, Any]) -> int:
    return _i(runner.get("model_rank", runner.get("rank")), 999)


def _horse_key(runner: dict[str, Any]) -> str:
    return str(runner.get("horse_id") or runner.get("horse_number") or "")


def _feat(runner: dict[str, Any], key: str, default: float = 0.0) -> float:
    feats = runner.get("features") if isinstance(runner.get("features"), dict) else {}
    if key in feats:
        return _f(feats.get(key), default)
    return default


def _field_size(context: dict[str, Any], runners: list[dict[str, Any]]) -> int:
    fs = _i(context.get("field_size"), 0)
    if fs > 0:
        return fs
    return max(len(runners), 1)


def _base_capacity(field_size: int) -> int:
    """Core band size before deep extras (always includes top ranks)."""
    n = max(field_size, 1)
    if n <= 2:
        return n
    if n <= 8:
        return min(n, 5)
    if n <= 12:
        return 6
    return 7


def _margin_thin(sorted_runners: list[dict[str, Any]]) -> bool:
    if len(sorted_runners) < 2:
        return False
    p1 = _f(sorted_runners[0].get("win_prob"), 0.0)
    p2 = _f(sorted_runners[1].get("win_prob"), 0.0)
    # Prefer representation residual when present
    r1 = abs(_feat(sorted_runners[0], "F_V3_20_log_odds_residual", 0.0))
    r2 = abs(_feat(sorted_runners[1], "F_V3_20_log_odds_residual", 0.0))
    if r1 > 0 or r2 > 0:
        return max(r1, r2) >= 0.35
    return abs(p1 - p2) < 0.08


def _route_score(runner: dict[str, Any]) -> float:
    """Higher = more useful deep admit. Uses Representation when available."""
    emb = runner.get("embedding")
    if isinstance(emb, list) and emb:
        # Prefer form / odds residual / popularity crowd dimensions if present
        feats = runner.get("features") if isinstance(runner.get("features"), dict) else {}
        return (
            _f(feats.get("F_V3_10_decayed_form_proxy"), 0.0)
            + abs(_f(feats.get("F_V3_20_log_odds_residual"), 0.0))
            + _f(feats.get("F_V3_21_popularity_crowd"), 0.0)
            + _f(feats.get("F_V3_rank_inv"), 0.0)
        )
    return _f(runner.get("win_prob"), 0.0) + (1.0 / max(_rank(runner), 1))


def _deep_extra(context: dict[str, Any], sorted_runners: list[dict[str, Any]], field_size: int) -> int:
    extra = 0
    if field_size >= 12:
        extra += 1
    # field_size_norm from representation (or derive)
    f01 = 0.0
    if sorted_runners:
        f01 = _feat(sorted_runners[0], "F_V3_01_field_size_norm", 0.0)
    if f01 <= 0.0:
        f01 = min(1.0, max(0.0, (field_size - 8) / 10.0))
    if f01 >= 0.4:
        extra += 1
    if _margin_thin(sorted_runners):
        extra += 1
    ctx_cap = context.get("admission_capacity_max")
    if ctx_cap is not None:
        # optional hard override still respects DEEP_K_MAX via caller
        pass
    return min(DEEP_K_MAX, extra)


def build_candidate_pool(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (candidate_pool, journal) for AP-V3-A."""
    field_size = _field_size(context, runners)
    sorted_runners = sorted(list(runners or []), key=_rank)
    n = len(sorted_runners)
    base = _base_capacity(field_size)
    deep = _deep_extra(context, sorted_runners, field_size)
    capacity_max = min(n, base + deep)
    # Optional context ceiling
    if context.get("admission_capacity_max") is not None:
        capacity_max = min(capacity_max, max(1, _i(context.get("admission_capacity_max"), capacity_max)))

    # Core band: top `base` by rank
    core_n = min(base, n, capacity_max)
    admitted: list[dict[str, Any]] = [dict(r) for r in sorted_runners[:core_n]]
    admitted_keys = {_horse_key(r) for r in admitted}
    rejected_reason: dict[str, str] = {}

    # Deep band: fill remaining slots by route_score among remaining
    slots_left = capacity_max - len(admitted)
    if slots_left > 0:
        deep_candidates = [r for r in sorted_runners[core_n:] if _horse_key(r) not in admitted_keys]
        deep_candidates.sort(key=_route_score, reverse=True)
        for r in deep_candidates[:slots_left]:
            row = dict(r)
            row["admission_band"] = "deep"
            admitted.append(row)
            admitted_keys.add(_horse_key(row))
        for r in deep_candidates[slots_left:]:
            rejected_reason[_horse_key(r)] = "deep_band_closed"
    else:
        for r in sorted_runners[core_n:]:
            rejected_reason[_horse_key(r)] = "capacity"

    for r in admitted:
        if "admission_band" not in r:
            r["admission_band"] = "core"

    # Stable order by model_rank for downstream stubs
    admitted.sort(key=_rank)

    used_repr = any(
        isinstance(r.get("features"), dict) and any(str(k).startswith("F_V3_") for k in (r.get("features") or {}))
        for r in sorted_runners
    ) or any(isinstance(r.get("embedding"), list) and r.get("embedding") for r in sorted_runners)

    journal = {
        "policy_id": POLICY_ID,
        "admission_id": ADMISSION_ID,
        "contract": CONTRACT_ID,
        "field_size": field_size,
        "base_capacity": base,
        "deep_extra": deep,
        "capacity_max": capacity_max,
        "admitted": [_horse_key(r) for r in admitted],
        "rejected_reason": rejected_reason,
        "admitted_count": len(admitted),
        "rejected_count": len(rejected_reason),
        "used_representation": used_repr,
        "leak_inputs": False,
        "deep_k_max": DEEP_K_MAX,
    }
    return admitted, journal


__all__ = [
    "POLICY_ID",
    "ADMISSION_ID",
    "CONTRACT_ID",
    "DEEP_K_MAX",
    "build_candidate_pool",
]
