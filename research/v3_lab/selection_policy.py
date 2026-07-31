# -*- coding: utf-8 -*-
"""Version 3 Lab — Selection Policy (P4).

SEL-V3-RO Reorder-only: reorder Candidate Pool without Rescue.
Invariants:
  - no horses added from outside the pool
  - no NEAR / winner-search triggers
  - |selected| == |pool| when capacity_n is None
"""
from __future__ import annotations

import math
from typing import Any

POLICY_ID = "SEL-V3-RO"
SELECTION_ID = "v3-sel-p4-v1"
CONTRACT_ID = "v3-lab-selection/2.0"


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


def _horse_key(runner: dict[str, Any]) -> str:
    return str(runner.get("horse_id") or runner.get("horse_number") or "")


def _feat(runner: dict[str, Any], key: str, default: float = 0.0) -> float:
    feats = runner.get("features") if isinstance(runner.get("features"), dict) else {}
    if key in feats:
        return _f(feats.get(key), default)
    return default


def reorder_score(runner: dict[str, Any]) -> float:
    """Anonymous reorder score (may differ from model_rank order)."""
    rank = _i(runner.get("model_rank", runner.get("rank")), 999)
    win_prob = _f(runner.get("win_prob"), 0.0)
    # Soft compress mitigation: blend model signal with form / odds residual / crowd
    form = _feat(runner, "F_V3_10_decayed_form_proxy", 0.0)
    residual = abs(_feat(runner, "F_V3_20_log_odds_residual", 0.0))
    crowd = _feat(runner, "F_V3_21_popularity_crowd", 0.0)
    rank_inv = _feat(runner, "F_V3_rank_inv", 1.0 / max(rank, 1))
    if form or residual or crowd:
        return 0.45 * win_prob + 0.25 * form + 0.20 * residual + 0.10 * crowd + 0.05 * rank_inv
    # Fallback without Representation: prefer win_prob to surface compress swaps
    return 0.85 * win_prob + 0.15 * (1.0 / max(rank, 1))


def _compute_swaps(before_keys: list[str], after_keys: list[str]) -> list[dict[str, Any]]:
    swaps: list[dict[str, Any]] = []
    if len(before_keys) != len(after_keys):
        return swaps
    pos_before = {k: i for i, k in enumerate(before_keys)}
    for new_i, key in enumerate(after_keys):
        old_i = pos_before.get(key)
        if old_i is None or old_i == new_i:
            continue
        if new_i < old_i:
            swaps.append(
                {
                    "horse_id": key,
                    "from_index": old_i,
                    "to_index": new_i,
                }
            )
    return swaps


def select_reorder(
    context: dict[str, Any],
    pool: list[dict[str, Any]],
    *,
    capacity_n: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reorder pool (SEL-V3-RO). Never admits outside horses."""
    pool_rows = [dict(r) for r in (pool or [])]
    pool_keys = [_horse_key(r) for r in pool_rows]
    pool_set = set(pool_keys)

    scored = sorted(
        pool_rows,
        key=lambda r: (-reorder_score(r), _i(r.get("model_rank"), 999), _horse_key(r)),
    )
    for i, row in enumerate(scored):
        row["selection_order"] = i + 1
        row["reorder_score"] = float(reorder_score(row))

    selected = scored
    truncated = False
    if capacity_n is not None and capacity_n >= 0:
        selected = scored[:capacity_n]
        truncated = len(selected) < len(scored)

    selected_keys = [_horse_key(r) for r in selected]
    # Rescue check: every selected horse must be from pool
    external = [k for k in selected_keys if k not in pool_set]
    swaps = _compute_swaps(pool_keys, selected_keys if not truncated else [_horse_key(r) for r in scored])

    used_repr = any(
        isinstance(r.get("features"), dict) and any(str(k).startswith("F_V3_") for k in (r.get("features") or {}))
        for r in pool_rows
    )

    journal = {
        "policy_id": POLICY_ID,
        "selection_id": SELECTION_ID,
        "contract": CONTRACT_ID,
        "swaps": swaps,
        "swap_count": len(swaps),
        "pool_size": len(pool_rows),
        "selected_size": len(selected),
        "size_invariant": (not truncated) and len(selected) == len(pool_rows),
        "truncated": truncated,
        "capacity_n": capacity_n,
        "rescue_forbidden": True,
        "pool_external_adds": len(external),
        "external_horses": external,
        "used_representation": used_repr,
        "leak_inputs": False,
        "order_before": pool_keys,
        "order_after": selected_keys,
    }
    return selected, journal


__all__ = [
    "POLICY_ID",
    "SELECTION_ID",
    "CONTRACT_ID",
    "reorder_score",
    "select_reorder",
]
