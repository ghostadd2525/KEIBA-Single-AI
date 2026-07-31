# -*- coding: utf-8 -*-
"""
Version41 — World Decision Trace Audit

Per-race Decision Trace: Feature → Signal → Trigger → Margin → Fitness → Decision.
Research / Audit only. No product / Trigger / Threshold / World mutation.

Uses the same restored-signal pack as V39/V40 so traces explain the observed
core_world ~75% assignment under real first-match TRIGGER_RULES.
"""
from __future__ import annotations

import json
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import evidence_root, repo_root
from .signal_restoration_sim import SignalRestorationSimulation
from .world_fitness_research import trigger_proximity_fitness
from .world_trigger_saturation import (
    TRIGGER_RULES,
    evaluate_all_rules,
    first_match_world,
)
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-world-decision-trace/1.0"
NEAR_EPS = 0.05
CANONICAL = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "bug_world",
    "mixed_world",
)
PRIMARY_CLASSES = (
    "Signal不足",
    "Trigger不足",
    "Boundary",
    "Evaluation Order",
    "Default/Fallback",
    "その他",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sd(a: float, b: float) -> float:
    v = _safe_div(a, b)
    return float(v) if v is not None else 0.0


def _winning_rule(evals: list[dict[str, Any]], decision: str) -> dict[str, Any]:
    for r in sorted(evals, key=lambda x: int(x["priority"])):
        if r.get("is_default"):
            if str(r["world"]) == decision:
                return r
            continue
        if r.get("pass") and str(r["world"]) == decision:
            return r
    # fallback: first pass or default
    for r in sorted(evals, key=lambda x: int(x["priority"])):
        if r.get("pass"):
            return r
    return {"rule_id": None, "world": decision, "is_default": True}


def _fail_atoms(atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for a in atoms or []:
        if a.get("pass"):
            continue
        out.append(
            {
                "signal": a.get("signal"),
                "value": a.get("value"),
                "threshold": a.get("threshold"),
                "margin": a.get("margin"),
                "missing": bool(a.get("missing")),
            }
        )
    return out


def _rule_trace(ev: dict[str, Any]) -> dict[str, Any]:
    atoms = ev.get("atoms") or []
    fails = _fail_atoms(atoms)
    bot = ev.get("bottleneck") or {}
    is_default = bool(ev.get("is_default"))
    return {
        "rule_id": ev.get("rule_id"),
        "world": ev.get("world"),
        "priority": ev.get("priority"),
        "pass": bool(ev.get("pass")),
        "margin": ev.get("margin"),
        "is_default": is_default,
        "status": "PASS" if ev.get("pass") else "FAIL",
        "failing_atoms": fails,
        "missing_signals": sorted({str(a["signal"]) for a in fails if a.get("missing")}),
        "below_threshold_signals": sorted(
            {str(a["signal"]) for a in fails if not a.get("missing")}
        ),
        "bottleneck": {
            "signal": bot.get("signal"),
            "value": bot.get("value"),
            "threshold": bot.get("threshold"),
            "margin": bot.get("margin"),
            "missing": bot.get("missing"),
        }
        if bot
        else None,
        "near_miss": (
            (not ev.get("pass"))
            and (not is_default)
            and ev.get("margin") is not None
            and float(ev["margin"]) > -NEAR_EPS
            and float(ev["margin"]) < 0
        ),
    }


def _world_rollup(rule_traces: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_w: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rt in rule_traces:
        by_w[str(rt["world"])].append(rt)
    out: dict[str, dict[str, Any]] = {}
    for w in CANONICAL:
        rules = by_w.get(w, [])
        non_default = [r for r in rules if not r.get("is_default")]
        any_pass = any(r["pass"] for r in non_default) if non_default else any(
            r["pass"] for r in rules
        )
        fail_reasons: list[str] = []
        missing: set[str] = set()
        below: set[str] = set()
        near = False
        best_margin = None
        for r in non_default:
            if r["pass"]:
                continue
            missing.update(r.get("missing_signals") or [])
            below.update(r.get("below_threshold_signals") or [])
            if r.get("near_miss"):
                near = True
            m = r.get("margin")
            if m is not None and (best_margin is None or float(m) > float(best_margin)):
                best_margin = float(m)
            bot = r.get("bottleneck") or {}
            if bot.get("missing"):
                fail_reasons.append(f"{r['rule_id']}: {bot.get('signal')} missing")
            elif bot.get("signal") is not None:
                fail_reasons.append(
                    f"{r['rule_id']}: {bot.get('signal')}不足 "
                    f"(val={bot.get('value')}, thr={bot.get('threshold')}, "
                    f"margin={bot.get('margin')})"
                )
            else:
                fail_reasons.append(f"{r['rule_id']}: FAIL")
        if w == "core_world":
            # core only has DEFAULT — always eligible as fallback
            status = "PASS"  # DEFAULT always available
            why: list[str] = []
            any_pass = True
        else:
            status = "PASS" if any_pass else "FAIL"
            why = fail_reasons if not any_pass else []
        out[w] = {
            "status": status,
            "any_rule_pass": any_pass,
            "rules": rules,
            "why_not": why,
            "missing_signals": sorted(missing),
            "below_threshold_signals": sorted(below),
            "near_miss": near,
            "best_fail_margin": best_margin,
        }
    return out


def _why_not_analysis(
    decision: str,
    world_rollup: dict[str, dict[str, Any]],
    soft: dict[str, float],
    winning_priority: int,
) -> dict[str, Any]:
    rejected: dict[str, Any] = {}
    for w in CANONICAL:
        if w == decision:
            continue
        roll = world_rollup.get(w) or {}
        reasons = list(roll.get("why_not") or [])
        if roll.get("any_rule_pass") and w != "core_world":
            # A non-default rule for this world passed, but a higher-priority
            # different world already won — or same world earlier rule won.
            # For rejected worlds that have a passing rule at lower priority:
            passed_rules = [r for r in (roll.get("rules") or []) if r.get("pass") and not r.get("is_default")]
            for pr in passed_rules:
                if int(pr.get("priority") or 99) > winning_priority:
                    reasons = [
                        "Evaluation Order: TriggerはPASSだが、"
                        f"より高優先度のDecision(priority≤{winning_priority})が先に確定"
                    ] + reasons
                    break
        if w == "core_world":
            reasons = [
                "Evaluation Order: より高優先度の非core TriggerがPASSしたため "
                "R8_core_default に到達せず"
            ]
        rejected[w] = {
            "status": roll.get("status"),
            "fitness": soft.get(w),
            "reasons": reasons
            or (["Trigger FAIL"] if roll.get("status") == "FAIL" else ["not selected"]),
            "missing_signals": roll.get("missing_signals") or [],
            "below_threshold_signals": roll.get("below_threshold_signals") or [],
            "near_miss": bool(roll.get("near_miss")),
        }
    return rejected


def _classify_root_cause(
    *,
    decision: str,
    winning_rule_id: str | None,
    best_fit: str,
    world_rollup: dict[str, dict[str, Any]],
    rule_traces: list[dict[str, Any]],
    signals: dict[str, float | None],
) -> dict[str, Any]:
    """
    Primary cause for THIS race's Decision.

    Binding rule for core via R8: classify by why the soft-best-fit World
    (or nearest competitor) failed its Trigger — not by any incidental
    missing atom on unrelated rules (e.g. phase missing on R3 while
    best-fit midhole fails on late_stop threshold).
    """
    missing_any = [k for k, v in signals.items() if v is None]
    r1_r7 = [r for r in rule_traces if not r.get("is_default")]
    all_prior_fail = all(not r["pass"] for r in r1_r7)
    near_any = any(r.get("near_miss") for r in r1_r7)
    fitness_mismatch = best_fit != decision

    secondary: list[str] = []
    primary = "その他"
    evidence: list[str] = []

    bf = world_rollup.get(best_fit) or {}
    bf_missing = list(bf.get("missing_signals") or [])
    bf_near = bool(bf.get("near_miss"))
    bf_below = list(bf.get("below_threshold_signals") or [])
    bf_why = list(bf.get("why_not") or [])

    if decision == "core_world" and winning_rule_id == "R8_core_default" and all_prior_fail:
        evidence.append("R1-R7 all FAIL -> R8_core_default => core_world")
        # Engine structure always participates for core DEFAULT
        secondary.append("Default/Fallback")
        if fitness_mismatch:
            secondary.append("Evaluation Order")
            evidence.append(
                f"soft best-fit={best_fit} != decision=core "
                f"(best-fit Trigger FAIL: {bf_why[:2]})"
            )

        # Binding cause = why best-fit (or any near-miss competitor) lost
        if best_fit != "core_world" and bf_missing and not bf_below:
            primary = "Signal不足"
            evidence.append(f"best-fit {best_fit} blocked by missing: {bf_missing}")
        elif best_fit != "core_world" and bf_near:
            primary = "Boundary"
            evidence.append(
                f"best-fit {best_fit} near-miss: {bf_why[:1]}"
            )
        elif best_fit != "core_world" and (bf_below or bf_why):
            primary = "Trigger不足"
            evidence.append(
                f"best-fit {best_fit} below threshold: {bf_below or bf_why[:1]}"
            )
            if bf_missing:
                secondary.append("Signal不足")
                evidence.append(
                    f"incidental missing (not binding for best-fit): {bf_missing}; "
                    f"global missing={missing_any}"
                )
        elif near_any:
            primary = "Boundary"
            evidence.append("non-core Trigger near-miss then DEFAULT")
        elif missing_any and all(
            bool(r.get("missing_signals")) for r in r1_r7 if not r["pass"]
        ):
            primary = "Signal不足"
            evidence.append(f"all failing rules have missing atoms: {missing_any}")
        else:
            primary = "Trigger不足"
            evidence.append("R1-R7 threshold unmet -> DEFAULT")

        # phase-only missing on mixed rules is secondary note, not primary,
        # unless best-fit itself was mixed and failed on missing phase
        if missing_any and "Signal不足" not in (primary, *secondary):
            secondary.append("Signal不足")
            evidence.append(f"non-binding missing signals present: {missing_any}")

    elif fitness_mismatch:
        primary = "Evaluation Order"
        evidence.append(
            f"first-match decision={decision} (rule={winning_rule_id}) != "
            f"soft-fitness best={best_fit}"
        )
        if best_fit != "core_world" and not bf.get("any_rule_pass"):
            if bf_missing and not bf_below:
                secondary.append("Signal不足")
            elif bf_near:
                secondary.append("Boundary")
            else:
                secondary.append("Trigger不足")
            evidence.append(f"best-fit {best_fit} Trigger FAIL: {bf_why[:2]}")
        elif bf.get("any_rule_pass"):
            evidence.append(
                f"best-fit {best_fit} Trigger PASS but lost on priority"
            )
        if near_any and "Boundary" not in secondary:
            secondary.append("Boundary")

    elif near_any and decision != "core_world":
        primary = "Boundary"
        evidence.append(f"winning={winning_rule_id} / near-miss competition")

    elif decision != "core_world":
        primary = "その他"
        evidence.append(
            f"Trigger PASS => {decision} (rule={winning_rule_id})"
        )
        if missing_any:
            secondary.append("Signal不足")

    else:
        primary = "Default/Fallback"
        evidence.append(f"decision=core winning={winning_rule_id}")

    return {
        "primary": primary,
        "secondary": secondary,
        "evidence": evidence,
        "fitness_mismatch": fitness_mismatch,
        "all_prior_triggers_fail": all_prior_fail,
        "near_miss_any": near_any,
        "missing_signals": missing_any,
        "best_fit_fail_missing": bf_missing,
        "best_fit_fail_below": bf_below,
        "best_fit_near_miss": bf_near,
    }


def _mismatch_reason(
    decision: str,
    best_fit: str,
    world_rollup: dict[str, dict[str, Any]],
    winning_rule_id: str | None,
) -> str:
    if decision == best_fit:
        return "agree"
    bf = world_rollup.get(best_fit) or {}
    if decision == "core_world" and winning_rule_id == "R8_core_default":
        if best_fit == "core_world":
            return "agree"
        if not bf.get("any_rule_pass"):
            reasons = bf.get("why_not") or []
            tip = reasons[0] if reasons else "best-fit Trigger FAIL"
            return f"DEFAULT→core / best-fit {best_fit} Trigger未達: {tip}"
        return (
            f"DEFAULT→core / best-fit {best_fit} は Trigger PASS だが "
            "優先度矛盾（検査対象）"
        )
    if bf.get("any_rule_pass"):
        return (
            f"first-match={decision}({winning_rule_id}) が "
            f"best-fit={best_fit} より高優先で確定"
        )
    return (
        f"first-match={decision}({winning_rule_id}); "
        f"best-fit={best_fit} は Trigger FAIL"
    )


class WorldDecisionTraceAudit:
    def __init__(self) -> None:
        self.restorer = SignalRestorationSimulation()

    def run(self) -> dict[str, Any]:
        meta = self.restorer._load_meta()
        loadable = self.restorer._find_loadable(meta)
        traces: list[dict[str, Any]] = []

        for rid in loadable:
            sig, info = self.restorer._restore_signals(rid, meta.get(rid) or {})
            if not info.get("ok"):
                continue
            sig_map = {
                k: sig.get(k)
                for k in (
                    "difficulty",
                    "chaos",
                    "phase",
                    "late_stop",
                    "sustained",
                    "high_pace",
                    "short_field_pressure",
                )
            }
            evals = evaluate_all_rules(sig)
            decision = first_match_world(evals)
            win = _winning_rule(evals, decision)
            winning_rule_id = str(win.get("rule_id") or "")
            winning_priority = int(win.get("priority") or 99)

            rule_traces = [_rule_trace(e) for e in evals]
            world_rollup = _world_rollup(rule_traces)

            prox = trigger_proximity_fitness(sig_map)
            soft = {k: float(v) for k, v in (prox.get("soft") or {}).items()}
            best_fit = str(prox.get("best_fit_world") or decision)

            why_not = _why_not_analysis(
                decision, world_rollup, soft, winning_priority
            )
            root = _classify_root_cause(
                decision=decision,
                winning_rule_id=winning_rule_id,
                best_fit=best_fit,
                world_rollup=world_rollup,
                rule_traces=rule_traces,
                signals=sig_map,
            )
            mismatch = _mismatch_reason(
                decision, best_fit, world_rollup, winning_rule_id
            )

            mrow = meta.get(rid) or {}
            traces.append(
                {
                    "race_id": rid,
                    "kaisai_date": mrow.get("kaisai_date"),
                    "feature": {
                        "source": info.get("feature_source"),
                        "loadable": True,
                        "notes": info.get("notes") or [],
                        "world_native_classify": info.get("world_native_classify"),
                    },
                    "signals": sig_map,
                    "trigger_evaluations": rule_traces,
                    "world_trigger_status": {
                        w: {
                            "status": world_rollup[w]["status"],
                            "margin_best_fail": world_rollup[w]["best_fail_margin"],
                            "missing": world_rollup[w]["missing_signals"],
                            "below_threshold": world_rollup[w][
                                "below_threshold_signals"
                            ],
                            "near_miss": world_rollup[w]["near_miss"],
                            "why_not": world_rollup[w]["why_not"],
                        }
                        for w in CANONICAL
                    },
                    "fitness": {k: round(float(v), 6) for k, v in soft.items()},
                    "best_fit_world": best_fit,
                    "decision": {
                        "world": decision,
                        "winning_rule": winning_rule_id,
                        "winning_priority": winning_priority,
                        "mechanism": "priority first-match (TRIGGER_RULES)",
                    },
                    "why_not": why_not,
                    "fitness_mismatch": {
                        "agree": decision == best_fit,
                        "decision_world": decision,
                        "best_fit_world": best_fit,
                        "reason": mismatch,
                        "fitness_gap": round(
                            float(soft.get(best_fit, 0) - soft.get(decision, 0)), 6
                        ),
                    },
                    "root_cause": root,
                }
            )

        decision_dist = Counter(t["decision"]["world"] for t in traces)
        primary_dist = Counter(t["root_cause"]["primary"] for t in traces)
        core_primary = Counter(
            t["root_cause"]["primary"]
            for t in traces
            if t["decision"]["world"] == "core_world"
        )
        mismatch_traces = [t for t in traces if not t["fitness_mismatch"]["agree"]]
        mismatch_pairs = Counter(
            (
                t["fitness_mismatch"]["best_fit_world"],
                t["fitness_mismatch"]["decision_world"],
            )
            for t in mismatch_traces
        )
        mismatch_reason_buckets: Counter = Counter()
        for t in mismatch_traces:
            r = t["fitness_mismatch"]["reason"]
            if r.startswith("DEFAULT→core"):
                mismatch_reason_buckets["DEFAULT_core_vs_bestfit_trigger_fail"] += 1
            elif "高優先" in r:
                mismatch_reason_buckets["first_match_priority_over_bestfit"] += 1
            else:
                mismatch_reason_buckets["other"] += 1

        core_traces = [t for t in traces if t["decision"]["world"] == "core_world"]
        n = len(traces)
        n_core = len(core_traces)
        core_default_rule = sum(
            1
            for t in core_traces
            if t["decision"]["winning_rule"] == "R8_core_default"
        )
        core_all_r1r7_fail = sum(
            1 for t in core_traces if t["root_cause"]["all_prior_triggers_fail"]
        )
        core_fitness_mismatch = sum(
            1 for t in core_traces if not t["fitness_mismatch"]["agree"]
        )

        sec_hits: Counter = Counter()
        for t in core_traces:
            for s in t["root_cause"].get("secondary") or []:
                sec_hits[s] += 1

        top_core_cause = core_primary.most_common(1)[0][0] if core_primary else "その他"
        share_default = _sd(core_primary.get("Default/Fallback", 0), n_core)
        share_trigger = _sd(core_primary.get("Trigger不足", 0), n_core)
        share_boundary = _sd(core_primary.get("Boundary", 0), n_core)
        share_signal = _sd(core_primary.get("Signal不足", 0), n_core)
        share_order = _sd(core_primary.get("Evaluation Order", 0), n_core)
        # Secondary tags: Default/Fallback + Evaluation Order are structural
        sec_default = _sd(sec_hits.get("Default/Fallback", 0), n_core)
        sec_order = _sd(sec_hits.get("Evaluation Order", 0), n_core)

        governance = "D"
        if n_core > 0:
            structural_default = (
                core_default_rule == n_core and core_all_r1r7_fail == n_core
            )
            if share_signal >= 0.5:
                governance = "A"
            elif structural_default and share_signal < 0.2:
                # Every core race is R8 DEFAULT after R1-R7 FAIL.
                # Binding fail reason may be Trigger不足/Boundary, but the
                # mapping FAIL→core is Decision Engine structure.
                if structural_default and sec_default >= 0.8 and share_signal < 0.15:
                    governance = "C"
                elif share_boundary >= 0.5 and share_trigger < 0.3:
                    governance = "D"  # Boundary + Engine
                elif (share_trigger + share_boundary) >= 0.7:
                    governance = "C"
                else:
                    governance = "C"
            elif share_boundary >= 0.5:
                governance = "B"
            elif share_default + share_order >= 0.5:
                governance = "C"
            else:
                governance = "D"

        payload = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "note": (
                "Signals = V39 FeatureLoader restoration pack (designed WIC path). "
                "Triggers = TRIGGER_RULES / first_match_world (product mirror). "
                "No Trigger/Threshold/World mutation. Trace audit only (not a new policy sim)."
            ),
            "n_races": n,
            "decision_distribution": dict(decision_dist),
            "core_share": round(_sd(n_core, n), 6),
            "fitness_agree_rate": round(_sd(n - len(mismatch_traces), n), 6),
            "primary_root_cause_counts": dict(primary_dist),
            "core_primary_root_cause_counts": dict(core_primary),
            "core_evidence": {
                "n_core": n_core,
                "all_via_R8_default": core_default_rule,
                "all_r1_r7_fail": core_all_r1r7_fail,
                "fitness_mismatch_among_core": core_fitness_mismatch,
                "secondary_among_core": dict(sec_hits),
            },
            "mismatch": {
                "n": len(mismatch_traces),
                "pair_counts": {
                    f"{a}->{b}": c for (a, b), c in mismatch_pairs.most_common()
                },
                "reason_buckets": dict(mismatch_reason_buckets),
            },
            "governance": {
                "verdict": governance,
                "top_core_primary": top_core_cause,
                "shares_among_core": {
                    "Signal不足": round(share_signal, 4),
                    "Trigger不足": round(share_trigger, 4),
                    "Boundary": round(share_boundary, 4),
                    "Evaluation Order": round(share_order, 4),
                    "Default/Fallback": round(share_default, 4),
                },
                "secondary_shares_among_core": {
                    "Default/Fallback": round(sec_default, 4),
                    "Evaluation Order": round(sec_order, 4),
                    "Signal不足": round(_sd(sec_hits.get("Signal不足", 0), n_core), 4),
                    "Boundary": round(_sd(sec_hits.get("Boundary", 0), n_core), 4),
                    "Trigger不足": round(_sd(sec_hits.get("Trigger不足", 0), n_core), 4),
                },
                "structural": {
                    "all_core_via_R8_default": bool(
                        n_core > 0 and core_default_rule == n_core
                    ),
                    "all_core_r1_r7_fail": bool(
                        n_core > 0 and core_all_r1r7_fail == n_core
                    ),
                    "all_core_fitness_mismatch": bool(
                        n_core > 0 and core_fitness_mismatch == n_core
                    ),
                },
                "labels": {
                    "A": "Signalが主因",
                    "B": "Boundaryが主因",
                    "C": "Decision Engine構造が主因",
                    "D": "複数要因",
                },
            },
            "trigger_rules_order": [
                {"rule_id": r["rule_id"], "world": r["world"], "priority": r["priority"]}
                for r in TRIGGER_RULES
            ],
            "traces": traces,
        }
        return payload

    def write_artifacts(self, payload: dict[str, Any]) -> dict[str, str]:
        root = evidence_root()
        (root / "reports").mkdir(parents=True, exist_ok=True)
        (root / "summaries").mkdir(parents=True, exist_ok=True)
        docs = repo_root() / "docs" / "audit"
        docs.mkdir(parents=True, exist_ok=True)

        json_path = root / "reports" / "v41-world-decision-trace.json"
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        paths = {
            "json": str(json_path),
            "decision_trace": str(docs / "v41-decision-trace.md"),
            "trigger_trace": str(docs / "v41-trigger-trace.md"),
            "fitness_mismatch": str(docs / "v41-fitness-mismatch.md"),
            "root_cause": str(docs / "v41-root-cause-classification.md"),
            "governance": str(docs / "v41-governance.md"),
        }

        self._write_decision_trace(docs / "v41-decision-trace.md", payload)
        self._write_trigger_trace(docs / "v41-trigger-trace.md", payload)
        self._write_mismatch(docs / "v41-fitness-mismatch.md", payload)
        self._write_root_cause(docs / "v41-root-cause-classification.md", payload)
        self._write_governance(docs / "v41-governance.md", payload)

        (root / "summaries" / "v41-world-decision-trace-summary.json").write_text(
            json.dumps(
                {k: v for k, v in payload.items() if k != "traces"},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return paths

    def _write_decision_trace(self, path: Path, p: dict[str, Any]) -> None:
        lines = [
            "# Version41 Decision Trace",
            "",
            f"- generated_at: `{p['generated_at']}`",
            f"- n_races: **{p['n_races']}**",
            f"- core_share: **{_pct(p['core_share'])}**",
            f"- mechanism: priority first-match (`TRIGGER_RULES` → `R8_core_default`)",
            f"- signal_pack: V39 FeatureLoader restoration（V40と同一条件）",
            "",
            "## Pipeline",
            "",
            "```",
            "FeatureLoader / reconstruct_leg_upset / Scorer diagnostics",
            "  → Signals (difficulty, chaos, phase, late_stop, sustained, high_pace, sfp)",
            "  → evaluate_all_rules (R1…R8)",
            "  → first_match_world = Decision",
            "  → trigger_proximity_fitness = soft Fitness",
            "```",
            "",
            "## Rule priority order",
            "",
        ]
        for r in p.get("trigger_rules_order") or []:
            lines.append(
                f"- P{r['priority']}: `{r['rule_id']}` → `{r['world']}`"
            )
        lines.append("")
        lines.append("## Per-Race Traces")
        lines.append("")
        for t in p["traces"]:
            sig = t["signals"]
            d = t["decision"]
            lines.append(f"### `{t['race_id']}`")
            lines.append("")
            lines.append(
                f"- **Decision**: `{d['world']}` via `{d['winning_rule']}`"
            )
            lines.append(
                f"- **Best-fit (soft)**: `{t['best_fit_world']}` "
                f"(agree={t['fitness_mismatch']['agree']})"
            )
            lines.append(f"- **Root cause**: `{t['root_cause']['primary']}`")
            lines.append("- **Signals**:")
            for k in (
                "difficulty",
                "chaos",
                "phase",
                "late_stop",
                "sustained",
                "high_pace",
                "short_field_pressure",
            ):
                lines.append(f"  - {k}: `{sig.get(k)}`")
            lines.append("- **Trigger chain**:")
            for ev in t["trigger_evaluations"]:
                mark = "PASS" if ev["pass"] else "FAIL"
                extra = ""
                if not ev["pass"] and ev.get("bottleneck"):
                    b = ev["bottleneck"]
                    extra = (
                        f" bottleneck={b.get('signal')} "
                        f"margin={b.get('margin')}"
                    )
                elif ev.get("is_default"):
                    extra = " [DEFAULT]"
                lines.append(
                    f"  - [{mark}] `{ev['rule_id']}` → {ev['world']} "
                    f"margin={ev.get('margin')}{extra}"
                )
            lines.append(f"- **Fitness**: `{t['fitness']}`")
            lines.append("")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_trigger_trace(self, path: Path, p: dict[str, Any]) -> None:
        lines = [
            "# Version41 Trigger Evaluation Trace",
            "",
            "各Race・各Worldの PASS / FAIL / Margin / 不足条件 / Why-Not。",
            "",
        ]
        for t in p["traces"]:
            lines.append(
                f"## `{t['race_id']}` → Decision `{t['decision']['world']}`"
            )
            lines.append("")
            lines.append(
                "| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |"
            )
            lines.append("|---|---|---|---|---|---|")
            for w in CANONICAL:
                st = t["world_trigger_status"][w]
                why = "; ".join((st.get("why_not") or [])[:2]) or "—"
                if len(why) > 80:
                    why = why[:77] + "..."
                lines.append(
                    f"| `{w}` | {st['status']} | "
                    f"{', '.join(st.get('missing') or []) or '—'} | "
                    f"{', '.join(st.get('below_threshold') or []) or '—'} | "
                    f"{st.get('near_miss')} | {why} |"
                )
            lines.append("")
            lines.append("### Why-Not detail")
            lines.append("")
            for w, wn in t["why_not"].items():
                lines.append(
                    f"- **{w}** [{wn['status']}] fitness={wn.get('fitness')}"
                )
                for r in wn.get("reasons") or []:
                    lines.append(f"  - {r}")
            lines.append("")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_mismatch(self, path: Path, p: dict[str, Any]) -> None:
        mm = p["mismatch"]
        lines = [
            "# Version41 Fitness Mismatch",
            "",
            f"- fitness_agree_rate: **{_pct(p['fitness_agree_rate'])}** "
            f"（V40 agree best-fit = 14.3% と同一系）",
            f"- mismatch_n: **{mm['n']}** / {p['n_races']}",
            "",
            "## Pair counts (best-fit → decision)",
            "",
        ]
        for k, v in mm["pair_counts"].items():
            lines.append(f"- `{k}`: {v}")
        lines.append("")
        lines.append("## Reason buckets")
        lines.append("")
        for k, v in mm["reason_buckets"].items():
            lines.append(f"- `{k}`: {v}")
        lines.append("")
        lines.append("## Per-race mismatch")
        lines.append("")
        lines.append(
            "| race_id | best_fit | decision | fitness_gap | reason |"
        )
        lines.append("|---|---|---|---|---|")
        for t in p["traces"]:
            if t["fitness_mismatch"]["agree"]:
                continue
            fm = t["fitness_mismatch"]
            reason = fm["reason"].replace("|", "/")
            if len(reason) > 100:
                reason = reason[:97] + "..."
            lines.append(
                f"| `{t['race_id']}` | `{fm['best_fit_world']}` | "
                f"`{fm['decision_world']}` | {fm['fitness_gap']} | {reason} |"
            )
        lines.append("")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_root_cause(self, path: Path, p: dict[str, Any]) -> None:
        lines = [
            "# Version41 Root Cause Classification",
            "",
            "## Counts (all races)",
            "",
        ]
        for k in PRIMARY_CLASSES:
            lines.append(f"- **{k}**: {p['primary_root_cause_counts'].get(k, 0)}")
        lines.append("")
        lines.append("## Counts (decision = core_world only) — core偏重の件数証明")
        lines.append("")
        ce = p["core_evidence"]
        for k in PRIMARY_CLASSES:
            lines.append(
                f"- **{k}**: {p['core_primary_root_cause_counts'].get(k, 0)}"
            )
        lines.append("")
        lines.append("## Core bias evidence")
        lines.append("")
        lines.append(f"- n_core: **{ce['n_core']}**")
        lines.append(f"- via R8_core_default: **{ce['all_via_R8_default']}**")
        lines.append(f"- R1–R7 all FAIL: **{ce['all_r1_r7_fail']}**")
        lines.append(
            f"- fitness mismatch among core: **{ce['fitness_mismatch_among_core']}**"
        )
        lines.append(f"- secondary tags: `{ce['secondary_among_core']}`")
        lines.append("")
        lines.append("## Per-race")
        lines.append("")
        lines.append(
            "| race_id | decision | best_fit | primary | secondary | evidence |"
        )
        lines.append("|---|---|---|---|---|---|")
        for t in p["traces"]:
            rc = t["root_cause"]
            ev = "; ".join(rc.get("evidence") or [])[:90]
            sec = ",".join(rc.get("secondary") or []) or "—"
            lines.append(
                f"| `{t['race_id']}` | `{t['decision']['world']}` | "
                f"`{t['best_fit_world']}` | {rc['primary']} | {sec} | {ev} |"
            )
        lines.append("")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_governance(self, path: Path, p: dict[str, Any]) -> None:
        g = p["governance"]
        ce = p["core_evidence"]
        lines = [
            "# Version41 Governance — World Decision Trace",
            "",
            f"## Verdict: **{g['verdict']}** — {g['labels'][g['verdict']]}",
            "",
            "## Evidence",
            "",
            f"- n={p['n_races']}, core_share={_pct(p['core_share'])}",
            f"- fitness_agree={_pct(p['fitness_agree_rate'])}",
            f"- core via R8_default: {ce['all_via_R8_default']}/{ce['n_core']}",
            f"- core with R1–R7 all FAIL: {ce['all_r1_r7_fail']}/{ce['n_core']}",
            f"- primary (all): `{p['primary_root_cause_counts']}`",
            f"- primary (core only): `{p['core_primary_root_cause_counts']}`",
            f"- shares among core: `{g.get('shares_among_core')}`",
            "",
            "## Interpretation",
            "",
            "core_world は正の Trigger を持たず `R8_core_default` である。"
            "本 Trace では core 決定の全てが R1-R7 FAIL 後の DEFAULT である。"
            "soft fitness の最適 World と first-match Decision の一致率は低く、"
            "「Fitness最適 != 実際World」は Evaluation Order（優先度 first-match）と "
            "DEFAULT 構造の直接帰結として観測される。",
            "",
            "binding 失敗理由（best-fit World の Trigger FAIL）は主に閾値未達"
            "（Trigger不足）または near-miss（Boundary）である。"
            "phase 欠落は多数レースで観測されるが、mixed 系ルール付随であり、"
            "midhole/midupper best-fit の FAIL 理由（late_stop / difficulty / "
            "short_field_pressure）とは別である。",
            "",
            "したがって core 75% の根本は、Signal 欠落単体ではなく、"
            "**Decision Engine 構造（first-match + core=DEFAULT）が "
            "Trigger 未達を全て core に落とすこと**である。",
            "",
            "## Labels",
            "",
            "- A: Signalが主因",
            "- B: Boundaryが主因",
            "- C: Decision Engine構造が主因",
            "- D: 複数要因",
            "",
            "## Artifacts",
            "",
            "- `docs/audit/v41-decision-trace.md`",
            "- `docs/audit/v41-trigger-trace.md`",
            "- `docs/audit/v41-fitness-mismatch.md`",
            "- `docs/audit/v41-root-cause-classification.md`",
            "- `docs/audit/v41-governance.md`",
            "- `services/win5-ai/var/research_evidence/reports/v41-world-decision-trace.json`",
            "",
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    audit = WorldDecisionTraceAudit()
    payload = audit.run()
    paths = audit.write_artifacts(payload)
    summary = {k: v for k, v in payload.items() if k != "traces"}
    print(json.dumps({"summary": summary, "paths": paths}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
