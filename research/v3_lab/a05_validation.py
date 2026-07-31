# -*- coding: utf-8 -*-
"""Version 3 Lab — A-05 Validation (no new Accuracy algorithms).

Reproduces Offline Hard Gate: Control (Flag OFF) vs A-05 ON.
Does not modify algorithms, Feature Flag defaults, or Production.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import flags
from .a01_accuracy import STAKE_YEN, summarize_arm_details
from .a03_accuracy import build_a03_accuracy_corpus
from .a05_accuracy import _arm_block
from .ab_harness import evaluate_arm
from .offline_gate import build_real_285r_corpus, corpus_fingerprint
from .pipeline import run_lab_pipeline

LAB_ROOT = Path(__file__).resolve().parent
ARTIFACTS = LAB_ROOT / "baselines" / "a05_validation"
VALIDATION_ID = "v3-a05-validation/1.0"

# Frozen algorithm modules (must not change during Validation)
FROZEN_MODULE_SHA256_16 = {
    "feature_generator.py": "32a71445b03ddb65",
    "admission_policy.py": "78a79ebce7786dea",
    "admission_policy_a03.py": "04142443526f62b0",  # A-03 frozen
    "admission_policy_a05.py": "368017d328a21cb0",  # A-05 Accuracy snapshot
    "evaluation_policy.py": "5fcd339f846e4d46",
    "evaluation_policy_d2.py": "9e6c63994517371b",
    "selection_policy.py": "cea5a9befae0b1a6",
    "selection_policy_a04.py": "4c3538e74ba05980",
}

EXPECTED_OFFLINE = {
    "control_hit": 59,
    "treatment_hit": 66,
    "delta_hit": 7,
    "churn_hit": 0,
    "worsened_n": 0,
    "worsened_winner_rank1": 0,
    "improved_n": 7,
    "treatment_roi": 0.5235,
    "control_roi": 0.0246,
}

EXPECTED_IMPROVED_RACE_IDS = [
    "2024-02-11-東京-10",
    "2024-04-21-東京-10",
    "2024-04-28-東京-10",
    "2024-06-02-京都-10",
    "2024-06-30-小倉-10",
    "2026-02-15-京都-11",
    "2026-03-22-中京-11",
]

EXPECTED_LAB = {
    "control_hit": 218,
    "treatment_hit": 218,
    "delta_hit": 0,
    "churn_hit": 0,
    "worsened_n": 0,
    "improved_n": 0,
}


def _sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def verify_frozen_modules() -> dict[str, Any]:
    rows = []
    ok = True
    for name, expected in FROZEN_MODULE_SHA256_16.items():
        path = LAB_ROOT / name
        actual = _sha16(path) if path.is_file() else ""
        match = actual == expected
        if not match:
            ok = False
        rows.append({"module": name, "expected": expected, "actual": actual, "match": match})
    return {"pass": ok, "modules": rows}


def verify_flag_defaults() -> dict[str, Any]:
    snap = flags.reset_flags_to_default()
    checks = {
        "a05_default_off": snap.get("F_V3_A05_ADM_FAVSAFE_ENABLED") is False,
        "a03_default_off": snap.get("F_V3_A03_POOL_ADMIT_ENABLED") is False,
        "a04_default_off": snap.get("F_V3_A04_SEL_HISTORY_ENABLED") is False,
        "d1_default_off": snap.get("F_V3_RANK_D1_ENABLED") is False,
    }
    return {"pass": all(checks.values()), "checks": checks, "snapshot": snap}


def verify_stage_isolation_a05(sample_race: dict[str, Any]) -> dict[str, Any]:
    flags.reset_flags_to_default()
    flags.apply_v3_lab_flags(read_env=False, F_V3_A05_ADM_FAVSAFE_ENABLED=True)
    bundle = run_lab_pipeline(sample_race["context"], sample_race["runners"])
    rep_on = bool(((bundle.get("representation") or {}).get("journal") or {}).get("enabled"))
    adm_policy = str((bundle.get("admission") or {}).get("policy_id") or "")
    sel_policy = str((bundle.get("selection") or {}).get("policy_id") or "")
    ev_on = bool(((bundle.get("evaluation") or {}).get("eval_journal") or {}).get("enabled"))
    purchase_mapper = str(
        (((bundle.get("purchase") or {}).get("purchase_plan") or {}).get("mapper") or "")
    )
    checks = {
        "representation_disabled": not rep_on,
        "admission_a05": adm_policy == "AP-V3-A05-favorite-safe-coverage",
        "selection_identity": sel_policy == "identity",
        "evaluation_disabled": not ev_on,
        "purchase_identity_mapper": purchase_mapper == "identity",
        "flags_only_a05": (
            flags.F_V3_A05_ADM_FAVSAFE_ENABLED
            and not flags.F_V3_A03_POOL_ADMIT_ENABLED
            and not flags.F_V3_REPRESENTATION
            and not flags.F_V3_ADMISSION
            and not flags.F_V3_SELECTION
            and not flags.F_V3_A04_SEL_HISTORY_ENABLED
            and not flags.F_V3_RANK_D1_ENABLED
            and not flags.F_V3_RANK_D2_ENABLED
        ),
    }
    return {"pass": all(checks.values()), "checks": checks, "race_id": sample_race.get("race_id")}


def verify_input_identity(corpus: list[dict[str, Any]]) -> dict[str, Any]:
    fp = corpus_fingerprint(corpus)
    c = evaluate_arm(corpus, flag_overrides={})
    t = evaluate_arm(corpus, flag_overrides={"F_V3_A05_ADM_FAVSAFE_ENABLED": True})
    ids = {r["race_id"] for r in corpus}
    same = (
        {d["race_id"] for d in c.get("details") or []}
        == {d["race_id"] for d in t.get("details") or []}
        == ids
    )
    return {
        "pass": same and len(corpus) == 285,
        "corpus_fingerprint": fp,
        "n": len(corpus),
        "same_race_ids": same,
        "note": "Control/Treatment share identical Offline corpus inputs",
    }


def _evaluate_panel(
    name: str,
    corpus: list[dict[str, Any]],
    expected: dict[str, Any],
    *,
    check_improved_ids: bool = False,
) -> dict[str, Any]:
    control = evaluate_arm(corpus, flag_overrides={})
    treatment = evaluate_arm(corpus, flag_overrides={"F_V3_A05_ADM_FAVSAFE_ENABLED": True})
    block = _arm_block(corpus, control, treatment, label="A-05")
    c_sum = block["control"]
    t_sum = block["treatment"]
    improved_ids = [x["race_id"] for x in block["improved_races"]]
    ids_match = (
        sorted(improved_ids) == sorted(EXPECTED_IMPROVED_RACE_IDS)
        if check_improved_ids
        else True
    )
    matches = (
        c_sum["hit"] == expected["control_hit"]
        and t_sum["hit"] == expected["treatment_hit"]
        and block["delta"]["hit"] == expected["delta_hit"]
        and block["churn_hit"] == expected["churn_hit"]
        and block["worsened_n"] == expected["worsened_n"]
        and block["improved_n"] == expected["improved_n"]
        and ids_match
    )
    if "worsened_winner_rank1" in expected:
        matches = matches and block["worsened_winner_rank1"] == expected["worsened_winner_rank1"]
    if "treatment_roi" in expected:
        matches = matches and t_sum["roi"] == expected["treatment_roi"]
    if "control_roi" in expected:
        matches = matches and c_sum["roi"] == expected["control_roi"]

    hard = {
        "worsened_winner_rank1_0": block["worsened_winner_rank1"] == 0,
        "delta_hit_gt_0": block["delta"]["hit"] > 0 if name.startswith("offline") else True,
        "churn_hit": block["churn_hit"],
        "pick_churn": block["pick_churn"],
    }
    # Offline primary hard gate
    if name.startswith("offline"):
        hard_pass = hard["worsened_winner_rank1_0"] and hard["delta_hit_gt_0"]
    else:
        hard_pass = block["worsened_winner_rank1"] == 0 and block["churn_hit"] == 0

    return {
        "panel": name,
        "metric_summary": {
            "control": c_sum,
            "treatment": t_sum,
            "delta": block["delta"],
            "churn_hit": block["churn_hit"],
            "pick_churn": block["pick_churn"],
            "worsened_winner_rank1": block["worsened_winner_rank1"],
            "roi_def": f"flat {STAKE_YEN}yen/race on top pick; ROI=(return-stake)/stake",
        },
        "race_diff": {
            "improved_count": block["improved_n"],
            "worsened_count": block["worsened_n"],
            "worsened_winner_rank1": block["worsened_winner_rank1"],
            "improved_races": block["improved_races"],
            "worsened_races": block["worsened_races"],
            "improved_race_ids": improved_ids,
            "expected_improved_race_ids": EXPECTED_IMPROVED_RACE_IDS if check_improved_ids else None,
            "improved_ids_match": ids_match,
        },
        "flag_comparison": {
            "off": {"F_V3_A05_ADM_FAVSAFE_ENABLED": False, **c_sum},
            "on": {"F_V3_A05_ADM_FAVSAFE_ENABLED": True, **t_sum},
        },
        "expected": expected,
        "matches_expected": matches,
        "hard_gate": {**hard, "pass": hard_pass},
        "pass": matches and hard_pass,
    }


def run_reproducibility(
    corpus: list[dict[str, Any]],
    *,
    rounds: int = 2,
) -> dict[str, Any]:
    panels = []
    for i in range(rounds):
        panels.append(
            _evaluate_panel(
                f"offline_round_{i+1}",
                corpus,
                EXPECTED_OFFLINE,
                check_improved_ids=True,
            )
        )
    ref = panels[0]
    stable = all(
        p["metric_summary"]["control"] == ref["metric_summary"]["control"]
        and p["metric_summary"]["treatment"] == ref["metric_summary"]["treatment"]
        and p["metric_summary"]["delta"] == ref["metric_summary"]["delta"]
        and p["metric_summary"]["churn_hit"] == ref["metric_summary"]["churn_hit"]
        and p["metric_summary"]["worsened_winner_rank1"]
        == ref["metric_summary"]["worsened_winner_rank1"]
        and p["race_diff"]["improved_race_ids"] == ref["race_diff"]["improved_race_ids"]
        and p["race_diff"]["worsened_count"] == 0
        for p in panels
    )
    return {
        "pass": stable and ref["pass"],
        "rounds": rounds,
        "reference": {
            "control_hit": ref["metric_summary"]["control"]["hit"],
            "treatment_hit": ref["metric_summary"]["treatment"]["hit"],
            "delta_hit": ref["metric_summary"]["delta"]["hit"],
            "churn_hit": ref["metric_summary"]["churn_hit"],
            "pick_churn": ref["metric_summary"]["pick_churn"],
            "worsened_winner_rank1": ref["metric_summary"]["worsened_winner_rank1"],
            "improved_n": ref["race_diff"]["improved_count"],
            "worsened_n": ref["race_diff"]["worsened_count"],
            "treatment_roi": ref["metric_summary"]["treatment"]["roi"],
            "improved_race_ids": ref["race_diff"]["improved_race_ids"],
        },
        "rounds_detail": [
            {
                "panel": p["panel"],
                "pass": p["pass"],
                "hit": p["metric_summary"]["treatment"]["hit"],
                "delta_hit": p["metric_summary"]["delta"]["hit"],
                "worsened_rank1": p["metric_summary"]["worsened_winner_rank1"],
            }
            for p in panels
        ],
        "matches_expected": ref["matches_expected"],
    }


def run_a05_validation(*, rounds: int = 2) -> dict[str, Any]:
    offline_corpus = build_real_285r_corpus()
    lab_corpus = build_a03_accuracy_corpus()

    offline_panel = _evaluate_panel(
        "offline_control_vs_a05",
        offline_corpus,
        EXPECTED_OFFLINE,
        check_improved_ids=True,
    )
    lab_panel = _evaluate_panel(
        "lab_control_vs_a05",
        lab_corpus,
        EXPECTED_LAB,
        check_improved_ids=False,
    )
    repro = run_reproducibility(offline_corpus, rounds=rounds)
    inputs = verify_input_identity(offline_corpus)
    modules = verify_frozen_modules()
    flag_defaults = verify_flag_defaults()
    sample = next(r for r in offline_corpus if len(r.get("runners") or []) >= 12)
    isolation = verify_stage_isolation_a05(sample)

    # Mutex still enforced
    mutex_ok = False
    try:
        flags.reset_flags_to_default()
        flags.apply_v3_lab_flags(
            read_env=False,
            F_V3_A03_POOL_ADMIT_ENABLED=True,
            F_V3_A05_ADM_FAVSAFE_ENABLED=True,
        )
    except ValueError:
        mutex_ok = True

    validation_pass = all(
        [
            offline_panel["pass"],
            lab_panel["pass"],
            repro["pass"],
            inputs["pass"],
            modules["pass"],
            flag_defaults["pass"],
            isolation["pass"],
            mutex_ok,
        ]
    )
    decision = "PASS" if validation_pass else "FAIL"

    return {
        "validation_id": VALIDATION_ID,
        "experiment_id": "v3-a05-favorite-safe-coverage",
        "flag": "F_V3_A05_ADM_FAVSAFE_ENABLED",
        "scope": "Control vs A-05 · Offline Hard Gate reproducibility",
        "algorithm_changes": False,
        "flag_default_changes": False,
        "production_wiring": False,
        "decision": decision,
        "adopt_lab": validation_pass,
        "offline_panel": offline_panel,
        "lab_panel": lab_panel,
        "reproducibility": repro,
        "input_identity": inputs,
        "frozen_modules": modules,
        "flag_defaults": flag_defaults,
        "stage_isolation": isolation,
        "mutex_a03_a05_rejected": mutex_ok,
        "hard_gate": offline_panel["hard_gate"],
    }


def write_artifacts(result: dict[str, Any] | None = None) -> dict[str, Any]:
    result = result or run_a05_validation(rounds=2)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    full_path = ARTIFACTS / "a05_validation_full.json"
    summary_path = ARTIFACTS / "a05_metric_summary.json"
    race_diff_path = ARTIFACTS / "a05_race_diff.json"
    repro_path = ARTIFACTS / "a05_reproducibility.json"

    full_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    off = result["offline_panel"]["metric_summary"]
    summary = {
        "validation_id": result["validation_id"],
        "decision": result["decision"],
        "offline": {
            "control": off["control"],
            "treatment": off["treatment"],
            "delta": off["delta"],
            "churn_hit": off["churn_hit"],
            "pick_churn": off["pick_churn"],
            "worsened_winner_rank1": off["worsened_winner_rank1"],
        },
        "lab": {
            "control": result["lab_panel"]["metric_summary"]["control"],
            "treatment": result["lab_panel"]["metric_summary"]["treatment"],
            "delta": result["lab_panel"]["metric_summary"]["delta"],
            "churn_hit": result["lab_panel"]["metric_summary"]["churn_hit"],
        },
        "hard_gate": result["hard_gate"],
        "reproducibility_pass": result["reproducibility"]["pass"],
        "sha_pass": result["frozen_modules"]["pass"],
        "input_identity_pass": result["input_identity"]["pass"],
        "corpus_fingerprint": result["input_identity"]["corpus_fingerprint"],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    race_diff = {
        "offline": result["offline_panel"]["race_diff"],
        "lab": result["lab_panel"]["race_diff"],
    }
    race_diff_path.write_text(json.dumps(race_diff, ensure_ascii=False, indent=2), encoding="utf-8")
    repro_path.write_text(
        json.dumps(result["reproducibility"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result["artifacts"] = {
        "full": str(full_path),
        "summary": str(summary_path),
        "race_diff": str(race_diff_path),
        "reproducibility": str(repro_path),
    }
    return result


if __name__ == "__main__":
    out = write_artifacts()
    print(
        json.dumps(
            {
                "decision": out["decision"],
                "hard_gate": out["hard_gate"],
                "offline_hit": {
                    "control": out["offline_panel"]["metric_summary"]["control"]["hit"],
                    "a05": out["offline_panel"]["metric_summary"]["treatment"]["hit"],
                },
                "repro": out["reproducibility"]["pass"],
                "sha": out["frozen_modules"]["pass"],
                "artifacts": out.get("artifacts"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
