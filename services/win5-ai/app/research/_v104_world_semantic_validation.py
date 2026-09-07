# -*- coding: utf-8 -*-
"""Version104 — World Semantic Validation (Shadow Observation).

Semantic Fidelity (思想忠実度), not Completeness.
Compare V43/V75 design intent vs CEW + decision_trace (+ derived Near Miss/Affinity).
No mutation of Prediction/Trigger/World/Contract/Decision. 実装禁止.
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))
sys.path.insert(0, str(Path(r"C:\win5-ai")))

from app.research._v74_world_strategy_validation import load_cew_labels  # noqa: E402
from app.research._v96_unsatisfied_world_affinity import (  # noqa: E402
    AFFINITY_WORLDS,
    affinity_for_world,
    build_signals_for_race,
    exclusion_reasons_research,
)
from app.research._v97_affinity_decision_value_shadow import load_dual, near_miss_meta  # noqa: E402
from app.research.w_s1_shadow_dual_eval import ranking_concepts  # noqa: E402

SCHEMA = "v104-world-semantic-validation/1.0"

# V43 design intent (observational checklist — does not change Trigger)
WORLD_INTENT = {
    "core_world": {
        "goal": "能力決着。上位能力差に沿って勝ち切る。残余DEFAULTではない。",
        "required_dirs": {"top_gap": "high", "ability_separation": "high"},
        "forbidden_high": ("chaos",),  # high chaos must not be core-positive signature
        "must_keys_expected": ("top_gap↑", "ability_separation↑"),
    },
    "midupper_world": {
        "goal": "上位能力＋展開＋適性。能力一本でも混戦でも中位穴でもない。",
        "required_dirs": {"upper_ability_band": "high"},
        "forbidden_high": (),
        "must_keys_expected": ("upper_ability_band↑", "development_pressure↑", "aptitude_fit↑"),
    },
    "midhole_world": {
        "goal": "中位帯まで勝ち筋が開く。上位独占が弱い。",
        "required_dirs": {"mid_eval_band_open": "high", "top_monopoly": "low"},
        "forbidden_high": ("top_gap",),
        "must_keys_expected": ("mid_eval_band_open↑", "top_monopoly↓"),
    },
    "rank7_world": {
        "goal": "展開・混戦。能力一本を過信しない。",
        "required_dirs": {"chaos": "high", "ability_subordinate": "high", "top_gap": "low"},
        "forbidden_high": ("top_gap",),
        "must_keys_expected": ("chaos↑", "pace_conflict↑", "ability_subordinate↑"),
    },
    "mixed_world": {
        "goal": "複数勝ち筋共存。単一方針禁止。",
        "required_dirs": {},
        "forbidden_high": (),
        "must_keys_expected": (),
    },
    "bug_world": {
        "goal": "例外・説明不能。exception なしに発動しない。",
        "required_dirs": {},
        "forbidden_high": (),
        "must_keys_expected": ("exception_flag↑",),
    },
}

CONCEPT_KEYS = (
    "top_gap",
    "ability_separation",
    "upper_ability_band",
    "mid_eval_band_open",
    "top_monopoly",
    "ability_subordinate",
)

STRATEGY_POS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "mixed_world",
    "bug_world",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _mean(xs: list[float]) -> float | None:
    return float(sum(xs) / len(xs)) if xs else None


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        x = float(v)
        if x != x:
            return None
        return x
    except (TypeError, ValueError):
        return None


def cosine(a: dict[str, float], b: dict[str, float], keys: tuple[str, ...]) -> float | None:
    xs = [a.get(k) for k in keys]
    ys = [b.get(k) for k in keys]
    if any(v is None for v in xs + ys):
        keys2 = [k for k in keys if a.get(k) is not None and b.get(k) is not None]
        if len(keys2) < 2:
            return None
        xs = [float(a[k]) for k in keys2]
        ys = [float(b[k]) for k in keys2]
    else:
        xs = [float(x) for x in xs]  # type: ignore
        ys = [float(y) for y in ys]  # type: ignore
    na = math.sqrt(sum(x * x for x in xs))
    nb = math.sqrt(sum(y * y for y in ys))
    if na < 1e-12 or nb < 1e-12:
        return None
    return sum(x * y for x, y in zip(xs, ys)) / (na * nb)


def build_rows() -> tuple[list[dict[str, Any]], dict[str, float]]:
    os.environ.setdefault("W_TRIGGER_PATH", "legacy")
    from ai_platform.core.world.v44_shadow_eval import build_polarity_thresholds

    corp = json.loads(
        (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
    )
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fxby = {str(r["race_id"]): r for r in (fx.get("rows") or fx.get("evaluations") or [])}
    races_by = {str(r["race_id"]): r for r in corp["races"]}
    cew = load_cew_labels()
    dual = load_dual()

    signal_table = [build_signals_for_race(rid, races_by[rid], fxby.get(rid) or {}) for rid in races_by]
    thr = build_polarity_thresholds(signal_table)

    # global medians for direction checks
    concept_pool: dict[str, list[float]] = defaultdict(list)
    chaos_pool: list[float] = []

    rows = []
    for rid, world in cew.items():
        race = races_by.get(rid)
        if not race:
            continue
        fxr = fxby.get(rid) or {}
        d = dual.get(rid) or {}
        trace = d.get("decision_trace") or {}
        concepts = ranking_concepts(race)
        signals = build_signals_for_race(rid, race, fxr)
        for k in CONCEPT_KEYS:
            v = _f(concepts.get(k))
            if v is not None:
                concept_pool[k].append(v)
        ch = _f(signals.get("chaos"))
        if ch is not None:
            chaos_pool.append(ch)

        tw = (trace.get(world) or {}) if world != "unsatisfied" else {}
        aff = {w: affinity_for_world(trace.get(w) or {}, w) for w in AFFINITY_WORLDS}
        nm = near_miss_meta(trace) if world == "unsatisfied" else None
        excl = exclusion_reasons_research(signals, thr)

        rows.append(
            {
                "race_id": rid,
                "cew_world": world,
                "concepts": {k: _f(concepts.get(k)) for k in CONCEPT_KEYS},
                "chaos": ch,
                "trace_self": tw,
                "trace": trace,
                "affinity": {w: aff[w]["must_affinity"] for w in AFFINITY_WORLDS},
                "near_miss": nm,
                "exclusion_reasons": excl,
                "transition": d.get("world_transition"),
                "trigger_path": d.get("trigger_path"),
            }
        )

    medians = {k: float(np.median(vs)) for k, vs in concept_pool.items() if vs}
    medians["chaos"] = float(np.median(chaos_pool)) if chaos_pool else 0.0
    return rows, medians


def direction_ok(value: float | None, direction: str, median: float) -> bool | None:
    if value is None:
        return None
    if direction == "high":
        return value >= median
    if direction == "low":
        return value <= median
    return None


def fidelity_positive(rows: list[dict[str, Any]], world: str, medians: dict[str, float]) -> dict[str, Any]:
    sub = [r for r in rows if r["cew_world"] == world]
    n = len(sub)
    intent = WORLD_INTENT.get(world) or {}
    if n == 0:
        return {"world": world, "n": 0, "status": "empty", "goal": intent.get("goal")}

    match_ok = 0
    must_ok = 0
    excl_clear = 0
    dir_hits = 0
    dir_total = 0
    forbidden_hits = 0
    forbidden_total = 0

    for r in sub:
        tw = r["trace_self"] or {}
        if tw.get("must"):
            must_ok += 1
        if tw.get("match"):
            match_ok += 1
        if tw.get("must") and not tw.get("exclude") and tw.get("match"):
            excl_clear += 1

        for key, direction in (intent.get("required_dirs") or {}).items():
            med = medians.get(key if key != "chaos" else "chaos")
            if med is None:
                continue
            val = r["chaos"] if key == "chaos" else (r["concepts"] or {}).get(key)
            ok = direction_ok(val, direction, med)
            if ok is None:
                continue
            dir_total += 1
            if ok:
                dir_hits += 1

        for key in intent.get("forbidden_high") or ():
            med = medians.get(key if key != "chaos" else "chaos")
            if med is None:
                continue
            val = r["chaos"] if key == "chaos" else (r["concepts"] or {}).get(key)
            if val is None:
                continue
            forbidden_total += 1
            # contamination: forbidden-high signal is high on this positive world race
            if val >= med:
                forbidden_hits += 1

    # profile means
    means = {}
    for k in list(CONCEPT_KEYS) + ["chaos"]:
        if k == "chaos":
            vals = [r["chaos"] for r in sub if r["chaos"] is not None]
        else:
            vals = [r["concepts"][k] for r in sub if r["concepts"].get(k) is not None]
        means[k] = _mean(vals)

    contract_fidelity = excl_clear / n if n else None
    signal_fidelity = (dir_hits / dir_total) if dir_total else None
    # lower forbidden contamination is better → fidelity = 1 - rate
    anti_forbidden = (1.0 - forbidden_hits / forbidden_total) if forbidden_total else None

    parts = [p for p in (contract_fidelity, signal_fidelity, anti_forbidden) if p is not None]
    fidelity = float(sum(parts) / len(parts)) if parts else None

    grade = "N/A"
    if fidelity is not None:
        if fidelity >= 0.85:
            grade = "HIGH"
        elif fidelity >= 0.65:
            grade = "MED"
        else:
            grade = "LOW"

    return {
        "world": world,
        "n": n,
        "goal": intent.get("goal"),
        "contract_match_clear_rate": contract_fidelity,
        "must_rate": must_ok / n,
        "match_rate": match_ok / n,
        "required_signal_direction_rate": signal_fidelity,
        "anti_forbidden_high_rate": anti_forbidden,
        "semantic_fidelity": fidelity,
        "fidelity_grade": grade,
        "concept_means": means,
    }


def world_separation(rows: list[dict[str, Any]], world_fidelity: dict[str, dict[str, Any]]) -> dict[str, Any]:
    worlds = [w for w, rec in world_fidelity.items() if rec.get("n", 0) > 0 and w != "unsatisfied"]
    means = {w: world_fidelity[w].get("concept_means") or {} for w in worlds}
    pairs = []
    for i, a in enumerate(worlds):
        for b in worlds[i + 1 :]:
            c = cosine(means[a], means[b], CONCEPT_KEYS)
            pairs.append({"a": a, "b": b, "cosine": c, "separated": (c is not None and c < 0.98)})
    # also compare to unsatisfied residual mean
    uns = [r for r in rows if r["cew_world"] == "unsatisfied"]
    uns_mean = {}
    for k in CONCEPT_KEYS:
        uns_mean[k] = _mean([r["concepts"][k] for r in uns if r["concepts"].get(k) is not None])
    vs_unsat = {w: cosine(means[w], uns_mean, CONCEPT_KEYS) for w in worlds}

    # label collision: same race cannot have two positive matches in CEW (by definition one label)
    # use affinity vector entropy among unsatisfied as soft separation of near worlds
    return {
        "pairwise_cosine": pairs,
        "mean_pairwise_cosine": _mean([p["cosine"] for p in pairs if p["cosine"] is not None]),
        "vs_unsatisfied_cosine": vs_unsat,
        "separation_note": (
            "Lower cosine ⇒ stronger concept-profile separation. "
            "CEW assigns one label; separation here is semantic profile distinctness."
        ),
    }


def near_miss_fidelity(rows: list[dict[str, Any]], world_fidelity: dict[str, dict[str, Any]], medians: dict[str, float]) -> dict[str, Any]:
    uns = [r for r in rows if r["cew_world"] == "unsatisfied"]
    near = []
    for r in uns:
        nm = r.get("near_miss")
        if not nm or nm.get("residual_class") != "NEAR_MISS":
            continue
        nw = nm.get("near_world")
        if not nw:
            continue
        tw = (r["trace"].get(nw) or {})
        struct_ok = bool(tw.get("must") and tw.get("exclude") and not tw.get("match"))
        aff_ok = float(r["affinity"].get(nw) or 0) >= 0.999
        # profile closer to near_world positive mean than to farthest other?
        means_nw = (world_fidelity.get(nw) or {}).get("concept_means") or {}
        cos_nw = cosine(r["concepts"], means_nw, CONCEPT_KEYS)
        others = []
        for w, rec in world_fidelity.items():
            if w in ("unsatisfied", nw) or not rec.get("n"):
                continue
            c = cosine(r["concepts"], rec.get("concept_means") or {}, CONCEPT_KEYS)
            if c is not None:
                others.append(c)
        nearest_other = max(others) if others else None
        profile_ok = (
            cos_nw is not None and nearest_other is not None and cos_nw + 1e-9 >= nearest_other - 0.02
        ) or (cos_nw is not None and nearest_other is None)

        # intent direction for near world
        intent = WORLD_INTENT.get(nw) or {}
        dir_ok_n = dir_tot = 0
        for key, direction in (intent.get("required_dirs") or {}).items():
            med = medians.get("chaos" if key == "chaos" else key)
            if med is None:
                continue
            val = r["chaos"] if key == "chaos" else r["concepts"].get(key)
            ok = direction_ok(val, direction, med)
            if ok is None:
                continue
            dir_tot += 1
            if ok:
                dir_ok_n += 1
        intent_dir = (dir_ok_n / dir_tot) if dir_tot else None

        near.append(
            {
                "race_id": r["race_id"],
                "near_world": nw,
                "struct_ok": struct_ok,
                "affinity_ok": aff_ok,
                "profile_aligned": profile_ok,
                "cos_to_near_world": cos_nw,
                "intent_direction_rate": intent_dir,
                "fidelity_unit": float(
                    np.mean(
                        [
                            1.0 if struct_ok else 0.0,
                            1.0 if aff_ok else 0.0,
                            1.0 if profile_ok else 0.0,
                        ]
                        + ([intent_dir] if intent_dir is not None else [])
                    )
                ),
            }
        )

    by_nw: dict[str, list] = defaultdict(list)
    for x in near:
        by_nw[x["near_world"]].append(x)

    summary = {}
    for nw, xs in by_nw.items():
        summary[nw] = {
            "n": len(xs),
            "struct_ok_rate": _mean([1.0 if x["struct_ok"] else 0.0 for x in xs]),
            "affinity_ok_rate": _mean([1.0 if x["affinity_ok"] else 0.0 for x in xs]),
            "profile_aligned_rate": _mean([1.0 if x["profile_aligned"] else 0.0 for x in xs]),
            "mean_fidelity": _mean([x["fidelity_unit"] for x in xs]),
            "mean_intent_direction": _mean(
                [x["intent_direction_rate"] for x in xs if x["intent_direction_rate"] is not None]
            ),
        }

    overall = _mean([x["fidelity_unit"] for x in near])
    return {
        "n_near_miss": len(near),
        "overall_near_miss_fidelity": overall,
        "by_near_world": summary,
        "note": "Near Miss fidelity = struct(must∧exclude) + affinity=1 + profile vs positive World mean",
    }


def explainability_fidelity(rows: list[dict[str, Any]], world_fidelity: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Can Affinity + Exclusion + EC-proxy explain design intent without new semantics?"""
    # EC-proxy: traces complete & consistent (from existing slots)
    scores = []
    for r in rows:
        w = r["cew_world"]
        trace = r["trace"] or {}
        # EC-T proxy: all strategy worlds have must/exclude/match
        trace_ok = all(
            isinstance(trace.get(x), dict)
            and "must" in trace[x]
            and "exclude" in trace[x]
            and "match" in trace[x]
            for x in ("core_world", "midupper_world", "midhole_world", "rank7_world")
        )
        excl_lists = r.get("exclusion_reasons") or {}
        has_excl_text = any(bool(v) for v in excl_lists.values()) if isinstance(excl_lists, dict) else False
        aff = r.get("affinity") or {}

        if w == "unsatisfied":
            nm = r.get("near_miss")
            if nm and nm.get("residual_class") == "NEAR_MISS":
                nw = nm.get("near_world")
                ok = bool(trace_ok and nw and aff.get(nw, 0) >= 0.999 and (excl_lists.get(nw) or has_excl_text))
                # explainability: can name the near world + exclusion
                scores.append(1.0 if ok else 0.0)
            else:
                # pure residual: explainable if affinities <1 and trace_ok (all must fail)
                ok = trace_ok and all(float(aff.get(x, 0)) < 1.0 for x in AFFINITY_WORLDS)
                scores.append(1.0 if ok else 0.0)
        else:
            # positive: Affinity N/A; Exclusion of others + clear self match + intent goal known
            tw = r["trace_self"] or {}
            self_clear = bool(tw.get("match") and tw.get("must") and not tw.get("exclude"))
            # other worlds have gaps or exclude — explainable differentiation
            others_diff = 0
            for ow in AFFINITY_WORLDS:
                if ow == w:
                    continue
                ot = trace.get(ow) or {}
                if ot.get("exclude") or (ot.get("must_gaps")) or not ot.get("must"):
                    others_diff += 1
            ok = trace_ok and self_clear and others_diff >= 1 and (w in WORLD_INTENT)
            scores.append(1.0 if ok else 0.0)

    return {
        "explainability_fidelity_rate": _mean(scores),
        "n": len(scores),
        "definition": (
            "Fraction of races whose design membership can be stated using "
            "Affinity (if unsat) + Exclusion reasons/flags + trace completeness proxy for EC — "
            "without Hit/ROI/new Features."
        ),
    }


def run() -> dict[str, Any]:
    rows, medians = build_rows()
    worlds = sorted({r["cew_world"] for r in rows})
    fidelity = {}
    for w in worlds:
        if w == "unsatisfied":
            # residual fidelity: not a winning world — check MUST NOT positive claim
            uns = [r for r in rows if r["cew_world"] == "unsatisfied"]
            # no positive match in any strategy world
            no_pos = 0
            for r in uns:
                tr = r["trace"] or {}
                if not any((tr.get(x) or {}).get("match") for x in STRATEGY_POS):
                    no_pos += 1
            fidelity[w] = {
                "world": w,
                "n": len(uns),
                "goal": WORLD_INTENT.get("unsatisfied", {}).get("goal")
                or "残余。勝ち筋主張をしない。",
                "semantic_fidelity": no_pos / len(uns) if uns else None,
                "fidelity_grade": "HIGH" if uns and no_pos == len(uns) else "MED",
                "residual_no_positive_match_rate": no_pos / len(uns) if uns else None,
                "contract_match_clear_rate": None,
                "required_signal_direction_rate": None,
                "anti_forbidden_high_rate": None,
                "concept_means": {
                    k: _mean([r["concepts"][k] for r in uns if r["concepts"].get(k) is not None])
                    for k in CONCEPT_KEYS
                },
            }
            continue
        fidelity[w] = fidelity_positive(rows, w, medians)

    # patch unsatisfied goal in WORLD_INTENT usage
    sep = world_separation(rows, fidelity)
    nm = near_miss_fidelity(rows, fidelity, medians)
    ex = explainability_fidelity(rows, fidelity)

    # overall synthesis
    pos_f = [fidelity[w]["semantic_fidelity"] for w in fidelity if w != "unsatisfied" and fidelity[w].get("semantic_fidelity") is not None]
    report = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "purpose": "World Semantic Fidelity (思想忠実度) — not Completeness / Hit / ROI",
        "adr": ["ADR-009", "ADR-010", "V103"],
        "n_races": len(rows),
        "medians_ref": medians,
        "world_fidelity": fidelity,
        "separation": sep,
        "near_miss_fidelity": nm,
        "explainability_fidelity": ex,
        "synthesis": {
            "mean_positive_world_fidelity": _mean(pos_f),
            "unsatisfied_residual_fidelity": fidelity.get("unsatisfied", {}).get("semantic_fidelity"),
            "near_miss_fidelity": nm.get("overall_near_miss_fidelity"),
            "explainability_fidelity": ex.get("explainability_fidelity_rate"),
            "mean_pairwise_separation_cosine": sep.get("mean_pairwise_cosine"),
            "verdict": None,
            "reason": None,
        },
    }
    # verdict
    mp = report["synthesis"]["mean_positive_world_fidelity"] or 0
    nmf = report["synthesis"]["near_miss_fidelity"] or 0
    ef = report["synthesis"]["explainability_fidelity"] or 0
    if mp >= 0.75 and nmf >= 0.75 and ef >= 0.85:
        verdict = "FIDELITY_ACCEPTABLE"
        reason = "Positive World / Near Miss / Explainability fidelity が概ね設計思想に沿う（Shadow）。"
    elif mp >= 0.6 and ef >= 0.7:
        verdict = "FIDELITY_PARTIAL"
        reason = "一部 World または Near Miss で思想とのズレ。Completeness ではなく Fidelity 課題。"
    else:
        verdict = "FIDELITY_WEAK"
        reason = "Contract 出力が設計思想を十分に表現できていない（観測）。定義変更は本フェーズ禁止。"
    report["synthesis"]["verdict"] = verdict
    report["synthesis"]["reason"] = reason
    return report


def write_docs(report: dict[str, Any]) -> dict[str, str]:
    docs = ROOT / "docs/research"
    docs.mkdir(parents=True, exist_ok=True)
    jpath = docs / "_v104-world-semantic-validation.json"
    jpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def fmt(x: Any) -> str:
        if x is None:
            return "—"
        if isinstance(x, float):
            return f"{x:.4f}"
        return str(x)

    syn = report["synthesis"]

    main = [
        "# Version104 — World Semantic Validation",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**n_races:** {report['n_races']}  ",
        "**Mode:** Shadow Observation · **実装禁止**  ",
        "**評価:** Semantic Fidelity（思想忠実度）— Completeness / Hit / ROI ではない",
        "",
        "## Verdict",
        "",
        f"**`{syn['verdict']}`**",
        "",
        syn["reason"],
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| mean positive World fidelity | {fmt(syn.get('mean_positive_world_fidelity'))} |",
        f"| unsatisfied residual fidelity | {fmt(syn.get('unsatisfied_residual_fidelity'))} |",
        f"| Near Miss fidelity | {fmt(syn.get('near_miss_fidelity'))} |",
        f"| Explainability fidelity | {fmt(syn.get('explainability_fidelity'))} |",
        f"| mean pairwise concept cosine | {fmt(syn.get('mean_pairwise_separation_cosine'))} |",
        "",
        "## 方法（要約）",
        "",
        "1. V43 Required/Forbidden 方向 × コーパス中央値で信号整合を観測",
        "2. CEW 正例で must∧¬exclude∧match の契約整合を観測",
        "3. Near Miss は must∧exclude + affinity=1 + 正例プロファイル近接",
        "4. Explainability は Affinity/Exclusion/Trace（EC proxy）のみで所属説明可能か",
        "",
        "定義・Logic は変更しない。",
        "",
        "## 関連",
        "",
        "- `v104-world-fidelity-report.md`",
        "- `v104-world-separation-report.md`",
        "- `v104-governance.md`",
        "",
    ]
    p_main = docs / "v104-world-semantic-validation.md"
    p_main.write_text("\n".join(main), encoding="utf-8")

    fid = [
        "# Version104 — World Fidelity Report",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "| World | n | Fidelity | Grade | contract_clear | signal_dir | anti_forbidden |",
        "|---|---:|---:|---|---:|---:|---:|",
    ]
    for w, rec in sorted(report["world_fidelity"].items(), key=lambda x: (-(x[1].get("n") or 0), x[0])):
        fid.append(
            f"| `{w}` | {rec.get('n', 0)} | {fmt(rec.get('semantic_fidelity'))} | "
            f"**{rec.get('fidelity_grade', '—')}** | {fmt(rec.get('contract_match_clear_rate'))} | "
            f"{fmt(rec.get('required_signal_direction_rate'))} | {fmt(rec.get('anti_forbidden_high_rate'))} |"
        )
    fid += ["", "## Goals（V43）", ""]
    for w, rec in report["world_fidelity"].items():
        fid += [f"### `{w}`", "", rec.get("goal") or "", ""]
    # Near miss section
    nm = report["near_miss_fidelity"]
    fid += [
        "## Near Miss Fidelity",
        "",
        f"- n={nm.get('n_near_miss')} overall={fmt(nm.get('overall_near_miss_fidelity'))}",
        "",
        "| near_world | n | struct | affinity | profile | mean fidelity | intent_dir |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for nw, s in (nm.get("by_near_world") or {}).items():
        fid.append(
            f"| `{nw}` | {s['n']} | {fmt(s.get('struct_ok_rate'))} | {fmt(s.get('affinity_ok_rate'))} | "
            f"{fmt(s.get('profile_aligned_rate'))} | {fmt(s.get('mean_fidelity'))} | "
            f"{fmt(s.get('mean_intent_direction'))} |"
        )
    fid += [
        "",
        "## Explainability Fidelity",
        "",
        f"- rate: **{fmt(report['explainability_fidelity'].get('explainability_fidelity_rate'))}**",
        "",
        report["explainability_fidelity"].get("definition") or "",
        "",
    ]
    p_fid = docs / "v104-world-fidelity-report.md"
    p_fid.write_text("\n".join(fid), encoding="utf-8")

    sep = report["separation"]
    sep_md = [
        "# Version104 — World Separation Report",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        f"mean pairwise cosine: **{fmt(sep.get('mean_pairwise_cosine'))}**",
        "",
        sep.get("separation_note") or "",
        "",
        "## Pairwise concept-profile cosine",
        "",
        "| A | B | cosine | separated(<0.98) |",
        "|---|---|---:|---|",
    ]
    for p in sep.get("pairwise_cosine") or []:
        sep_md.append(
            f"| `{p['a']}` | `{p['b']}` | {fmt(p.get('cosine'))} | {p.get('separated')} |"
        )
    sep_md += [
        "",
        "## vs unsatisfied residual",
        "",
        "| World | cosine to unsatisfied mean |",
        "|---|---:|",
    ]
    for w, c in (sep.get("vs_unsatisfied_cosine") or {}).items():
        sep_md.append(f"| `{w}` | {fmt(c)} |")
    sep_md.append("")
    p_sep = docs / "v104-world-separation-report.md"
    p_sep.write_text("\n".join(sep_md), encoding="utf-8")

    gov = [
        "# Version104 — Governance",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | World Semantic Validation（Fidelity） |",
        "| Implementation Required | **No** |",
        "| Deployment Required | No |",
        f"| Verdict | `{syn['verdict']}` |",
        "| Prediction/Trigger/World/Contract/Decision | **No change** |",
        "| KPI | Semantic Fidelity only |",
        "| Excluded | Completeness再定義 / Hit / ROI / Calibration / Decision |",
        "| Risk | Low |",
        "| Expected Next Action | Fidelity LOW World は設計↔Trace 差分の文書化のみ。定義変更は別ゲート |",
        "",
        "## 成果物",
        "",
        "| 成果物 | Path |",
        "|---|---|",
        "| Validation | `v104-world-semantic-validation.md` |",
        "| Fidelity | `v104-world-fidelity-report.md` |",
        "| Separation | `v104-world-separation-report.md` |",
        "| Governance | `v104-governance.md` |",
        "",
    ]
    p_gov = docs / "v104-governance.md"
    p_gov.write_text("\n".join(gov), encoding="utf-8")

    return {
        "json": str(jpath),
        "validation": str(p_main),
        "fidelity": str(p_fid),
        "separation": str(p_sep),
        "gov": str(p_gov),
    }


def main() -> None:
    report = run()
    paths = write_docs(report)
    out = {
        "n": report["n_races"],
        "synthesis": report["synthesis"],
        "world_grades": {
            w: {"n": r.get("n"), "fidelity": r.get("semantic_fidelity"), "grade": r.get("fidelity_grade")}
            for w, r in report["world_fidelity"].items()
        },
        "near_miss": {
            "overall": report["near_miss_fidelity"].get("overall_near_miss_fidelity"),
            "by": {
                k: v.get("mean_fidelity")
                for k, v in (report["near_miss_fidelity"].get("by_near_world") or {}).items()
            },
        },
        "paths": paths,
    }
    text = json.dumps(out, ensure_ascii=True, indent=2)
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
