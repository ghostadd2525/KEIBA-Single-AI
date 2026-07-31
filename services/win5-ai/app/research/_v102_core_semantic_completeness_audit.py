# -*- coding: utf-8 -*-
"""Version102 — Core Semantic Completeness Audit (Shadow Observation).

ADR-009 / ADR-010 adopted.
Audit whether currently held Core semantics alone can fully explain a race.
No new Features. No Prediction/World/Decision mutation. 実装禁止.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))
sys.path.insert(0, str(Path(r"C:\win5-ai")))

from app.research._v74_world_strategy_validation import load_cew_labels  # noqa: E402
from app.research._v96_unsatisfied_world_affinity import (  # noqa: E402
    AFFINITY_WORLDS,
    affinity_for_world,
    build_signals_for_race,
    exclusion_reasons_research,
    primary_near_world,
    structural_class,
)
from app.research._v97_affinity_decision_value_shadow import load_dual, near_miss_meta  # noqa: E402
from app.research._v100_core_completeness_shadow import EXPECTED_STRATEGY  # noqa: E402

SCHEMA = "v102-core-semantic-completeness-audit/1.0"
STRATEGY_WORLDS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "mixed_world",
    "bug_world",
)

# Required semantic slots for a closed explanation (no new features)
REQUIRED_POSITIVE = (
    "prediction_bundle",
    "world_label",
    "must_trace",
    "must_gaps",
    "exclusion_trace",
    "match_trace",
    "transition",
    "expected_strategy",
    "explanation_confidence_ec",  # observational: derivable from traces (ADR-010)
)
REQUIRED_UNSAT = REQUIRED_POSITIVE + (
    "near_miss_class",
    "near_world_or_pure",
    "affinity_vector",
    "exclusion_reasons",
)

# Dependency edges (design graph)
DEPENDENCY_EDGES = [
    ("prediction_bundle", "world_label"),  # world evaluated after/with ranking concepts; PE not mutated
    ("world_label", "must_trace"),
    ("must_trace", "must_gaps"),
    ("must_trace", "exclusion_trace"),
    ("must_trace", "match_trace"),
    ("world_label", "transition"),
    ("world_label", "expected_strategy"),
    ("world_label", "near_miss_class"),  # only if unsatisfied
    ("near_miss_class", "near_world_or_pure"),
    ("near_world_or_pure", "affinity_vector"),
    ("near_world_or_pure", "exclusion_reasons"),
    ("must_trace", "explanation_confidence_ec"),
    ("exclusion_trace", "explanation_confidence_ec"),
    ("near_miss_class", "explanation_confidence_ec"),
    ("expected_strategy", "explanation_confidence_ec"),
]

# Explainability flow (user-specified)
EXPLAIN_FLOW = [
    "prediction_bundle",
    "world_label",
    "near_miss_class",
    "affinity_vector",
    "expected_strategy",
    "explanation_confidence_ec",
]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _rate(ok: int, n: int) -> float | None:
    return (ok / n) if n else None


def slot_presence(rid: str, race: dict[str, Any], fx: dict[str, Any], cew: str | None, dual: dict[str, Any], thr: dict[str, float]) -> dict[str, Any]:
    """What semantic slots are present from CURRENT holdings (no new features)."""
    runners = list(race.get("runners") or [])
    trace = dual.get("decision_trace") or {}
    unsat = cew == "unsatisfied"

    # Prediction bundle: ranks+scores present (not Prediction Confidence)
    pred_ok = False
    if runners:
        ranks = [u.get("model_rank") for u in runners]
        scores = [u.get("win_prob") for u in runners]
        pred_ok = all(r is not None and str(r) != "" for r in ranks) and all(
            s is not None and s != "" for s in scores
        )
        top1 = str(fx.get("predicted_top1_horse_id") or "")
        ids = [str(u.get("horse_id") or "") for u in runners]
        pred_ok = pred_ok and bool(top1) and top1 in ids

    world_ok = bool(cew)
    must_ok = excl_ok = match_ok = gaps_ok = False
    if isinstance(trace, dict) and trace:
        must_ok = all(isinstance(trace.get(w), dict) and "must" in (trace.get(w) or {}) for w in STRATEGY_WORLDS)
        excl_ok = all(isinstance(trace.get(w), dict) and "exclude" in (trace.get(w) or {}) for w in STRATEGY_WORLDS)
        match_ok = all(isinstance(trace.get(w), dict) and "match" in (trace.get(w) or {}) for w in STRATEGY_WORLDS)
        gaps_ok = all(isinstance(trace.get(w), dict) and "must_gaps" in (trace.get(w) or {}) for w in STRATEGY_WORLDS)

    transition_ok = bool(dual.get("world_transition") or dual.get("trigger_path"))
    # Expected Strategy: NOT a Core-emitted object — only design-map resolvable
    es_in_payload = dual.get("expected_strategy") is not None or race.get("expected_strategy") is not None
    es_map_ok = bool(cew) and cew in EXPECTED_STRATEGY
    es_ok = es_map_ok  # held as mappable knowledge, not race payload field

    # Near miss / affinity / exclusion reasons
    residual = None
    near_world = None
    affinity = None
    excl_reasons = None
    nm_class_ok = False
    near_or_pure_ok = False
    affinity_ok = False
    excl_reason_ok = False
    affinity_native = "affinity" in dual or "affinity" in (race or {})
    excl_reason_native = False
    if isinstance(trace, dict):
        # native exclusion reasons in trace?
        for w in STRATEGY_WORLDS:
            tw = trace.get(w) or {}
            if "exclusion_reasons" in tw or "exclude_reasons" in tw:
                excl_reason_native = True
                break

    if unsat and isinstance(trace, dict):
        residual = structural_class(trace)
        nm_class_ok = residual in ("NEAR_MISS", "PURE_RESIDUAL")
        meta = near_miss_meta(trace)
        near_world = meta.get("near_world") if meta else primary_near_world(
            {w: affinity_for_world(trace.get(w) or {}, w) for w in AFFINITY_WORLDS}
        )
        if residual == "PURE_RESIDUAL":
            near_or_pure_ok = True
        else:
            near_or_pure_ok = near_world is not None

        affinity = {}
        for w in AFFINITY_WORLDS:
            affinity[w] = affinity_for_world(trace.get(w) or {}, w)["must_affinity"]
        affinity_ok = len(affinity) == 4

        signals = build_signals_for_race(rid, race, fx)
        excl_map = exclusion_reasons_research(signals, thr)
        if residual == "NEAR_MISS" and near_world:
            excl_reasons = list(excl_map.get(near_world) or [])
            excl_reason_ok = len(excl_reasons) > 0
        elif residual == "PURE_RESIDUAL":
            excl_reason_ok = True  # explained as all-must-fail; reasons optional
            excl_reasons = []
        else:
            excl_reason_ok = False
    elif not unsat:
        nm_class_ok = True  # N/A — slot not required as positive
        near_or_pure_ok = True
        affinity_ok = True
        excl_reason_ok = True

    # Explanation Confidence: not emitted; derivable observationally if traces ok
    ec_emitted = dual.get("explanation_confidence") is not None or dual.get("explanation_confidence_bundle") is not None
    ec_derivable = bool(world_ok and must_ok and excl_ok and match_ok and gaps_ok and transition_ok and es_ok)
    if unsat:
        ec_derivable = ec_derivable and nm_class_ok and near_or_pure_ok and affinity_ok and excl_reason_ok

    slots = {
        "prediction_bundle": pred_ok,
        "world_label": world_ok,
        "must_trace": must_ok,
        "must_gaps": gaps_ok,
        "exclusion_trace": excl_ok,
        "match_trace": match_ok,
        "transition": transition_ok,
        "expected_strategy": es_ok,
        "expected_strategy_in_race_payload": es_in_payload,
        "near_miss_class": nm_class_ok if unsat else None,
        "near_world_or_pure": near_or_pure_ok if unsat else None,
        "affinity_vector": affinity_ok if unsat else None,
        "affinity_in_race_payload": affinity_native,
        "exclusion_reasons": excl_reason_ok if unsat else None,
        "exclusion_reasons_in_trace_payload": excl_reason_native,
        "explanation_confidence_ec": ec_derivable,
        "explanation_confidence_emitted": ec_emitted,
    }
    meta = {
        "cew_world": cew,
        "unsatisfied": unsat,
        "residual_class": residual,
        "near_world": near_world,
        "affinity": affinity,
        "exclusion_reasons": excl_reasons,
        "expected_strategy_text": EXPECTED_STRATEGY.get(cew) if cew else None,
        "world_transition": dual.get("world_transition"),
        "trigger_path": dual.get("trigger_path"),
        "affinity_top": (
            max(AFFINITY_WORLDS, key=lambda w: (affinity[w], -AFFINITY_WORLDS.index(w)))
            if affinity
            else None
        ),
    }
    return {"slots": slots, "meta": meta}


def coverage_for_race(slots: dict[str, Any], unsat: bool) -> dict[str, Any]:
    req = REQUIRED_UNSAT if unsat else REQUIRED_POSITIVE
    present = []
    missing = []
    for k in req:
        v = slots.get(k)
        if v is True:
            present.append(k)
        else:
            missing.append(k)
    return {
        "required": list(req),
        "n_required": len(req),
        "n_present": len(present),
        "coverage": len(present) / len(req) if req else None,
        "missing_slots": missing,
        "closed": len(missing) == 0,
    }


def flow_closed(slots: dict[str, Any], unsat: bool) -> dict[str, Any]:
    """Explainability flow edges must hold when applicable."""
    edges = []
    ok_all = True
    seq = list(EXPLAIN_FLOW)
    # For positive worlds, near_miss_class and affinity are N/A — skip those nodes
    if not unsat:
        seq = [s for s in seq if s not in ("near_miss_class", "affinity_vector")]

    for i in range(len(seq) - 1):
        a, b = seq[i], seq[i + 1]
        av = slots.get(a)
        bv = slots.get(b)
        # edge holds if both present (True), or upstream present enables downstream
        holds = bool(av) and bool(bv)
        edges.append({"from": a, "to": b, "holds": holds, "from_ok": bool(av), "to_ok": bool(bv)})
        if not holds:
            ok_all = False
    return {"nodes": seq, "edges": edges, "flow_closed": ok_all}


def redundancy_row(meta: dict[str, Any], unsat: bool) -> dict[str, Any]:
    """Detect overlapping semantics among Near Miss / Affinity / Transition / Expected Strategy."""
    cew = meta.get("cew_world")
    transition = meta.get("world_transition") or ""
    # parse "A->B"
    trans_src = trans_dst = None
    if isinstance(transition, str) and "->" in transition:
        parts = transition.split("->", 1)
        trans_src, trans_dst = parts[0].strip(), parts[1].strip()

    near = meta.get("near_world")
    aff_top = meta.get("affinity_top")
    es = cew  # expected strategy keyed only by world label

    overlaps = []
    if unsat and near and aff_top and near == aff_top:
        overlaps.append({"pair": "near_world≡affinity_top", "value": near})
    if trans_dst and cew and trans_dst == cew:
        overlaps.append({"pair": "transition_dst≡world_label", "value": cew})
    if es and cew and es == cew:
        overlaps.append({"pair": "expected_strategy_key≡world_label", "value": cew, "note": "ES is world-keyed map only"})
    if unsat and near and trans_src and near == trans_src:
        overlaps.append({"pair": "near_world≡transition_src", "value": near})

    # semantic redundancy score: how many identity overlaps
    return {
        "overlaps": overlaps,
        "n_overlaps": len(overlaps),
        "transition_src": trans_src,
        "transition_dst": trans_dst,
        "near_world": near,
        "affinity_top": aff_top,
        "world_label": cew,
    }


def missing_semantic_inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Semantics NOT held as first-class Core payload, causing explanation to rely on
    external maps / research derivation — WITHOUT proposing new Features.
    """
    # Structural inventory (corpus-level) + race counts where gap bites
    structural = [
        {
            "id": "MS-1",
            "missing": "Expected Strategy as race payload",
            "held_instead": "V75 static map keyed by world_label",
            "impact": "ES adds no race-specific semantic beyond World",
            "new_feature": False,
        },
        {
            "id": "MS-2",
            "missing": "Affinity vector in dual-eval / Core emit",
            "held_instead": "Derivable from decision_trace must_gaps (research)",
            "impact": "Affinity not first-class; explanation needs derivation step",
            "new_feature": False,
        },
        {
            "id": "MS-3",
            "missing": "Exclusion reasons list in decision_trace",
            "held_instead": "exclude:bool only; reasons via research mirror of V44 predicates",
            "impact": "Why excluded needs off-payload reconstruction",
            "new_feature": False,
        },
        {
            "id": "MS-4",
            "missing": "ExplanationConfidenceBundle emit (ADR-010)",
            "held_instead": "Derivable from Completeness/trace slots",
            "impact": "EC defined but not returned as Core object",
            "new_feature": False,
        },
        {
            "id": "MS-5",
            "missing": "Near Miss class / near_world as Core emit",
            "held_instead": "Derivable from must∧exclude in decision_trace",
            "impact": "Taxonomy exists in research; not serialized on race",
            "new_feature": False,
        },
        {
            "id": "MS-6",
            "missing": "Natural-language why sentence",
            "held_instead": "Structured traces only",
            "impact": "Machine-closed ≠ human prose; not a Feature gap",
            "new_feature": False,
        },
    ]

    counts = Counter()
    for r in rows:
        s = r["slots"]
        if not s.get("expected_strategy_in_race_payload"):
            counts["MS-1"] += 1
        if r["meta"].get("unsatisfied") and not s.get("affinity_in_race_payload"):
            counts["MS-2"] += 1
        if r["meta"].get("unsatisfied") and not s.get("exclusion_reasons_in_trace_payload"):
            counts["MS-3"] += 1
        if not s.get("explanation_confidence_emitted"):
            counts["MS-4"] += 1
        if r["meta"].get("unsatisfied"):
            # class not in payload
            if "residual_class" not in (r.get("dual_keys") or []):
                counts["MS-5"] += 1
        counts["MS-6"] += 1  # never have NL why in payload

    for item in structural:
        item["n_races_affected"] = counts.get(item["id"], 0)

    return {"items": structural, "note": "No new Features proposed — inventory of non-first-class semantics only"}


def run() -> dict[str, Any]:
    os.environ.setdefault("W_TRIGGER_PATH", "legacy")
    from ai_platform.core.world.v44_shadow_eval import build_polarity_thresholds

    corp = json.loads(
        (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
    )
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []
    fxby = {str(r["race_id"]): r for r in fx_rows}
    cew_map = load_cew_labels()
    dual_map = load_dual()
    races_by = {str(r["race_id"]): r for r in corp["races"]}

    signal_table = [build_signals_for_race(rid, race, fxby.get(rid) or {}) for rid, race in races_by.items()]
    thr = build_polarity_thresholds(signal_table)

    rows = []
    for rid in sorted(cew_map.keys()):
        race = races_by.get(rid)
        if not race:
            continue
        dual = dual_map.get(rid) or {}
        fxr = fxby.get(rid) or {}
        cew = cew_map.get(rid)
        sp = slot_presence(rid, race, fxr, cew, dual, thr)
        unsat = bool(sp["meta"]["unsatisfied"])
        cov = coverage_for_race(sp["slots"], unsat)
        flow = flow_closed(sp["slots"], unsat)
        red = redundancy_row(sp["meta"], unsat)
        rows.append(
            {
                "race_id": rid,
                "slots": sp["slots"],
                "meta": sp["meta"],
                "coverage": cov,
                "flow": flow,
                "redundancy": red,
                "dual_keys": sorted(dual.keys()),
            }
        )

    n = len(rows)
    n_closed = sum(1 for r in rows if r["coverage"]["closed"])
    n_flow = sum(1 for r in rows if r["flow"]["flow_closed"])
    by_slot = {}
    all_slots = set()
    for r in rows:
        for k, v in r["slots"].items():
            if v is None:
                continue
            all_slots.add(k)
    for k in sorted(all_slots):
        vals = [r["slots"][k] for r in rows if r["slots"].get(k) is not None]
        by_slot[k] = _rate(sum(1 for v in vals if v), len(vals))

    # Missing required slots frequency
    miss_req = Counter()
    for r in rows:
        for m in r["coverage"]["missing_slots"]:
            miss_req[m] += 1

    # Dependency empirical: P(child|parent) among applicable
    dep_emp = []
    for a, b in DEPENDENCY_EDGES:
        both = numer = 0
        for r in rows:
            sa, sb = r["slots"].get(a), r["slots"].get(b)
            if sa is None or sb is None:
                # skip N/A
                if a in ("near_miss_class", "near_world_or_pure", "affinity_vector", "exclusion_reasons") or b in (
                    "near_miss_class",
                    "near_world_or_pure",
                    "affinity_vector",
                    "exclusion_reasons",
                ):
                    if not r["meta"]["unsatisfied"]:
                        continue
                else:
                    continue
            if sa is True:
                both += 1
                if sb is True:
                    numer += 1
        dep_emp.append(
            {
                "from": a,
                "to": b,
                "support_parent": both,
                "p_child_given_parent": (numer / both) if both else None,
            }
        )

    # Redundancy aggregates
    overlap_c = Counter()
    for r in rows:
        for o in r["redundancy"]["overlaps"]:
            overlap_c[o["pair"]] += 1
    near_aff_agree = sum(
        1
        for r in rows
        if r["meta"]["unsatisfied"]
        and r["meta"].get("near_world")
        and r["meta"].get("affinity_top")
        and r["meta"]["near_world"] == r["meta"]["affinity_top"]
    )
    n_unsat = sum(1 for r in rows if r["meta"]["unsatisfied"])

    inv = missing_semantic_inventory(rows)

    # Verdict: can current semantics explain? Distinguish payload-closed vs derivable-closed
    payload_first_class_gaps = ["MS-1", "MS-2", "MS-3", "MS-4", "MS-5"]
    verdict = {
        "derivable_explanation_closed_rate": _rate(n_closed, n),
        "explainability_flow_closed_rate": _rate(n_flow, n),
        "first_class_payload_complete": False,  # MS-* show ES/Affinity/EC/NM not emitted
        "audit_verdict": "DERIVABLE_COMPLETE_BUT_NOT_FIRST_CLASS",
        "reason": (
            "Structured traces allow deriving a closed explanation for essentially all races, "
            "but Expected Strategy / Affinity / Exclusion reasons / Near Miss class / EC Bundle "
            "are not first-class Core emits — explanation depends on maps + derivation (no new Features)."
        ),
    }
    if n_closed == n and n_flow == n:
        verdict["audit_verdict"] = "DERIVABLE_COMPLETE_BUT_NOT_FIRST_CLASS"
    elif n_closed / n >= 0.95:
        verdict["audit_verdict"] = "MOSTLY_DERIVABLE_PARTIAL_GAPS"
    else:
        verdict["audit_verdict"] = "SEMANTIC_GAPS_BLOCK_EXPLANATION"

    report = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "adr": ["ADR-009", "ADR-010"],
        "purpose": "Audit whether currently held Core semantics alone fully explain races",
        "locks": [
            "Prediction",
            "Ranking",
            "Score",
            "Confidence(EC)",
            "Trigger",
            "World",
            "Near Miss",
            "Affinity",
            "Transition",
            "Expected Strategy",
            "Decision",
            "Single AI",
            "Win5 AI",
        ],
        "n_races": n,
        "n_unsatisfied": n_unsat,
        "semantic_coverage": {
            "mean_coverage": float(sum(r["coverage"]["coverage"] for r in rows) / n),
            "closed_rate": _rate(n_closed, n),
            "slot_rates": by_slot,
            "missing_required_counts": dict(miss_req),
        },
        "dependency_graph": {
            "design_edges": [{"from": a, "to": b} for a, b in DEPENDENCY_EDGES],
            "empirical": dep_emp,
        },
        "missing_semantic_inventory": inv,
        "redundancy": {
            "overlap_counts": dict(overlap_c),
            "near_world_eq_affinity_top_rate": _rate(near_aff_agree, n_unsat) if n_unsat else None,
            "interpretation": (
                "expected_strategy_key≡world_label is structural redundancy (map keyed by World). "
                "near_world≡affinity_top indicates overlapping Near Miss signals."
            ),
        },
        "explainability_flow": {
            "flow": EXPLAIN_FLOW,
            "closed_rate": _rate(n_flow, n),
            "edge_fail_counts": dict(
                Counter(
                    f"{e['from']}->{e['to']}"
                    for r in rows
                    for e in r["flow"]["edges"]
                    if not e["holds"]
                )
            ),
        },
        "verdict": verdict,
        "samples_incomplete": [
            {
                "race_id": r["race_id"],
                "world": r["meta"]["cew_world"],
                "missing_slots": r["coverage"]["missing_slots"],
                "flow_closed": r["flow"]["flow_closed"],
            }
            for r in rows
            if not r["coverage"]["closed"] or not r["flow"]["flow_closed"]
        ][:25],
        "_rows_slim": [
            {
                "race_id": r["race_id"],
                "world": r["meta"]["cew_world"],
                "coverage": r["coverage"]["coverage"],
                "closed": r["coverage"]["closed"],
                "flow_closed": r["flow"]["flow_closed"],
                "n_overlaps": r["redundancy"]["n_overlaps"],
            }
            for r in rows
        ],
    }
    return report


def write_docs(report: dict[str, Any]) -> dict[str, str]:
    docs = ROOT / "docs/research"
    docs.mkdir(parents=True, exist_ok=True)
    slim_rows = report.pop("_rows_slim", [])
    jpath = docs / "_v102-core-semantic-completeness-audit.json"
    jpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (docs / "_v102-semantic-audit-per-race.json").write_text(
        json.dumps({"n": len(slim_rows), "rows": slim_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def fmt(x: Any) -> str:
        if x is None:
            return "—"
        if isinstance(x, float):
            return f"{x:.4f}"
        return str(x)

    cov = report["semantic_coverage"]
    v = report["verdict"]

    # 1 Coverage
    cov_md = [
        "# Version102 — Semantic Coverage Report",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**n_races:** {report['n_races']}  ",
        "**Mode:** Shadow Observation · **実装禁止**  ",
        "**非評価:** Hit / ROI / Calibration / Decision / Prediction 改善",
        "",
        "## Verdict",
        "",
        f"**`{v['audit_verdict']}`**",
        "",
        v["reason"],
        "",
        f"- derivable closed rate: **{fmt(v['derivable_explanation_closed_rate'])}**",
        f"- explainability flow closed rate: **{fmt(v['explainability_flow_closed_rate'])}**",
        f"- first-class payload complete: **{v['first_class_payload_complete']}**",
        "",
        "## Slot coverage（現有情報）",
        "",
        f"- mean coverage: **{fmt(cov['mean_coverage'])}**",
        f"- fully closed races: **{fmt(cov['closed_rate'])}**",
        "",
        "| Slot | Rate |",
        "|---|---:|",
    ]
    for k, rate in (cov.get("slot_rates") or {}).items():
        cov_md.append(f"| `{k}` | {fmt(rate)} |")
    cov_md += [
        "",
        "## Missing required slots",
        "",
        "```",
        json.dumps(cov.get("missing_required_counts") or {}, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 解釈",
        "",
        "Coverage は『導出すれば説明が閉じるか』を測る。",
        "first-class 未 emit（Affinity/ES/EC 等）は Missing Inventory を参照。",
        "",
    ]
    p_cov = docs / "v102-semantic-coverage-report.md"
    p_cov.write_text("\n".join(cov_md), encoding="utf-8")

    # 2 Missing inventory
    inv = report["missing_semantic_inventory"]
    inv_md = [
        "# Version102 — Missing Semantic Inventory",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "**原則:** 新しい Feature は追加しない。現有情報で説明できない／first-class でない部分のみ。",
        "",
        "| ID | Missing（first-class） | Held instead | n_races |",
        "|---|---|---|---:|",
    ]
    for it in inv["items"]:
        inv_md.append(
            f"| `{it['id']}` | {it['missing']} | {it['held_instead']} | {it['n_races_affected']} |"
        )
    inv_md += [
        "",
        "## 詳細",
        "",
    ]
    for it in inv["items"]:
        inv_md += [
            f"### `{it['id']}`",
            "",
            f"- impact: {it['impact']}",
            f"- new_feature: **{it['new_feature']}**",
            "",
        ]
    inv_md += [
        "## 結論",
        "",
        "説明不能な『未知概念』よりも、**保持形態が導出依存**であることが主欠落。",
        "Feature 追加ではなく、既存 Trace の first-class 露出が論点（実装は別 Decision・本監査では禁止）。",
        "",
    ]
    p_inv = docs / "v102-missing-semantic-inventory.md"
    p_inv.write_text("\n".join(inv_md), encoding="utf-8")

    # 3 Dependency graph
    dep = report["dependency_graph"]
    dep_md = [
        "# Version102 — Semantic Dependency Graph",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "## Design graph",
        "",
        "```mermaid",
        "flowchart TD",
        "  P[prediction_bundle]",
        "  W[world_label]",
        "  MT[must_trace]",
        "  MG[must_gaps]",
        "  EX[exclusion_trace]",
        "  MA[match_trace]",
        "  TR[transition]",
        "  ES[expected_strategy]",
        "  NM[near_miss_class]",
        "  NW[near_world_or_pure]",
        "  AF[affinity_vector]",
        "  ER[exclusion_reasons]",
        "  EC[explanation_confidence_ec]",
        "  P --> W",
        "  W --> MT",
        "  MT --> MG",
        "  MT --> EX",
        "  MT --> MA",
        "  W --> TR",
        "  W --> ES",
        "  W --> NM",
        "  NM --> NW",
        "  NW --> AF",
        "  NW --> ER",
        "  MT --> EC",
        "  EX --> EC",
        "  NM --> EC",
        "  ES --> EC",
        "```",
        "",
        "## Empirical P(child | parent)",
        "",
        "| From | To | support | P |",
        "|---|---|---:|---:|",
    ]
    for e in dep["empirical"]:
        dep_md.append(
            f"| `{e['from']}` | `{e['to']}` | {e['support_parent']} | {fmt(e['p_child_given_parent'])} |"
        )
    dep_md.append("")
    p_dep = docs / "v102-dependency-graph.md"
    p_dep.write_text("\n".join(dep_md), encoding="utf-8")

    # 4 Redundancy
    red = report["redundancy"]
    red_md = [
        "# Version102 — Semantic Redundancy Report",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        f"- near_world ≡ affinity_top rate (unsatisfied): **{fmt(red.get('near_world_eq_affinity_top_rate'))}**",
        "",
        "## Overlap counts",
        "",
        "| Pair | n |",
        "|---|---:|",
    ]
    for k, c in (red.get("overlap_counts") or {}).items():
        red_md.append(f"| `{k}` | {c} |")
    red_md += [
        "",
        "## 解釈",
        "",
        red.get("interpretation") or "",
        "",
        "- **Transition** は経路（from→to）を持ち World ラベルと部分重複するが、from 側に追加意味がある。",
        "- **Expected Strategy** が World キーのみなら、World と情報理論的に冗長（レース固有戦略文なし）。",
        "- **Near Miss vs Affinity** 高一致は重複シグナル。役割は『クラス』vs『連続近さ』で区別可能。",
        "",
    ]
    p_red = docs / "v102-redundancy-report.md"
    p_red.write_text("\n".join(red_md), encoding="utf-8")

    # 5 Flow
    fl = report["explainability_flow"]
    fl_md = [
        "# Version102 — Explainability Flow",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "## Flow",
        "",
        "```text",
        "Prediction → World → Near Miss → Affinity → Expected Strategy → Explanation Confidence",
        "```",
        "",
        f"- flow closed rate: **{fmt(fl.get('closed_rate'))}**",
        "",
        "Positive World では Near Miss / Affinity ノードをスキップして評価。",
        "",
        "## Edge failures",
        "",
        "```",
        json.dumps(fl.get("edge_fail_counts") or {}, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 論理閉鎖の条件",
        "",
        "各矢印の両端スロットが現有情報（または許容導出）で True であること。",
        "Hit/ROI はフローに含めない。",
        "",
    ]
    p_fl = docs / "v102-explainability-flow.md"
    p_fl.write_text("\n".join(fl_md), encoding="utf-8")

    # 6 Governance
    gov = [
        "# Version102 — Governance",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Core Semantic Completeness Audit |",
        "| ADR-009 / ADR-010 | **正式採用・維持** |",
        "| Implementation Required | **No** |",
        "| Deployment Required | No |",
        f"| Audit Verdict | `{v['audit_verdict']}` |",
        "| New Features | **禁止** |",
        "| Prediction/World/Decision Change | **No** |",
        "| KPI | Completeness / Semantic only |",
        "| Excluded | Hit / ROI / Calibration / Decision / Prediction 改善 |",
        "| Risk | Low |",
        "| Expected Next Action | first-class emit（ES/Affinity/EC）は別 Decision。本監査では実装しない |",
        "",
        "## 成果物",
        "",
        "| 成果物 | Path |",
        "|---|---|",
        "| Semantic Coverage | `v102-semantic-coverage-report.md` |",
        "| Missing Inventory | `v102-missing-semantic-inventory.md` |",
        "| Dependency Graph | `v102-dependency-graph.md` |",
        "| Redundancy | `v102-redundancy-report.md` |",
        "| Explainability Flow | `v102-explainability-flow.md` |",
        "| Governance | `v102-governance.md` |",
        "",
    ]
    p_gov = docs / "v102-governance.md"
    p_gov.write_text("\n".join(gov), encoding="utf-8")

    return {
        "json": str(jpath),
        "coverage": str(p_cov),
        "inventory": str(p_inv),
        "dependency": str(p_dep),
        "redundancy": str(p_red),
        "flow": str(p_fl),
        "gov": str(p_gov),
    }


def main() -> None:
    report = run()
    paths = write_docs(report)
    out = {
        "n": report["n_races"],
        "verdict": report["verdict"],
        "closed_rate": report["semantic_coverage"]["closed_rate"],
        "flow_closed_rate": report["explainability_flow"]["closed_rate"],
        "slot_rates_highlight": {
            k: report["semantic_coverage"]["slot_rates"].get(k)
            for k in (
                "prediction_bundle",
                "world_label",
                "expected_strategy",
                "affinity_vector",
                "explanation_confidence_ec",
                "expected_strategy_in_race_payload",
                "affinity_in_race_payload",
                "explanation_confidence_emitted",
            )
        },
        "redundancy": report["redundancy"]["overlap_counts"],
        "missing_ids": [x["id"] for x in report["missing_semantic_inventory"]["items"]],
        "paths": paths,
    }
    text = json.dumps(out, ensure_ascii=True, indent=2)
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
