# -*- coding: utf-8 -*-
"""Version 3 Lab — Feature Flags (all default OFF).

Canonical stage flags:
  - F_V3_REPRESENTATION (P2)
  - F_V3_ADMISSION (P3)
  - F_V3_SELECTION (P4)
  - F_V3_RANK_D1_ENABLED (A-01 Evaluation D1)
  - F_V3_RANK_D2_ENABLED (A-02 Evaluation D2)
  - F_V3_A03_POOL_ADMIT_ENABLED (A-03 Admission Pool Coverage)
  - F_V3_A05_ADM_FAVSAFE_ENABLED (A-05 Admission Favorite-Safe Coverage)
  - F_V3_A04_SEL_HISTORY_ENABLED (A-04 Selection History Crowding)

Aliases: F_V3_*_ENABLED mirrors where applicable.

Flag OFF ⇒ identity for that stage.
This package must never be imported by V2 production runtime.
"""
from __future__ import annotations

import os
from typing import Any

# --- Canonical stage flags ---
F_V3_REPRESENTATION = False
F_V3_ADMISSION = False
F_V3_SELECTION = False
F_V3_RANK_D1_ENABLED = False  # A-01 D1 Recalibrator

# --- Legacy / other stage flags (default OFF) ---
F_V3_LAB_ENABLED = False
F_V3_REPRESENTATION_ENABLED = False
F_V3_ADMISSION_ENABLED = False
F_V3_SELECTION_ENABLED = False
F_V3_EVALUATION_ENABLED = False  # alias path for evaluation stage
F_V3_PURCHASE_ENABLED = False
F_V3_RANK_D2_ENABLED = False
F_V3_A03_POOL_ADMIT_ENABLED = False  # A-03 Pool Coverage Admission
F_V3_A05_ADM_FAVSAFE_ENABLED = False  # A-05 Favorite-Safe Coverage Admission
F_V3_A04_SEL_HISTORY_ENABLED = False  # A-04 Selection History Crowding Promote
F_V3_AP_BANDED_ENABLED = False
F_V3_AP_COVERAGE_ENABLED = False
F_V3_SEL_REORDER_ENABLED = False

_ENV_ALIASES: dict[str, tuple[str, ...]] = {
    "F_V3_REPRESENTATION": ("F_V3_REPRESENTATION", "F_V3_REPRESENTATION_ENABLED"),
    "F_V3_ADMISSION": ("F_V3_ADMISSION", "F_V3_ADMISSION_ENABLED"),
    "F_V3_SELECTION": ("F_V3_SELECTION", "F_V3_SELECTION_ENABLED"),
    "F_V3_LAB_ENABLED": ("F_V3_LAB_ENABLED",),
    "F_V3_EVALUATION_ENABLED": ("F_V3_EVALUATION_ENABLED",),
    "F_V3_PURCHASE_ENABLED": ("F_V3_PURCHASE_ENABLED",),
    "F_V3_RANK_D1_ENABLED": ("F_V3_RANK_D1_ENABLED", "WIN5_V3_RANK_D1_ENABLED"),
    "F_V3_RANK_D2_ENABLED": ("F_V3_RANK_D2_ENABLED", "WIN5_V3_RANK_D2_ENABLED"),
    "F_V3_A03_POOL_ADMIT_ENABLED": (
        "F_V3_A03_POOL_ADMIT_ENABLED",
        "WIN5_V3_A03_POOL_ADMIT_ENABLED",
    ),
    "F_V3_A05_ADM_FAVSAFE_ENABLED": (
        "F_V3_A05_ADM_FAVSAFE_ENABLED",
        "WIN5_V3_A05_ADM_FAVSAFE_ENABLED",
    ),
    "F_V3_A04_SEL_HISTORY_ENABLED": (
        "F_V3_A04_SEL_HISTORY_ENABLED",
        "WIN5_V3_A04_SEL_HISTORY_ENABLED",
    ),
    "F_V3_AP_BANDED_ENABLED": ("F_V3_AP_BANDED_ENABLED", "WIN5_V3_AP_BANDED_ENABLED"),
    "F_V3_AP_COVERAGE_ENABLED": ("F_V3_AP_COVERAGE_ENABLED", "WIN5_V3_AP_COVERAGE_ENABLED"),
    "F_V3_SEL_REORDER_ENABLED": ("F_V3_SEL_REORDER_ENABLED", "WIN5_V3_SEL_REORDER_ENABLED"),
}


def _env_bool(names: tuple[str, ...] | str, default: bool = False) -> bool:
    if isinstance(names, str):
        names = (names,)
    for name in names:
        raw = os.environ.get(name)
        if raw is None:
            continue
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}
    return default


def apply_v3_lab_flags(*, read_env: bool = True, **overrides: bool | None) -> dict[str, Any]:
    global F_V3_REPRESENTATION, F_V3_REPRESENTATION_ENABLED, F_V3_LAB_ENABLED
    global F_V3_ADMISSION, F_V3_ADMISSION_ENABLED
    global F_V3_SELECTION, F_V3_SELECTION_ENABLED, F_V3_EVALUATION_ENABLED
    global F_V3_PURCHASE_ENABLED, F_V3_RANK_D1_ENABLED, F_V3_RANK_D2_ENABLED
    global F_V3_A03_POOL_ADMIT_ENABLED, F_V3_A05_ADM_FAVSAFE_ENABLED
    global F_V3_A04_SEL_HISTORY_ENABLED
    global F_V3_AP_BANDED_ENABLED, F_V3_AP_COVERAGE_ENABLED, F_V3_SEL_REORDER_ENABLED

    overrides = dict(overrides)
    if "F_V3_REPRESENTATION_ENABLED" in overrides and "F_V3_REPRESENTATION" not in overrides:
        overrides["F_V3_REPRESENTATION"] = overrides.get("F_V3_REPRESENTATION_ENABLED")
    if "F_V3_ADMISSION_ENABLED" in overrides and "F_V3_ADMISSION" not in overrides:
        overrides["F_V3_ADMISSION"] = overrides.get("F_V3_ADMISSION_ENABLED")
    if "F_V3_SELECTION_ENABLED" in overrides and "F_V3_SELECTION" not in overrides:
        overrides["F_V3_SELECTION"] = overrides.get("F_V3_SELECTION_ENABLED")

    mapping = {
        "F_V3_REPRESENTATION": "F_V3_REPRESENTATION",
        "F_V3_ADMISSION": "F_V3_ADMISSION",
        "F_V3_SELECTION": "F_V3_SELECTION",
        "F_V3_LAB_ENABLED": "F_V3_LAB_ENABLED",
        "F_V3_EVALUATION_ENABLED": "F_V3_EVALUATION_ENABLED",
        "F_V3_PURCHASE_ENABLED": "F_V3_PURCHASE_ENABLED",
        "F_V3_RANK_D1_ENABLED": "F_V3_RANK_D1_ENABLED",
        "F_V3_RANK_D2_ENABLED": "F_V3_RANK_D2_ENABLED",
        "F_V3_A03_POOL_ADMIT_ENABLED": "F_V3_A03_POOL_ADMIT_ENABLED",
        "F_V3_A05_ADM_FAVSAFE_ENABLED": "F_V3_A05_ADM_FAVSAFE_ENABLED",
        "F_V3_A04_SEL_HISTORY_ENABLED": "F_V3_A04_SEL_HISTORY_ENABLED",
        "F_V3_AP_BANDED_ENABLED": "F_V3_AP_BANDED_ENABLED",
        "F_V3_AP_COVERAGE_ENABLED": "F_V3_AP_COVERAGE_ENABLED",
        "F_V3_SEL_REORDER_ENABLED": "F_V3_SEL_REORDER_ENABLED",
    }

    for key, attr in mapping.items():
        if key in overrides and overrides[key] is not None:
            globals()[attr] = bool(overrides[key])
        elif read_env:
            globals()[attr] = _env_bool(_ENV_ALIASES.get(key, (key,)), False)

    if F_V3_A03_POOL_ADMIT_ENABLED and F_V3_A05_ADM_FAVSAFE_ENABLED:
        raise ValueError(
            "F_V3_A03_POOL_ADMIT_ENABLED and F_V3_A05_ADM_FAVSAFE_ENABLED "
            "must not be ON simultaneously"
        )

    F_V3_REPRESENTATION_ENABLED = bool(F_V3_REPRESENTATION)
    F_V3_ADMISSION_ENABLED = bool(F_V3_ADMISSION)
    F_V3_SELECTION_ENABLED = bool(F_V3_SELECTION)
    return snapshot_flags()


def snapshot_flags() -> dict[str, Any]:
    return {
        "F_V3_REPRESENTATION": F_V3_REPRESENTATION,
        "F_V3_REPRESENTATION_ENABLED": F_V3_REPRESENTATION_ENABLED,
        "F_V3_ADMISSION": F_V3_ADMISSION,
        "F_V3_ADMISSION_ENABLED": F_V3_ADMISSION_ENABLED,
        "F_V3_SELECTION": F_V3_SELECTION,
        "F_V3_SELECTION_ENABLED": F_V3_SELECTION_ENABLED,
        "F_V3_LAB_ENABLED": F_V3_LAB_ENABLED,
        "F_V3_EVALUATION_ENABLED": F_V3_EVALUATION_ENABLED,
        "F_V3_PURCHASE_ENABLED": F_V3_PURCHASE_ENABLED,
        "F_V3_RANK_D1_ENABLED": F_V3_RANK_D1_ENABLED,
        "F_V3_RANK_D2_ENABLED": F_V3_RANK_D2_ENABLED,
        "F_V3_A03_POOL_ADMIT_ENABLED": F_V3_A03_POOL_ADMIT_ENABLED,
        "F_V3_A05_ADM_FAVSAFE_ENABLED": F_V3_A05_ADM_FAVSAFE_ENABLED,
        "F_V3_A04_SEL_HISTORY_ENABLED": F_V3_A04_SEL_HISTORY_ENABLED,
        "F_V3_AP_BANDED_ENABLED": F_V3_AP_BANDED_ENABLED,
        "F_V3_AP_COVERAGE_ENABLED": F_V3_AP_COVERAGE_ENABLED,
        "F_V3_SEL_REORDER_ENABLED": F_V3_SEL_REORDER_ENABLED,
        "any_stage_on": any_stage_enabled(),
        "representation_on": representation_enabled(),
        "admission_on": admission_enabled(),
        "selection_on": selection_enabled(),
        "evaluation_on": evaluation_enabled(),
        "a03_admission_on": a03_admission_enabled(),
        "a05_admission_on": a05_admission_enabled(),
        "a04_selection_on": a04_selection_enabled(),
    }


def representation_enabled() -> bool:
    return bool(F_V3_REPRESENTATION)


def admission_enabled() -> bool:
    """P3 AP-V3-A or A-03 Pool Coverage or A-05 Favorite-Safe Admission."""
    return bool(
        F_V3_ADMISSION
        or F_V3_A03_POOL_ADMIT_ENABLED
        or F_V3_A05_ADM_FAVSAFE_ENABLED
    )


def a03_admission_enabled() -> bool:
    return bool(F_V3_A03_POOL_ADMIT_ENABLED)


def a05_admission_enabled() -> bool:
    return bool(F_V3_A05_ADM_FAVSAFE_ENABLED)


def selection_enabled() -> bool:
    """P4 SEL-V3-RO or A-04 History Crowding Selection."""
    return bool(F_V3_SELECTION or F_V3_A04_SEL_HISTORY_ENABLED)


def a04_selection_enabled() -> bool:
    return bool(F_V3_A04_SEL_HISTORY_ENABLED)


def evaluation_enabled() -> bool:
    """Evaluation ON when D1, D2, or legacy evaluation alias is ON."""
    return bool(F_V3_RANK_D1_ENABLED or F_V3_RANK_D2_ENABLED or F_V3_EVALUATION_ENABLED)


def any_stage_enabled() -> bool:
    return bool(
        representation_enabled()
        or admission_enabled()
        or selection_enabled()
        or evaluation_enabled()
        or (
            F_V3_LAB_ENABLED
            and (
                F_V3_PURCHASE_ENABLED
                or F_V3_RANK_D2_ENABLED
                or F_V3_AP_BANDED_ENABLED
                or F_V3_AP_COVERAGE_ENABLED
                or F_V3_SEL_REORDER_ENABLED
            )
        )
    )


def reset_flags_to_default() -> dict[str, Any]:
    return apply_v3_lab_flags(
        read_env=False,
        F_V3_REPRESENTATION=False,
        F_V3_ADMISSION=False,
        F_V3_SELECTION=False,
        F_V3_LAB_ENABLED=False,
        F_V3_EVALUATION_ENABLED=False,
        F_V3_PURCHASE_ENABLED=False,
        F_V3_RANK_D1_ENABLED=False,
        F_V3_RANK_D2_ENABLED=False,
        F_V3_A03_POOL_ADMIT_ENABLED=False,
        F_V3_A05_ADM_FAVSAFE_ENABLED=False,
        F_V3_A04_SEL_HISTORY_ENABLED=False,
        F_V3_AP_BANDED_ENABLED=False,
        F_V3_AP_COVERAGE_ENABLED=False,
        F_V3_SEL_REORDER_ENABLED=False,
    )


__all__ = [
    "F_V3_REPRESENTATION",
    "F_V3_REPRESENTATION_ENABLED",
    "F_V3_ADMISSION",
    "F_V3_ADMISSION_ENABLED",
    "F_V3_SELECTION",
    "F_V3_SELECTION_ENABLED",
    "F_V3_LAB_ENABLED",
    "F_V3_EVALUATION_ENABLED",
    "F_V3_PURCHASE_ENABLED",
    "F_V3_RANK_D1_ENABLED",
    "F_V3_RANK_D2_ENABLED",
    "F_V3_A03_POOL_ADMIT_ENABLED",
    "F_V3_A05_ADM_FAVSAFE_ENABLED",
    "F_V3_A04_SEL_HISTORY_ENABLED",
    "F_V3_AP_BANDED_ENABLED",
    "F_V3_AP_COVERAGE_ENABLED",
    "F_V3_SEL_REORDER_ENABLED",
    "apply_v3_lab_flags",
    "snapshot_flags",
    "representation_enabled",
    "admission_enabled",
    "a03_admission_enabled",
    "a05_admission_enabled",
    "selection_enabled",
    "a04_selection_enabled",
    "evaluation_enabled",
    "any_stage_enabled",
    "reset_flags_to_default",
]
