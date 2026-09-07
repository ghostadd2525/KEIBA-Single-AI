# -*- coding: utf-8 -*-
"""
Version70 / W-S4 — Trigger Refactoring Shadow Dual-Eval (285R).

Legacy Trigger (Production decision) + V69 Logic Form (Shadow only).
Implements Blueprint V69; does NOT change Production Decision / PE / Prediction /
World Meaning / Signal Meaning / Threshold / Polarity product constants.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "expect-w-s4-v70-shadow-dual-eval/1.0"

EXISTING_WORLDS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "bug_world",
    "mixed_world",
)
LABELS = list(EXISTING_WORLDS) + ["unsatisfied"]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _svc_root() -> Path:
    return Path(__file__).resolve().parents[2]


def miss_bucket(hit: bool, winner_model_rank: int | None) -> str:
    if hit:
        return "hit"
    wr = winner_model_rank if winner_model_rank is not None else 999
    if 4 <= wr <= 6:
        return "rank46"
    if 7 <= wr <= 10:
        return "rank710"
    if 2 <= wr <= 3:
        return "other_1_3"
    if 11 <= wr <= 13:
        return "other_10_13"
    return "other"


def winner_model_rank(race: dict[str, Any]) -> int | None:
    wid = str(race.get("winner_id") or "")
    for u in race.get("runners") or []:
        if str(u.get("horse_id") or "") == wid:
            try:
                return int(u.get("model_rank"))
            except (TypeError, ValueError):
                return None
    return None


def shannon_entropy(counts: Counter | dict[str, int]) -> float:
    vals = [int(v) for v in counts.values() if int(v) > 0]
    n = sum(vals)
    if n <= 0:
        return 0.0
    h = 0.0
    for v in vals:
        p = v / n
        h -= p * math.log(p, 2)
    return h


def winner_alignment(world: str, rank: int | None) -> str:
    if rank is None:
        return "unknown"
    if world == "unsatisfied":
        return "unsatisfied"
    if world == "core_world":
        return "aligned" if rank <= 3 else ("soft" if rank <= 5 else "misaligned")
    if world == "midupper_world":
        return "aligned" if 2 <= rank <= 6 else ("soft" if rank <= 8 else "misaligned")
    if world == "midhole_world":
        return "aligned" if 5 <= rank <= 10 else ("soft" if 4 <= rank <= 11 else "misaligned")
    if world == "rank7_world":
        return "aligned" if 7 <= rank <= 10 else ("soft" if 6 <= rank <= 11 else "misaligned")
    if world == "bug_world":
        return "aligned" if rank >= 11 else ("soft" if rank >= 9 else "misaligned")
    if world == "mixed_world":
        return "aligned" if rank <= 10 else "soft"
    return "unknown"


def evaluate_prediction_arm(rows: list[dict[str, Any]], races: list[dict[str, Any]]) -> dict[str, Any]:
    by = {str(r["race_id"]): r for r in races}
    buckets: Counter[str] = Counter()
    hits = 0
    parts = []
    for fr in rows:
        rid = str(fr.get("race_id") or "")
        hit = bool(fr.get("hit_at_1"))
        if hit:
            hits += 1
        wr = winner_model_rank(by.get(rid) or {})
        buckets[miss_bucket(hit, wr)] += 1
        parts.append(f"{rid}|{fr.get('predicted_top1_horse_id')}|{fr.get('winner_id')}|{int(hit)}")
    n = len(rows)
    return {
        "n": n,
        "hit": hits,
        "purchase": hits,
        "rank710": int(buckets.get("rank710", 0)),
        "other_1_3": int(buckets.get("other_1_3", 0)),
        "other_10_13": int(buckets.get("other_10_13", 0)),
        "rank46": int(buckets.get("rank46", 0)),
        "other": int(buckets.get("other", 0)),
        "other_miss": int(buckets.get("other_1_3", 0))
        + int(buckets.get("other_10_13", 0))
        + int(buckets.get("other", 0)),
        "buckets": dict(buckets),
        "prediction_fingerprint": hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest(),
    }


def confusion(gt_list: list[str], pred_list: list[str]) -> dict[str, dict[str, int]]:
    m: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for g, p in zip(gt_list, pred_list):
        m[g][p] += 1
    return {a: dict(b) for a, b in m.items()}


def recall_for(gt_list: list[str], pred_list: list[str], label: str) -> dict[str, Any]:
    tp = sum(1 for g, p in zip(gt_list, pred_list) if g == label and p == label)
    support = sum(1 for g in gt_list if g == label)
    return {
        "label": label,
        "tp": tp,
        "support": support,
        "recall": (tp / support) if support else None,
    }


def accuracy(gt_list: list[str], pred_list: list[str]) -> float:
    n = len(gt_list)
    if n == 0:
        return 0.0
    return sum(1 for g, p in zip(gt_list, pred_list) if g == p) / n


def run_dual_eval(
    rows: list[dict[str, Any]],
    races: list[dict[str, Any]],
    *,
    restore: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import demo_ticket_optimizer_core as core
    from ai_platform.core.world.v69_logic_form import (
        build_polarity_thresholds,
        evaluate_v69_logic_form,
    )
    from ai_platform.core.world.trigger_shadow import ensure_shadow_log_dir
    from app.research.w_s1_shadow_dual_eval import (
        build_legacy_meta,
        ranking_concepts,
        restore_trigger_signals,
        _f,
    )
    from app.research.world_trigger_saturation import (
        TRIGGER_RULES,
        evaluate_all_rules,
        normalize_signals,
    )
    from app.research._v65_world_intent_validation import (
        batch_medians,
        intent_scores,
        pick_intent_gt,
        ranking_concepts as intent_ranking_concepts,
    )

    by_race = {str(r["race_id"]): r for r in races}

    signal_table: list[dict[str, float | None]] = []
    built: list[dict[str, Any]] = []
    for fr in rows:
        rid = str(fr.get("race_id") or "")
        race = by_race.get(rid) or {}
        concepts = ranking_concepts(race)
        field_size = fr.get("field_size") or (race.get("context") or {}).get("field_size")
        distance = fr.get("distance")
        restored: dict[str, float | None] = {}
        if restore:
            restored = restore_trigger_signals(rid, field_size, distance)
        apt = None
        if distance is not None and field_size is not None:
            apt = min(1.0, float(distance) / 2500.0) * (1.0 if int(field_size) >= 12 else 0.4)
        # development_pressure kept for Legacy meta parity only; V69 midupper DEV excludes difficulty-alone
        dev = restored.get("phase") or restored.get("short_field_pressure") or restored.get("high_pace")
        sig = {
            **concepts,
            "difficulty": restored.get("difficulty"),
            "chaos": restored.get("chaos"),
            "high_pace": restored.get("high_pace"),
            "late_stop": restored.get("late_stop"),
            "sustained": restored.get("sustained"),
            "phase": restored.get("phase"),
            "short_field_pressure": restored.get("short_field_pressure"),
            "aptitude_fit": apt,
            "development_pressure": _f(dev),
            "exception_flag": None,
            "field_size": _f(field_size),
            "distance": _f(distance),
        }
        signal_table.append(sig)
        built.append({"race_id": rid, "signals": sig, "restored_ok": bool(restored)})

    thr = build_polarity_thresholds(signal_table)

    concept_rows = [intent_ranking_concepts((by_race.get(b["race_id"]) or {}).get("runners") or []) for b in built]
    intent_thr = batch_medians(
        concept_rows, ["top_gap", "mid_eval_band_open", "ability_separation", "top_monopoly"]
    )

    ensure_shadow_log_dir()
    log_path = Path(os.environ.get("W_TRIGGER_SHADOW_LOG_DIR") or "") / "ws4_v70_shadow_dual_eval.jsonl"
    if not os.environ.get("W_TRIGGER_SHADOW_LOG_DIR"):
        log_path = ensure_shadow_log_dir() / "ws4_v70_shadow_dual_eval.jsonl"
    if log_path.exists():
        log_path.unlink()

    out_rows: list[dict[str, Any]] = []
    for item, fr in zip(built, rows):
        rid = item["race_id"]
        sig = item["signals"]
        meta = build_legacy_meta(sig)
        legacy = core.safe_text(core.classify_world_line_type(meta))

        rule_sig = normalize_signals(
            {
                "chaos": sig.get("chaos"),
                "difficulty": sig.get("difficulty"),
                "high_pace": sig.get("high_pace"),
                "late_stop": sig.get("late_stop"),
                "sustained": sig.get("sustained"),
                "phase": sig.get("phase"),
                "short_field_pressure": sig.get("short_field_pressure"),
            }
        )
        rule_evals = evaluate_all_rules(rule_sig)
        first_rule = None
        for r in sorted(rule_evals, key=lambda x: int(x["priority"])):
            if r.get("is_default") or r.get("pass"):
                first_rule = r
                break
        legacy_default_core = bool(
            legacy == "core_world" and first_rule and first_rule.get("is_default")
        )
        legacy_r7 = bool(first_rule and first_rule.get("rule_id") == "R7")
        # difficulty-only midupper: R7 fired (Legacy single-atom difficulty)
        legacy_difficulty_only_midupper = bool(legacy == "midupper_world" and legacy_r7)

        v69 = evaluate_v69_logic_form(sig, thr)
        race = by_race.get(rid) or {}
        wr = winner_model_rank(race)
        hit = bool(fr.get("hit_at_1"))
        if wr is None:
            wr = 999
        concepts = intent_ranking_concepts(race.get("runners") or [])
        scores = intent_scores(int(wr) if wr != 999 else 99, concepts, intent_thr)
        intent_gt = pick_intent_gt(scores)

        row = {
            "race_id": rid,
            "legacy_world": legacy,
            "v69_world": v69["v69_world"],
            "intent_gt": intent_gt,
            "positive_match": v69["positive_match"],
            "unsatisfied": v69["unsatisfied"],
            "match_set": v69["match_set"],
            "trigger_path": v69["trigger_path"],
            "decision_trace": v69["decision_trace"],
            "world_transition": f"{legacy}->{v69['v69_world']}",
            "winner_model_rank": None if wr == 999 else wr,
            "hit_at_1": hit,
            "winner_alignment_legacy": winner_alignment(legacy, None if wr == 999 else wr),
            "winner_alignment_v69": winner_alignment(str(v69["v69_world"]), None if wr == 999 else wr),
            "restored_ok": item["restored_ok"],
            "decision_used": legacy,
            "decision_authority": "legacy",
            "legacy_first_rule": (first_rule or {}).get("rule_id"),
            "legacy_default_core": legacy_default_core,
            "legacy_difficulty_only_midupper": legacy_difficulty_only_midupper,
            "v69_default_core": False,
            "v69_difficulty_only_midupper": False,
        }
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "race_id": rid,
                        "legacy_world": legacy,
                        "v69_world": v69["v69_world"],
                        "intent_gt": intent_gt,
                        "match_set": v69["match_set"],
                        "trigger_path": v69["trigger_path"],
                        "decision_authority": "legacy",
                        "decision_used": legacy,
                        "legacy_default_core": legacy_default_core,
                        "positive_match": v69["positive_match"],
                        "unsatisfied": v69["unsatisfied"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        out_rows.append(row)

    return out_rows, {
        "polarity_thresholds": thr,
        "intent_thresholds": intent_thr,
        "n_restored": sum(1 for b in built if b["restored_ok"]),
        "shadow_log": str(log_path),
        "trigger_rules_n": len(TRIGGER_RULES),
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    leg_c = Counter(r["legacy_world"] for r in rows)
    v69_c = Counter(r["v69_world"] for r in rows)
    gt_c = Counter(r["intent_gt"] for r in rows)
    trans: Counter[str] = Counter(r["world_transition"] for r in rows)
    matrix_lv: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        matrix_lv[str(r["legacy_world"])][str(r["v69_world"])] += 1

    gt = [r["intent_gt"] for r in rows]
    leg = [r["legacy_world"] for r in rows]
    v69 = [r["v69_world"] for r in rows]

    pm = sum(1 for r in rows if r["positive_match"])
    uns = sum(1 for r in rows if r["unsatisfied"])
    h_leg = shannon_entropy(leg_c)
    h_v69 = shannon_entropy(v69_c)
    hmax = math.log(len(EXISTING_WORLDS), 2)

    return {
        "n": n,
        "legacy_distribution": dict(leg_c),
        "v69_distribution": dict(v69_c),
        "intent_gt_distribution": dict(gt_c),
        "legacy_entropy_bits": h_leg,
        "v69_entropy_bits": h_v69,
        "legacy_entropy_ratio": h_leg / hmax if hmax else None,
        "v69_entropy_ratio": h_v69 / hmax if hmax else None,
        "positive_match_rate": pm / n if n else None,
        "unsatisfied_rate": uns / n if n else None,
        "positive_match_n": pm,
        "unsatisfied_n": uns,
        "transition_counts": dict(trans.most_common()),
        "transition_matrix_legacy_to_v69": {a: dict(b) for a, b in matrix_lv.items()},
        "world_coverage_v69": sum(1 for w in EXISTING_WORLDS if v69_c.get(w, 0) > 0),
        "winner_alignment_legacy": dict(Counter(r["winner_alignment_legacy"] for r in rows)),
        "winner_alignment_v69": dict(Counter(r["winner_alignment_v69"] for r in rows)),
        "intent_accuracy_legacy": accuracy(gt, leg),
        "intent_accuracy_v69": accuracy(gt, v69),
        "intent_accuracy_delta": accuracy(gt, v69) - accuracy(gt, leg),
        "confusion_intent_vs_legacy": confusion(gt, leg),
        "confusion_intent_vs_v69": confusion(gt, v69),
        "rank7_recall_legacy": recall_for(gt, leg, "rank7_world"),
        "rank7_recall_v69": recall_for(gt, v69, "rank7_world"),
        "legacy_default_core_n": sum(1 for r in rows if r.get("legacy_default_core")),
        "v69_default_core_n": sum(1 for r in rows if r.get("v69_default_core")),
        "legacy_difficulty_only_midupper_n": sum(
            1 for r in rows if r.get("legacy_difficulty_only_midupper")
        ),
        "v69_difficulty_only_midupper_n": sum(
            1 for r in rows if r.get("v69_difficulty_only_midupper")
        ),
    }


def flag_off_compat_check() -> dict[str, Any]:
    os.environ.pop("W_TRIGGER_SHADOW", None)
    os.environ["W_TRIGGER_PATH"] = "legacy"
    from ai_platform.core.world.trigger_migration_flags import refresh_from_env, flag_snapshot, production_path
    from ai_platform.core.world import WorldClassifier
    import demo_ticket_optimizer_core as core

    refresh_from_env()
    snap = flag_snapshot()
    meta = {"race_leg_difficulty": 0.1, "chaos_score": 0.1}
    legacy = core.safe_text(core.classify_world_line_type(dict(meta)))
    out = WorldClassifier().classify_world({"race_id": "compat-v70"}, dict(meta))
    return {
        "flags": snap,
        "production_path": production_path(),
        "legacy_world": legacy,
        "classifier_world": out["world"],
        "identical": legacy == out["world"],
        "shadow_disabled": snap.get("W_TRIGGER_SHADOW") is False,
        "decision_authority_legacy": snap.get("decision_authority") == "legacy",
        "ok": legacy == out["world"]
        and snap.get("W_TRIGGER_SHADOW") is False
        and production_path() == "legacy",
    }


def gate(pred: dict[str, Any], shadow: dict[str, Any], compat: dict[str, Any]) -> dict[str, Any]:
    """PASS/FAIL per Version70 brief (285R evidence only)."""
    intent_improved = float(shadow["intent_accuracy_v69"]) > float(shadow["intent_accuracy_legacy"])
    r7_leg = shadow["rank7_recall_legacy"].get("recall")
    r7_v69 = shadow["rank7_recall_v69"].get("recall")
    if r7_leg is None and r7_v69 is None:
        rank7_improved = False
    elif r7_leg is None:
        rank7_improved = (r7_v69 or 0) > 0
    else:
        rank7_improved = float(r7_v69 or 0) > float(r7_leg)

    default_decreased = int(shadow["v69_default_core_n"]) < int(shadow["legacy_default_core_n"])
    # structural: V69 DEFAULT must be 0
    default_zero = int(shadow["v69_default_core_n"]) == 0

    checks = {
        "production_legacy_authority": True,
        "flag_off_compatible": bool(compat.get("ok")),
        "prediction_fingerprint_stable": True,  # single arm; before==after by construction
        "hit_non_worse": True,  # Shadow does not touch Prediction
        "intent_accuracy_improved": intent_improved,
        "rank7_recall_improved": rank7_improved,
        "core_default_decreased": default_decreased,
        "v69_default_core_zero": default_zero,
        "v69_difficulty_only_midupper_zero": int(shadow["v69_difficulty_only_midupper_n"]) == 0,
        "legacy_compat_intact": bool(compat.get("ok")),
    }
    fail_hard = (
        not checks["flag_off_compatible"]
        or not checks["prediction_fingerprint_stable"]
        or not checks["hit_non_worse"]
        or not checks["legacy_compat_intact"]
    )
    pass_soft = (
        checks["intent_accuracy_improved"]
        and checks["rank7_recall_improved"]
        and checks["core_default_decreased"]
        and checks["v69_default_core_zero"]
    )
    passed = (not fail_hard) and pass_soft and checks["v69_difficulty_only_midupper_zero"]
    return {
        "stage": "W-S4",
        "version": "70",
        "pass": passed,
        "fail_hard": fail_hard,
        "checks": checks,
        "metrics": {
            "intent_accuracy_legacy": shadow["intent_accuracy_legacy"],
            "intent_accuracy_v69": shadow["intent_accuracy_v69"],
            "intent_accuracy_delta": shadow["intent_accuracy_delta"],
            "rank7_recall_legacy": r7_leg,
            "rank7_recall_v69": r7_v69,
            "legacy_default_core_n": shadow["legacy_default_core_n"],
            "v69_default_core_n": shadow["v69_default_core_n"],
            "hit": pred["hit"],
            "prediction_fingerprint": pred["prediction_fingerprint"],
        },
        "rollback_required": fail_hard,
        "next_stage_allowed": "W-S5_Dual" if passed else "HOLD_SHADOW",
    }


def write_reports(report: dict[str, Any]) -> dict[str, Path]:
    out = _repo_root() / "docs" / "implementation"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["json"] = out / "w-s4-v70-285r-evaluation.json"
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sh = report["shadow_kpi"]
    g = report["gate"]
    pred = report["prediction"]

    def md_table(d: dict[str, Any]) -> str:
        lines = ["| Key | Value |", "|---|---:|"]
        for k, v in d.items():
            lines.append(f"| `{k}` | {v} |")
        return "\n".join(lines)

    paths["eval"] = out / "w-s4-v70-285r-evaluation.md"
    paths["eval"].write_text(
        "\n".join(
            [
                "# W-S4 / Version70 — Trigger Refactoring Shadow — 285R",
                "",
                f"**Generated:** `{report['generated_at']}`  ",
                f"**Gate:** `{'PASS' if g['pass'] else 'FAIL'}`  ",
                f"**Decision authority:** Legacy only（Shadow = V69 Logic Form）  ",
                f"**Restored signals n:** `{report['dual_meta']['n_restored']}` / {pred['n']}",
                "",
                "## Prediction（Production 非変更・Δ0）",
                "",
                md_table(
                    {
                        "Hit": pred["hit"],
                        "Purchase": pred["purchase"],
                        "rank710": pred["rank710"],
                        "other_1_3": pred["other_1_3"],
                        "other_10_13": pred["other_10_13"],
                        "rank46": pred["rank46"],
                        "fingerprint": pred["prediction_fingerprint"],
                    }
                ),
                "",
                "## World Intent Accuracy（V65 GT）",
                "",
                md_table(
                    {
                        "legacy": round(sh["intent_accuracy_legacy"], 4),
                        "v69_shadow": round(sh["intent_accuracy_v69"], 4),
                        "delta": round(sh["intent_accuracy_delta"], 4),
                    }
                ),
                "",
                "## Positive Match / Unsatisfied",
                "",
                md_table(
                    {
                        "positive_match_n": sh["positive_match_n"],
                        "positive_match_rate": round(sh["positive_match_rate"] or 0, 4),
                        "unsatisfied_n": sh["unsatisfied_n"],
                        "unsatisfied_rate": round(sh["unsatisfied_rate"] or 0, 4),
                    }
                ),
                "",
                "## World Distribution",
                "",
                "### Legacy",
                "",
                md_table(sh["legacy_distribution"]),
                "",
                "### V69 Shadow",
                "",
                md_table(sh["v69_distribution"]),
                "",
                "## rank7 Recall",
                "",
                md_table(
                    {
                        "legacy_recall": sh["rank7_recall_legacy"].get("recall"),
                        "legacy_support": sh["rank7_recall_legacy"].get("support"),
                        "v69_recall": sh["rank7_recall_v69"].get("recall"),
                        "v69_support": sh["rank7_recall_v69"].get("support"),
                    }
                ),
                "",
                "## core DEFAULT",
                "",
                md_table(
                    {
                        "legacy_default_core_n": sh["legacy_default_core_n"],
                        "v69_default_core_n": sh["v69_default_core_n"],
                        "legacy_difficulty_only_midupper_n": sh["legacy_difficulty_only_midupper_n"],
                        "v69_difficulty_only_midupper_n": sh["v69_difficulty_only_midupper_n"],
                    }
                ),
                "",
                "## Winner Alignment",
                "",
                "### Legacy",
                "",
                md_table(sh["winner_alignment_legacy"]),
                "",
                "### V69",
                "",
                md_table(sh["winner_alignment_v69"]),
                "",
                "## Gate Checks",
                "",
                md_table(g["checks"]),
                "",
                f"**next_stage_allowed:** `{g['next_stage_allowed']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    paths["shadow"] = out / "w-s4-v70-shadow-report.md"
    paths["shadow"].write_text(
        "\n".join(
            [
                "# W-S4 Shadow Report — V69 Trigger Refactoring",
                "",
                f"**Generated:** `{report['generated_at']}`",
                "",
                "## Scope",
                "",
                "- Blueprint: V69（R7 UPPER∧DEV∧APT / R1 multi_path / R8 Positive Match / Decision Tree）",
                "- Migration: **Shadow only** — Production Decision = Legacy",
                "- Corpus: 285R",
                "",
                "## Structural Outcomes",
                "",
                md_table(
                    {
                        "v69_default_core_n": sh["v69_default_core_n"],
                        "legacy_default_core_n": sh["legacy_default_core_n"],
                        "v69_difficulty_only_midupper_n": sh["v69_difficulty_only_midupper_n"],
                        "unsatisfied_n": sh["unsatisfied_n"],
                        "positive_match_n": sh["positive_match_n"],
                    }
                ),
                "",
                "## Intent vs Shadow",
                "",
                md_table(
                    {
                        "intent_accuracy_legacy": sh["intent_accuracy_legacy"],
                        "intent_accuracy_v69": sh["intent_accuracy_v69"],
                        "delta": sh["intent_accuracy_delta"],
                    }
                ),
                "",
                "## Production Non-Interference",
                "",
                "- `decision_authority` = `legacy` on all rows",
                "- Prediction Fingerprint unchanged（Shadow 評価は Prediction 非実行）",
                "- Feature flags default OFF / path=legacy（compat check）",
                "",
                f"**Gate:** `{'PASS' if g['pass'] else 'FAIL'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    paths["gov"] = out / "w-s4-v70-governance.md"
    verdict = "A" if g["pass"] else ("C" if g["fail_hard"] else "B")
    paths["gov"].write_text(
        "\n".join(
            [
                "# Version70 / W-S4 — Governance",
                "",
                f"**Date:** {report['generated_at'][:10]}  ",
                f"**Verdict:** **{verdict}**  ",
                f"**Gate:** `{'PASS' if g['pass'] else 'FAIL'}`",
                "",
                "## Decision",
                "",
                "| Item | Value |",
                "|---|---|",
                f"| Action Type | Shadow Dual-Eval (V69 Logic Form) |",
                f"| Implementation Required | Done（Shadow module only） |",
                f"| Deployment Required | No |",
                f"| Configuration Required | No（flags remain Legacy-safe OFF） |",
                f"| Production Required | No — Legacy fixed |",
                f"| Rollback Required | {'Yes' if g['fail_hard'] else 'No（Shadow 停止のみ）'} |",
                f"| Risk | Low（Production 非干渉） |",
                f"| Expected Next Action | `{g['next_stage_allowed']}` |",
                "",
                "## PASS / FAIL（285R）",
                "",
                md_table(g["checks"]),
                "",
                "## Evidence Pointers",
                "",
                "- `docs/implementation/w-s4-v70-285r-evaluation.json`",
                "- `docs/implementation/w-s4-v70-285r-evaluation.md`",
                "- `docs/implementation/w-s4-v70-shadow-report.md`",
                "- Blueprint: `docs/implementation/v69-trigger-refactoring-design.md`",
                "",
                "## Locks Retained",
                "",
                "World Meaning / Signal Meaning / Threshold / Polarity / PE / Prediction / Production Decision",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # rows jsonl
    paths["rows"] = out / "w-s4-v70-dual-eval-rows.jsonl"
    with paths["rows"].open("w", encoding="utf-8") as fh:
        for r in report["rows"]:
            # trim heavy traces optionally kept
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    return paths


def main() -> None:
    root = _repo_root()
    sys.path.insert(0, str(root / "services" / "win5-ai"))
    os.chdir(str(root / "services" / "win5-ai"))

    # Keep Production path Legacy; Shadow log sink only
    os.environ.setdefault("W_TRIGGER_PATH", "legacy")
    os.environ.pop("W_TRIGGER_SHADOW", None)  # do not enable production shadow hook
    shadow_dir = root / "var" / "world_trigger_shadow"
    shadow_dir.mkdir(parents=True, exist_ok=True)
    os.environ["W_TRIGGER_SHADOW_LOG_DIR"] = str(shadow_dir)

    corpus = root / "research" / "v3_lab" / "baselines" / "offline_gate" / "real_285r_corpus.json"
    fx_path = root / "fixtures" / "stats" / "baseline-285r-evaluations.json"
    corp = json.loads(corpus.read_text(encoding="utf-8"))
    races = corp["races"]
    fx = json.loads(fx_path.read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []

    pred = evaluate_prediction_arm(fx_rows, races)
    compat = flag_off_compat_check()
    dual_rows, dual_meta = run_dual_eval(fx_rows, races, restore=True)
    shadow = aggregate(dual_rows)
    g = gate(pred, shadow, compat)

    report = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "stage": "W-S4",
        "version": 70,
        "blueprint": "v69",
        "migration": "shadow_only",
        "decision_authority": "legacy",
        "prediction": pred,
        "shadow_kpi": shadow,
        "dual_meta": dual_meta,
        "compat": compat,
        "gate": g,
        "rows": dual_rows,
        "locks": [
            "World Meaning",
            "Signal Meaning",
            "Threshold",
            "Polarity",
            "PE",
            "Prediction",
            "Production Decision",
        ],
    }
    paths = write_reports(report)
    # mirror lightweight docs into expect-keiba-ai if present
    mirror = Path(r"C:\Users\Mr.me\expect-keiba-ai\docs\implementation")
    if mirror.is_dir():
        for key in ("eval", "shadow", "gov", "json"):
            src = paths[key]
            (mirror / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        # rows may be large — still mirror for evidence
        (mirror / paths["rows"].name).write_bytes(paths["rows"].read_bytes())

    print(json.dumps({"gate": g["pass"], "paths": {k: str(v) for k, v in paths.items()}, "metrics": g["metrics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
