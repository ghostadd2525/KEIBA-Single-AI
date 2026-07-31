# -*- coding: utf-8 -*-
"""Version 3 Lab — stage stubs (identity when Flag OFF)."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import flags
from .contracts import CONTRACT_IDS


def _copy_runners(runners: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return deepcopy(runners or [])


def run_representation(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
) -> dict[str, Any]:
    """P2: Feature Generator when F_V3_REPRESENTATION ON; else identity."""
    from .feature_generator import (
        CONTRACT_ID,
        FEATURE_KEYS,
        REPRESENTATION_ID,
        generate_race_features,
    )

    race_id = str(context.get("race_id") or "")
    enabled = bool(flags.representation_enabled())
    if not enabled:
        out_runners = _copy_runners(runners)
        journal = {
            "contract": CONTRACT_ID,
            "enabled": False,
            "mode": "identity",
            "feature_keys": [],
            "embedding_dim": 0,
            "note": "F_V3_REPRESENTATION OFF — passthrough",
        }
        return {
            "race_id": race_id,
            "runners": out_runners,
            "embedding_dim": 0,
            "representation_id": "identity",
            "feature_keys": [],
            "journal": journal,
        }

    out_runners, gen_journal = generate_race_features(context, _copy_runners(runners))
    journal = {
        "contract": CONTRACT_ID,
        "enabled": True,
        "mode": "feature_generator",
        "feature_keys": list(FEATURE_KEYS),
        "embedding_dim": len(FEATURE_KEYS),
        "generator": gen_journal,
        "note": "P2 Representation — F-V3 features attached; Evaluation still stub",
    }
    return {
        "race_id": race_id,
        "runners": out_runners,
        "embedding_dim": len(FEATURE_KEYS),
        "representation_id": REPRESENTATION_ID,
        "feature_keys": list(FEATURE_KEYS),
        "journal": journal,
    }


def run_admission(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
) -> dict[str, Any]:
    """Admission: A-05 Favorite-Safe, else A-03 Pool Coverage, else P3, else identity.

    A-03 and A-05 are mutually exclusive (enforced in flags).
    Does not modify Representation / Evaluation / Selection / Purchase modules.
    """
    from .admission_policy import (
        ADMISSION_ID as P3_ADMISSION_ID,
        CONTRACT_ID as P3_CONTRACT_ID,
        POLICY_ID as P3_POLICY_ID,
        build_candidate_pool,
    )
    from .admission_policy_a03 import (
        ADMISSION_ID as A03_ADMISSION_ID,
        CONTRACT_ID as A03_CONTRACT_ID,
        POLICY_ID as A03_POLICY_ID,
        build_candidate_pool_a03,
    )
    from .admission_policy_a05 import (
        ADMISSION_ID as A05_ADMISSION_ID,
        CONTRACT_ID as A05_CONTRACT_ID,
        POLICY_ID as A05_POLICY_ID,
        build_candidate_pool_a05,
    )

    race_id = str(context.get("race_id") or "")
    use_a05 = bool(flags.a05_admission_enabled())
    use_a03 = bool(flags.a03_admission_enabled())
    if use_a03 and use_a05:
        raise ValueError("A-03 and A-05 Admission flags must not be ON together")
    use_p3 = bool(flags.F_V3_ADMISSION) and not use_a03 and not use_a05

    if not use_a03 and not use_a05 and not use_p3:
        pool = _copy_runners(runners)
        journal = {
            "contract": P3_CONTRACT_ID,
            "enabled": False,
            "mode": "identity",
            "policy_id": "identity",
            "admission_id": "identity",
            "admitted": [r.get("horse_id") or r.get("horse_number") for r in pool],
            "rejected_reason": {},
            "capacity_max": len(pool),
            "admitted_count": len(pool),
            "rejected_count": 0,
            "deep_extra": 0,
            "used_representation": False,
            "note": "Admission OFF — pool = all runners",
        }
        return {
            "race_id": race_id,
            "candidate_pool": pool,
            "capacity_max": len(pool),
            "policy_id": "identity",
            "admission_id": "identity",
            "pool_journal": journal,
        }

    if use_a05:
        pool, pol_journal = build_candidate_pool_a05(context, _copy_runners(runners))
        journal = {
            "contract": A05_CONTRACT_ID,
            "enabled": True,
            "mode": "favorite_safe_coverage_promote",
            "policy_id": A05_POLICY_ID,
            "admission_id": A05_ADMISSION_ID,
            "note": "A-05 Admission — Favorite-Safe Coverage (A-03 frozen)",
            **pol_journal,
        }
        return {
            "race_id": race_id,
            "candidate_pool": pool,
            "capacity_max": int(pol_journal.get("capacity_max") or len(pool)),
            "policy_id": A05_POLICY_ID,
            "admission_id": A05_ADMISSION_ID,
            "pool_journal": journal,
        }

    if use_a03:
        pool, pol_journal = build_candidate_pool_a03(context, _copy_runners(runners))
        journal = {
            "contract": A03_CONTRACT_ID,
            "enabled": True,
            "mode": "pool_coverage_promote",
            "policy_id": A03_POLICY_ID,
            "admission_id": A03_ADMISSION_ID,
            "note": "A-03 Admission — Pool Coverage Deep Promote (Evaluation unchanged)",
            **pol_journal,
        }
        return {
            "race_id": race_id,
            "candidate_pool": pool,
            "capacity_max": int(pol_journal.get("capacity_max") or len(pool)),
            "policy_id": A03_POLICY_ID,
            "admission_id": A03_ADMISSION_ID,
            "pool_journal": journal,
        }

    pool, pol_journal = build_candidate_pool(context, _copy_runners(runners))
    journal = {
        "contract": P3_CONTRACT_ID,
        "enabled": True,
        "mode": "banded_deep",
        "policy_id": P3_POLICY_ID,
        "admission_id": P3_ADMISSION_ID,
        "note": "P3 Admission — AP-V3-A Banded Deep; Selection still stub",
        **pol_journal,
    }
    return {
        "race_id": race_id,
        "candidate_pool": pool,
        "capacity_max": int(pol_journal.get("capacity_max") or len(pool)),
        "policy_id": P3_POLICY_ID,
        "admission_id": P3_ADMISSION_ID,
        "pool_journal": journal,
    }


def run_selection(
    context: dict[str, Any],
    pool: list[dict[str, Any]],
    *,
    capacity_n: int | None = None,
) -> dict[str, Any]:
    """Selection: A-04 History Crowding, else P4 SEL-V3-RO, else identity.

    A-04 takes precedence when F_V3_A04_SEL_HISTORY_ENABLED is ON (single A-04 path).
    Does not modify Representation / Admission / Evaluation / Purchase modules.
    """
    from .selection_policy import (
        CONTRACT_ID as P4_CONTRACT_ID,
        POLICY_ID as P4_POLICY_ID,
        SELECTION_ID as P4_SELECTION_ID,
        select_reorder,
    )
    from .selection_policy_a04 import (
        CONTRACT_ID as A04_CONTRACT_ID,
        POLICY_ID as A04_POLICY_ID,
        SELECTION_ID as A04_SELECTION_ID,
        select_history_crowding,
    )

    race_id = str(context.get("race_id") or "")
    use_a04 = bool(flags.a04_selection_enabled())
    use_p4 = bool(flags.F_V3_SELECTION) and not use_a04

    if not use_a04 and not use_p4:
        selected = _copy_runners(pool)
        if capacity_n is not None and capacity_n >= 0:
            selected = selected[:capacity_n]
        journal = {
            "contract": P4_CONTRACT_ID,
            "enabled": False,
            "mode": "identity",
            "policy_id": "identity",
            "selection_id": "identity",
            "swaps": [],
            "swap_count": 0,
            "pool_size": len(pool or []),
            "selected_size": len(selected),
            "size_invariant": len(selected) == len(pool or []),
            "rescue_forbidden": True,
            "pool_external_adds": 0,
            "note": "Selection OFF — passthrough pool order",
        }
        return {
            "race_id": race_id,
            "selected": selected,
            "policy_id": "identity",
            "selection_id": "identity",
            "selection_journal": journal,
        }

    if use_a04:
        selected, pol_journal = select_history_crowding(
            context, _copy_runners(pool), capacity_n=capacity_n
        )
        journal = {
            "contract": A04_CONTRACT_ID,
            "enabled": True,
            "mode": "history_crowding_promote",
            "policy_id": A04_POLICY_ID,
            "selection_id": A04_SELECTION_ID,
            "note": "A-04 Selection — History Crowding Promote (Evaluation unchanged)",
            **pol_journal,
        }
        return {
            "race_id": race_id,
            "selected": selected,
            "policy_id": A04_POLICY_ID,
            "selection_id": A04_SELECTION_ID,
            "selection_journal": journal,
        }

    selected, pol_journal = select_reorder(context, _copy_runners(pool), capacity_n=capacity_n)
    journal = {
        "contract": P4_CONTRACT_ID,
        "enabled": True,
        "mode": "reorder_only",
        "policy_id": P4_POLICY_ID,
        "selection_id": P4_SELECTION_ID,
        "note": "P4 Selection — SEL-V3-RO Reorder-only; Evaluation still stub",
        **pol_journal,
    }
    return {
        "race_id": race_id,
        "selected": selected,
        "policy_id": P4_POLICY_ID,
        "selection_id": P4_SELECTION_ID,
        "selection_journal": journal,
    }


def run_evaluation(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluation: D1 (A-01) or D2 (A-02) when flagged; else identity.

    Mutual preference: D1 wins if both D1 and D2 are ON (A-01 frozen path).
    """
    from .evaluation_policy import rank_identity, rank_with_d1
    from .evaluation_policy import (
        EVALUATION_ID as D1_EVALUATION_ID,
        POLICY_ID as D1_POLICY_ID,
    )
    from .evaluation_policy_d2 import rank_with_d2
    from .evaluation_policy_d2 import (
        EVALUATION_ID as D2_EVALUATION_ID,
        POLICY_ID as D2_POLICY_ID,
    )

    race_id = str(context.get("race_id") or "")
    use_d1 = bool(flags.F_V3_RANK_D1_ENABLED or (
        flags.F_V3_EVALUATION_ENABLED and not flags.F_V3_RANK_D2_ENABLED
    ))
    use_d2 = bool(flags.F_V3_RANK_D2_ENABLED) and not use_d1

    if not use_d1 and not use_d2:
        ranked, win_prob, id_journal = rank_identity(_copy_runners(runners))
        journal = {
            "enabled": False,
            "mode": "identity",
            "note": "Evaluation OFF — model_rank passthrough",
            **id_journal,
        }
        return {
            "race_id": race_id,
            "ranked": ranked,
            "win_prob": win_prob,
            "policy_id": "identity",
            "evaluation_id": "identity",
            "eval_journal": journal,
        }

    if use_d1:
        ranked, win_prob, pol_journal = rank_with_d1(context, _copy_runners(runners))
        journal = {
            "enabled": True,
            "mode": "d1_recalibrator",
            "note": "A-01 Evaluation — D1 Recalibrator (Feature-invariant)",
            **pol_journal,
        }
        return {
            "race_id": race_id,
            "ranked": ranked,
            "win_prob": win_prob,
            "policy_id": D1_POLICY_ID,
            "evaluation_id": D1_EVALUATION_ID,
            "eval_journal": journal,
        }

    ranked, win_prob, pol_journal = rank_with_d2(context, _copy_runners(runners))
    journal = {
        "enabled": True,
        "mode": "d2_listwise_pairwise",
        "note": "A-02 Evaluation — D2 Listwise Reranker (independent of A-01)",
        **pol_journal,
    }
    return {
        "race_id": race_id,
        "ranked": ranked,
        "win_prob": win_prob,
        "policy_id": D2_POLICY_ID,
        "evaluation_id": D2_EVALUATION_ID,
        "eval_journal": journal,
    }


def run_purchase(
    context: dict[str, Any],
    selected: list[dict[str, Any]],
) -> dict[str, Any]:
    race_id = str(context.get("race_id") or "")
    enabled = bool(flags.F_V3_LAB_ENABLED and flags.F_V3_PURCHASE_ENABLED)
    plan = {
        "legs": [
            {
                "horse_id": r.get("horse_id"),
                "horse_number": r.get("horse_number"),
                "model_rank": r.get("model_rank"),
            }
            for r in selected
        ],
        "mapper": "identity" if not enabled else "v3-purchase-stub",
    }
    journal = {
        "contract": CONTRACT_IDS["purchase"],
        "enabled": enabled,
        "mode": "stub" if enabled else "identity",
        "delete_boundary_unchanged": True,
        "note": "P1 stub — passthrough plan; Delete Boundary untouched",
    }
    return {
        "race_id": race_id,
        "purchase_plan": plan,
        "purchase_journal": journal,
    }


__all__ = [
    "run_representation",
    "run_admission",
    "run_selection",
    "run_evaluation",
    "run_purchase",
]
