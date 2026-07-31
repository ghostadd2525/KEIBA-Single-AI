# -*- coding: utf-8 -*-
"""Version 3 Lab — Selection Policy A-04 (History Crowding Promote).

Selection-only intervention for Baseline v2 residual Boundary / Reorder misses.
Does not modify Representation, Admission, Evaluation, or Purchase modules.
Does not alter SEL-V3-RO (P4) code path.

When the admitted pool is crowded near the top and a near-boundary horse has
clear history_score advantage, promote that horse inside the pool
(model_rank=1 + anonymous strength lift) so downstream Evaluation D1 picks it.
Clear fields are left unchanged (churn protection for Eval / Control / Pool).
"""
from __future__ import annotations

import math
from typing import Any

POLICY_ID = "SEL-V3-A04-history-crowding"
SELECTION_ID = "v3-sel-a04-v1"
CONTRACT_ID = "v3-lab-selection/2.0"

CROWDING_MIN = 0.40
HIST_GAP_MIN = 0.15
NEAR_RANK_MAX = 3


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


def _hist(runner: dict[str, Any]) -> float:
    if runner.get("history_score") is not None and runner.get("history_score") != "":
        return _f(runner.get("history_score"), 0.0)
    return _f(runner.get("win_prob"), 0.0)


def field_crowding(field: list[dict[str, Any]]) -> float:
    """1 when top win_probs are tight (Boundary/Reorder); 0 when clear favorite."""
    wps = sorted((_f(r.get("win_prob"), 0.0) for r in field), reverse=True)
    if not wps:
        return 0.0
    third = wps[2] if len(wps) >= 3 else wps[-1]
    top_gap = wps[0] - third
    return max(0.0, min(1.0, 1.0 - (top_gap / 0.15)))


def select_history_crowding(
    context: dict[str, Any],
    pool: list[dict[str, Any]],
    *,
    capacity_n: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reorder-only Selection with conditional history promote inside pool."""
    del context  # race context reserved; no leak columns
    pool_rows = [dict(r) for r in (pool or [])]
    pool_keys = [_horse_key(r) for r in pool_rows]
    pool_set = set(pool_keys)
    crowding = field_crowding(pool_rows)

    promoted = False
    promoted_id = None
    selected = pool_rows

    if crowding >= CROWDING_MIN and pool_rows:
        near = [r for r in pool_rows if _i(r.get("model_rank", r.get("rank")), 999) <= NEAR_RANK_MAX]
        if not near:
            near = list(pool_rows)
        leader = max(near, key=lambda r: (_hist(r), _f(r.get("win_prob"), 0.0)))
        rank1 = min(pool_rows, key=lambda r: _i(r.get("model_rank", r.get("rank")), 999))
        hist_gap = _hist(leader) - _hist(rank1)
        same = _horse_key(leader) == _horse_key(rank1)
        if (not same) and hist_gap >= HIST_GAP_MIN:
            promoted = True
            promoted_id = _horse_key(leader)
            top_wp = max((_f(r.get("win_prob"), 0.0) for r in pool_rows), default=0.0)
            others = [dict(r) for r in pool_rows if _horse_key(r) != promoted_id]
            others.sort(key=lambda r: _i(r.get("model_rank", r.get("rank")), 999))
            lead = dict(leader)
            lead["model_rank"] = 1
            lead["win_prob"] = max(_f(lead.get("win_prob"), 0.0), top_wp + 0.08)
            feats = dict(lead.get("features") or {}) if isinstance(lead.get("features"), dict) else {}
            feats["F_V3_10_decayed_form_proxy"] = max(_hist(lead), _f(lead.get("win_prob"), 0.0))
            lead["features"] = feats
            lead["a04_promoted"] = True
            lead["selection_order"] = 1
            lead["reorder_score"] = float(_hist(lead))
            for i, row in enumerate(others, start=2):
                row["model_rank"] = i
                row["a04_promoted"] = False
                row["selection_order"] = i
                row["reorder_score"] = float(_hist(row))
            selected = [lead] + others

    if not promoted:
        # Stable passthrough order with selection metadata (no Rescue)
        selected = [dict(r) for r in pool_rows]
        selected.sort(key=lambda r: _i(r.get("model_rank", r.get("rank")), 999))
        for i, row in enumerate(selected):
            row["selection_order"] = i + 1
            row["reorder_score"] = float(_f(row.get("win_prob"), 0.0))
            row["a04_promoted"] = False

    truncated = False
    if capacity_n is not None and capacity_n >= 0:
        if len(selected) > capacity_n:
            selected = selected[:capacity_n]
            truncated = True

    selected_keys = [_horse_key(r) for r in selected]
    external = [k for k in selected_keys if k not in pool_set]
    swaps: list[dict[str, Any]] = []
    pos_before = {k: i for i, k in enumerate(pool_keys)}
    for new_i, key in enumerate(selected_keys):
        old_i = pos_before.get(key)
        if old_i is not None and new_i < old_i:
            swaps.append({"horse_id": key, "from_index": old_i, "to_index": new_i})

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
        "used_representation": False,
        "leak_inputs": False,
        "order_before": pool_keys,
        "order_after": selected_keys,
        "field_crowding": round(crowding, 4),
        "promote": promoted,
        "promoted_id": promoted_id,
        "crowding_min": CROWDING_MIN,
        "hist_gap_min": HIST_GAP_MIN,
        "target": "I-Boundary+I-Reorder",
        "independent_of_evaluation_logic": True,
    }
    return selected, journal


__all__ = [
    "POLICY_ID",
    "SELECTION_ID",
    "CONTRACT_ID",
    "CROWDING_MIN",
    "HIST_GAP_MIN",
    "NEAR_RANK_MAX",
    "field_crowding",
    "select_history_crowding",
]
