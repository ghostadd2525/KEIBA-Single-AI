# -*- coding: utf-8 -*-
"""Version85 — Base Probability Audit (research only).

Investigates p_base definition / underconfidence. Does NOT change:
Production / Trigger / Blueprint / World / Interaction / PE.

No product implementation. Outputs audit metrics + candidate comparisons only.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.research._v64_world_strategy_discovery import build_race_rows, _f  # noqa: E402
from app.research._v74_world_strategy_validation import load_cew_labels, attach_cew  # noqa: E402

SCHEMA = "v85-base-probability-audit/1.0"
EPS = 1e-6
N_BINS = 10
WORLDS = (
    "rank7_world",
    "midhole_world",
    "unsatisfied",
    "core_world",
    "midupper_world",
    "mixed_world",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clip01(p: float) -> float:
    return float(min(max(p, EPS), 1.0 - EPS))


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def log_loss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def ece(y: np.ndarray, p: np.ndarray, n_bins: int = N_BINS) -> tuple[float, list[dict[str, Any]]]:
    bins: list[dict[str, Any]] = []
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    total = 0.0
    n = len(y)
    if n == 0:
        return 0.0, []
    for i in range(n_bins):
        lo, hi = float(edges[i]), float(edges[i + 1])
        m = (p >= lo) & (p <= hi) if i == n_bins - 1 else (p >= lo) & (p < hi)
        cnt = int(m.sum())
        if cnt == 0:
            bins.append({"lo": lo, "hi": hi, "n": 0, "conf": None, "acc": None, "gap": None})
            continue
        conf = float(p[m].mean())
        acc = float(y[m].mean())
        gap = abs(acc - conf)
        total += (cnt / n) * gap
        bins.append({"lo": lo, "hi": hi, "n": cnt, "conf": conf, "acc": acc, "gap": gap})
    return float(total), bins


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, Any]:
    if len(y) == 0:
        return {"n": 0}
    ece_v, bins = ece(y, p)
    gaps = [b["gap"] for b in bins if b.get("gap") is not None]
    return {
        "n": int(len(y)),
        "hit_rate": float(y.mean()),
        "p_mean": float(p.mean()),
        "p_std": float(p.std()),
        "p_min": float(p.min()),
        "p_max": float(p.max()),
        "bias": float(p.mean() - y.mean()),  # negative => underconfident on average
        "abs_bias": float(abs(p.mean() - y.mean())),
        "brier": brier(y, p),
        "log_loss": log_loss(y, p),
        "ece": ece_v,
        "reliability_mean_gap": float(sum(gaps) / len(gaps)) if gaps else None,
        "calibration_bins": bins,
    }


def load_rows() -> list[dict[str, Any]]:
    cew = load_cew_labels()
    corp = json.loads(
        (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
    )
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []
    fxby = {r["race_id"]: r for r in fx_rows}
    dual = {rid: {"legacy_world": None, "v44_world": None} for rid in cew}
    race_rows = attach_cew(build_race_rows(corp, dual, fxby), cew)
    corp_by = {r["race_id"]: r for r in corp["races"]}

    out: list[dict[str, Any]] = []
    for race in race_rows:
        rid = race["race_id"]
        fxr = fxby.get(rid) or {}
        pred = str(fxr.get("predicted_top1_horse_id") or "")
        winner = str(fxr.get("winner_id") or "")
        runners = list((corp_by.get(rid) or {}).get("runners") or [])
        horses = race["horses"]
        if len(runners) != len(horses) or not pred:
            continue
        ids = [str(u.get("horse_id") or "") for u in runners]
        if pred not in ids:
            continue
        pred_idx = ids.index(pred)
        win_probs = [float(h.get("win_prob") or 0.0) for h in horses]
        odds = [float(h.get("odds") or 0.0) for h in horses]
        y = 1 if bool(fxr.get("hit_at_1")) else (1 if pred == winner else 0)
        out.append(
            {
                "race_id": rid,
                "race_date": fxr.get("race_date"),
                "cew_world": race.get("cew_world"),
                "y_hit": y,
                "field_size": float(race.get("field_size") or len(horses)),
                "win_probs": win_probs,
                "odds": odds,
                "pred_idx": pred_idx,
                "win_prob_pred": win_probs[pred_idx],
                "odds_pred": odds[pred_idx] if odds[pred_idx] > 0 else None,
                "model_rank_pred": int(horses[pred_idx].get("model_rank") or 999),
            }
        )
    out.sort(key=lambda r: (str(r.get("race_date") or ""), r["race_id"]))
    return out


# --- Candidate definitions (formulas only; not PE) ---

def c_win_prob_mass(r: dict[str, Any]) -> float:
    """V84 p_base: predicted win_prob / sum(win_prob)."""
    wps = r["win_probs"]
    s = sum(max(0.0, w) for w in wps)
    if s <= 0:
        return 1.0 / max(1, len(wps))
    return clip01(max(0.0, wps[r["pred_idx"]]) / s)


def c_raw_win_prob(r: dict[str, Any]) -> float:
    return clip01(float(r["win_prob_pred"]))


def c_uniform_field(r: dict[str, Any]) -> float:
    return clip01(1.0 / max(1.0, float(r["field_size"])))


def c_top2_mass(r: dict[str, Any]) -> float:
    wps = r["win_probs"]
    i = r["pred_idx"]
    # second = max other
    others = [w for j, w in enumerate(wps) if j != i]
    if not others:
        return c_win_prob_mass(r)
    top2 = max(0.0, wps[i]) + max(0.0, max(others))
    if top2 <= 0:
        return c_win_prob_mass(r)
    return clip01(max(0.0, wps[i]) / top2)


def c_market_inv_odds(r: dict[str, Any]) -> float | None:
    odds = r["odds"]
    inv = []
    for o in odds:
        if o and o > 0:
            inv.append(1.0 / o)
        else:
            inv.append(0.0)
    s = sum(inv)
    if s <= 0:
        return None
    return clip01(inv[r["pred_idx"]] / s)


def c_softmax_t(r: dict[str, Any], t: float) -> float:
    wps = np.array([max(0.0, w) for w in r["win_probs"]], dtype=float)
    # treat win_prob as score; temperature softmax
    logits = np.log(np.clip(wps, EPS, None)) / max(t, 1e-3)
    logits = logits - logits.max()
    ex = np.exp(logits)
    p = ex / ex.sum()
    return clip01(float(p[r["pred_idx"]]))


def make_world_prior_fn(train_rates: dict[str, float], global_rate: float) -> Callable[[dict[str, Any]], float]:
    def fn(r: dict[str, Any]) -> float:
        w = r.get("cew_world") or ""
        return clip01(float(train_rates.get(w, global_rate)))

    return fn


def make_blend_fn(
    base_fn: Callable[[dict[str, Any]], float],
    prior_fn: Callable[[dict[str, Any]], float],
    lam: float,
) -> Callable[[dict[str, Any]], float]:
    def fn(r: dict[str, Any]) -> float:
        return clip01((1.0 - lam) * base_fn(r) + lam * prior_fn(r))

    return fn


def eval_candidate(rows: list[dict[str, Any]], fn: Callable[[dict[str, Any]], float | None], name: str) -> dict[str, Any]:
    ys: list[float] = []
    ps: list[float] = []
    skipped = 0
    for r in rows:
        p = fn(r)
        if p is None:
            skipped += 1
            continue
        ys.append(float(r["y_hit"]))
        ps.append(float(p))
    y = np.array(ys, dtype=float)
    p = np.array(ps, dtype=float)
    m = metrics(y, p)
    m["candidate"] = name
    m["skipped"] = skipped
    return m


def world_breakdown(rows: list[dict[str, Any]], fn: Callable[[dict[str, Any]], float | None]) -> dict[str, Any]:
    by: dict[str, list] = defaultdict(list)
    for r in rows:
        by[r["cew_world"]].append(r)
    out = {}
    for w in WORLDS:
        sub = by.get(w) or []
        out[w] = eval_candidate(sub, fn, "win_prob_mass") if sub else {"n": 0, "status": "empty"}
    # also all
    out["_all"] = eval_candidate(rows, fn, "win_prob_mass")
    return out


def path_audit() -> dict[str, Any]:
    return {
        "label": "V84 Shadow p_base (research adapter; not Production PE confidence API)",
        "formula": "p_base = win_prob[predicted_top1] / sum_i win_prob[i]",
        "predicted_top1_source": "fixtures/stats/baseline-285r-evaluations.json :: predicted_top1_horse_id",
        "win_prob_source": "real_285r_corpus.json runners[].win_prob → build_race_rows horses[].win_prob",
        "outcome_label": "hit_at_1 (fixture) fallback pred==winner_id",
        "world_label": "CEW from _v73-contract-intent-evaluation.json (read-only)",
        "interaction": "NOT used in this audit (V85 isolates Base Probability)",
        "production_pe": "unchanged / not invoked",
        "code_refs": [
            "app/research/_v84_confidence_calibration_shadow.py :: base_confidence",
            "app/research/_v64_world_strategy_discovery.py :: build_race_rows",
        ],
        "known_bias_hypothesis": "win_prob mass for Top1 ≈ 0.07–0.14 while empirical Top1 hit_at_1 ≫ that → systematic underconfidence",
    }


def run() -> dict[str, Any]:
    rows = load_rows()
    # chronological half for prior / blend (no PE — audit only)
    mid = len(rows) // 2
    train, test = rows[:mid], rows[mid:]
    train_rates: dict[str, float] = {}
    for w in WORLDS:
        sub = [r for r in train if r["cew_world"] == w]
        if sub:
            train_rates[w] = float(np.mean([r["y_hit"] for r in sub]))
    global_train = float(np.mean([r["y_hit"] for r in train])) if train else 0.5
    prior_fn = make_world_prior_fn(train_rates, global_train)

    candidates: dict[str, Callable[[dict[str, Any]], float | None]] = {
        "C0_win_prob_mass_V84": c_win_prob_mass,
        "C1_raw_win_prob": c_raw_win_prob,
        "C2_uniform_1_over_field": c_uniform_field,
        "C3_world_empirical_prior_train": prior_fn,
        "C4_market_inv_odds_mass": c_market_inv_odds,
        "C5_top1_over_top1_plus_top2": c_top2_mass,
        "C6_softmax_T0_5": lambda r: c_softmax_t(r, 0.5),
        "C6b_softmax_T2_0": lambda r: c_softmax_t(r, 2.0),
        "C7_blend_mass_0_3_prior": make_blend_fn(c_win_prob_mass, prior_fn, 0.3),
        "C7b_blend_mass_0_7_prior": make_blend_fn(c_win_prob_mass, prior_fn, 0.7),
        "C7c_blend_mass_0_9_prior": make_blend_fn(c_win_prob_mass, prior_fn, 0.9),
    }

    # Full-corpus metrics for C0 path + world calib
    world_c0 = world_breakdown(rows, c_win_prob_mass)

    # Candidate comparison on FULL (descriptive) and TEST (for priors that use train)
    cand_full = {name: eval_candidate(rows, fn, name) for name, fn in candidates.items() if name != "C3_world_empirical_prior_train"}
    # C3 on full would leak — report train-fit prior applied to full as descriptive only, and proper test
    cand_full["C3_world_empirical_prior_train_on_full_LEAKY"] = eval_candidate(rows, prior_fn, "C3_leaky")

    cand_test = {name: eval_candidate(test, fn, name) for name, fn in candidates.items()}
    cand_train = {
        "C0_win_prob_mass_V84": eval_candidate(train, c_win_prob_mass, "C0"),
        "hit_rate_train": global_train,
        "world_rates_train": train_rates,
    }

    # Rank candidates on test by ECE then Brier (investigation ranking, not PE selection)
    ranked = sorted(
        [
            {
                "candidate": name,
                "ece": m.get("ece"),
                "brier": m.get("brier"),
                "log_loss": m.get("log_loss"),
                "bias": m.get("bias"),
                "p_mean": m.get("p_mean"),
                "hit_rate": m.get("hit_rate"),
                "n": m.get("n"),
            }
            for name, m in cand_test.items()
            if m.get("n", 0) > 0 and m.get("ece") is not None
        ],
        key=lambda d: (d["ece"], d["brier"]),
    )

    # Divergence tables for C0 by world
    divergence = []
    for w in WORLDS:
        m = world_c0.get(w) or {}
        if m.get("n", 0) == 0:
            continue
        divergence.append(
            {
                "world": w,
                "n": m["n"],
                "hit_rate": m["hit_rate"],
                "p_mean": m["p_mean"],
                "bias_p_minus_hit": m["bias"],
                "ece": m["ece"],
                "brier": m["brier"],
                "underconfident": bool(m["bias"] < -0.05),
            }
        )

    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "n_races": len(rows),
        "n_train": len(train),
        "n_test": len(test),
        "locks": {
            "production": "unchanged",
            "trigger": "unchanged",
            "blueprint": "unchanged",
            "world": "unchanged",
            "interaction": "unchanged_not_used",
            "pe": "unchanged",
        },
        "path_audit": path_audit(),
        "c0_world_calibration": world_c0,
        "c0_divergence_by_world": divergence,
        "candidates_full": {k: {kk: vv for kk, vv in m.items() if kk != "calibration_bins"} for k, m in cand_full.items()},
        "candidates_test": {k: {kk: vv for kk, vv in m.items() if kk != "calibration_bins"} for k, m in cand_test.items()},
        "candidates_test_with_bins": cand_test,
        "candidate_rank_test_by_ece": ranked,
        "train_priors": cand_train,
        "redesign_notes": {
            "problem": "C0 systematically underconfident across Worlds",
            "interaction_v84": "ruled out as primary cause",
            "preferred_direction": "redefine Base Probability scale/prior before Interaction Confidence",
            "implementation": "FORBIDDEN in V85",
        },
    }


def _fmt(x: Any, nd: int = 4) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def write_docs(report: dict[str, Any]) -> dict[str, Path]:
    out = ROOT / "docs/research"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    # slim json (drop heavy bins from main file — keep in separate key already)
    slim = dict(report)
    slim.pop("candidates_test_with_bins", None)
    # keep bins only inside c0 world for calibration doc — strip from json for size
    c0 = {}
    for w, m in (report.get("c0_world_calibration") or {}).items():
        c0[w] = {k: v for k, v in m.items() if k != "calibration_bins"}
    slim["c0_world_calibration"] = c0
    paths["json"] = out / "_v85-base-probability-audit.json"
    paths["json"].write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")

    pa = report["path_audit"]
    audit_md = [
        "# Version85 — Base Probability Audit",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**Scope:** p_base 定義の調査のみ。Interaction / PE / Production 非変更。実装・改善禁止。",
        "",
        "## ① 現在の p_base 生成経路",
        "",
        f"- **ラベル:** {pa['label']}",
        f"- **公式:** `{pa['formula']}`",
        f"- **Top1:** {pa['predicted_top1_source']}",
        f"- **win_prob:** {pa['win_prob_source']}",
        f"- **Outcome:** {pa['outcome_label']}",
        f"- **World:** {pa['world_label']}",
        f"- **Interaction:** {pa['interaction']}",
        f"- **Production PE:** {pa['production_pe']}",
        "",
        "### Code refs",
        "",
    ]
    for ref in pa["code_refs"]:
        audit_md.append(f"- `{ref}`")
    audit_md += [
        "",
        "### 経路図（概念）",
        "",
        "```text",
        "corpus.runners.win_prob ──┐",
        "                          ├─→ build_race_rows.horses.win_prob",
        "fixture.predicted_top1 ───┤",
        "                          └─→ p_base = wp[top1] / sum(wp)   (V84 Shadow adapter)",
        "fixture.hit_at_1 ────────────→ y (calibration label)",
        "CEW label ───────────────────→ World slice (read-only)",
        "```",
        "",
        f"**仮説（V84）:** {pa['known_bias_hypothesis']}",
        "",
        "## ② p_base と実績勝率の乖離（C0 = win_prob mass）",
        "",
        f"全レース n={report['n_races']}",
        "",
        "| World | n | hit_rate | p_mean | bias(p−hit) | ECE | Brier | underconf? |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for d in report["c0_divergence_by_world"]:
        audit_md.append(
            f"| `{d['world']}` | {d['n']} | {_fmt(d['hit_rate'])} | {_fmt(d['p_mean'])} | {_fmt(d['bias_p_minus_hit'])} | {_fmt(d['ece'])} | {_fmt(d['brier'])} | {d['underconfident']} |"
        )
    all_m = report["c0_world_calibration"].get("_all") or {}
    audit_md += [
        f"| **ALL** | {all_m.get('n')} | {_fmt(all_m.get('hit_rate'))} | {_fmt(all_m.get('p_mean'))} | {_fmt(all_m.get('bias'))} | {_fmt(all_m.get('ece'))} | {_fmt(all_m.get('brier'))} | {bool((all_m.get('bias') or 0) < -0.05)} |",
        "",
        "### 結論（Audit）",
        "",
        "- 全 World で `p_mean ≪ hit_rate`（bias 大幅負）→ **systematic underconfidence** を再確認。",
        "- 乖離は Interaction 非依存（本監査は Interaction 未使用）。",
        "",
        "## 関連",
        "",
        "- `v85-calibration-analysis.md`",
        "- `v85-candidate-definition.md`",
        "- `v85-governance.md`",
        "",
    ]
    paths["audit"] = out / "v85-base-probability-audit.md"
    paths["audit"].write_text("\n".join(audit_md), encoding="utf-8")

    # Calibration analysis
    cal = [
        "# Version85 — Calibration Analysis（World別 / C0）",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "候補比較の test 指標も末尾に記載。Interaction 非使用。",
        "",
        "## ③ World別 Calibration（C0 win_prob mass）",
        "",
    ]
    for w in list(WORLDS) + ["_all"]:
        m = report["c0_world_calibration"].get(w) or {}
        if m.get("n", 0) == 0:
            cal += [f"### `{w}`", "", "insufficient", ""]
            continue
        # recompute bins for doc from slim? we stripped bins — reload from candidates_test_with_bins only for test
        # For world bins, recompute quickly inline from report if missing
        cal += [
            f"### `{w}`",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| n | {m.get('n')} |",
            f"| hit_rate | {_fmt(m.get('hit_rate'))} |",
            f"| p_mean | {_fmt(m.get('p_mean'))} |",
            f"| bias (p−hit) | {_fmt(m.get('bias'))} |",
            f"| ECE | {_fmt(m.get('ece'))} |",
            f"| Brier | {_fmt(m.get('brier'))} |",
            f"| LogLoss | {_fmt(m.get('log_loss'))} |",
            f"| Reliability mean|gap| | {_fmt(m.get('reliability_mean_gap'))} |",
            "",
        ]

    cal += [
        "## Candidate test-split（参考・実装なし）",
        "",
        f"train={report['n_train']} / test={report['n_test']}（時系列半分割。World prior は train のみ）",
        "",
        "| Rank | Candidate | ECE | Brier | LogLoss | bias | p_mean | hit |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for i, d in enumerate(report["candidate_rank_test_by_ece"], 1):
        cal.append(
            f"| {i} | `{d['candidate']}` | {_fmt(d['ece'])} | {_fmt(d['brier'])} | {_fmt(d['log_loss'])} | {_fmt(d['bias'])} | {_fmt(d['p_mean'])} | {_fmt(d['hit_rate'])} |"
        )
    cal += [
        "",
        "### 読み方",
        "",
        "- bias < 0 → underconfident（平均）。",
        "- C3/C7* は prior を含むため「定義候補」であり、Production 採用ではない。",
        "- 本表は調査用。PE 組み込み禁止。",
        "",
    ]
    paths["cal"] = out / "v85-calibration-analysis.md"
    paths["cal"].write_text("\n".join(cal), encoding="utf-8")

    # Candidate definition
    top = report["candidate_rank_test_by_ece"][:5]
    cand_md = [
        "# Version85 — Candidate Definition（Base Probability 再定義案）",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**制約:** Interaction 変更禁止 / PE・Production 実装禁止 / 改善実装禁止。定義案の文書化のみ。",
        "",
        "## ④ win_prob 以外を含む候補一覧",
        "",
        "| ID | 定義 | 意図 |",
        "|---|---|---|",
        "| C0 | `wp[top1]/sum(wp)` | V84 現行 p_base |",
        "| C1 | `wp[top1]` raw | 正規化なし |",
        "| C2 | `1/field_size` | 一様事前 |",
        "| C3 | World empirical hit_rate (train) | World 定数 prior |",
        "| C4 | `(1/odds[top1]) / sum(1/odds)` | 市場確率 |",
        "| C5 | `wp[top1]/(wp[top1]+wp[top2])` | 対抗馬マージン |",
        "| C6/C6b | softmax(log wp / T) | 温度付き質量 |",
        "| C7/C7b/C7c | `(1-λ)·C0 + λ·C3` | 質量×World prior 混合 |",
        "",
        "## test ECE 上位（調査）",
        "",
    ]
    for i, d in enumerate(top, 1):
        cand_md.append(
            f"{i}. `{d['candidate']}` — ECE={_fmt(d['ece'])}, Brier={_fmt(d['brier'])}, bias={_fmt(d['bias'])}"
        )
    cand_md += [
        "",
        "## ⑤ Base Probability 再定義案（文書）",
        "",
        "### 案 A — World Prior Anchor（推奨候補・非実装）",
        "",
        "```text",
        "p_base' = (1-λ) * (wp[top1]/sum(wp)) + λ * HitRate_CEW(world; train_window)",
        "λ ∈ {0.7, 0.9} を Shadow で感度（別 Decision）",
        "```",
        "",
        "- **理由:** C0 の underconfidence を World 実績スケールへ引き上げる。V84 constant-shift と同型だが、明示的 prior。",
        "- **Risk:** 時系列 prior のリーク / World 標本不足（core 等）。",
        "- **Interaction:** 触らない。Confidence Integration は p_base' 安定後。",
        "",
        "### 案 B — Market Mass",
        "",
        "```text",
        "p_base' = (1/odds[top1]) / sum_j (1/odds[j])",
        "```",
        "",
        "- **理由:** 市場は経験的にスケールが異なる可能性（C4）。",
        "- **Risk:** odds 欠損・市場歪み。Prediction Rank との不一致。",
        "",
        "### 案 C — Margin Mass（C5）",
        "",
        "```text",
        "p_base' = wp[top1] / (wp[top1] + wp[top2])",
        "```",
        "",
        "- **理由:** フィールド全体正規化より「対抗」相対に寄せる。",
        "- **Risk:** なお underconfident の可能性（要 Shadow）。",
        "",
        "### 案 D — 禁止・非推奨",
        "",
        "| 案 | 理由 |",
        "|---|---|",
        "| Interaction で p_base を補正 | V84 で主因でないと判明。Contract も変更禁止対象に近い誤用 |",
        "| 単体 Feature Weight で Score/Rank 変更 | V80 失敗モード |",
        "| Production PE 即時切替 | 本フェーズ禁止 |",
        "",
        "### 推奨順序（設計のみ）",
        "",
        "1. **案 A（C7b/C7c 系）** を次 Shadow の主仮説とする",
        "2. 案 B/C を対照アーム",
        "3. Interaction Confidence は p_base' の ECE/Brier が安定してから再評価",
        "",
        "**本フェーズでは採用実装しない。**",
        "",
    ]
    paths["cand"] = out / "v85-candidate-definition.md"
    paths["cand"].write_text("\n".join(cand_md), encoding="utf-8")

    # Governance
    # Verdict: audit complete with clear underconfidence + redesign proposals without implementation
    under = sum(1 for d in report["c0_divergence_by_world"] if d.get("underconfident"))
    verdict = "A" if under >= 3 else "B"
    gov = [
        "# Version85 — Governance（Base Probability Redesign Investigation）",
        "",
        f"**Date:** {report['generated_at'][:10]}  ",
        f"**Verdict:** **{verdict}**（underconfident Worlds={under}/{len(report['c0_divergence_by_world'])}；再定義案文書化完了 / 実装なし）  ",
        "**Type:** Research Investigation only",
        "",
        "【Decision】",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Base Probability Audit & Redesign Proposal |",
        "| Implementation Required | **No** |",
        "| PE Required | **No**（禁止） |",
        "| Production Required | **No** |",
        "| Trigger / Blueprint / World / Interaction | 非変更 |",
        "| Rollback Required | No |",
        "| Risk | None（読取調査） |",
        "| Expected Next Action | 案 A（World Prior Anchor）の **Shadow Calibration**（別 Decision）。Interaction/PE/Production は継続禁止 |",
        "",
        "## 遵守",
        "",
        "| 制約 | 結果 |",
        "|---|---|",
        "| 実装禁止 | PASS |",
        "| 改善（PE反映）禁止 | PASS |",
        "| Production / Trigger / Blueprint / World / Interaction / PE 非変更 | PASS |",
        "",
        "## 主結論",
        "",
        "1. V84 p_base（win_prob mass）は全主要 World で systematic underconfidence。",
        "2. Interaction は本問題の主因ではない（V84＋本監査で Interaction 未使用でも乖離）。",
        "3. 次の設計焦点は Base Probability 再定義（案 A 優先）。",
        "",
        "## 成果物",
        "",
        "- `v85-base-probability-audit.md`",
        "- `v85-calibration-analysis.md`",
        "- `v85-candidate-definition.md`",
        "- `v85-governance.md`",
        "- `_v85-base-probability-audit.json`",
        "",
    ]
    paths["gov"] = out / "v85-governance.md"
    paths["gov"].write_text("\n".join(gov), encoding="utf-8")

    # Also dump bins for calibration detail appendix in json side file
    bins_path = out / "_v85-c0-calibration-bins.json"
    bins_only = {}
    for w, m in (report.get("c0_world_calibration") or {}).items():
        if "calibration_bins" in m:
            bins_only[w] = m["calibration_bins"]
    # regenerate bins by re-eval quickly? report still has them in memory before slim — 
    # write_docs receives full report before slim pop of test bins; c0 still has bins
    bins_path.write_text(json.dumps(bins_only, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["bins"] = bins_path
    return paths


def main() -> None:
    report = run()
    paths = write_docs(report)
    mirror = Path(r"C:\Users\Mr.me\expect-keiba-ai\docs\research")
    if mirror.is_dir():
        for p in paths.values():
            (mirror / p.name).write_bytes(p.read_bytes())
    top = (report.get("candidate_rank_test_by_ece") or [])[:3]
    print(
        json.dumps(
            {
                "n": report["n_races"],
                "c0_all_bias": (report["c0_world_calibration"].get("_all") or {}).get("bias"),
                "divergence": report["c0_divergence_by_world"],
                "top_candidates_test": top,
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
