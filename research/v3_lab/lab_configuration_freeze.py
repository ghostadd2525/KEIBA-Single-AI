# -*- coding: utf-8 -*-
"""Version 3 Lab — Configuration Freeze (A-01 Evaluation + A-03 Admission).

Records the official Lab stack. Does not modify Accuracy algorithm modules.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .a01_accuracy import summarize_arm_details
from .a03_accuracy import build_a03_accuracy_corpus
from .ab_harness import churn_hit, evaluate_arm
from .contracts import CONTRACT_IDS
from .taxonomy import CONTROL_CORPUS_SIZE, CONTROL_HIT

LAB_ROOT = Path(__file__).resolve().parent
CONFIG_FREEZE_ID = "v3-lab-configuration-freeze/1.0"
BASELINE_V2_ID = "v3-lab-baseline-v2-a01-a03"
BASELINE_P5_ID = "v3-lab-baseline-p5-v1"
FREEZE_DATE = "2026-07-24"

# Official Lab stack (flags remain default OFF in code; this documents the adopted combo)
LAB_CONFIGURATION: dict[str, Any] = {
    "configuration_id": "v3-lab-config-a01-a03/1.0",
    "freeze_id": CONFIG_FREEZE_ID,
    "freeze_date": FREEZE_DATE,
    "frozen": True,
    "production_wiring": False,
    "name": "Lab Stack A-01 + A-03",
    "pipeline": [
        {
            "stage": "representation",
            "mode": "baseline",
            "policy_id": "identity",
            "flag": "F_V3_REPRESENTATION",
            "flag_state_in_stack": False,
            "note": "Baseline passthrough",
        },
        {
            "stage": "admission",
            "mode": "A-03",
            "policy_id": "AP-V3-A03-pool-coverage",
            "admission_id": "v3-adm-a03-v1",
            "flag": "F_V3_A03_POOL_ADMIT_ENABLED",
            "flag_state_in_stack": True,
            "contract": "v3-lab-admission/2.1",
            "validation": "PASS",
        },
        {
            "stage": "selection",
            "mode": "baseline",
            "policy_id": "identity",
            "flag": "F_V3_SELECTION",
            "flag_state_in_stack": False,
            "note": "Baseline passthrough",
        },
        {
            "stage": "evaluation",
            "mode": "A-01",
            "policy_id": "D1-Recalibrator",
            "evaluation_id": "v3-eval-a01-d1",
            "flag": "F_V3_RANK_D1_ENABLED",
            "flag_state_in_stack": True,
            "contract": "v3-lab-evaluation/2.0",
            "validation": "PASS",
        },
        {
            "stage": "purchase",
            "mode": "baseline",
            "mapper": "identity",
            "flag": "F_V3_PURCHASE_ENABLED",
            "flag_state_in_stack": False,
            "note": "Baseline passthrough · Delete unchanged",
        },
    ],
    "stack_flags_on": [
        "F_V3_A03_POOL_ADMIT_ENABLED",
        "F_V3_RANK_D1_ENABLED",
    ],
    "stack_flags_explicitly_off": [
        "F_V3_REPRESENTATION",
        "F_V3_ADMISSION",
        "F_V3_SELECTION",
        "F_V3_RANK_D2_ENABLED",
        "F_V3_PURCHASE_ENABLED",
    ],
    "diagram": {
        "ascii": (
            "Representation (Baseline)\n"
            "        ↓\n"
            "Admission (A-03)\n"
            "        ↓\n"
            "Selection (Baseline)\n"
            "        ↓\n"
            "Evaluation (A-01)\n"
            "        ↓\n"
            "Purchase (Baseline)"
        ),
    },
}

# Candidate roles after Configuration Freeze
CANDIDATE_REGISTRY_V2: dict[str, Any] = {
    "registry_id": "v3-accuracy-candidate-registry/2.0",
    "phase": "Lab Configuration Freeze",
    "freeze_id": CONFIG_FREEZE_ID,
    "freeze_date": FREEZE_DATE,
    "closed": True,
    "baseline_v2": {
        "id": BASELINE_V2_ID,
        "path": "research/v3_lab/baselines/lab_baseline_v2_a01_a03.json",
        "stack_hit": 255,
        "control_hit": CONTROL_HIT,
    },
    "baseline_p5": {
        "id": BASELINE_P5_ID,
        "path": "research/v3_lab/baselines/lab_baseline_p5.json",
        "note": "Foundation freeze retained; Accuracy stack baseline is v2",
    },
    "decision": {
        "adopted_stack": ["A-03 Admission", "A-01 Evaluation"],
        "a02_role": "secondary_candidate_held",
        "simultaneous_d1_d2": False,
        "production_wiring": False,
    },
    "stack_primary": {
        "name": "A-01 + A-03",
        "evaluation": "A-01",
        "admission": "A-03",
        "lab_hit": 255,
        "churn_hit": 0,
        "validation": "PASS",
        "status": "lab_adopted_configuration",
    },
    "evaluation_primary": {
        "candidate_id": "A-01",
        "flag": "F_V3_RANK_D1_ENABLED",
        "lab_hit_alone": 246,
        "status": "lab_primary_evaluation",
        "in_adopted_stack": True,
        "frozen_logic": True,
    },
    "admission_primary": {
        "candidate_id": "A-03",
        "flag": "F_V3_A03_POOL_ADMIT_ENABLED",
        "lab_hit_incremental": 255,
        "status": "lab_primary_admission",
        "in_adopted_stack": True,
        "frozen_logic": True,
    },
    "evaluation_secondary": {
        "candidate_id": "A-02",
        "flag": "F_V3_RANK_D2_ENABLED",
        "lab_hit_alone": 242,
        "status": "lab_secondary_candidate",
        "in_adopted_stack": False,
        "note": "Held as Secondary; not in official Lab stack",
        "frozen_logic": True,
    },
}

FEATURE_FLAG_INVENTORY_V2: list[dict[str, Any]] = [
    {"flag": "F_V3_REPRESENTATION", "default": False, "stack": "OFF", "role": "baseline_stage"},
    {"flag": "F_V3_ADMISSION", "default": False, "stack": "OFF", "role": "p3_policy_not_in_stack"},
    {"flag": "F_V3_SELECTION", "default": False, "stack": "OFF", "role": "baseline_stage"},
    {"flag": "F_V3_A03_POOL_ADMIT_ENABLED", "default": False, "stack": "ON", "role": "adopted_admission_a03"},
    {"flag": "F_V3_RANK_D1_ENABLED", "default": False, "stack": "ON", "role": "adopted_evaluation_a01"},
    {"flag": "F_V3_RANK_D2_ENABLED", "default": False, "stack": "OFF", "role": "secondary_candidate_a02"},
    {"flag": "F_V3_PURCHASE_ENABLED", "default": False, "stack": "OFF", "role": "baseline_stage"},
    {"flag": "F_V3_EVALUATION_ENABLED", "default": False, "stack": "OFF", "role": "legacy_alias"},
    {"flag": "F_V3_LAB_ENABLED", "default": False, "stack": "OFF", "role": "legacy_reserved"},
]

EXPERIMENT_STATUS_V2: list[dict[str, Any]] = [
    {"experiment_id": "v3-p5-freeze", "status": "complete", "note": "foundation"},
    {"experiment_id": "v3-a01-d1-recal", "status": "lab_primary_evaluation", "in_stack": True},
    {"experiment_id": "v3-a02-d2-rerank", "status": "lab_secondary_candidate", "in_stack": False},
    {"experiment_id": "v3-a03-pool-coverage", "status": "lab_primary_admission", "in_stack": True},
    {"experiment_id": "v3-lab-configuration-freeze", "status": "complete", "freeze_id": CONFIG_FREEZE_ID},
]


def _sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def module_fingerprint() -> dict[str, str]:
    names = [
        "feature_generator.py",
        "admission_policy.py",
        "admission_policy_a03.py",
        "selection_policy.py",
        "evaluation_policy.py",
        "evaluation_policy_d2.py",
    ]
    return {n: _sha16(LAB_ROOT / n) for n in names if (LAB_ROOT / n).is_file()}


def build_lab_baseline_v2() -> dict[str, Any]:
    """Measure official stack on A-03 corpus (Control OFF vs A-01+A-03)."""
    corpus = build_a03_accuracy_corpus()
    control = evaluate_arm(corpus, flag_overrides={})
    stack = evaluate_arm(
        corpus,
        flag_overrides={
            "F_V3_RANK_D1_ENABLED": True,
            "F_V3_A03_POOL_ADMIT_ENABLED": True,
        },
    )
    a01 = evaluate_arm(corpus, flag_overrides={"F_V3_RANK_D1_ENABLED": True})
    c_sum = summarize_arm_details(corpus, control)
    s_sum = summarize_arm_details(corpus, stack)
    a01_sum = summarize_arm_details(corpus, a01)
    ch = churn_hit(control, stack)
    ch_a01 = churn_hit(a01, stack)
    return {
        "baseline_id": BASELINE_V2_ID,
        "freeze_id": CONFIG_FREEZE_ID,
        "freeze_date": FREEZE_DATE,
        "generated_on": FREEZE_DATE,
        "parent_baseline": BASELINE_P5_ID,
        "corpus": {
            "id": "a03-285-*",
            "n": CONTROL_CORPUS_SIZE,
            "builder": "build_a03_accuracy_corpus",
        },
        "control": {
            "name": "Lab Baseline OFF (identity)",
            "hit": c_sum["hit"],
            "metrics": c_sum,
        },
        "a01_reference": {
            "name": "A-01 Evaluation only",
            "hit": a01_sum["hit"],
            "metrics": a01_sum,
        },
        "stack": {
            "name": "A-01 Evaluation + A-03 Admission",
            "flags_on": list(LAB_CONFIGURATION["stack_flags_on"]),
            "hit": s_sum["hit"],
            "metrics": s_sum,
            "churn_vs_control": ch,
            "churn_vs_a01": ch_a01,
        },
        "delta_stack_vs_control": {
            "hit": s_sum["hit"] - c_sum["hit"],
            "purchase": s_sum["purchase"] - c_sum["purchase"],
            "rank710": s_sum["rank710"] - c_sum["rank710"],
            "rank46": s_sum["rank46"] - c_sum["rank46"],
            "other": s_sum["other"] - c_sum["other"],
            "roi": round(s_sum["roi"] - c_sum["roi"], 4),
        },
        "configuration": LAB_CONFIGURATION,
        "candidates": CANDIDATE_REGISTRY_V2,
        "contracts": dict(CONTRACT_IDS),
        "module_sha256_16": module_fingerprint(),
        "invariants": {
            "control_hit_218": c_sum["hit"] == CONTROL_HIT,
            "stack_hit_255": s_sum["hit"] == 255,
            "churn_vs_control_0": ch == 0,
            "churn_vs_a01_0": ch_a01 == 0,
            "production_wiring": False,
            "algorithms_unchanged": True,
        },
        "notes": {
            "a02": "Secondary candidate held; not in stack",
            "defaults": "All F_V3_* remain default OFF in runtime; stack documents Lab adoption intent",
        },
    }


def artifacts_dir() -> Path:
    return LAB_ROOT / "baselines"


def write_configuration_freeze_artifacts(
    baseline: dict[str, Any] | None = None,
) -> dict[str, Path]:
    baseline = baseline or build_lab_baseline_v2()
    out = artifacts_dir()
    out.mkdir(parents=True, exist_ok=True)
    cfg_dir = out / "lab_configuration_freeze"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "baseline_v2": out / "lab_baseline_v2_a01_a03.json",
        "configuration": cfg_dir / "lab_configuration_registry.json",
        "candidates": cfg_dir / "accuracy_candidate_registry_v2.json",
        "flags": cfg_dir / "feature_flag_inventory_v2.json",
        "experiments": cfg_dir / "experiment_status_v2.json",
        "snapshot": cfg_dir / "configuration_freeze_snapshot.json",
    }
    paths["baseline_v2"].write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["configuration"].write_text(
        json.dumps(LAB_CONFIGURATION, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["candidates"].write_text(
        json.dumps(CANDIDATE_REGISTRY_V2, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["flags"].write_text(
        json.dumps(
            {"inventory_id": "v3-feature-flag-inventory/config-freeze", "flags": FEATURE_FLAG_INVENTORY_V2},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["experiments"].write_text(
        json.dumps(
            {"status_id": "v3-experiment-status/config-freeze", "experiments": EXPERIMENT_STATUS_V2},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["snapshot"].write_text(
        json.dumps(
            {
                "freeze_id": CONFIG_FREEZE_ID,
                "baseline_id": BASELINE_V2_ID,
                "configuration": LAB_CONFIGURATION,
                "candidates": CANDIDATE_REGISTRY_V2,
                "invariants": baseline["invariants"],
                "stack_metrics": baseline["stack"]["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return paths


__all__ = [
    "CONFIG_FREEZE_ID",
    "BASELINE_V2_ID",
    "LAB_CONFIGURATION",
    "CANDIDATE_REGISTRY_V2",
    "FEATURE_FLAG_INVENTORY_V2",
    "EXPERIMENT_STATUS_V2",
    "build_lab_baseline_v2",
    "write_configuration_freeze_artifacts",
]


if __name__ == "__main__":
    base = build_lab_baseline_v2()
    paths = write_configuration_freeze_artifacts(base)
    print(
        json.dumps(
            {
                "freeze_id": CONFIG_FREEZE_ID,
                "baseline_id": BASELINE_V2_ID,
                "control_hit": base["control"]["hit"],
                "stack_hit": base["stack"]["hit"],
                "invariants": base["invariants"],
                "paths": {k: str(v) for k, v in paths.items()},
            },
            indent=2,
            ensure_ascii=False,
        )
    )
