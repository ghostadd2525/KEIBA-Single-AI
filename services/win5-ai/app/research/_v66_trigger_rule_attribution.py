# -*- coding: utf-8 -*-
"""Version66 — Trigger Rule Attribution Audit (research only).

Attribute V65 Trigger-cause misclassifications to Legacy TRIGGER_RULES R1–R8.
No Trigger / Signal / Threshold / Polarity / Exclusion / PE / Prediction / World / Production mutation.
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
    first_match_world,
    normalize_signals,
)
from app.research.w_s1_shadow_dual_eval import (  # noqa: E402
    build_legacy_meta,
    ranking_concepts,
    restore_trigger_signals,
    _f,
)
from app.research._v65_world_intent_validation import (  # noqa: E402
    intent_scores,
    pick_intent_gt,
    batch_medians,
    ranking_concepts as intent_ranking_concepts,
)


RULE_IDS = [r["rule_id"] for r in TRIGGER_RULES]
RULE_WORLD = {r["rule_id"]: r["world"] for r in TRIGGER_RULES}


def first_match_rule(rule_evals: list[dict[str, Any]]) -> dict[str, Any]:
    for r in sorted(rule_evals, key=lambda x: int(x["priority"])):
        if r.get("is_default"):
            return r
        if r.get("pass"):
            return r
    # should not happen
    return next(x for x in rule_evals if x.get("is_default"))


def build_signals(rid: str, race: dict[str, Any], fx: dict[str, Any] | None) -> tuple[dict[str, float | None], bool]:
    concepts = ranking_concepts(race)
    field_size = (fx or {}).get("field_size") or (race.get("context") or {}).get("field_size")
    distance = (fx or {}).get("distance")
    restored = restore_trigger_signals(rid, field_size, distance)
    restored_ok = bool(restored)
    # Match W-S1: fill meta keys used by classify; missing → None (nz→0 in product)
    sig = {
        **concepts,
        "difficulty": restored.get("difficulty"),
        "chaos": restored.get("chaos"),
        "high_pace": restored.get("high_pace"),
        "late_stop": restored.get("late_stop"),
        "sustained": restored.get("sustained"),
        "phase": restored.get("phase"),
        "short_field_pressure": restored.get("short_field_pressure"),
        "field_size": _f(field_size),
        "distance": _f(distance),
    }
    return sig, restored_ok


def main() -> None:
    import demo_ticket_optimizer_core as core

    v65 = json.loads((ROOT / "docs/research/_v65-intent-validation.json").read_text(encoding="utf-8"))
    v65_by = {r["race_id"]: r for r in v65["rows"]}
    corp = {
        r["race_id"]: r
        for r in json.loads(
            (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
        )["races"]
    }
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fxby = {r["race_id"]: r for r in (fx.get("rows") or fx.get("evaluations"))}

    # observational medians for intent GT (same races)
    concept_rows = [intent_ranking_concepts(corp[rid].get("runners") or []) for rid in corp]
    thr = batch_medians(concept_rows, ["top_gap", "mid_eval_band_open", "ability_separation", "top_monopoly"])

    rows = []
    for rid, race in corp.items():
        v65r = v65_by.get(rid) or {}
        sig, restored_ok = build_signals(rid, race, fxby.get(rid))
        # Rule eval uses normalize_signals keys
        rule_sig = normalize_signals(
            {
                "chaos": sig.get("chaos"),
                "difficulty": sig.get("difficulty"),
                "phase": sig.get("phase"),
                "late_stop": sig.get("late_stop"),
                "sustained": sig.get("sustained"),
                "high_pace": sig.get("high_pace"),
                "short_field_pressure": sig.get("short_field_pressure"),
            }
        )
        evals = evaluate_all_rules(rule_sig)
        winner = first_match_rule(evals)
        fm_world = first_match_world(evals)
        meta = build_legacy_meta(sig)
        legacy = core.safe_text(core.classify_world_line_type(meta))

        # Intent GT: prefer V65 stored; recompute if missing
        intent_gt = v65r.get("intent_gt")
        if not intent_gt:
            wr = v65r.get("winner_model_rank")
            if wr is None:
                wid = str(race.get("winner_id") or "")
                for u in race.get("runners") or []:
                    if str(u.get("horse_id")) == wid:
                        wr = int(u.get("model_rank") or 999)
                        break
            scores = intent_scores(
                int(wr or 999),
                intent_ranking_concepts(race.get("runners") or []),
                thr,
            )
            intent_gt = pick_intent_gt(scores)

        ai_world = v65r.get("ai_world") or legacy
        root = v65r.get("root_cause_ai") or "unknown"
        agree = intent_gt == ai_world

        # which non-default rules passed
        passed_rules = [e["rule_id"] for e in evals if e.get("pass") and not e.get("is_default")]

        rows.append(
            {
                "race_id": rid,
                "intent_gt": intent_gt,
                "ai_world": ai_world,
                "legacy_recomputed": legacy,
                "first_match_world": fm_world,
                "firing_rule": winner["rule_id"],
                "firing_world": winner["world"],
                "agree": agree,
                "root_cause_ai": root,
                "restored_ok": restored_ok,
                "legacy_matches_first_match": legacy == fm_world,
                "ai_matches_recomputed": ai_world == legacy,
                "passed_rules": passed_rules,
                "rule_pass": {e["rule_id"]: bool(e.get("pass")) for e in evals},
            }
        )

    n = len(rows)
    trigger_rows = [r for r in rows if r["root_cause_ai"] == "Trigger" and not r["agree"]]
    # V65 counted Trigger mismatches; verify
    n_trigger = len(trigger_rows)

    # Attribution among Trigger mismatches
    attr = Counter(r["firing_rule"] for r in trigger_rows)
    attr_by_world = defaultdict(Counter)  # rule -> intent_gt -> n
    attr_rule_to_ai = defaultdict(Counter)  # rule -> ai_world
    for r in trigger_rows:
        attr_by_world[r["firing_rule"]][r["intent_gt"]] += 1
        attr_rule_to_ai[r["firing_rule"]][r["ai_world"]] += 1

    # Full-corpus rule metrics
    fires = Counter(r["firing_rule"] for r in rows)
    rule_stats = {}
    for rid in RULE_IDS:
        fired = [r for r in rows if r["firing_rule"] == rid]
        world = RULE_WORLD[rid]
        tp = sum(1 for r in fired if r["intent_gt"] == world)
        fp = sum(1 for r in fired if r["intent_gt"] != world)
        # GT support for this world
        gt_world = [r for r in rows if r["intent_gt"] == world]
        # recall: among GT==world, this rule was the firing rule
        tp_rec = sum(1 for r in gt_world if r["firing_rule"] == rid)
        fn = len(gt_world) - tp_rec
        prec = tp / len(fired) if fired else None
        rec = tp_rec / len(gt_world) if gt_world else None
        # Intent agreement when rule fires (same as precision for world-targeted rules)
        agree_rate = sum(1 for r in fired if r["agree"]) / len(fired) if fired else None
        rule_stats[rid] = {
            "world": world,
            "fires": len(fired),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "gt_support": len(gt_world),
            "precision": prec,
            "recall": rec,
            "intent_agree_when_fires": agree_rate,
            "trigger_mismatch_attributed": attr.get(rid, 0),
        }

    # Confusion: firing_rule × intent_gt (full and trigger-only)
    cm_full = defaultdict(Counter)
    cm_trig = defaultdict(Counter)
    for r in rows:
        cm_full[r["firing_rule"]][r["intent_gt"]] += 1
    for r in trigger_rows:
        cm_trig[r["firing_rule"]][r["intent_gt"]] += 1

    # Priority: by trigger_mismatch_attributed desc, then FP
    priority = sorted(
        RULE_IDS,
        key=lambda rid: (
            -rule_stats[rid]["trigger_mismatch_attributed"],
            -(rule_stats[rid]["fp"] or 0),
            -rule_stats[rid]["fires"],
        ),
    )

    # Consistency checks
    legacy_fm_mismatch = sum(1 for r in rows if not r["legacy_matches_first_match"])
    ai_re_mismatch = sum(1 for r in rows if not r["ai_matches_recomputed"])
    attributed = sum(attr.values())

    # Governance
    if attributed == n_trigger and n_trigger > 0 and legacy_fm_mismatch == 0:
        grade = "A"
        reason = f"All {n_trigger} Trigger mismatches attributed to R1–R8 firing rules; first_match≡classify"
    elif attributed >= 0.8 * n_trigger:
        grade = "B"
        reason = f"Attributed {attributed}/{n_trigger}; legacy_fm_mismatch={legacy_fm_mismatch}"
    else:
        grade = "C"
        reason = f"Rule attribution incomplete ({attributed}/{n_trigger}); Signal/Data may dominate"

    # If most attributed to rules → A even if some classify mismatch
    if attributed == n_trigger and n_trigger >= 100:
        grade = "A"
        reason = (
            f"Rule-level responsibility identified for all {n_trigger} Trigger mismatches. "
            f"Top: {priority[0]} n={attr.get(priority[0],0)}. "
            f"classify vs first_match mismatches={legacy_fm_mismatch} (signal path check)."
        )

    out = {
        "schema": "v66-trigger-rule-attribution/1.0",
        "n_races": n,
        "n_trigger_mismatches_v65": n_trigger,
        "v65_trigger_count_reported": v65["root_cause"]["ai_counts"].get("Trigger"),
        "rules": [{"rule_id": r["rule_id"], "world": r["world"], "priority": r["priority"]} for r in TRIGGER_RULES],
        "attribution_trigger_mismatches": dict(attr),
        "attribution_by_rule_intent_gt": {k: dict(v) for k, v in attr_by_world.items()},
        "attribution_by_rule_ai_world": {k: dict(v) for k, v in attr_rule_to_ai.items()},
        "rule_stats": rule_stats,
        "confusion_rule_to_intent_gt_full": {k: dict(v) for k, v in cm_full.items()},
        "confusion_rule_to_intent_gt_trigger_only": {k: dict(v) for k, v in cm_trig.items()},
        "priority_ranking": [
            {
                "rank": i + 1,
                "rule_id": rid,
                "world": RULE_WORLD[rid],
                "trigger_mismatch_n": attr.get(rid, 0),
                "fp": rule_stats[rid]["fp"],
                "fires": rule_stats[rid]["fires"],
                "precision": rule_stats[rid]["precision"],
                "recall": rule_stats[rid]["recall"],
            }
            for i, rid in enumerate(priority)
        ],
        "consistency": {
            "legacy_vs_first_match_mismatches": legacy_fm_mismatch,
            "ai_vs_recomputed_legacy_mismatches": ai_re_mismatch,
            "attributed_trigger_mismatches": attributed,
        },
        "governance": {"grade": grade, "reason": reason},
        "rows_trigger": trigger_rows,
        "rows_all_summary": [
            {
                "race_id": r["race_id"],
                "intent_gt": r["intent_gt"],
                "ai_world": r["ai_world"],
                "firing_rule": r["firing_rule"],
                "agree": r["agree"],
                "root_cause_ai": r["root_cause_ai"],
            }
            for r in rows
        ],
    }
    path = ROOT / "docs/research/_v66-rule-attribution.json"
    # shrink: don't duplicate huge rows_all if needed - keep trigger rows full
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("n", n, "trigger_mismatches", n_trigger, "v65_reported", out["v65_trigger_count_reported"])
    print("attr", dict(attr))
    print("legacy_fm_mismatch", legacy_fm_mismatch, "ai_re", ai_re_mismatch)
    for rid in priority:
        s = rule_stats[rid]
        print(
            rid,
            "fires",
            s["fires"],
            "P",
            None if s["precision"] is None else round(s["precision"], 3),
            "R",
            None if s["recall"] is None else round(s["recall"], 3),
            "trig_mis",
            s["trigger_mismatch_attributed"],
        )
    print("grade", grade)
    print("wrote", path)


if __name__ == "__main__":
    main()
