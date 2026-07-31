# -*- coding: utf-8 -*-
"""A-05 Shadow Runner — parallel eval, fail-open, no purchase side effects."""
from __future__ import annotations

import time
import traceback
from copy import deepcopy
from typing import Any

from .. import flags
from ..ab_harness import _pick_horse_id
from ..pipeline import run_lab_pipeline
from .config import ShadowSettings, load_shadow_settings


def _odds_of_pick(runners: list[dict[str, Any]], pick: str) -> float:
    for r in runners or []:
        if str(r.get("horse_id") or "") == pick:
            try:
                return float(r.get("odds") or 0.0)
            except Exception:
                return 0.0
    return 0.0


def _control_pick(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
    *,
    production_pick: str | None,
) -> tuple[str, str, dict[str, Any] | None]:
    """Return (pick, policy_id, optional_bundle).

    If production_pick is provided, it is the Production Decision (unchanged).
    Otherwise Lab identity (all flags OFF) simulates Control.
    """
    if production_pick is not None and str(production_pick) != "":
        return str(production_pick), "production_control", None

    flags.reset_flags_to_default()
    flags.apply_v3_lab_flags(read_env=False)
    bundle = run_lab_pipeline(deepcopy(context), deepcopy(runners))
    pick = _pick_horse_id(bundle)
    policy = str((bundle.get("admission") or {}).get("policy_id") or "identity")
    return pick, policy, bundle


def _shadow_pick_a05(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Run Lab pipeline with A-05 ON only (in-process). Resets flags after."""
    flags.reset_flags_to_default()
    flags.apply_v3_lab_flags(read_env=False, F_V3_A05_ADM_FAVSAFE_ENABLED=True)
    try:
        # Guard: A-03 must not be on
        if flags.a03_admission_enabled():
            raise RuntimeError("A-03 must not be ON during A-05 Shadow")
        bundle = run_lab_pipeline(deepcopy(context), deepcopy(runners))
        pick = _pick_horse_id(bundle)
        adm = bundle.get("admission") or {}
        journal = adm.get("pool_journal") or {}
        meta = {
            "policy_id": str(adm.get("policy_id") or ""),
            "admission_id": str(adm.get("admission_id") or ""),
            "promote": bool(journal.get("promote")),
            "promoted_id": journal.get("promoted_id"),
            "favsafe_blocked": bool(journal.get("favsafe_blocked")),
            "favsafe_reason": str(journal.get("favsafe_reason") or ""),
            "top_margin": journal.get("top_margin"),
            "field_size": journal.get("field_size"),
            "coverage_components": journal.get("coverage_components") or {},
            "purchase_mapper": str(
                (((bundle.get("purchase") or {}).get("purchase_plan") or {}).get("mapper") or "")
            ),
            "purchase_executed": False,
        }
        return pick, meta, bundle
    finally:
        # Always restore defaults so production Flag mesh stays OFF
        flags.reset_flags_to_default()


def run_shadow_race(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
    *,
    production_pick: str | None = None,
    winner_id: str | None = None,
    winner_rank: int | None = None,
    purchase_eligible: bool = True,
    settings: ShadowSettings | None = None,
) -> dict[str, Any]:
    """Evaluate one race: Control (production decision) + Shadow (A-05).

    - Does not change Production Decision / Purchase.
    - Shadow failures are fail-open (control fields still returned).
    - Restores F_V3_* defaults after Shadow arm.
    """
    settings = settings or load_shadow_settings()
    race_id = str((context or {}).get("race_id") or "")
    t0 = time.perf_counter()

    control_pick, control_policy, _ = _control_pick(
        context, runners, production_pick=production_pick
    )

    record: dict[str, Any] = {
        "race_id": race_id,
        "shadow_runtime_enabled": bool(settings.shadow_runtime_enabled),
        "phase": settings.phase,
        "control_pick": control_pick,
        "control_policy": control_policy,
        "shadow_pick": None,
        "shadow_policy": None,
        "shadow_ok": False,
        "shadow_error": None,
        "a05_promote": False,
        "favsafe_blocked": False,
        "favsafe_reason": "",
        "field_size": len(runners or []),
        "top_margin": None,
        "top_odds": None,
        "winner_id": winner_id,
        "winner_rank": winner_rank,
        "control_hit": None,
        "shadow_hit": None,
        "pick_changed": None,
        "control_odds": _odds_of_pick(runners, control_pick),
        "shadow_odds": None,
        "purchase_forbidden": True,
        "purchase_executed": False,
        "fail_open": bool(settings.fail_open),
        "elapsed_ms": None,
    }

    if not settings.shadow_runtime_enabled:
        record["shadow_error"] = "shadow_runtime_disabled"
        record["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        # Still allow labeled compare of control-only when disabled
        if winner_id is not None:
            record["control_hit"] = control_pick == str(winner_id)
        return record

    try:
        shadow_pick, meta, _bundle = _shadow_pick_a05(context, runners)
        record["shadow_pick"] = shadow_pick
        record["shadow_policy"] = meta.get("policy_id")
        record["a05_promote"] = bool(meta.get("promote"))
        record["favsafe_blocked"] = bool(meta.get("favsafe_blocked"))
        record["favsafe_reason"] = str(meta.get("favsafe_reason") or "")
        record["top_margin"] = meta.get("top_margin")
        if meta.get("field_size") is not None:
            record["field_size"] = meta.get("field_size")
        record["shadow_odds"] = _odds_of_pick(runners, shadow_pick)
        record["pick_changed"] = str(control_pick) != str(shadow_pick)
        record["shadow_ok"] = True
        record["purchase_executed"] = False
        if meta.get("purchase_mapper") and meta.get("purchase_mapper") != "identity":
            # Lab stub may report mapper name; execution remains forbidden
            record["purchase_mapper_observed"] = meta.get("purchase_mapper")
        # Top odds from input rank-1
        sorted_r = sorted(runners or [], key=lambda r: int(r.get("model_rank") or 999))
        if sorted_r:
            try:
                record["top_odds"] = float(sorted_r[0].get("odds") or 0.0)
            except Exception:
                record["top_odds"] = None
        if winner_id is not None:
            wid = str(winner_id)
            record["control_hit"] = control_pick == wid
            record["shadow_hit"] = shadow_pick == wid
    except Exception as exc:
        if not settings.fail_open:
            raise
        record["shadow_ok"] = False
        record["shadow_error"] = f"{type(exc).__name__}: {exc}"
        record["shadow_traceback"] = traceback.format_exc(limit=5)
        # Control untouched
        if winner_id is not None:
            record["control_hit"] = control_pick == str(winner_id)
    finally:
        flags.reset_flags_to_default()

    record["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    return record


__all__ = ["run_shadow_race"]
