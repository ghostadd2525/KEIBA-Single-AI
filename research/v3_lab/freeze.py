# -*- coding: utf-8 -*-
"""Version 3 Lab — P5 Freeze snapshot (no Accuracy algorithms).

Builds a frozen Lab Baseline from contracts / flags / registry / AB harness.
Does not modify Representation / Admission / Selection policy logic.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from . import flags
from .ab_harness import (
    run_ab,
    run_p2_representation_ab,
    run_p3_admission_ab,
    run_p4_selection_ab,
)
from .contracts import CONTRACT_IDS, STAGE_ORDER
from .metrics import METRIC_POINTS
from .registry import list_experiments
from .taxonomy import (
    CONTROL_CORPUS_SIZE,
    CONTROL_HIT,
    CONTROL_MISS,
    taxonomy_snapshot,
    validate_taxonomy_lock,
)

FREEZE_ID = "v3-lab-freeze/1.0"
BASELINE_ID = "v3-lab-baseline-p5-v1"
FREEZE_DATE = "2026-07-24"

# Pipeline stages frozen at P5 (Evaluation / Purchase remain stubs)
FROZEN_PIPELINE = tuple(STAGE_ORDER)

FROZEN_CONTRACTS = dict(CONTRACT_IDS)

CANONICAL_STAGE_FLAGS = (
    "F_V3_REPRESENTATION",
    "F_V3_ADMISSION",
    "F_V3_SELECTION",
)

RESERVED_FLAGS = (
    "F_V3_LAB_ENABLED",
    "F_V3_EVALUATION_ENABLED",
    "F_V3_PURCHASE_ENABLED",
    "F_V3_RANK_D1_ENABLED",
    "F_V3_RANK_D2_ENABLED",
    "F_V3_AP_BANDED_ENABLED",
    "F_V3_AP_COVERAGE_ENABLED",
    "F_V3_SEL_REORDER_ENABLED",
)

ALIAS_FLAGS = (
    "F_V3_REPRESENTATION_ENABLED",
    "F_V3_ADMISSION_ENABLED",
    "F_V3_SELECTION_ENABLED",
)

DESIGN_ALIGNMENT = (
    {
        "design": "Representation → Admission → Selection → Evaluation → Purchase",
        "impl": "research/v3_lab/pipeline.py + stages.py",
        "status": "aligned",
    },
    {
        "design": "Feature Contract / Representation First (柱 I)",
        "impl": "feature_generator.py · F_V3_REPRESENTATION · contract 2.0",
        "status": "aligned",
    },
    {
        "design": "Admission Policy AP-V3-A Banded Deep (柱 II)",
        "impl": "admission_policy.py · F_V3_ADMISSION · contract 2.0",
        "status": "aligned",
    },
    {
        "design": "Selection Reorder-only SEL-V3-RO (柱 III · Rescue 禁止)",
        "impl": "selection_policy.py · F_V3_SELECTION · contract 2.0",
        "status": "aligned",
    },
    {
        "design": "Evaluation Ranking D1/D2 · Purchase Mapper",
        "impl": "stages stubs only (1.0 contracts)",
        "status": "stub_deferred",
    },
    {
        "design": "V2 Production non-interference · Flag OFF identity",
        "impl": "all F_V3_* default OFF · package not wired to production",
        "status": "aligned",
    },
)


def flag_inventory() -> dict[str, Any]:
    flags.reset_flags_to_default()
    snap = flags.snapshot_flags()
    inventory = []
    for name in CANONICAL_STAGE_FLAGS:
        inventory.append(
            {
                "flag": name,
                "default": False,
                "role": "canonical_stage",
                "value": bool(snap.get(name)),
            }
        )
    for name in ALIAS_FLAGS:
        inventory.append(
            {
                "flag": name,
                "default": False,
                "role": "alias",
                "value": bool(snap.get(name)),
            }
        )
    for name in RESERVED_FLAGS:
        inventory.append(
            {
                "flag": name,
                "default": False,
                "role": "reserved_or_legacy",
                "value": bool(snap.get(name)),
            }
        )
    all_off = all(not bool(snap.get(k)) for k in (*CANONICAL_STAGE_FLAGS, *ALIAS_FLAGS, *RESERVED_FLAGS))
    return {
        "all_default_off": all_off,
        "any_stage_on": bool(snap.get("any_stage_on")),
        "identity_when_all_off": True,
        "flags": inventory,
    }


def registry_freeze_view() -> dict[str, Any]:
    rows = []
    for exp in list_experiments():
        rows.append(
            {
                "experiment_id": exp.get("experiment_id"),
                "phase": exp.get("phase"),
                "flag": exp.get("flag"),
                "status": exp.get("status"),
                "accuracy_intervention": bool(exp.get("accuracy_intervention")),
                "alias_of": exp.get("alias_of"),
            }
        )
    return {
        "frozen": True,
        "count": len(rows),
        "experiments": rows,
    }


def _ab_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "experiment_id": result.get("experiment_id"),
        "flag": result.get("flag"),
        "control_hit": (result.get("control") or {}).get("hit"),
        "treatment_hit": (result.get("treatment") or {}).get("hit"),
        "churn_hit": result.get("churn_hit"),
        "control_reproduces_218": result.get("control_reproduces_218"),
        "hard_gate_pass": ((result.get("hard_gate") or {}).get("pass")),
    }


def run_freeze_ab_suite() -> dict[str, Any]:
    """Final AB confirmation for P5 (identity + stage parity)."""
    identity = run_ab(treatment_flags={})
    p2 = run_p2_representation_ab()
    p3 = run_p3_admission_ab()
    p4 = run_p4_selection_ab()
    return {
        "control_identity": _ab_summary({**identity, "experiment_id": "control-identity", "flag": None}),
        "p2_representation": _ab_summary(p2),
        "p3_admission": _ab_summary(p3),
        "p4_selection": _ab_summary(p4),
        "parity_all_pass": all(
            [
                identity.get("control_reproduces_218"),
                identity.get("churn_hit") == 0,
                p2.get("churn_hit") == 0 and p2["treatment"]["hit"] == CONTROL_HIT,
                p3.get("churn_hit") == 0 and p3["treatment"]["hit"] == CONTROL_HIT,
                p4.get("churn_hit") == 0 and p4["treatment"]["hit"] == CONTROL_HIT,
            ]
        ),
        "hard_gate_none_claimed": not any(
            [
                identity["hard_gate"]["pass"],
                p2["hard_gate"]["pass"],
                p3["hard_gate"]["pass"],
                p4["hard_gate"]["pass"],
            ]
        ),
    }


def build_lab_baseline(*, run_ab: bool = True) -> dict[str, Any]:
    """Assemble frozen Lab Baseline artifact."""
    tax_errors = validate_taxonomy_lock()
    inventory = flag_inventory()
    ab = run_freeze_ab_suite() if run_ab else {"skipped": True}
    return {
        "freeze_id": FREEZE_ID,
        "baseline_id": BASELINE_ID,
        "freeze_date": FREEZE_DATE,
        "generated_on": str(date.today()),
        "control": {
            "name": "V2 Final (PE-V2-A)",
            "hit": CONTROL_HIT,
            "corpus_size": CONTROL_CORPUS_SIZE,
            "miss": CONTROL_MISS,
        },
        "pipeline": {
            "frozen": True,
            "stages": list(FROZEN_PIPELINE),
            "implemented": ["representation", "admission", "selection"],
            "stubs": ["evaluation", "purchase"],
        },
        "contracts": {
            "frozen": True,
            "ids": dict(FROZEN_CONTRACTS),
        },
        "feature_flags": inventory,
        "experiment_registry": registry_freeze_view(),
        "metrics_points": list(METRIC_POINTS),
        "taxonomy": taxonomy_snapshot(),
        "taxonomy_lock_errors": tax_errors,
        "design_alignment": list(DESIGN_ALIGNMENT),
        "ab_harness": ab,
        "boundaries": {
            "v2_production_unchanged": True,
            "no_prediction_api_wiring": True,
            "no_ui_ops_explain_changes": True,
            "no_accuracy_algorithm_added_in_p5": True,
            "evaluation_not_started": True,
        },
        "ready_for_accuracy_experiments": True,
        "note": "P5 Freeze — Lab foundation fixed; Evaluation / Accuracy AB require separate approval",
    }


def baseline_path() -> Path:
    return Path(__file__).resolve().parent / "baselines" / "lab_baseline_p5.json"


def write_lab_baseline(path: Path | None = None, *, run_ab: bool = True) -> Path:
    out = path or baseline_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = build_lab_baseline(run_ab=run_ab)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def validate_freeze(baseline: dict[str, Any] | None = None) -> list[str]:
    """Return errors if freeze invariants are broken."""
    errors: list[str] = []
    flags.reset_flags_to_default()
    snap = flags.snapshot_flags()
    for name in (*CANONICAL_STAGE_FLAGS, *ALIAS_FLAGS, *RESERVED_FLAGS):
        if snap.get(name):
            errors.append(f"flag default not OFF: {name}")
    if snap.get("any_stage_on"):
        errors.append("any_stage_on must be False at default")
    if list(STAGE_ORDER) != list(FROZEN_PIPELINE):
        errors.append("STAGE_ORDER drifted from FROZEN_PIPELINE")
    if dict(CONTRACT_IDS) != FROZEN_CONTRACTS:
        errors.append("CONTRACT_IDS drifted from FROZEN_CONTRACTS")
    errors.extend(validate_taxonomy_lock())
    data = baseline if baseline is not None else build_lab_baseline(run_ab=False)
    if not data.get("feature_flags", {}).get("all_default_off"):
        errors.append("feature_flags.all_default_off expected True")
    if data.get("control", {}).get("hit") != CONTROL_HIT:
        errors.append("baseline control hit mismatch")
    return errors


__all__ = [
    "FREEZE_ID",
    "BASELINE_ID",
    "FREEZE_DATE",
    "FROZEN_PIPELINE",
    "FROZEN_CONTRACTS",
    "flag_inventory",
    "registry_freeze_view",
    "run_freeze_ab_suite",
    "build_lab_baseline",
    "baseline_path",
    "write_lab_baseline",
    "validate_freeze",
]


if __name__ == "__main__":
    path = write_lab_baseline(run_ab=True)
    print(f"wrote {path}")
