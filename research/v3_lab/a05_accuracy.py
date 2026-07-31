# -*- coding: utf-8 -*-
"""Version 3 Lab — A-05 Accuracy (Favorite-Safe Coverage Admission).

Admission-only. A-03 frozen. Lab + Offline AB:
  Control (flags OFF) vs A-03 vs A-05.

Hard Gate (Offline primary):
  worsened_winner_rank1 = 0 AND ΔHit > 0.
Lab Hit 279 reproduction is NOT required.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .a01_accuracy import STAKE_YEN, summarize_arm_details
from .a03_accuracy import build_a03_accuracy_corpus
from .ab_harness import churn_hit, evaluate_arm
from .metrics import MetricsSink
from .offline_gate import build_real_285r_corpus
from .taxonomy import taxonomy_snapshot

LAB_ROOT = Path(__file__).resolve().parent
ARTIFACTS = LAB_ROOT / "baselines" / "a05_accuracy"


def _improved_worsened(
    corpus: list[dict[str, Any]],
    control: dict[str, Any],
    treatment: dict[str, Any],
) -> dict[str, Any]:
    c_map = {d["race_id"]: d for d in control.get("details") or []}
    t_map = {d["race_id"]: d for d in treatment.get("details") or []}
    row_map = {r["race_id"]: r for r in corpus}
    improved = []
    worsened = []
    for rid, c in c_map.items():
        t = t_map.get(rid) or {}
        row = row_map.get(rid) or {}
        if (not c.get("hit")) and t.get("hit"):
            improved.append(
                {
                    "race_id": rid,
                    "miss_layer": row.get("miss_layer"),
                    "winner_rank": row.get("winner_rank"),
                    "control_pick": c.get("pick"),
                    "treatment_pick": t.get("pick"),
                }
            )
        elif c.get("hit") and (not t.get("hit")):
            worsened.append(
                {
                    "race_id": rid,
                    "miss_layer": row.get("miss_layer"),
                    "winner_rank": row.get("winner_rank"),
                    "control_pick": c.get("pick"),
                    "treatment_pick": t.get("pick"),
                }
            )
    return {"improved": improved, "worsened": worsened}


def _pick_churn(control: dict[str, Any], treatment: dict[str, Any]) -> int:
    c_map = {d["race_id"]: d for d in control.get("details") or []}
    t_map = {d["race_id"]: d for d in treatment.get("details") or []}
    n = 0
    for rid, c in c_map.items():
        t = t_map.get(rid) or {}
        if str(c.get("pick") or "") != str(t.get("pick") or ""):
            n += 1
    return n


def _arm_block(
    corpus: list[dict[str, Any]],
    control: dict[str, Any],
    treatment: dict[str, Any],
    *,
    label: str,
) -> dict[str, Any]:
    c_sum = summarize_arm_details(corpus, control)
    t_sum = summarize_arm_details(corpus, treatment)
    races = _improved_worsened(corpus, control, treatment)
    worsened_rank1 = sum(1 for w in races["worsened"] if int(w.get("winner_rank") or 0) == 1)
    ch = churn_hit(control, treatment)
    pc = _pick_churn(control, treatment)
    return {
        "label": label,
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
        "pick_churn": pc,
        "worsened_winner_rank1": worsened_rank1,
        "improved_n": len(races["improved"]),
        "worsened_n": len(races["worsened"]),
        "improved_races": races["improved"],
        "worsened_races": races["worsened"],
        "improved_layers": dict(Counter(str(x.get("miss_layer")) for x in races["improved"])),
        "worsened_layers": dict(Counter(str(x.get("miss_layer")) for x in races["worsened"])),
    }


def run_surface_ab(
    corpus: list[dict[str, Any]],
    *,
    surface: str,
) -> dict[str, Any]:
    """Compare Control / A-03 / A-05 on one corpus."""
    control = evaluate_arm(corpus, flag_overrides={})
    a03 = evaluate_arm(corpus, flag_overrides={"F_V3_A03_POOL_ADMIT_ENABLED": True})
    a05 = evaluate_arm(corpus, flag_overrides={"F_V3_A05_ADM_FAVSAFE_ENABLED": True})

    a03_block = _arm_block(corpus, control, a03, label="A-03")
    a05_block = _arm_block(corpus, control, a05, label="A-05")

    # Mutual exclusion smoke: both ON must raise
    mutex_ok = False
    try:
        evaluate_arm(
            corpus[:1],
            flag_overrides={
                "F_V3_A03_POOL_ADMIT_ENABLED": True,
                "F_V3_A05_ADM_FAVSAFE_ENABLED": True,
            },
        )
    except ValueError:
        mutex_ok = True

    return {
        "surface": surface,
        "n": len(corpus),
        "control": summarize_arm_details(corpus, control),
        "a03": a03_block,
        "a05": a05_block,
        "a03_vs_a05_hit": {
            "a03_hit": a03_block["treatment"]["hit"],
            "a05_hit": a05_block["treatment"]["hit"],
            "delta_a05_minus_a03": a05_block["treatment"]["hit"] - a03_block["treatment"]["hit"],
        },
        "mutex_a03_a05_rejected": mutex_ok,
    }


def run_a05_ab(*, force_reload_offline: bool = False) -> dict[str, Any]:
    lab_corpus = build_a03_accuracy_corpus()
    offline_corpus = build_real_285r_corpus(force_reload=force_reload_offline)

    lab = run_surface_ab(lab_corpus, surface="lab_accuracy")
    offline = run_surface_ab(offline_corpus, surface="offline_real_285r")

    off_a05 = offline["a05"]
    delta_hit = off_a05["delta"]["hit"]
    wr1 = off_a05["worsened_winner_rank1"]
    hard_pass = wr1 == 0 and delta_hit > 0
    decision = "PASS" if hard_pass else "FAIL"
    if wr1 != 0:
        decision = "FAIL_WORSENED_RANK1"
    elif delta_hit <= 0:
        decision = "FAIL_NO_DELTA_HIT"

    sink = MetricsSink()
    sink.emit("lab.a05.offline.hit", value=off_a05["treatment"]["hit"])
    sink.emit("lab.a05.offline.delta_hit", value=delta_hit)
    sink.emit("lab.a05.offline.worsened_rank1", value=wr1)

    result = {
        "experiment_id": "v3-a05-favorite-safe-coverage",
        "flag": "F_V3_A05_ADM_FAVSAFE_ENABLED",
        "stage": "Admission",
        "policy_id": "AP-V3-A05-favorite-safe-coverage",
        "contract": "v3-lab-admission/2.2",
        "a03_frozen": True,
        "taxonomy": taxonomy_snapshot(),
        "lab": lab,
        "offline": offline,
        "hard_gate": {
            "primary": "offline",
            "require_worsened_winner_rank1_0": wr1 == 0,
            "require_delta_hit_gt_0": delta_hit > 0,
            "worsened_winner_rank1": wr1,
            "delta_hit": delta_hit,
            "churn_hit": off_a05["churn_hit"],
            "pick_churn": off_a05["pick_churn"],
            "lab_hit_279_required": False,
            "pass": hard_pass,
        },
        "decision": decision,
        "stake_yen": STAKE_YEN,
        "roi_def": f"flat bet {STAKE_YEN}yen/race on top pick; ROI=(return-stake)/stake",
        "metrics": sink.snapshot(),
    }
    return result


def write_artifacts(result: dict[str, Any] | None = None) -> dict[str, Any]:
    result = result or run_a05_ab()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    full_path = ARTIFACTS / "a05_ab_full.json"
    summary_path = ARTIFACTS / "a05_metric_summary.json"
    race_diff_path = ARTIFACTS / "a05_race_diff.json"

    # Drop huge details from control arms already summarized
    full_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "experiment_id": result["experiment_id"],
        "decision": result["decision"],
        "hard_gate": result["hard_gate"],
        "lab": {
            "control_hit": result["lab"]["control"]["hit"],
            "a03_hit": result["lab"]["a03"]["treatment"]["hit"],
            "a05_hit": result["lab"]["a05"]["treatment"]["hit"],
            "a05_delta_hit": result["lab"]["a05"]["delta"]["hit"],
            "a05_worsened_rank1": result["lab"]["a05"]["worsened_winner_rank1"],
            "a05_churn_hit": result["lab"]["a05"]["churn_hit"],
            "a05_purchase": result["lab"]["a05"]["treatment"]["purchase"],
            "a05_roi": result["lab"]["a05"]["treatment"]["roi"],
        },
        "offline": {
            "control_hit": result["offline"]["control"]["hit"],
            "a03_hit": result["offline"]["a03"]["treatment"]["hit"],
            "a05_hit": result["offline"]["a05"]["treatment"]["hit"],
            "a05_delta_hit": result["offline"]["a05"]["delta"]["hit"],
            "a05_worsened_rank1": result["offline"]["a05"]["worsened_winner_rank1"],
            "a05_churn_hit": result["offline"]["a05"]["churn_hit"],
            "a05_pick_churn": result["offline"]["a05"]["pick_churn"],
            "a05_purchase": result["offline"]["a05"]["treatment"]["purchase"],
            "a05_roi": result["offline"]["a05"]["treatment"]["roi"],
            "a05_improved_n": result["offline"]["a05"]["improved_n"],
            "a05_worsened_n": result["offline"]["a05"]["worsened_n"],
        },
        "mutex_ok": result["lab"]["mutex_a03_a05_rejected"] and result["offline"]["mutex_a03_a05_rejected"],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    race_diff = {
        "lab": {
            "a03": {
                "improved": result["lab"]["a03"]["improved_races"],
                "worsened": result["lab"]["a03"]["worsened_races"],
            },
            "a05": {
                "improved": result["lab"]["a05"]["improved_races"],
                "worsened": result["lab"]["a05"]["worsened_races"],
            },
        },
        "offline": {
            "a03": {
                "improved": result["offline"]["a03"]["improved_races"],
                "worsened": result["offline"]["a03"]["worsened_races"],
            },
            "a05": {
                "improved": result["offline"]["a05"]["improved_races"],
                "worsened": result["offline"]["a05"]["worsened_races"],
            },
        },
    }
    race_diff_path.write_text(json.dumps(race_diff, ensure_ascii=False, indent=2), encoding="utf-8")
    result["artifacts"] = {
        "full": str(full_path),
        "summary": str(summary_path),
        "race_diff": str(race_diff_path),
    }
    return result


if __name__ == "__main__":
    out = write_artifacts()
    print(json.dumps({
        "decision": out["decision"],
        "hard_gate": out["hard_gate"],
        "lab_hits": {
            "control": out["lab"]["control"]["hit"],
            "a03": out["lab"]["a03"]["treatment"]["hit"],
            "a05": out["lab"]["a05"]["treatment"]["hit"],
        },
        "offline_hits": {
            "control": out["offline"]["control"]["hit"],
            "a03": out["offline"]["a03"]["treatment"]["hit"],
            "a05": out["offline"]["a05"]["treatment"]["hit"],
        },
        "artifacts": out.get("artifacts"),
    }, ensure_ascii=False, indent=2))
