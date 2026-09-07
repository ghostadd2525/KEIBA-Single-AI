# -*- coding: utf-8 -*-
"""Version65 — World Intent Validation (research only).

Design-intent GT (V42–V45) vs AI-assigned World on 285R.
Primary AI label = Production Legacy world.
Shadow V44 reported as contrast only.
No PE / Strategy / Trigger / Signal / World / Threshold / Production mutation.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
WORLDS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "mixed_world",
    "bug_world",
)
GT_PRIORITY = (
    "bug_world",
    "midhole_world",
    "rank7_world",
    "core_world",
    "midupper_world",
    "mixed_world",
)
LABELS = list(WORLDS) + ["unsatisfied"]


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        x = float(v)
        if math.isnan(x):
            return None
        return x
    except (TypeError, ValueError):
        return None


def ranking_concepts(runners: list[dict[str, Any]]) -> dict[str, float | None]:
    probs = [_f(u.get("win_prob")) for u in runners]
    probs = [p for p in probs if p is not None]
    if len(probs) < 2:
        return {
            "top_gap": None,
            "ability_separation": None,
            "upper_ability_band": None,
            "mid_eval_band_open": None,
            "top_monopoly": None,
            "ability_subordinate": None,
        }
    probs = sorted(probs, reverse=True)
    s = sum(probs) or 1.0
    top_gap = probs[0] - probs[1]
    median = probs[len(probs) // 2]
    return {
        "top_gap": top_gap,
        "ability_separation": probs[0] - median,
        "upper_ability_band": sum(probs[:3]) / s,
        "mid_eval_band_open": (sum(probs[3:10]) / s) if len(probs) > 3 else 0.0,
        "top_monopoly": probs[0] / s,
        "ability_subordinate": 1.0 - min(1.0, top_gap * 5.0),
    }


def batch_medians(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        for k in keys:
            v = _f(r.get(k))
            if v is not None:
                buckets[k].append(v)
    out = {}
    for k, vals in buckets.items():
        vals = sorted(vals)
        out[k] = float(vals[len(vals) // 2])
    return out


def intent_scores(wr: int, concepts: dict[str, float | None], thr: dict[str, float]) -> dict[str, float]:
    """V42/V43 Expected Characteristics → observable intent scores.

    Authority: V42 design 正本 (ability-resolution core, etc.) + V43 Expected Characteristics
    + V44 polarity vocabulary (high/low via batch median). Not V44 Logic Form output.
    """
    tg = _f(concepts.get("top_gap"))
    mid = _f(concepts.get("mid_eval_band_open"))
    sep = _f(concepts.get("ability_separation"))
    tg_hi = thr.get("top_gap") is not None and tg is not None and tg >= thr["top_gap"]
    tg_lo = thr.get("top_gap") is not None and tg is not None and tg <= thr["top_gap"]
    mid_hi = thr.get("mid_eval_band_open") is not None and mid is not None and mid >= thr["mid_eval_band_open"]
    sep_hi = thr.get("ability_separation") is not None and sep is not None and sep >= thr["ability_separation"]

    scores = {w: 0.0 for w in WORLDS}
    # core — V42/V43: 能力決着・TopGap大・上位が勝ち切る
    if tg_hi and sep_hi and wr <= 3:
        scores["core_world"] = 1.0
    elif tg_hi and wr <= 3:
        scores["core_world"] = 0.75
    elif tg_hi and wr <= 5:
        scores["core_world"] = 0.5
    # midupper — V43: 上位能力帯、core/rank7の中間
    if 2 <= wr <= 6 and not tg_lo:
        scores["midupper_world"] = 1.0 if not (tg_hi and wr <= 2) else 0.5
    elif 2 <= wr <= 6:
        scores["midupper_world"] = 0.5
    # midhole — V43: 中位帯が開く
    if 5 <= wr <= 10 and mid_hi:
        scores["midhole_world"] = 1.0
    elif 5 <= wr <= 10:
        scores["midhole_world"] = 0.5
    # rank7 — V42/V43: 低TopGap・混戦・能力どおりになりにくい
    if tg_lo and 7 <= wr <= 10:
        scores["rank7_world"] = 1.0
    elif tg_lo and 6 <= wr <= 11:
        scores["rank7_world"] = 0.5
    elif 7 <= wr <= 10:
        scores["rank7_world"] = 0.5
    # bug — V43: 既存枠に乗らない深穴
    if wr >= 11:
        scores["bug_world"] = 1.0
    elif wr >= 9:
        scores["bug_world"] = 0.5
    # mixed — V43: 強適合が2つ以上同時
    strong = [w for w in ("core_world", "midupper_world", "midhole_world", "rank7_world", "bug_world") if scores[w] >= 1.0]
    weak = [w for w in ("core_world", "midupper_world", "midhole_world", "rank7_world", "bug_world") if scores[w] >= 0.5]
    if len(strong) >= 2:
        scores["mixed_world"] = 1.0
    elif len(weak) >= 3:
        scores["mixed_world"] = 0.5
    return scores


def pick_intent_gt(scores: dict[str, float]) -> str:
    strong = {w: s for w, s in scores.items() if w != "mixed_world" and s >= 1.0}
    if len(strong) == 1:
        return next(iter(strong))
    if len(strong) >= 2 and scores.get("mixed_world", 0) >= 1.0:
        return "mixed_world"
    if len(strong) >= 2:
        for w in GT_PRIORITY:
            if w in strong:
                return w
    best = max(scores.values())
    if best < 0.5:
        return "unsatisfied"
    cands = [w for w, s in scores.items() if s == best and w != "mixed_world"] or [
        w for w, s in scores.items() if s == best
    ]
    if len(cands) == 1:
        return cands[0]
    for w in GT_PRIORITY:
        if w in cands:
            return w
    return cands[0]


def root_cause_ai(gt: str, ai: str, row: dict[str, Any]) -> str:
    """Root cause for Intent-GT vs Production AI (Legacy) mismatch."""
    if gt == ai:
        return "ok"
    if row.get("restored_ok") is False:
        return "Data"
    trace = row.get("decision_trace") or {}
    tgt = trace.get(gt) if isinstance(trace.get(gt), dict) else {}
    # V42/V45: Legacy core is often DEFAULT residual
    if ai == "core_world" and gt != "core_world":
        return "Trigger"
    if ai == "midupper_world" and gt in ("rank7_world", "midhole_world", "core_world", "bug_world"):
        # V45: difficulty-only / sfp paths — Trigger role violation
        return "Trigger"
    if ai == "mixed_world" and gt != "mixed_world":
        # V45: phase-alone mixed
        return "Trigger"
    if tgt.get("exclude") is True:
        return "Exclusion"
    if gt != "unsatisfied" and tgt.get("must") is not True:
        return "Must"
    if gt == "bug_world":
        return "Must"  # exception_flag never supplied
    if gt == "rank7_world" and ai != "rank7_world":
        # Legacy never assigns rank7 on this corpus
        return "Trigger"
    return "Trigger"


def root_cause_shadow(gt: str, shadow: str, row: dict[str, Any]) -> str:
    if gt == shadow:
        return "ok"
    if row.get("restored_ok") is False:
        return "Data"
    trace = row.get("decision_trace") or {}
    tgt = trace.get(gt) if isinstance(trace.get(gt), dict) else {}
    if shadow == "unsatisfied" and gt != "unsatisfied":
        if tgt.get("exclude") is True and tgt.get("must") is True:
            return "Exclusion"
        if tgt.get("must") is not True:
            return "Must"
        return "Must"
    if shadow != "unsatisfied" and gt != "unsatisfied" and shadow != gt:
        if tgt.get("exclude") is True:
            return "Exclusion"
        if tgt.get("must") is not True:
            return "Must"
        return "Trigger"
    if shadow != "unsatisfied" and gt == "unsatisfied":
        return "Trigger"
    return "Signal"


def prf(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    out = {}
    for lab in LABELS:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lab and p == lab)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p != lab)
        out[lab] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": tp + fn,
            "precision": (tp / (tp + fp)) if (tp + fp) else None,
            "recall": (tp / (tp + fn)) if (tp + fn) else None,
        }
    return out


def confusion(y_true: list[str], y_pred: list[str]) -> dict[str, dict[str, int]]:
    mat = {a: {b: 0 for b in LABELS} for a in LABELS}
    for t, p in zip(y_true, y_pred):
        if t in mat and p in mat[t]:
            mat[t][p] += 1
    return mat


def macro(pr: dict[str, Any]) -> dict[str, float | None]:
    precs = [v["precision"] for v in pr.values() if v["precision"] is not None and (v["tp"] + v["fp"]) > 0]
    recs = [v["recall"] for v in pr.values() if v["recall"] is not None and v["support"] > 0]
    return {
        "macro_precision": sum(precs) / len(precs) if precs else None,
        "macro_recall": sum(recs) / len(recs) if recs else None,
    }


def main() -> None:
    corp = {
        r["race_id"]: r
        for r in json.loads(
            (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
        )["races"]
    }
    dual = [
        json.loads(l)
        for l in (ROOT / "docs/implementation/w-s1-dual-eval-rows.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]

    concept_rows = []
    enriched = []
    for d in dual:
        race = corp.get(d["race_id"])
        if not race:
            continue
        concepts = ranking_concepts(race.get("runners") or [])
        wr = d.get("winner_model_rank")
        if wr is None:
            wid = str(race.get("winner_id") or "")
            for u in race.get("runners") or []:
                if str(u.get("horse_id")) == wid:
                    wr = int(u.get("model_rank") or 999)
                    break
        concept_rows.append(concepts)
        enriched.append({**d, "concepts": concepts, "wr": int(wr)})

    thr = batch_medians(
        concept_rows, ["top_gap", "mid_eval_band_open", "ability_separation", "top_monopoly"]
    )

    y_gt, y_ai, y_shadow = [], [], []
    rows_out = []
    for d in enriched:
        scores = intent_scores(d["wr"], d["concepts"], thr)
        gt = pick_intent_gt(scores)
        ai = d.get("legacy_world") or "unsatisfied"
        shadow = d.get("v44_world") or "unsatisfied"
        y_gt.append(gt)
        y_ai.append(ai)
        y_shadow.append(shadow)
        rows_out.append(
            {
                "race_id": d["race_id"],
                "intent_gt": gt,
                "intent_scores": scores,
                "ai_world": ai,
                "shadow_world": shadow,
                "winner_model_rank": d["wr"],
                "agree_ai": gt == ai,
                "agree_shadow": gt == shadow,
                "root_cause_ai": root_cause_ai(gt, ai, d),
                "root_cause_shadow": root_cause_shadow(gt, shadow, d),
                "restored_ok": d.get("restored_ok"),
                "concepts": d["concepts"],
            }
        )

    n = len(y_gt)
    acc_ai = sum(1 for a, b in zip(y_gt, y_ai) if a == b) / n
    acc_shadow = sum(1 for a, b in zip(y_gt, y_shadow) if a == b) / n
    pr_ai = prf(y_gt, y_ai)
    pr_shadow = prf(y_gt, y_shadow)
    cm_ai = confusion(y_gt, y_ai)
    cm_shadow = confusion(y_gt, y_shadow)
    cause_ai = Counter(r["root_cause_ai"] for r in rows_out if r["root_cause_ai"] != "ok")
    cause_shadow = Counter(r["root_cause_shadow"] for r in rows_out if r["root_cause_shadow"] != "ok")
    pairs_ai = Counter((r["intent_gt"], r["ai_world"], r["root_cause_ai"]) for r in rows_out if r["root_cause_ai"] != "ok")

    design_share = {
        "core_world": 0.30,
        "midupper_world": 0.35,
        "rank7_world": 0.15,
        "mixed_world": 0.10,
        "bug_world": 0.05,
        "midhole_world": 0.05,
    }
    gt_dist = Counter(y_gt)
    ai_dist = Counter(y_ai)
    shadow_dist = Counter(y_shadow)

    # Governance on primary AI (Legacy)
    if acc_ai >= 0.60:
        grade, reason = "A", f"AI(Legacy) vs Intent GT acc={acc_ai:.1%}"
    elif acc_ai >= 0.35:
        grade, reason = "B", f"partial divergence acc={acc_ai:.1%}"
    else:
        grade, reason = "C", f"AI(Legacy) vs Intent GT acc={acc_ai:.1%} — design intent not met"

    # V42 structural failure boost to C if core is DEFAULT-like mismatch dominant
    core_fp_as_default = sum(
        1 for r in rows_out if r["ai_world"] == "core_world" and r["intent_gt"] != "core_world"
    )
    if acc_ai < 0.50 and core_fp_as_default >= 40:
        grade = "C"
        reason += f"; Legacy core over-assignment vs intent n={core_fp_as_default} (V42 DEFAULT pattern)"

    out = {
        "schema": "v65-world-intent-validation/1.0",
        "n": n,
        "gt_definition": {
            "name": "Design_Intent_Oracle_V42_V43_V44_V45",
            "authorities": [
                "V42 world semantics / core-intent (ability resolution, not DEFAULT)",
                "V43 Expected Characteristics",
                "V44 polarity vocabulary (batch median high/low)",
                "V45 compliance gap context (not used as GT labels)",
            ],
            "thresholds_observational": thr,
            "ai_primary": "legacy_world (Production AI assignment)",
            "ai_contrast": "v44_world (Shadow Spec path)",
        },
        "agreement": {"ai_vs_intent": acc_ai, "shadow_vs_intent": acc_shadow},
        "distributions": {
            "design_share": design_share,
            "intent_gt": dict(gt_dist),
            "ai_legacy": dict(ai_dist),
            "shadow_v44": dict(shadow_dist),
        },
        "precision_recall": {"ai": pr_ai, "shadow": pr_shadow, "ai_macro": macro(pr_ai), "shadow_macro": macro(pr_shadow)},
        "confusion_matrix": {"ai_rows_gt_cols_pred": cm_ai, "shadow_rows_gt_cols_pred": cm_shadow},
        "root_cause": {
            "ai_counts": dict(cause_ai),
            "shadow_counts": dict(cause_shadow),
            "ai_top_pairs": [
                {"gt": a, "ai": b, "cause": c, "n": n_}
                for (a, b, c), n_ in pairs_ai.most_common(25)
            ],
        },
        "governance": {"grade": grade, "reason": reason, "primary_system": "Production_Legacy_AI"},
        "rows": rows_out,
    }
    path = ROOT / "docs/research/_v65-intent-validation.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("n", n)
    print("acc AI(Legacy)", round(acc_ai, 4), "Shadow", round(acc_shadow, 4))
    print("gt", dict(gt_dist))
    print("ai", dict(ai_dist))
    print("macro AI", macro(pr_ai))
    print("causes AI", dict(cause_ai))
    print("grade", grade, reason)
    print("wrote", path)


if __name__ == "__main__":
    main()
