# -*- coding: utf-8 -*-
"""Version64 — World Classification Validation (research only).

Validates Shadow World vs V43/V44 design Ground Truth on 285R.
No PE / Prediction / Trigger / Signal / Threshold / World Logic / Production mutation.
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
# Priority for semantic GT ties (specificity / V44 primary order, mixed last)
GT_PRIORITY = (
    "bug_world",
    "midhole_world",
    "rank7_world",
    "core_world",
    "midupper_world",
    "mixed_world",
)


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


def semantic_gt_scores(
    wr: int,
    concepts: dict[str, float | None],
    thr: dict[str, float],
) -> dict[str, float]:
    """V43 Expected Characteristics → observable scores (not Trigger Logic Form).

    Mapping (documented in validation md):
    - core: large top_gap + winner in ability top band (rank<=3)
    - midupper: winner mid-upper (2..6), not extreme low-gap chaos path
    - midhole: winner mid band (5..10) + mid_eval_band_open high
    - rank7: small top_gap + winner 7..10
    - bug: winner deep (>=11)
    - mixed: two or more primary semantic fits (>=0.5)
    """
    tg = _f(concepts.get("top_gap"))
    mid = _f(concepts.get("mid_eval_band_open"))
    tg_hi = thr.get("top_gap") is not None and tg is not None and tg >= thr["top_gap"]
    tg_lo = thr.get("top_gap") is not None and tg is not None and tg <= thr["top_gap"]
    mid_hi = thr.get("mid_eval_band_open") is not None and mid is not None and mid >= thr["mid_eval_band_open"]

    scores = {
        "core_world": 0.0,
        "midupper_world": 0.0,
        "midhole_world": 0.0,
        "rank7_world": 0.0,
        "bug_world": 0.0,
        "mixed_world": 0.0,
    }
    # core
    if tg_hi and wr <= 3:
        scores["core_world"] = 1.0
    elif tg_hi and wr <= 5:
        scores["core_world"] = 0.5
    # midupper
    if 2 <= wr <= 6 and not tg_lo:
        scores["midupper_world"] = 1.0 if not tg_hi else 0.5
    elif 2 <= wr <= 6:
        scores["midupper_world"] = 0.5
    # midhole
    if 5 <= wr <= 10 and mid_hi:
        scores["midhole_world"] = 1.0
    elif 5 <= wr <= 10:
        scores["midhole_world"] = 0.5
    # rank7
    if tg_lo and 7 <= wr <= 10:
        scores["rank7_world"] = 1.0
    elif tg_lo and 6 <= wr <= 11:
        scores["rank7_world"] = 0.5
    elif 7 <= wr <= 10:
        scores["rank7_world"] = 0.5
    # bug
    if wr >= 11:
        scores["bug_world"] = 1.0
    elif wr >= 9:
        scores["bug_world"] = 0.5

    primary_strong = [
        w
        for w in ("core_world", "midupper_world", "midhole_world", "rank7_world", "bug_world")
        if scores[w] >= 1.0
    ]
    primary_fits = [
        w
        for w in ("core_world", "midupper_world", "midhole_world", "rank7_world", "bug_world")
        if scores[w] >= 0.5
    ]
    # V43 mixed = 複数勝ち筋が同時に妥当（弱い二重適合では mixed にしない）
    if len(primary_strong) >= 2:
        scores["mixed_world"] = 1.0
    elif len(primary_fits) >= 3:
        scores["mixed_world"] = 0.5
    return scores


def pick_gt_primary(scores: dict[str, float]) -> str:
    # Prefer non-mixed single strong winner first
    strong = {
        w: s
        for w, s in scores.items()
        if w != "mixed_world" and s >= 1.0
    }
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
    cands = [w for w, s in scores.items() if s == best and w != "mixed_world"]
    if not cands:
        cands = [w for w, s in scores.items() if s == best]
    if len(cands) == 1:
        return cands[0]
    for w in GT_PRIORITY:
        if w in cands:
            return w
    return cands[0]


def classify_root_cause(row: dict[str, Any], gt: str, pred: str) -> str:
    """Map mismatch to Signal / Trigger / Exclusion / Must不足 / Data不足."""
    if gt == pred:
        return "ok"
    restored = row.get("restored_ok")
    if restored is False:
        return "Data不足"
    trace = row.get("decision_trace") or {}
    # Pred unsatisfied but GT has a world
    if pred == "unsatisfied" and gt != "unsatisfied":
        # Check if GT world had must fail or exclude in shadow trace
        t = trace.get(gt) if isinstance(trace.get(gt), dict) else None
        if t:
            if t.get("exclude") is True and t.get("must") is True:
                return "Exclusion"
            if t.get("must") is not True:
                gaps = t.get("must_gaps") or []
                if gaps:
                    return "Must不足"
                return "Signal"
        # near worlds from match_set empty
        return "Must不足"
    # Pred has world but GT different
    if pred != "unsatisfied" and gt != "unsatisfied" and pred != gt:
        tpred = trace.get(pred) if isinstance(trace.get(pred), dict) else {}
        tgt = trace.get(gt) if isinstance(trace.get(gt), dict) else {}
        if tgt.get("exclude") is True:
            return "Exclusion"
        if tgt.get("must") is not True:
            return "Must不足"
        # Legacy vs design path — if legacy equals pred somehow N/A; shadow wrong target
        if row.get("legacy_world") == gt and pred != gt:
            return "Trigger"
        if tpred.get("match") is True and tgt.get("match") is not True:
            return "Signal"
        return "Trigger"
    # Pred has world, GT unsatisfied
    if pred != "unsatisfied" and gt == "unsatisfied":
        return "Trigger"
    return "Signal"


def prf(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    out = {}
    for lab in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lab and p == lab)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p != lab)
        prec = tp / (tp + fp) if (tp + fp) else None
        rec = tp / (tp + fn) if (tp + fn) else None
        out[lab] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": tp + fn,
            "precision": prec,
            "recall": rec,
        }
    return out


def confusion(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, dict[str, int]]:
    mat = {a: {b: 0 for b in labels} for a in labels}
    for t, p in zip(y_true, y_pred):
        tt = t if t in mat else None
        pp = p if p in labels else None
        if tt is None or pp is None:
            continue
        mat[tt][pp] += 1
    return mat


def main() -> None:
    corp = {
        r["race_id"]: r
        for r in json.loads(
            (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(
                encoding="utf-8"
            )
        )["races"]
    }
    dual = [
        json.loads(l)
        for l in (ROOT / "docs/implementation/w-s1-dual-eval-rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if l.strip()
    ]

    # Build concept rows for medians
    concept_rows = []
    enriched = []
    for d in dual:
        rid = d["race_id"]
        race = corp.get(rid)
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
        enriched.append({**d, "concepts": concepts, "wr": wr})

    thr = batch_medians(concept_rows, ["top_gap", "mid_eval_band_open", "ability_separation", "top_monopoly"])

    y_gt = []
    y_shadow = []
    y_legacy = []
    rows_out = []
    wa_shadow = Counter()
    wa_gt = Counter()
    wa_legacy = Counter()

    for d in enriched:
        scores = semantic_gt_scores(int(d["wr"]), d["concepts"], thr)
        gt = pick_gt_primary(scores)
        shadow = d.get("v44_world") or "unsatisfied"
        legacy = d.get("legacy_world") or "unsatisfied"
        y_gt.append(gt)
        y_shadow.append(shadow)
        y_legacy.append(legacy)

        wa_s = winner_alignment(shadow, int(d["wr"]))
        wa_g = winner_alignment(gt, int(d["wr"]))
        wa_l = winner_alignment(legacy, int(d["wr"]))
        wa_shadow[wa_s] += 1
        wa_gt[wa_g] += 1
        wa_legacy[wa_l] += 1

        cause = classify_root_cause(d, gt, shadow)
        rows_out.append(
            {
                "race_id": d["race_id"],
                "gt_semantic": gt,
                "gt_scores": scores,
                "shadow": shadow,
                "legacy": legacy,
                "winner_model_rank": d["wr"],
                "match_shadow_gt": shadow == gt,
                "wa_shadow": wa_s,
                "wa_gt": wa_g,
                "wa_legacy": wa_l,
                "root_cause": cause,
                "restored_ok": d.get("restored_ok"),
                "positive_match": d.get("positive_match"),
                "unsatisfied": d.get("unsatisfied"),
                "match_set": d.get("match_set"),
            }
        )

    labels = list(WORLDS) + ["unsatisfied"]
    n = len(y_gt)
    acc_shadow = sum(1 for a, b in zip(y_gt, y_shadow) if a == b) / n
    acc_legacy = sum(1 for a, b in zip(y_gt, y_legacy) if a == b) / n

    # Contract self-check: shadow in match_set or unsatisfied with empty
    self_ok = 0
    for d, r in zip(enriched, rows_out):
        ms = d.get("match_set") or []
        sh = r["shadow"]
        if sh == "unsatisfied":
            self_ok += int(len(ms) == 0)
        else:
            self_ok += int(sh in ms or sh == "mixed_world")

    pr_shadow = prf(y_gt, y_shadow, labels)
    pr_legacy = prf(y_gt, y_legacy, labels)
    cm_shadow = confusion(y_gt, y_shadow, labels)
    cm_legacy = confusion(y_gt, y_legacy, labels)

    cause_counts = Counter(r["root_cause"] for r in rows_out if r["root_cause"] != "ok")
    cause_by_pair = Counter(
        (r["gt_semantic"], r["shadow"], r["root_cause"])
        for r in rows_out
        if r["root_cause"] != "ok"
    )

    # Design share vs observed
    design_share = {
        "core_world": 0.30,
        "midupper_world": 0.35,
        "rank7_world": 0.15,
        "mixed_world": 0.10,
        "bug_world": 0.05,
        "midhole_world": 0.05,
    }
    shadow_dist = Counter(y_shadow)
    gt_dist = Counter(y_gt)
    legacy_dist = Counter(y_legacy)

    # Macro precision/recall (exclude labels with support 0 for recall; precision if pred 0)
    def macro(pr):
        precs = [v["precision"] for v in pr.values() if v["precision"] is not None and (v["tp"] + v["fp"]) > 0]
        recs = [v["recall"] for v in pr.values() if v["recall"] is not None and v["support"] > 0]
        return {
            "macro_precision": sum(precs) / len(precs) if precs else None,
            "macro_recall": sum(recs) / len(recs) if recs else None,
        }

    # Governance grade
    # A: high accuracy + WA aligned rate for shadow decent + design-like
    wa_aligned_rate = wa_shadow.get("aligned", 0) / n
    # C if accuracy low or unsatisfied dominates shadow badly vs design
    unsat_shadow = shadow_dist.get("unsatisfied", 0) / n
    if acc_shadow >= 0.60 and wa_aligned_rate >= 0.35 and unsat_shadow <= 0.40:
        grade = "A"
        reason = f"acc={acc_shadow:.1%}, WA_aligned={wa_aligned_rate:.1%}, unsat={unsat_shadow:.1%}"
    elif acc_shadow >= 0.35 or wa_aligned_rate >= 0.25:
        grade = "B"
        reason = f"partial: acc={acc_shadow:.1%}, WA_aligned={wa_aligned_rate:.1%}, unsat={unsat_shadow:.1%}"
    else:
        grade = "C"
        reason = f"acc={acc_shadow:.1%}, WA_aligned={wa_aligned_rate:.1%}, unsat={unsat_shadow:.1%} — design intent not met"

    # Force C if shadow mostly unsatisfied (cannot be design-faithful classification)
    if unsat_shadow >= 0.50:
        grade = "C"
        reason = f"Shadow unsatisfied={unsat_shadow:.1%} (>=50%); Positive Match principle not achieved on 285R. acc_vs_semantic_GT={acc_shadow:.1%}"

    out = {
        "schema": "v64-world-classification-validation/1.0",
        "n": n,
        "gt_definition": {
            "name": "V43_Semantic_ExpectedCharacteristics_Oracle",
            "authority": ["V43 World Semantic Contract §Expected Characteristics", "V44 polarity vocabulary (median)", "V45 gap context"],
            "note": "Independent of V44 Logic Form executor output; uses race concepts + winner_model_rank bands only.",
            "thresholds": thr,
            "not_used_as_gt": "V44 shadow label itself (would be tautological)",
        },
        "predicted": {
            "primary": "v44_shadow_world",
            "contrast": "legacy_production_world",
        },
        "accuracy": {
            "shadow_vs_gt": acc_shadow,
            "legacy_vs_gt": acc_legacy,
            "shadow_contract_self_consistency": self_ok / n,
        },
        "distributions": {
            "design_share": design_share,
            "gt_semantic": dict(gt_dist),
            "shadow": dict(shadow_dist),
            "legacy": dict(legacy_dist),
        },
        "precision_recall": {
            "shadow": pr_shadow,
            "legacy": pr_legacy,
            "shadow_macro": macro(pr_shadow),
            "legacy_macro": macro(pr_legacy),
        },
        "confusion_matrix": {
            "shadow_rows_gt_cols_pred": cm_shadow,
            "legacy_rows_gt_cols_pred": cm_legacy,
        },
        "winner_alignment": {
            "shadow": dict(wa_shadow),
            "gt_semantic": dict(wa_gt),
            "legacy": dict(wa_legacy),
            "shadow_aligned_rate": wa_aligned_rate,
            "gt_aligned_rate": wa_gt.get("aligned", 0) / n,
            "legacy_aligned_rate": wa_legacy.get("aligned", 0) / n,
        },
        "root_cause": {
            "counts": dict(cause_counts),
            "top_pairs": [
                {"gt": a, "pred": b, "cause": c, "n": n_}
                for (a, b, c), n_ in cause_by_pair.most_common(30)
            ],
        },
        "governance": {"grade": grade, "reason": reason},
        "rows": rows_out,
    }

    path = ROOT / "docs/research/_v64-classification-validation.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("n", n)
    print("acc shadow", round(acc_shadow, 4), "legacy", round(acc_legacy, 4))
    print("self", round(self_ok / n, 4))
    print("dist shadow", dict(shadow_dist))
    print("dist gt", dict(gt_dist))
    print("WA shadow", dict(wa_shadow), "rate", round(wa_aligned_rate, 4))
    print("macro", macro(pr_shadow))
    print("causes", dict(cause_counts))
    print("grade", grade, reason)
    print("wrote", path)


if __name__ == "__main__":
    main()
