# -*- coding: utf-8 -*-
"""Version 3 Lab — A-03 Validation (no new Accuracy algorithms).

Validates A-03 alone and A-01+A-03 incremental stack.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import flags
from .a01_accuracy import STAKE_YEN, summarize_arm_details
from .a03_accuracy import A01_PRIMARY_HIT, build_a03_accuracy_corpus, run_a03_ab
from .ab_harness import churn_hit, evaluate_arm
from .pipeline import run_lab_pipeline
from .taxonomy import CONTROL_CORPUS_SIZE, CONTROL_HIT

LAB_ROOT = Path(__file__).resolve().parent

# Modules that must remain unchanged through A-03 Validation
# (Admission A-03 policy is snapshotted separately; P3 admission_policy stays frozen)
FROZEN_MODULE_SHA256_16 = {
    "feature_generator.py": "32a71445b03ddb65",
    "evaluation_policy.py": "5fcd339f846e4d46",
    "evaluation_policy_d2.py": "9e6c63994517371b",
    "selection_policy.py": "cea5a9befae0b1a6",
    "admission_policy.py": "78a79ebce7786dea",
    "admission_policy_a03.py": "04142443526f62b0",
}

EXPECTED_A03_SOLO = {
    "control_hit": 218,
    "treatment_hit": 227,
    "churn_hit": 0,
    "delta_hit": 9,
    "pool_improved": 9,
}

EXPECTED_A01_A03 = {
    "control_hit": 246,
    "treatment_hit": 255,
    "churn_hit": 0,
    "delta_hit": 9,
    "pool_improved": 9,
}


def _sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def verify_frozen_modules() -> dict[str, Any]:
    """Confirm Representation / Evaluation / Selection / P3 Admission / A-03 policy SHA."""
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


def verify_stage_isolation_a03_solo(sample_race: dict[str, Any]) -> dict[str, Any]:
    """A-03 Flag only: Admission A-03 ON; Rep/Sel/Eval/Purchase identity."""
    flags.reset_flags_to_default()
    flags.apply_v3_lab_flags(read_env=False, F_V3_A03_POOL_ADMIT_ENABLED=True)
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
        "admission_a03": adm_policy == "AP-V3-A03-pool-coverage",
        "selection_identity": sel_policy == "identity",
        "evaluation_disabled": not ev_on,
        "purchase_identity_mapper": purchase_mapper == "identity",
        "flags_only_a03": (
            flags.F_V3_A03_POOL_ADMIT_ENABLED
            and not flags.F_V3_REPRESENTATION
            and not flags.F_V3_ADMISSION
            and not flags.F_V3_SELECTION
            and not flags.F_V3_RANK_D1_ENABLED
            and not flags.F_V3_RANK_D2_ENABLED
        ),
    }
    return {"pass": all(checks.values()), "checks": checks, "race_id": sample_race.get("race_id")}


def verify_stage_isolation_a01_a03(sample_race: dict[str, Any]) -> dict[str, Any]:
    """A-01+A-03: Eval D1 + Admission A-03; Rep/Sel/Purchase identity; no D2."""
    flags.reset_flags_to_default()
    flags.apply_v3_lab_flags(
        read_env=False,
        F_V3_RANK_D1_ENABLED=True,
        F_V3_A03_POOL_ADMIT_ENABLED=True,
    )
    bundle = run_lab_pipeline(sample_race["context"], sample_race["runners"])
    rep_on = bool(((bundle.get("representation") or {}).get("journal") or {}).get("enabled"))
    adm_policy = str((bundle.get("admission") or {}).get("policy_id") or "")
    sel_policy = str((bundle.get("selection") or {}).get("policy_id") or "")
    ev_mode = str(((bundle.get("evaluation") or {}).get("eval_journal") or {}).get("mode") or "")
    purchase_mapper = str(
        (((bundle.get("purchase") or {}).get("purchase_plan") or {}).get("mapper") or "")
    )
    checks = {
        "representation_disabled": not rep_on,
        "admission_a03": adm_policy == "AP-V3-A03-pool-coverage",
        "selection_identity": sel_policy == "identity",
        "evaluation_d1": ev_mode == "d1_recalibrator",
        "purchase_identity_mapper": purchase_mapper == "identity",
        "no_d2": not flags.F_V3_RANK_D2_ENABLED,
        "no_p3_admission_flag": not flags.F_V3_ADMISSION,
        "no_representation_flag": not flags.F_V3_REPRESENTATION,
        "no_selection_flag": not flags.F_V3_SELECTION,
    }
    return {"pass": all(checks.values()), "checks": checks, "race_id": sample_race.get("race_id")}


def verify_input_identity(corpus: list[dict[str, Any]]) -> dict[str, Any]:
    digests = []
    for row in corpus:
        payload = {
            "race_id": row["race_id"],
            "winner_id": row.get("winner_id"),
            "runners": [
                {
                    "horse_id": r.get("horse_id"),
                    "model_rank": r.get("model_rank"),
                    "win_prob": r.get("win_prob"),
                    "odds": r.get("odds"),
                    "running_style": r.get("running_style"),
                }
                for r in (row.get("runners") or [])
            ],
        }
        digests.append(hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest())
    corpus_fp = hashlib.sha256("".join(digests).encode()).hexdigest()[:24]

    c = evaluate_arm(corpus, flag_overrides={})
    t_solo = evaluate_arm(corpus, flag_overrides={"F_V3_A03_POOL_ADMIT_ENABLED": True})
    t_stack = evaluate_arm(
        corpus,
        flag_overrides={"F_V3_RANK_D1_ENABLED": True, "F_V3_A03_POOL_ADMIT_ENABLED": True},
    )
    ids = {r["race_id"] for r in corpus}
    same = (
        {d["race_id"] for d in c.get("details") or []}
        == {d["race_id"] for d in t_solo.get("details") or []}
        == {d["race_id"] for d in t_stack.get("details") or []}
        == ids
    )
    return {
        "pass": same and len(corpus) == CONTROL_CORPUS_SIZE,
        "corpus_fingerprint": corpus_fp,
        "n": len(corpus),
        "same_race_ids": same,
        "note": "Control/Treatment arms share identical corpus inputs",
    }


def build_race_diff(
    corpus: list[dict[str, Any]],
    control: dict[str, Any],
    treatment: dict[str, Any],
) -> dict[str, Any]:
    c_map = {d["race_id"]: d for d in control.get("details") or []}
    t_map = {d["race_id"]: d for d in treatment.get("details") or []}
    improved: list[dict[str, Any]] = []
    worsened: list[dict[str, Any]] = []
    unchanged_hit: list[str] = []
    unchanged_miss: list[str] = []
    for row in corpus:
        rid = row["race_id"]
        c = c_map.get(rid) or {}
        t = t_map.get(rid) or {}
        c_hit = bool(c.get("hit"))
        t_hit = bool(t.get("hit"))
        layer = row.get("miss_layer")
        entry = {
            "race_id": rid,
            "miss_layer": layer,
            "winner_id": row.get("winner_id"),
            "winner_rank": row.get("winner_rank"),
            "control_pick": c.get("pick"),
            "treatment_pick": t.get("pick"),
            "control_hit": c_hit,
            "treatment_hit": t_hit,
            "pick_changed": str(c.get("pick") or "") != str(t.get("pick") or ""),
        }
        if c_hit and t_hit:
            unchanged_hit.append(rid)
            entry["status"] = "unchanged_hit"
        elif (not c_hit) and (not t_hit):
            unchanged_miss.append(rid)
            entry["status"] = "unchanged_miss"
        elif (not c_hit) and t_hit:
            improved.append(entry)
            entry["status"] = "improved"
        else:
            worsened.append(entry)
            entry["status"] = "worsened_churn"
    by_layer = Counter(str(x.get("miss_layer") or "?") for x in improved)
    return {
        "improved_count": len(improved),
        "worsened_count": len(worsened),
        "unchanged_hit_count": len(unchanged_hit),
        "unchanged_miss_count": len(unchanged_miss),
        "improved_by_layer": dict(by_layer),
        "pool_improved_count": by_layer.get("Pool", 0),
        "improved_races": improved,
        "worsened_races": worsened,
        "races": None,  # filled by caller if needed
    }


def _panel(
    name: str,
    corpus: list[dict[str, Any]],
    control_flags: dict[str, bool],
    treatment_flags: dict[str, bool],
    expected: dict[str, Any],
) -> dict[str, Any]:
    control = evaluate_arm(corpus, flag_overrides=control_flags)
    treatment = evaluate_arm(corpus, flag_overrides=treatment_flags)
    ch = churn_hit(control, treatment)
    c_sum = summarize_arm_details(corpus, control)
    t_sum = summarize_arm_details(corpus, treatment)
    diff = build_race_diff(corpus, control, treatment)
    matches = (
        c_sum["hit"] == expected["control_hit"]
        and t_sum["hit"] == expected["treatment_hit"]
        and ch == expected["churn_hit"]
        and (t_sum["hit"] - c_sum["hit"]) == expected["delta_hit"]
        and diff["pool_improved_count"] == expected["pool_improved"]
        and diff["worsened_count"] == 0
    )
    return {
        "panel": name,
        "control_flags": control_flags,
        "treatment_flags": treatment_flags,
        "metric_summary": {
            "control": c_sum,
            "treatment": t_sum,
            "delta": {
                "hit": t_sum["hit"] - c_sum["hit"],
                "purchase": t_sum["purchase"] - c_sum["purchase"],
                "rank710": t_sum["rank710"] - c_sum["rank710"],
                "rank46": t_sum["rank46"] - c_sum["rank46"],
                "other": t_sum["other"] - c_sum["other"],
                "roi": round(t_sum["roi"] - c_sum["roi"], 4),
            },
            "churn_hit": ch,
            "roi_def": f"flat {STAKE_YEN}yen/race on top pick; ROI=(return-stake)/stake",
        },
        "race_diff": {
            "improved_count": diff["improved_count"],
            "worsened_count": diff["worsened_count"],
            "unchanged_hit_count": diff["unchanged_hit_count"],
            "unchanged_miss_count": diff["unchanged_miss_count"],
            "improved_by_layer": diff["improved_by_layer"],
            "pool_improved_count": diff["pool_improved_count"],
            "improved_races": diff["improved_races"],
            "worsened_races": diff["worsened_races"],
        },
        "flag_comparison": {
            "off": {"flags": control_flags, **c_sum},
            "on": {"flags": treatment_flags, **t_sum},
        },
        "expected": expected,
        "matches_expected": matches,
        "pass": matches and ch == 0 and t_sum["hit"] > c_sum["hit"],
    }


def run_reproducibility(*, rounds: int = 2) -> dict[str, Any]:
    results = [run_a03_ab() for _ in range(rounds)]
    ref = results[0]
    stable = True
    keys = ("decision", "churn_hit", "control_reproduces_a01_246")
    metric_keys = ("hit", "purchase", "rank710", "rank46", "other", "roi")
    for r in results[1:]:
        for k in keys:
            if r.get(k) != ref.get(k):
                stable = False
        for arm in ("control", "treatment", "baseline", "a03_only"):
            for mk in metric_keys:
                if arm in r and arm in ref:
                    if (r.get(arm) or {}).get(mk) != (ref.get(arm) or {}).get(mk):
                        stable = False
        if r.get("delta") != ref.get("delta"):
            stable = False
    return {
        "pass": stable,
        "rounds": rounds,
        "reference": {
            "baseline_hit": ref["baseline"]["hit"],
            "a03_only_hit": ref["a03_only"]["hit"],
            "control_hit": ref["control"]["hit"],
            "treatment_hit": ref["treatment"]["hit"],
            "churn_hit": ref["churn_hit"],
            "delta_hit": ref["delta"]["hit"],
            "decision": ref["decision"],
            "pool_improved": len(ref.get("improved_races") or []),
        },
        "matches_expected": (
            ref["baseline"]["hit"] == EXPECTED_A03_SOLO["control_hit"]
            and ref["a03_only"]["hit"] == EXPECTED_A03_SOLO["treatment_hit"]
            and ref["control"]["hit"] == EXPECTED_A01_A03["control_hit"]
            and ref["treatment"]["hit"] == EXPECTED_A01_A03["treatment_hit"]
            and ref["churn_hit"] == 0
            and len(ref.get("improved_races") or []) == 9
        ),
    }


def run_a03_validation() -> dict[str, Any]:
    corpus = build_a03_accuracy_corpus()
    # Prefer a Pool race for A-03 isolation sample
    pool_sample = next(r for r in corpus if r.get("miss_layer") == "Pool")
    hit_sample = next(r for r in corpus if r.get("control_hit"))

    solo = _panel(
        "a03_solo",
        corpus,
        control_flags={},
        treatment_flags={"F_V3_A03_POOL_ADMIT_ENABLED": True},
        expected=EXPECTED_A03_SOLO,
    )
    stack = _panel(
        "a01_plus_a03",
        corpus,
        control_flags={"F_V3_RANK_D1_ENABLED": True},
        treatment_flags={
            "F_V3_RANK_D1_ENABLED": True,
            "F_V3_A03_POOL_ADMIT_ENABLED": True,
        },
        expected=EXPECTED_A01_A03,
    )
    repro = run_reproducibility(rounds=2)
    inputs = verify_input_identity(corpus)
    modules = verify_frozen_modules()
    iso_solo = verify_stage_isolation_a03_solo(pool_sample)
    iso_stack = verify_stage_isolation_a01_a03(hit_sample)

    validation_pass = all(
        [
            solo["pass"],
            stack["pass"],
            stack["metric_summary"]["treatment"]["hit"] > A01_PRIMARY_HIT,
            repro["pass"],
            repro["matches_expected"],
            inputs["pass"],
            modules["pass"],
            iso_solo["pass"],
            iso_stack["pass"],
        ]
    )
    decision = "PASS" if validation_pass else "FAIL"

    return {
        "validation_id": "v3-a03-validation/1.0",
        "experiment_id": "v3-a03-pool-coverage",
        "flag": "F_V3_A03_POOL_ADMIT_ENABLED",
        "decision": decision,
        "adopt_lab": decision == "PASS",
        "production_wiring": False,
        "panels": {
            "a03_solo": solo,
            "a01_plus_a03": stack,
        },
        "hard_gate": {
            "a03_solo_hit_gt_218": solo["metric_summary"]["treatment"]["hit"] > CONTROL_HIT,
            "a01_a03_hit_gt_246": stack["metric_summary"]["treatment"]["hit"] > A01_PRIMARY_HIT,
            "churn_solo_0": solo["metric_summary"]["churn_hit"] == 0,
            "churn_stack_0": stack["metric_summary"]["churn_hit"] == 0,
            "pool_9_solo": solo["race_diff"]["pool_improved_count"] == 9,
            "pool_9_stack": stack["race_diff"]["pool_improved_count"] == 9,
            "pass": validation_pass,
        },
        "reproducibility": repro,
        "input_identity": inputs,
        "frozen_modules": modules,
        "stage_isolation": {
            "a03_solo": iso_solo,
            "a01_plus_a03": iso_stack,
        },
        "metric_summary": {
            "a03_solo": solo["metric_summary"],
            "a01_plus_a03": stack["metric_summary"],
        },
        "race_diff": {
            "a03_solo": solo["race_diff"],
            "a01_plus_a03": stack["race_diff"],
        },
        "notes": {
            "scope": "Validation only — no new Accuracy algorithm",
            "unchanged": [
                "Representation",
                "Evaluation logic",
                "Selection",
                "Purchase",
                "Version2 Production",
                "Prediction API",
                "UI",
                "Operations",
                "Explainability",
            ],
            "corpus": "Lab synthetic 285R (a03-285-*)",
        },
    }


def artifacts_dir() -> Path:
    return LAB_ROOT / "baselines" / "a03_validation"


def write_validation_artifacts(result: dict[str, Any] | None = None) -> dict[str, Path]:
    result = result or run_a03_validation()
    out = artifacts_dir()
    out.mkdir(parents=True, exist_ok=True)
    full = out / "a03_validation_full.json"
    summary = out / "a03_metric_summary.json"
    race = out / "a03_race_diff.json"
    full.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary.write_text(
        json.dumps(result["metric_summary"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    race.write_text(
        json.dumps(result["race_diff"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"full": full, "summary": summary, "race_diff": race}


__all__ = [
    "EXPECTED_A03_SOLO",
    "EXPECTED_A01_A03",
    "verify_frozen_modules",
    "run_reproducibility",
    "run_a03_validation",
    "write_validation_artifacts",
]


if __name__ == "__main__":
    res = run_a03_validation()
    paths = write_validation_artifacts(res)
    print(
        json.dumps(
            {
                "decision": res["decision"],
                "hard_gate": res["hard_gate"],
                "repro": res["reproducibility"]["pass"],
                "paths": {k: str(v) for k, v in paths.items()},
            },
            indent=2,
            ensure_ascii=False,
        )
    )
