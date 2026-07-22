# -*- coding: utf-8 -*-
"""RePick v2 — RP-V2-A (G1-strict / V2.1 anonymous NEAR).

Contract:
  docs/releases/v2-accuracy-design-review.md §2.2 RP-V2-A
  docs/ops/repick-v2-1-trigger-narrowing-design.md (TN-A/C/D)

Rules (Must):
  - WIN5_REPICK_V2_ENABLED default OFF → identity
  - First AB facet: RP-V2-A only (SLOT / rank6 stay OFF)
  - Anonymous trigger only (no winner / result / G1 race allowlist)
  - V2.1 narrowing: TN-A (N+1 only) ∧ TN-C (deep victim required) ∧ TN-D (mid cap)
  - N invariant, max1 displacement
  - Daily fire_cap
"""
from __future__ import annotations

import os
from typing import Any

# Feature Flag — default OFF
WIN5_REPICK_V2_ENABLED = False

# Optional sub-flags (RP-V2-B / D) — stay OFF for this AB
WIN5_REPICK_V2_SLOT = False
WIN5_REPICK_V2_RANK6 = False

RV2_RANK_MIN = 7
RV2_RANK_MAX = 10
RV2_NEAR_K = 1  # TN-A: NEAR_STRICT → surv_pos == N+1 only (was N+1..N+2)
RV2_MID_CAP = 2  # TN-D: |{selected: rank∈[7,10]}| < K
RV2_DAILY_FIRE_CAP = 3  # meeting-day fire cap

# Process-local fire counters (AB / single process). Key = YYYY-MM-DD from race_id.
_FIRE_BY_DAY: dict[str, int] = {}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def reset_fire_caps() -> None:
    """Clear daily fire counters (call between AB arms)."""
    _FIRE_BY_DAY.clear()


def apply_win5_repick_v2_flags(
    enabled: bool | None = None,
    *,
    slot: bool | None = None,
    rank6: bool | None = None,
) -> dict[str, Any]:
    """Toggle RePick v2 flags. None for enabled → read env once."""
    global WIN5_REPICK_V2_ENABLED, WIN5_REPICK_V2_SLOT, WIN5_REPICK_V2_RANK6
    if enabled is None:
        enabled = _env_bool("WIN5_REPICK_V2_ENABLED", WIN5_REPICK_V2_ENABLED)
    WIN5_REPICK_V2_ENABLED = bool(enabled)
    if slot is not None:
        WIN5_REPICK_V2_SLOT = bool(slot)
    if rank6 is not None:
        WIN5_REPICK_V2_RANK6 = bool(rank6)
    return {
        "WIN5_REPICK_V2_ENABLED": WIN5_REPICK_V2_ENABLED,
        "WIN5_REPICK_V2_SLOT": WIN5_REPICK_V2_SLOT,
        "WIN5_REPICK_V2_RANK6": WIN5_REPICK_V2_RANK6,
        "facet": "RP-V2-A",
        "band": f"{RV2_RANK_MIN}-{RV2_RANK_MAX}",
        "near_k": RV2_NEAR_K,
        "mid_cap": RV2_MID_CAP,
        "daily_fire_cap": RV2_DAILY_FIRE_CAP,
    }


def _safe_text(v: Any, default: str = "") -> str:
    try:
        if v is None:
            return default
        return str(v).strip()
    except Exception:
        return default


def _nz(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _rank(h: dict[str, Any]) -> int:
    try:
        return int(_nz(h.get("model_rank", h.get("rank", 999)), 999))
    except Exception:
        return 999


def _meeting_day(race_id: str) -> str:
    parts = _safe_text(race_id).split("-")
    if len(parts) >= 3 and len(parts[0]) == 4:
        return "-".join(parts[:3])
    return _safe_text(race_id) or "_"


def _is_alpha_paid(h: dict[str, Any]) -> bool:
    return (
        int(_nz(h.get("_v2_tw_flag", 0), 0)) == 1
        or int(_nz(h.get("_v2_act_c2_flag", 0), 0)) == 1
        or int(_nz(h.get("_v2_te_flag", 0), 0)) == 1
        or int(_nz(h.get("_v2_p1_flag", 0), 0)) == 1
        or int(_nz(h.get("_v2_tr7n_flag", 0), 0)) == 1
        or int(_nz(h.get("_v2_tr7f_flag", 0), 0)) == 1
        or int(_nz(h.get("_win5_repick_v2_flag", 0), 0)) == 1
    )


def _is_rp_protected(h: dict[str, Any]) -> bool:
    return (
        int(_nz(h.get("_phase249_rp1_rank6_protect_flag", 0), 0)) == 1
        or int(_nz(h.get("_phase249_rp2_rank710_protect_flag", 0), 0)) == 1
        or int(_nz(h.get("_win5_repick_v2_flag", 0), 0)) == 1
    )


def _empty_journal(n: int, reason: str, **extra: Any) -> dict[str, Any]:
    j: dict[str, Any] = {
        "enabled": bool(WIN5_REPICK_V2_ENABLED),
        "fired": False,
        "displaced": False,
        "trigger_match": False,
        "actuator_ok": False,
        "reason": reason,
        "facet": "RP-V2-A",
        "anonymous": 1,
        "cand_name": "",
        "cand_rank": "",
        "cand_surv_pos": "",
        "victim_name": "",
        "victim_rank": "",
        "race_id": "",
        "repick_n": n,
        "repick_size_before": n,
        "repick_size_after": n,
        "before_names": "",
        "after_names": "",
        "candidate_count": 0,
        "mid_selected": 0,
        "fire_day": "",
        "fire_day_count": 0,
    }
    j.update(extra)
    return j


def _build_surv_index(rescored: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, dict[str, Any]]]:
    name_to_pos: dict[str, int] = {}
    name_to_horse: dict[str, dict[str, Any]] = {}
    for i, h in enumerate(rescored):
        nm = _safe_text(h.get("horse_name", ""))
        if not nm:
            continue
        if nm not in name_to_pos:
            name_to_pos[nm] = i + 1
            name_to_horse[nm] = h
    return name_to_pos, name_to_horse


def _count_mid_selected(selected: list[dict[str, Any]]) -> int:
    return sum(1 for h in selected if RV2_RANK_MIN <= _rank(h) <= RV2_RANK_MAX)


def _select_rp_v2_a_near_candidate(
    *,
    selected_names: set[str],
    name_to_pos: dict[str, int],
    name_to_horse: dict[str, dict[str, Any]],
    n: int,
) -> tuple[dict[str, Any] | None, int, str, int]:
    """RP-V2-A NEAR (TN-A): surv_pos == N+1, model_rank∈[7,10], not selected."""
    cands: list[tuple[int, float, float, str, dict[str, Any]]] = []
    for nm, pos in name_to_pos.items():
        if nm in selected_names:
            continue
        h = name_to_horse[nm]
        rk = _rank(h)
        if rk < RV2_RANK_MIN or rk > RV2_RANK_MAX:
            continue
        # TN-A NEAR_STRICT: only N+1
        if pos != n + RV2_NEAR_K:
            continue
        surv = _nz(h.get("_world_survival_score", 0.0), 0.0)
        wp = _nz(h.get("win_prob", 0.0), 0.0)
        cands.append((pos, -surv, -wp, nm, h))
    if not cands:
        return None, 0, "", 0
    cands.sort()
    _pos, _s, _w, nm, h = cands[0]
    return dict(h), int(name_to_pos[nm]), "RP-V2-A", len(cands)


def apply_win5_repick_v2(
    selected: list[dict[str, Any]],
    rescored: list[dict[str, Any]],
    pool_size: int,
    meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """RP-V2-A anonymous NEAR max1 displacement. Flag OFF → identity.

    Does not read meta['winner'], race results, or frozen G1 race lists.
    """
    import demo_ticket_optimizer_core as core

    meta = meta if meta is not None else {}
    n = max(1, int(pool_size))
    selected = [dict(h) for h in (selected or [])]
    before_names = [_safe_text(h.get("horse_name", "")) for h in selected]
    before_join = "|".join(before_names)
    before_n = len(selected)
    rid = _safe_text(meta.get("race_id", ""))
    day = _meeting_day(rid)
    mid_n = _count_mid_selected(selected)

    if not WIN5_REPICK_V2_ENABLED:
        meta["_win5_repick_v2_journal"] = _empty_journal(
            before_n,
            "disabled",
            race_id=rid,
            before_names=before_join,
            after_names=before_join,
            repick_n=n,
            repick_size_before=before_n,
            repick_size_after=before_n,
            mid_selected=mid_n,
            fire_day=day,
            fire_day_count=_FIRE_BY_DAY.get(day, 0),
        )
        return selected

    if not selected or not rescored:
        meta["_win5_repick_v2_journal"] = _empty_journal(
            before_n,
            "empty_input",
            race_id=rid,
            before_names=before_join,
            after_names=before_join,
            repick_n=n,
            mid_selected=mid_n,
            fire_day=day,
        )
        return selected

    # TN-D MID_CAP
    if mid_n >= RV2_MID_CAP:
        meta["_win5_repick_v2_journal"] = _empty_journal(
            before_n,
            "mid_cap",
            race_id=rid,
            before_names=before_join,
            after_names=before_join,
            repick_n=n,
            mid_selected=mid_n,
            fire_day=day,
            fire_day_count=_FIRE_BY_DAY.get(day, 0),
        )
        return selected

    # Daily fire_cap
    day_count = int(_FIRE_BY_DAY.get(day, 0))
    if day_count >= RV2_DAILY_FIRE_CAP:
        meta["_win5_repick_v2_journal"] = _empty_journal(
            before_n,
            "fire_cap",
            race_id=rid,
            before_names=before_join,
            after_names=before_join,
            repick_n=n,
            mid_selected=mid_n,
            fire_day=day,
            fire_day_count=day_count,
        )
        return selected

    name_to_pos, name_to_horse = _build_surv_index(list(rescored))
    selected_names = {nm for nm in before_names if nm}

    cand, cand_pos, facet, cand_n = _select_rp_v2_a_near_candidate(
        selected_names=selected_names,
        name_to_pos=name_to_pos,
        name_to_horse=name_to_horse,
        n=n,
    )
    if cand is None:
        meta["_win5_repick_v2_journal"] = _empty_journal(
            before_n,
            "no_near_candidate",
            race_id=rid,
            before_names=before_join,
            after_names=before_join,
            repick_n=n,
            candidate_count=0,
            mid_selected=mid_n,
            fire_day=day,
            fire_day_count=day_count,
        )
        return selected

    cand_name = _safe_text(cand.get("horse_name", ""))
    cand_rank = _rank(cand)
    base_extra = {
        "trigger_match": True,
        "facet": facet,
        "race_id": rid,
        "cand_name": cand_name,
        "cand_rank": cand_rank,
        "cand_surv_pos": cand_pos,
        "before_names": before_join,
        "repick_n": n,
        "candidate_count": cand_n,
        "anonymous": 1,
        "mid_selected": mid_n,
        "fire_day": day,
        "fire_day_count": day_count,
    }

    def removable(h: dict[str, Any]) -> bool:
        nm = _safe_text(h.get("horse_name", ""))
        if not nm or nm == cand_name:
            return False
        if _is_alpha_paid(h):
            return False
        if _is_rp_protected(h):
            return False
        try:
            if core.is_sub_world_hard_guard_candidate(h, meta):
                return False
        except Exception:
            pass
        return True

    # TN-C: deep victim REQUIRED (model_rank >= 11). No shallow fallback.
    prefer = [h for h in selected if removable(h) and _rank(h) >= 11]
    if not prefer:
        meta["_win5_repick_v2_journal"] = _empty_journal(
            before_n,
            "no_deep_victim",
            **base_extra,
            after_names=before_join,
            repick_size_before=before_n,
            repick_size_after=before_n,
        )
        return selected

    prefer.sort(
        key=lambda h: (
            _nz(h.get("_world_survival_score", 0.0), 0.0),
            _nz(h.get("win_prob", 0.0), 0.0),
        )
    )
    victim = prefer[0]
    victim_name = _safe_text(victim.get("horse_name", ""))
    victim_rank = _rank(victim)

    out = [h for h in selected if _safe_text(h.get("horse_name", "")) != victim_name]
    kept = dict(cand)
    kept["_win5_repick_v2_flag"] = 1
    out.append(kept)

    if len(out) != before_n:
        meta["_win5_repick_v2_journal"] = _empty_journal(
            before_n,
            "size_invariant_violation",
            **base_extra,
            victim_name=victim_name,
            victim_rank=victim_rank,
            after_names=before_join,
            repick_size_before=before_n,
            repick_size_after=before_n,
        )
        return selected

    after_names = [_safe_text(h.get("horse_name", "")) for h in out]
    _FIRE_BY_DAY[day] = day_count + 1
    meta["_win5_repick_v2_journal"] = {
        **_empty_journal(before_n, "ok"),
        **base_extra,
        "fired": True,
        "displaced": True,
        "actuator_ok": True,
        "reason": "displaced",
        "victim_name": victim_name,
        "victim_rank": victim_rank,
        "after_names": "|".join(after_names),
        "repick_size_before": before_n,
        "repick_size_after": len(out),
        "fire_day_count": _FIRE_BY_DAY[day],
    }
    return out


# Env can enable for ops without code edit (still defaults OFF when unset)
if _env_bool("WIN5_REPICK_V2_ENABLED", False):
    WIN5_REPICK_V2_ENABLED = True
