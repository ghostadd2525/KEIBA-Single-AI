# -*- coding: utf-8 -*-
"""Version 3 Lab — Offline Gate (real 285R · no algorithm / wiring changes).

Control: Lab Flag OFF (identity top-1)
Treatment: Lab Baseline v3 (A-01 + A-03 + A-04)

Reads labeled_test + daily snapshots from the win5-ai parent tree (READ-only).
Does not import V2 Accuracy policies into the treatment path.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .a01_accuracy import STAKE_YEN, summarize_arm_details
from .ab_harness import churn_hit, evaluate_arm

LAB_ROOT = Path(__file__).resolve().parent
WIN5_ROOT = LAB_ROOT.parents[2]  # research/v3_lab -> research -> KEIBA-Single-AI -> win5-ai
COMPARE = WIN5_ROOT / "compare"
PE_TX_FIRE = COMPARE / "v2_pe_v2_a_treatment_fire_path.csv"
PE_SUMMARY = COMPARE / "v2_pe_v2_a_ab_summary.json"

CONTROL_HIT_V2_PE = 218
GATE_ID = "v3-offline-gate/1.0"


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "" or (isinstance(v, float) and math.isnan(v)):
            return default
        n = float(v)
        if not math.isfinite(n):
            return default
        return n
    except Exception:
        return default


def _i(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def _ensure_win5_path() -> None:
    root = str(WIN5_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def load_pe_reference() -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if PE_SUMMARY.is_file():
        summary = json.loads(PE_SUMMARY.read_text(encoding="utf-8"))
    hits: set[str] = set()
    rows: list[dict[str, Any]] = []
    if PE_TX_FIRE.is_file():
        with PE_TX_FIRE.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                rows.append(r)
                if str(r.get("after_miss_group") or "") == "Hit":
                    hits.add(str(r.get("race_id") or ""))
    return {
        "summary": summary,
        "treatment_hit_races": sorted(hits),
        "treatment_hit_n": len(hits),
        "n_rows": len(rows),
        "note": "V2 PE-V2-A Hit is purchase/pool survival Hit — not Lab top-1 Hit",
    }


def build_real_285r_corpus(*, force_reload: bool = False) -> list[dict[str, Any]]:
    """Build Lab-shaped corpus from labeled_test + daily snapshots."""
    cache = artifacts_dir() / "real_285r_corpus.json"
    if cache.is_file() and not force_reload:
        payload = json.loads(cache.read_text(encoding="utf-8"))
        races = payload.get("races") or []
        if len(races) == 285:
            return races

    _ensure_win5_path()
    from _run_phase182_belief_shadow import load_race_bundle
    from _run_phase252_staged_evaluation import load_winners_and_jobs

    jobs, winners = load_winners_and_jobs()
    races: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []
    t0 = time.time()
    for job in jobs:
        rid = str(job.get("race_id") or "")
        winner_name = str(winners.get(rid) or "").strip()
        bundle = load_race_bundle(rid)
        if not bundle:
            quality.append({"race_id": rid, "status": "bundle_missing"})
            continue
        df = bundle["race_df"]
        runners: list[dict[str, Any]] = []
        winner_id = ""
        winner_rank = 0
        for idx, row in df.iterrows():
            name = str(row.get("horse_name") or "").strip()
            hid = str(row.get("horse_id") or name or f"{rid}-{idx}")
            mr = max(_i(row.get("model_rank"), 999), 1)
            runner = {
                "horse_id": hid,
                "horse_name": name,
                "horse_number": _i(row.get("horse_number"), _i(row.get("umaban"), 0)),
                "model_rank": mr,
                "win_prob": max(0.0, min(1.0, _f(row.get("win_prob"), 0.0))),
                "odds": _f(row.get("odds"), 0.0),
                "popularity": _i(row.get("popularity"), 0),
                "history_score": _f(row.get("history_score"), _f(row.get("win_prob"), 0.0)),
                "running_style": str(row.get("running_style") or ""),
            }
            runners.append(runner)
            if winner_name and name == winner_name:
                winner_id = hid
                winner_rank = mr
        issues = []
        if not runners:
            issues.append("empty_runners")
        if not winner_id:
            issues.append("winner_unmatched")
        if any(_f(r.get("odds"), 0.0) <= 1.0 for r in runners):
            issues.append("odds_le_1_present")
        if any(not r.get("running_style") for r in runners):
            issues.append("style_blank_present")
        quality.append(
            {
                "race_id": rid,
                "status": "ok" if not issues else "degraded",
                "field_size": len(runners),
                "winner_name": winner_name,
                "winner_id": winner_id,
                "winner_rank": winner_rank,
                "issues": issues,
            }
        )
        if not winner_id or not runners:
            continue
        races.append(
            {
                "race_id": rid,
                "context": {"race_id": rid, "field_size": len(runners)},
                "runners": runners,
                "winner_id": winner_id,
                "winner_name": winner_name,
                "winner_rank": winner_rank,
                "purchase_eligible": True,
                "miss_layer": None,
                "control_hit": None,
                "source": "labeled_test+demo_daily_outputs",
            }
        )

    artifacts_dir().mkdir(parents=True, exist_ok=True)
    cache.write_text(
        json.dumps(
            {
                "builder": "build_real_285r_corpus",
                "n_jobs": len(jobs),
                "n_races": len(races),
                "elapsed_sec": round(time.time() - t0, 2),
                "quality": quality,
                "races": races,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifacts_dir() / "data_quality.json").write_text(
        json.dumps(
            {
                "n_jobs": len(jobs),
                "n_races_built": len(races),
                "status_counts": dict(Counter(q["status"] for q in quality)),
                "issue_counts": dict(
                    Counter(i for q in quality for i in (q.get("issues") or []))
                ),
                "rows": quality,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return races


def build_race_diff(
    corpus: list[dict[str, Any]],
    control: dict[str, Any],
    treatment: dict[str, Any],
) -> dict[str, Any]:
    c_map = {d["race_id"]: d for d in control.get("details") or []}
    t_map = {d["race_id"]: d for d in treatment.get("details") or []}
    improved = []
    worsened = []
    anomalies = []
    for row in corpus:
        rid = row["race_id"]
        c = c_map.get(rid) or {}
        t = t_map.get(rid) or {}
        c_hit = bool(c.get("hit"))
        t_hit = bool(t.get("hit"))
        entry = {
            "race_id": rid,
            "winner_id": row.get("winner_id"),
            "winner_name": row.get("winner_name"),
            "winner_rank": row.get("winner_rank"),
            "field_size": len(row.get("runners") or []),
            "control_pick": c.get("pick"),
            "treatment_pick": t.get("pick"),
            "control_hit": c_hit,
            "treatment_hit": t_hit,
            "pick_changed": str(c.get("pick") or "") != str(t.get("pick") or ""),
        }
        if (not c_hit) and t_hit:
            improved.append(entry)
        elif c_hit and (not t_hit):
            worsened.append(entry)
        # anomaly: treatment pick missing odds / extreme rank jump
        pick = str(t.get("pick") or "")
        runners = {str(r.get("horse_id")): r for r in (row.get("runners") or [])}
        pr = runners.get(pick)
        if pr is not None and _f(pr.get("odds"), 0.0) <= 1.0:
            anomalies.append({**entry, "anomaly": "treatment_pick_odds_le_1"})
        if pr is not None and _i(pr.get("model_rank"), 999) >= 10 and t_hit:
            anomalies.append({**entry, "anomaly": "treatment_hit_deep_rank_ge_10"})
    return {
        "improved_count": len(improved),
        "worsened_count": len(worsened),
        "improved_races": improved,
        "worsened_races": worsened,
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
    }


def corpus_fingerprint(corpus: list[dict[str, Any]]) -> str:
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
                    "history_score": r.get("history_score"),
                    "running_style": r.get("running_style"),
                }
                for r in (row.get("runners") or [])
            ],
        }
        digests.append(hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest())
    return hashlib.sha256("".join(digests).encode()).hexdigest()[:24]


def run_offline_gate(*, force_reload: bool = False) -> dict[str, Any]:
    corpus = build_real_285r_corpus(force_reload=force_reload)
    pe_ref = load_pe_reference()

    control = evaluate_arm(corpus, flag_overrides={})
    treatment = evaluate_arm(
        corpus,
        flag_overrides={
            "F_V3_RANK_D1_ENABLED": True,
            "F_V3_A03_POOL_ADMIT_ENABLED": True,
            "F_V3_A04_SEL_HISTORY_ENABLED": True,
        },
    )
    c_sum = summarize_arm_details(corpus, control)
    t_sum = summarize_arm_details(corpus, treatment)
    ch = churn_hit(control, treatment)
    diff = build_race_diff(corpus, control, treatment)

    hard_pass = (
        len(corpus) == 285
        and t_sum["hit"] > c_sum["hit"]
        and ch == 0
    )
    # Production-facing reference gate (top-1 vs V2 pool-Hit are different metrics)
    vs_v2_pe = {
        "v2_pe_hit_reference": CONTROL_HIT_V2_PE,
        "lab_treatment_top1_hit": t_sum["hit"],
        "lab_exceeds_v2_pe_hit_number": t_sum["hit"] > CONTROL_HIT_V2_PE,
        "comparable": False,
        "note": "V2 PE Hit counts purchase/pool survival; Lab Hit is top-1 pick. Numbers are not interchangeable.",
    }

    decision = "PASS" if hard_pass else "FAIL"
    fail_reasons = []
    if len(corpus) != 285:
        fail_reasons.append(f"corpus_n={len(corpus)} expected 285")
    if t_sum["hit"] <= c_sum["hit"]:
        fail_reasons.append("treatment_hit_not_gt_control")
    if ch != 0:
        fail_reasons.append(f"churn_hit={ch}")

    dq_path = artifacts_dir() / "data_quality.json"
    dq = json.loads(dq_path.read_text(encoding="utf-8")) if dq_path.is_file() else {}

    return {
        "gate_id": GATE_ID,
        "decision": decision,
        "adopt_for_shadow": decision == "PASS",
        "production_wiring": False,
        "corpus": {
            "id": "real-labeled-test-285",
            "n": len(corpus),
            "fingerprint": corpus_fingerprint(corpus),
            "source": "phase154 labeled_test + demo_daily_outputs",
        },
        "control": {
            "name": "Lab Flag OFF (identity top-1)",
            "flags_on": [],
            **c_sum,
        },
        "treatment": {
            "name": "Lab Baseline v3 (A-01 + A-03 + A-04)",
            "flags_on": [
                "F_V3_RANK_D1_ENABLED",
                "F_V3_A03_POOL_ADMIT_ENABLED",
                "F_V3_A04_SEL_HISTORY_ENABLED",
            ],
            **t_sum,
        },
        "delta": {
            "hit": t_sum["hit"] - c_sum["hit"],
            "purchase": t_sum["purchase"] - c_sum["purchase"],
            "rank710": t_sum["rank710"] - c_sum["rank710"],
            "rank46": t_sum["rank46"] - c_sum["rank46"],
            "other": t_sum["other"] - c_sum["other"],
            "roi": round(t_sum["roi"] - c_sum["roi"], 4),
        },
        "churn_hit": ch,
        "race_diff": diff,
        "hard_gate": {
            "require_n_285": len(corpus) == 285,
            "require_hit_gt_control": t_sum["hit"] > c_sum["hit"],
            "require_churn_0": ch == 0,
            "pass": hard_pass,
            "fail_reasons": fail_reasons,
            "definition": "Lab top-1: Treatment Hit > Control Hit ∧ churn=0 ∧ n=285",
        },
        "v2_pe_reference": {**pe_ref, **vs_v2_pe},
        "data_quality_summary": {
            "n_jobs": dq.get("n_jobs"),
            "n_races_built": dq.get("n_races_built"),
            "status_counts": dq.get("status_counts"),
            "issue_counts": dq.get("issue_counts"),
        },
        "risk_summary": {
            "extrapolation": "Real corpus evaluated; Lab synthetic Hit 279 is not claimed here",
            "metric_mismatch_v2_pe": vs_v2_pe["note"],
            "churn": ch,
            "anomalies": diff["anomaly_count"],
            "data_degraded": int((dq.get("status_counts") or {}).get("degraded") or 0),
        },
        "notes": {
            "scope": "Offline Gate only — no algorithm / Flag default / wiring changes",
            "roi_def": f"flat bet {STAKE_YEN}yen/race on top pick; ROI=(return-stake)/stake",
            "purchase_def": "all real races treated purchase_eligible=true (Delete boundary not applied)",
        },
    }


def artifacts_dir() -> Path:
    return LAB_ROOT / "baselines" / "offline_gate"


def write_offline_gate_artifacts(result: dict[str, Any] | None = None) -> dict[str, Path]:
    result = result or run_offline_gate()
    out = artifacts_dir()
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "full": out / "offline_gate_full.json",
        "metrics": out / "offline_gate_metric_summary.json",
        "race_diff": out / "offline_gate_race_diff.json",
        "decision": out / "offline_gate_decision.json",
    }
    paths["full"].write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["metrics"].write_text(
        json.dumps(
            {
                "control": result["control"],
                "treatment": result["treatment"],
                "delta": result["delta"],
                "churn_hit": result["churn_hit"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["race_diff"].write_text(
        json.dumps(result["race_diff"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    paths["decision"].write_text(
        json.dumps(
            {
                "gate_id": result["gate_id"],
                "decision": result["decision"],
                "hard_gate": result["hard_gate"],
                "control_hit": result["control"]["hit"],
                "treatment_hit": result["treatment"]["hit"],
                "churn_hit": result["churn_hit"],
                "production_wiring": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return paths


__all__ = [
    "GATE_ID",
    "build_real_285r_corpus",
    "run_offline_gate",
    "write_offline_gate_artifacts",
]


if __name__ == "__main__":
    res = run_offline_gate(force_reload="--reload" in sys.argv)
    paths = write_offline_gate_artifacts(res)
    print(
        json.dumps(
            {
                "decision": res["decision"],
                "control_hit": res["control"]["hit"],
                "treatment_hit": res["treatment"]["hit"],
                "churn_hit": res["churn_hit"],
                "delta": res["delta"],
                "hard_gate": res["hard_gate"],
                "paths": {k: str(v) for k, v in paths.items()},
            },
            indent=2,
            ensure_ascii=False,
        )
    )
