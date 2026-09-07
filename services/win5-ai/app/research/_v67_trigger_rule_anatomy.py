# -*- coding: utf-8 -*-
"""Version67 — Trigger Rule Anatomy Audit (research only).

Decompose R1 / R7 / R8 internal conditions on 285R.
No Trigger / Threshold / Signal / Polarity / PE / Prediction / Production mutation.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.research.world_trigger_saturation import (  # noqa: E402
    TRIGGER_RULES,
    evaluate_all_rules,
    normalize_signals,
    atomic_margin,
)
from app.research.w_s1_shadow_dual_eval import (  # noqa: E402
    ranking_concepts,
    restore_trigger_signals,
    _f,
)


TARGET_RULES = ("R1_mixed_short_field", "R7_midupper_diff", "R8_core_default")

# Explicit condition catalog from real TRIGGER_RULES / classify_world_line_type
CONDITIONS = {
    "R1_mixed_short_field": {
        "world": "mixed_world",
        "structure": "AND(sfp>=0.72, OR(phase>=0.48, chaos>=0.42, difficulty>=0.42))",
        "logic": "AND of Must-like gate + OR Aux bundle (product code; roles descriptive)",
        "atoms": [
            {"id": "R1.sfp_ge_0.72", "signal": "short_field_pressure", "op": "ge", "threshold": 0.72, "role": "AND_gate"},
            {"id": "R1.phase_ge_0.48", "signal": "phase", "op": "ge", "threshold": 0.48, "role": "OR_arm"},
            {"id": "R1.chaos_ge_0.42", "signal": "chaos", "op": "ge", "threshold": 0.42, "role": "OR_arm"},
            {"id": "R1.difficulty_ge_0.42", "signal": "difficulty", "op": "ge", "threshold": 0.42, "role": "OR_arm"},
        ],
        "composites": [
            {"id": "R1.OR_bundle", "role": "OR", "of": ["R1.phase_ge_0.48", "R1.chaos_ge_0.42", "R1.difficulty_ge_0.42"]},
            {"id": "R1.full", "role": "AND", "of": ["R1.sfp_ge_0.72", "R1.OR_bundle"]},
        ],
    },
    "R7_midupper_diff": {
        "world": "midupper_world",
        "structure": "AND(difficulty>=0.50)",
        "logic": "single Must-like atom (no Aux/Exclusion in rule body)",
        "atoms": [
            {"id": "R7.difficulty_ge_0.50", "signal": "difficulty", "op": "ge", "threshold": 0.50, "role": "AND_only"},
        ],
        "composites": [
            {"id": "R7.full", "role": "AND", "of": ["R7.difficulty_ge_0.50"]},
        ],
    },
    "R8_core_default": {
        "world": "core_world",
        "structure": "DEFAULT (no positive Must; residual after R1–R7 FAIL)",
        "logic": "Exclusion-of-others / residual — not Ability Must (V42)",
        "atoms": [],
        "composites": [
            {"id": "R8.default_always", "role": "DEFAULT", "of": []},
        ],
    },
}


def eval_atom(sig: dict[str, float | None], atom: dict[str, Any]) -> dict[str, Any]:
    am = atomic_margin(sig, atom["signal"], float(atom["threshold"]))
    return {
        "id": atom["id"],
        "signal": atom["signal"],
        "threshold": atom["threshold"],
        "role": atom["role"],
        "value": am["value"],
        "pass": bool(am["pass"]),
        "missing": bool(am["missing"]),
        "margin": am["margin"],
    }


def first_match_rule(evals: list[dict[str, Any]]) -> str:
    for r in sorted(evals, key=lambda x: int(x["priority"])):
        if r.get("is_default"):
            return str(r["rule_id"])
        if r.get("pass"):
            return str(r["rule_id"])
    return "R8_core_default"


def build_sig(rid: str, race: dict[str, Any], fx: dict[str, Any] | None) -> tuple[dict[str, float | None], bool]:
    concepts = ranking_concepts(race)
    field_size = (fx or {}).get("field_size") or (race.get("context") or {}).get("field_size")
    distance = (fx or {}).get("distance")
    restored = restore_trigger_signals(rid, field_size, distance)
    raw = {
        "chaos": restored.get("chaos"),
        "difficulty": restored.get("difficulty"),
        "phase": restored.get("phase"),
        "late_stop": restored.get("late_stop"),
        "sustained": restored.get("sustained"),
        "high_pace": restored.get("high_pace"),
        "short_field_pressure": restored.get("short_field_pressure"),
    }
    return normalize_signals(raw), bool(restored)


def main() -> None:
    v66 = json.loads((ROOT / "docs/research/_v66-rule-attribution.json").read_text(encoding="utf-8"))
    summary = {r["race_id"]: r for r in v66["rows_all_summary"]}
    corp = {
        r["race_id"]: r
        for r in json.loads(
            (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
        )["races"]
    }
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fxby = {r["race_id"]: r for r in (fx.get("rows") or fx.get("evaluations"))}

    race_rows = []
    for rid, race in corp.items():
        sig, restored_ok = build_sig(rid, race, fxby.get(rid))
        evals = evaluate_all_rules(sig)
        firing = first_match_rule(evals)
        meta = summary.get(rid) or {}
        intent = meta.get("intent_gt")
        agree = bool(meta.get("agree"))

        atom_state = {}
        for rule_id in ("R1_mixed_short_field", "R7_midupper_diff"):
            for atom in CONDITIONS[rule_id]["atoms"]:
                atom_state[atom["id"]] = eval_atom(sig, atom)

        # composites
        r1_or = any(atom_state[a]["pass"] for a in ("R1.phase_ge_0.48", "R1.chaos_ge_0.42", "R1.difficulty_ge_0.42"))
        r1_sfp = atom_state["R1.sfp_ge_0.72"]["pass"]
        r1_full = r1_sfp and r1_or
        r7_full = atom_state["R7.difficulty_ge_0.50"]["pass"]

        # R1 OR arm contribution when R1 fires
        or_arms_true = [
            a
            for a in ("R1.phase_ge_0.48", "R1.chaos_ge_0.42", "R1.difficulty_ge_0.42")
            if atom_state[a]["pass"]
        ]

        # R8 residual: which prior rules failed + bottlenecks
        prior_fail = {}
        for e in evals:
            if e["rule_id"] == "R8_core_default":
                continue
            prior_fail[e["rule_id"]] = {
                "pass": bool(e.get("pass")),
                "bottleneck": e.get("bottleneck"),
            }

        race_rows.append(
            {
                "race_id": rid,
                "intent_gt": intent,
                "agree": agree,
                "firing_rule": firing,
                "restored_ok": restored_ok,
                "signals": {k: sig.get(k) for k in ("short_field_pressure", "phase", "chaos", "difficulty", "high_pace", "late_stop", "sustained")},
                "atoms": {k: {kk: vv for kk, vv in v.items() if kk != "id"} for k, v in atom_state.items()},
                "r1_or": r1_or,
                "r1_sfp": r1_sfp,
                "r1_full": r1_full,
                "r7_full": r7_full,
                "r1_or_arms_true": or_arms_true,
                "prior_fail": prior_fail,
                "trigger_mismatch_top3": (not agree)
                and firing in TARGET_RULES
                and meta.get("root_cause_ai") == "Trigger",
            }
        )

    n = len(race_rows)

    def cond_metrics(cond_id: str, world: str, pred_pass_fn) -> dict[str, Any]:
        # Precision: among pass, GT==world; Recall: among GT==world, pass
        passes = [r for r in race_rows if pred_pass_fn(r)]
        gt_w = [r for r in race_rows if r["intent_gt"] == world]
        tp = sum(1 for r in passes if r["intent_gt"] == world)
        fp = len(passes) - tp
        fn = sum(1 for r in gt_w if not pred_pass_fn(r))
        return {
            "pass_n": len(passes),
            "gt_support": len(gt_w),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": (tp / len(passes)) if passes else None,
            "recall": (tp / len(gt_w)) if gt_w else None,
            "pass_rate": len(passes) / n,
            "missing_rate": None,
        }

    # Missing rates per atom
    missing_rates = {}
    for rule_id in ("R1_mixed_short_field", "R7_midupper_diff"):
        for atom in CONDITIONS[rule_id]["atoms"]:
            cid = atom["id"]
            miss = sum(1 for r in race_rows if r["atoms"][cid]["missing"])
            missing_rates[cid] = miss / n

    condition_analysis = {}
    # R1 atoms + composites
    for atom in CONDITIONS["R1_mixed_short_field"]["atoms"]:
        cid = atom["id"]
        m = cond_metrics(cid, "mixed_world", lambda r, c=cid: r["atoms"][c]["pass"])
        m["missing_rate"] = missing_rates[cid]
        m["role"] = atom["role"]
        m["rule"] = "R1_mixed_short_field"
        condition_analysis[cid] = m
    condition_analysis["R1.OR_bundle"] = {
        **cond_metrics("R1.OR_bundle", "mixed_world", lambda r: r["r1_or"]),
        "role": "OR",
        "rule": "R1_mixed_short_field",
        "missing_rate": None,
    }
    condition_analysis["R1.full"] = {
        **cond_metrics("R1.full", "mixed_world", lambda r: r["r1_full"]),
        "role": "AND_full",
        "rule": "R1_mixed_short_field",
        "missing_rate": None,
    }
    for atom in CONDITIONS["R7_midupper_diff"]["atoms"]:
        cid = atom["id"]
        m = cond_metrics(cid, "midupper_world", lambda r, c=cid: r["atoms"][c]["pass"])
        m["missing_rate"] = missing_rates[cid]
        m["role"] = atom["role"]
        m["rule"] = "R7_midupper_diff"
        condition_analysis[cid] = m

    # R8: DEFAULT fires when firing_rule==R8
    condition_analysis["R8.default_fires"] = {
        **cond_metrics("R8.default_fires", "core_world", lambda r: r["firing_rule"] == "R8_core_default"),
        "role": "DEFAULT",
        "rule": "R8_core_default",
        "missing_rate": None,
    }

    # Dead conditions
    dead = []
    for cid, m in condition_analysis.items():
        pr = m["pass_rate"]
        if pr is None:
            continue
        label = None
        if pr >= 0.95:
            label = "always_or_nearly_always_True"
        elif pr <= 0.05:
            label = "always_or_nearly_always_False"
        elif m.get("missing_rate") is not None and m["missing_rate"] >= 0.5:
            label = "high_missing"
        if label:
            dead.append({"condition": cid, "label": label, "pass_rate": pr, "missing_rate": m.get("missing_rate")})

    # Failure modes for Top3 trigger mismatches
    fail_r1 = Counter()
    fail_r7 = Counter()
    fail_r8 = Counter()
    r1_or_contrib = Counter()
    r8_prior_bottleneck = Counter()

    for r in race_rows:
        if not r["trigger_mismatch_top3"]:
            continue
        fr = r["firing_rule"]
        if fr == "R1_mixed_short_field":
            # which OR arms enabled the FP
            arms = r["r1_or_arms_true"]
            if not arms:
                fail_r1["OR_empty_but_fired"] += 1  # should not happen
            else:
                for a in arms:
                    r1_or_contrib[a] += 1
                if len(arms) == 1:
                    fail_r1[f"OR_sole:{arms[0]}"] += 1
                else:
                    fail_r1[f"OR_multi:{len(arms)}"] += 1
            fail_r1["sfp_gate_true"] += int(r["r1_sfp"])
            # dependency
            if not r["restored_ok"]:
                fail_r1["dep:Data"] += 1
            elif any(r["atoms"][a]["missing"] for a in r["atoms"] if a.startswith("R1.")):
                fail_r1["dep:Signal"] += 1
            else:
                fail_r1["dep:Rule設計"] += 1
        elif fr == "R7_midupper_diff":
            fail_r7["difficulty_ge_0.50"] += 1
            if not r["restored_ok"]:
                fail_r7["dep:Data"] += 1
            elif r["atoms"]["R7.difficulty_ge_0.50"]["missing"]:
                fail_r7["dep:Signal"] += 1
            else:
                fail_r7["dep:Rule設計"] += 1
        elif fr == "R8_core_default":
            # why earlier rules failed — bottleneck signal
            for rid, pf in r["prior_fail"].items():
                if pf["pass"]:
                    continue
                bot = pf.get("bottleneck") or {}
                sig = bot.get("signal") or "unknown"
                miss = bot.get("missing")
                r8_prior_bottleneck[f"{rid}:{sig}:{'missing' if miss else 'margin'}"] += 1
            if not r["restored_ok"]:
                fail_r8["dep:Data"] += 1
            else:
                # residual design
                fail_r8["dep:Rule設計"] += 1

    # When R1 fails (not full), bottleneck among races where GT==mixed (FN path)
    r1_fn_bottleneck = Counter()
    for r in race_rows:
        if r["intent_gt"] != "mixed_world":
            continue
        if r["r1_full"]:
            continue
        if not r["r1_sfp"] and not r["r1_or"]:
            r1_fn_bottleneck["both_sfp_and_OR"] += 1
        elif not r["r1_sfp"]:
            r1_fn_bottleneck["sfp_fail"] += 1
        else:
            r1_fn_bottleneck["OR_fail"] += 1

    # Priority within rules (by FP contribution / failure counts)
    priority = {
        "R1_mixed_short_field": sorted(
            [
                {"condition": "R1.sfp_ge_0.72", "note": "AND gate required for all R1 fires", "trigger_fp_n": 50, "precision": condition_analysis["R1.sfp_ge_0.72"]["precision"]},
                {"condition": "R1.difficulty_ge_0.42", "note": "OR arm contribution on R1 FP", "or_contrib_on_fp": r1_or_contrib.get("R1.difficulty_ge_0.42", 0), "precision": condition_analysis["R1.difficulty_ge_0.42"]["precision"]},
                {"condition": "R1.chaos_ge_0.42", "note": "OR arm contribution on R1 FP", "or_contrib_on_fp": r1_or_contrib.get("R1.chaos_ge_0.42", 0), "precision": condition_analysis["R1.chaos_ge_0.42"]["precision"]},
                {"condition": "R1.phase_ge_0.48", "note": "OR arm contribution on R1 FP", "or_contrib_on_fp": r1_or_contrib.get("R1.phase_ge_0.48", 0), "precision": condition_analysis["R1.phase_ge_0.48"]["precision"]},
            ],
            key=lambda x: (-(x.get("or_contrib_on_fp") or x.get("trigger_fp_n") or 0),),
        ),
        "R7_midupper_diff": [
            {
                "condition": "R7.difficulty_ge_0.50",
                "note": "sole atom; all 57 Trigger FP pass through this condition",
                "trigger_fp_n": 57,
                "precision": condition_analysis["R7.difficulty_ge_0.50"]["precision"],
                "pass_rate": condition_analysis["R7.difficulty_ge_0.50"]["pass_rate"],
            }
        ],
        "R8_core_default": [
            {
                "condition": "R8.DEFAULT_residual",
                "note": "no positive Must; fires when R1–R7 all FAIL",
                "trigger_fp_n": 46,
                "precision": condition_analysis["R8.default_fires"]["precision"],
                "top_prior_bottlenecks": r8_prior_bottleneck.most_common(8),
            }
        ],
    }

    # Dependency summary
    dependency = {
        "R1_mixed_short_field": {
            "Rule設計": fail_r1.get("dep:Rule設計", 0),
            "Data": fail_r1.get("dep:Data", 0),
            "Signal": fail_r1.get("dep:Signal", 0),
            "n_trigger_fp": 50,
        },
        "R7_midupper_diff": {
            "Rule設計": fail_r7.get("dep:Rule設計", 0),
            "Data": fail_r7.get("dep:Data", 0),
            "Signal": fail_r7.get("dep:Signal", 0),
            "n_trigger_fp": 57,
        },
        "R8_core_default": {
            "Rule設計": fail_r8.get("dep:Rule設計", 0),
            "Data": fail_r8.get("dep:Data", 0),
            "Signal": fail_r8.get("dep:Signal", 0),
            "n_trigger_fp": 46,
        },
    }

    # Governance
    # A if we identified concrete conditions; C if structure itself (DEFAULT/single difficulty) needs redesign
    # User scale: A=改善ポイント特定 B=追加分析 C=Rule構造変更が必要
    # R8 is structurally DEFAULT → points to C for R8; R7 single difficulty is also structural
    # Overall: conditions identified clearly → but Top3 include structural issues → C or B?
    # "改善ポイント特定" = A if we know which conditions
    # "Rule構造変更が必要" = C if AND/OR/DEFAULT design is the root not tunable thresholds
    # We identified points AND structure issues (DEFAULT, difficulty-only). Governance C for needing structure change,
    # or A for having identified improvement points within anatomy?
    # Reading again: A 改善ポイント特定 / B 追加分析必要 / C Rule構造変更が必要
    # R7 is single condition - "improvement point" IS the difficulty atom, but fixing may need structure (add Must axes) = C
    # R8 DEFAULT = C structure
    # R1 has identifiable OR arms = A-ish for R1
    # Overall verdict: C because Top3 responsibility is dominated by structural patterns (DEFAULT + difficulty-only + broad OR),
    # while still listing concrete conditions. Or A because points are identified.
    # I'll use: overall **C** with note that condition-level points are identified but primary remedies are structural (DEFAULT / single-signal Must), not threshold tweaks. User forbade threshold changes anyway.
    # Actually A = "改善ポイント特定" - we DID identify points. C = need structure change.
    # Both can be true. Prefer C when DEFAULT and single-atom rules dominate FP, because anatomy shows structure not dead conditions.
    
    structural = True  # R8 DEFAULT + R7 single atom + R1 OR breadth
    grade = "C"
    reason = (
        "Condition-level failures identified, but dominant patterns are structural: "
        "R8=DEFAULT residual (no Must), R7=difficulty-only Must, R1=broad OR after sfp gate. "
        "Not explained away as Signal/Data alone."
    )

    out = {
        "schema": "v67-trigger-rule-anatomy/1.0",
        "n": n,
        "target_rules": list(TARGET_RULES),
        "rule_internal": CONDITIONS,
        "condition_analysis": condition_analysis,
        "dead_conditions": dead,
        "failure_modes": {
            "R1": dict(fail_r1),
            "R1_or_arm_contrib_on_trigger_fp": dict(r1_or_contrib),
            "R1_fn_bottleneck_gt_mixed": dict(r1_fn_bottleneck),
            "R7": dict(fail_r7),
            "R8": dict(fail_r8),
            "R8_prior_bottlenecks": r8_prior_bottleneck.most_common(20),
        },
        "dependency": dependency,
        "priority": priority,
        "governance": {"grade": grade, "reason": reason},
        # compact race sample not full signals to keep file smaller — store summary counts only
        "fires": {
            "R1": sum(1 for r in race_rows if r["firing_rule"] == "R1_mixed_short_field"),
            "R7": sum(1 for r in race_rows if r["firing_rule"] == "R7_midupper_diff"),
            "R8": sum(1 for r in race_rows if r["firing_rule"] == "R8_core_default"),
        },
    }
    path = ROOT / "docs/research/_v67-rule-anatomy.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("n", n)
    print("dead", dead)
    print("cond P/R sample")
    for k in ["R1.sfp_ge_0.72", "R1.OR_bundle", "R1.full", "R7.difficulty_ge_0.50", "R8.default_fires"]:
        m = condition_analysis[k]
        print(k, "P", m["precision"], "R", m["recall"], "pass_rate", round(m["pass_rate"], 3))
    print("R1 or contrib", dict(r1_or_contrib))
    print("R1 fail", dict(fail_r1))
    print("R7 fail", dict(fail_r7))
    print("R8 dep", dependency["R8_core_default"])
    print("R8 bottlenecks", r8_prior_bottleneck.most_common(8))
    print("grade", grade)
    print("wrote", path)


if __name__ == "__main__":
    main()
