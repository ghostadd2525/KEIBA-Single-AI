# -*- coding: utf-8 -*-
"""Pool+Entry v2 (PE-V2) — Flag-gated Candidate Pool sidecar.

Contract:
  docs/releases/v2-accuracy-design-review.md §2.1 PE-V2-A

Rules (Must):
  - WIN5_POOL_ENTRY_V2_ENABLED default OFF → identity
  - First AB facet: PE-V2-A (Deep-rank allowlist) only
  - rank 10–13, max +1 pool insert per race
  - No winner / result columns in trigger
"""
from __future__ import annotations

import os
from typing import Any

# Feature Flag — default OFF
WIN5_POOL_ENTRY_V2_ENABLED = False

# PE-V2-A constants (Deep-rank allowlist)
PE_V2_A_RANK_MIN = 10
PE_V2_A_RANK_MAX = 13
PE_V2_A_MIN_ROUTE_SCORE = 0.1
PE_V2_A_SCORE_SPREAD_MAX = 0.004
PE_V2_A_MAX_INSERTS = 1


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def apply_win5_pool_entry_v2_flags(enabled: bool | None = None) -> dict[str, Any]:
    """Toggle Pool+Entry v2 flag. None → read env once against current default."""
    global WIN5_POOL_ENTRY_V2_ENABLED
    if enabled is None:
        enabled = _env_bool("WIN5_POOL_ENTRY_V2_ENABLED", WIN5_POOL_ENTRY_V2_ENABLED)
    WIN5_POOL_ENTRY_V2_ENABLED = bool(enabled)
    return {
        "WIN5_POOL_ENTRY_V2_ENABLED": WIN5_POOL_ENTRY_V2_ENABLED,
        "facet": "PE-V2-A",
        "rank_band": f"{PE_V2_A_RANK_MIN}-{PE_V2_A_RANK_MAX}",
        "max_inserts": PE_V2_A_MAX_INSERTS,
    }


def _safe_text(v: Any, default: str = "") -> str:
    try:
        if v is None:
            return default
        return str(v).strip()
    except Exception:
        return default


def _rank(h: dict[str, Any]) -> int:
    import demo_ticket_optimizer_core as core

    try:
        return int(core.nz(h.get("model_rank", h.get("rank", 999)), 999))
    except Exception:
        return 999


def _empty_journal(pool_n: int, reason: str, **extra: Any) -> dict[str, Any]:
    j: dict[str, Any] = {
        "enabled": bool(WIN5_POOL_ENTRY_V2_ENABLED),
        "facet": "PE-V2-A",
        "fired": False,
        "inserted": False,
        "reason": reason,
        "cand_name": "",
        "cand_rank": "",
        "cand_route_score": "",
        "pool_size_before": pool_n,
        "pool_size_after": pool_n,
    }
    j.update(extra)
    return j


def is_pe_v2_a_candidate(meta: dict[str, Any] | None, candidate: dict[str, Any] | None) -> bool:
    import demo_ticket_optimizer_core as core

    candidate = candidate or {}
    rk = _rank(candidate)
    if rk < PE_V2_A_RANK_MIN or rk > PE_V2_A_RANK_MAX:
        return False
    score = float(core.calc_other_miss_deep_route_score(meta, candidate))
    return score >= PE_V2_A_MIN_ROUTE_SCORE


def is_pe_v2_a_race(meta: dict[str, Any] | None, candidates: list[dict[str, Any]] | None) -> bool:
    """Anonymous race-context proxy for other_10_13 deep pool-outside band."""
    import demo_ticket_optimizer_core as core

    if not WIN5_POOL_ENTRY_V2_ENABLED:
        return False
    meta = meta or {}
    pool = list(candidates or [])

    try:
        sub_world = core.resolve_race_sub_world_intent(meta, pool, pool)
    except Exception:
        sub_world = _safe_text(meta.get("sub_world_type", meta.get("race_sub_world", "")), "")

    world_type = _safe_text(
        meta.get(
            "world_type",
            meta.get("race_world_type", meta.get("post_world_type", "")),
        ),
        "",
    )
    if sub_world not in core.OTHER_MISS_DEEP_TARGET_SUBWORLDS:
        return False
    if world_type not in core.OTHER_MISS_DEEP_TARGET_WORLDS:
        return False

    field_size = core.get_context_field_size(
        meta, (pool[0] if pool else None)
    )
    if field_size < core.OTHER_MISS_DEEP_FIELD_MIN:
        return False

    prob_ctx = core.calc_race_probability_context(meta, pool)
    top_median_gap = core.nz(
        prob_ctx.get("top_median_gap", core.get_context_top_median_gap(meta, None)),
        0.0,
    )
    top_average_gap = core.nz(
        prob_ctx.get("top_average_gap", core.get_context_top_average_gap(meta, None)),
        0.0,
    )
    if not (0.0 < top_median_gap <= core.OTHER_MISS_DEEP_TOP_MEDIAN_GAP_MAX):
        return False
    if not (0.0 < top_average_gap <= core.OTHER_MISS_DEEP_TOP_AVERAGE_GAP_MAX):
        return False

    deep_ctx = core.calc_rank1015_deep_observation_context(meta, pool)
    if int(core.nz(deep_ctx.get("rank1015_score_available_count", 0), 0)) < core.OTHER_MISS_DEEP_MIN_AVAILABLE_COUNT:
        return False
    spread = core.nz(deep_ctx.get("rank1015_score_spread", 1.0), 1.0)
    if spread > PE_V2_A_SCORE_SPREAD_MAX:
        return False

    return any(is_pe_v2_a_candidate(meta, h) for h in pool)


def apply_pe_v2_a(
    base_pool: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    meta: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """PE-V2-A actuator — max +1 deep rank 10–13 allowlist insert."""
    import demo_ticket_optimizer_core as core

    meta = meta if meta is not None else {}
    pool = [dict(h) for h in (base_pool or [])]
    pool_n = len(pool)

    if not WIN5_POOL_ENTRY_V2_ENABLED:
        meta["_win5_pool_entry_v2_journal"] = _empty_journal(pool_n, "disabled")
        return pool

    if not is_pe_v2_a_race(meta, list(candidates or [])):
        meta["_win5_pool_entry_v2_journal"] = _empty_journal(pool_n, "no_race_trigger")
        return pool

    existing = {_safe_text(h.get("horse_name", ""), "") for h in pool}
    eligible: list[dict[str, Any]] = []
    for h in list(candidates or []):
        name = _safe_text(h.get("horse_name", ""), "")
        if not name or name in existing:
            continue
        if int(h.get("_other_miss_deep_pool_rescue_insert_flag", 0) or 0) == 1:
            continue
        if int(h.get("_pe_v2_a_insert_flag", 0) or 0) == 1:
            continue
        if not is_pe_v2_a_candidate(meta, h):
            continue
        eligible.append(h)

    if not eligible:
        meta["_win5_pool_entry_v2_journal"] = _empty_journal(pool_n, "no_eligible_candidate")
        return pool

    eligible.sort(
        key=lambda h: (
            float(core.calc_other_miss_deep_route_score(meta, h)),
            float(core.nz(h.get("win_prob", h.get("prob", 0.0)), 0.0)),
            -abs(_rank(h) - 11.5),
        ),
        reverse=True,
    )
    pick = dict(eligible[0])
    route_score = float(core.calc_other_miss_deep_route_score(meta, pick))
    pick["_pe_v2_a_insert_flag"] = 1
    pick["_pe_v2_a_route_score"] = round(route_score, 6)
    reason = _safe_text(pick.get("selection_reason", ""), "")
    pick["selection_reason"] = (reason + "|" if reason else "") + "pe_v2_a_deep_allowlist(rank10-13)"
    pick["required_role_type"] = "deep_route_guard"
    pick["assigned_role"] = "deep_route_guard"

    new_pool = pool + [pick][:PE_V2_A_MAX_INSERTS]
    meta["_win5_pool_entry_v2_journal"] = {
        "enabled": True,
        "facet": "PE-V2-A",
        "fired": True,
        "inserted": True,
        "reason": "insert",
        "cand_name": _safe_text(pick.get("horse_name", ""), ""),
        "cand_rank": _rank(pick),
        "cand_route_score": round(route_score, 6),
        "pool_size_before": pool_n,
        "pool_size_after": len(new_pool),
    }
    return new_pool


def apply_win5_pool_entry_v2(
    base_pool: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    meta: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Entry hook for build_candidate_pool — PE-V2-A only (first AB)."""
    return apply_pe_v2_a(base_pool, candidates, meta)
