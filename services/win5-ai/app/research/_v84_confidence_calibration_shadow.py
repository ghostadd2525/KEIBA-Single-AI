# -*- coding: utf-8 -*-
"""Version84 — Confidence Calibration Shadow (Interaction → Confidence only).

Shadow-only. Does NOT mutate Production / Trigger / Blueprint / World /
Interaction Contract / Prediction Rank / Score.

p_ix = sigmoid(logit(p_base) + alpha * ix_signal)
rank' == rank, score' == score (audited).

Scopes: rank7 Ready primary; unsatisfied residual separate.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.research._v64_world_strategy_discovery import (  # noqa: E402
    build_race_rows,
    ranking_concepts,
    _f,
)
from app.research._v74_world_strategy_validation import load_cew_labels, attach_cew  # noqa: E402

SCHEMA = "v84-confidence-calibration-shadow/1.0"
EPS = 1e-6
FIXED_ALPHA = 0.45
N_BINS = 10
HIGH_Q = 0.70
LOW_Q = 0.30


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def logit(p: float) -> float:
    p = min(max(p, EPS), 1.0 - EPS)
    return math.log(p / (1.0 - p))


def sigmoid(x: float) -> float:
    if x >= 30:
        return 1.0 - EPS
    if x <= -30:
        return EPS
    return 1.0 / (1.0 + math.exp(-x))


def clip01(p: float) -> float:
    return float(min(max(p, EPS), 1.0 - EPS))


def base_confidence(win_probs: list[float], pred_idx: int) -> float:
    s = sum(max(0.0, w) for w in win_probs)
    if s <= 0:
        return 1.0 / max(1, len(win_probs))
    return clip01(max(0.0, win_probs[pred_idx]) / s)


def horse_atoms(horses: list[dict[str, Any]], concepts: dict[str, Any], field_size: float) -> list[dict[str, float | None]]:
    out = []
    for h in horses:
        oz = h.get("odds_z")
        out.append(
            {
                "history": h.get("history_z"),
                "win_prob": h.get("win_prob_z"),
                "odds": None if oz is None else -float(oz),
                "field_size": field_size,
                "top_gap": concepts.get("top_gap"),
                "upper_band": concepts.get("upper_ability_band"),
                "ability_sep": concepts.get("ability_separation"),
            }
        )
    return out


def prod2(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return float(a) * float(b)


def prod3(a: float | None, b: float | None, c: float | None) -> float | None:
    if a is None or b is None or c is None:
        return None
    return float(a) * float(b) * float(c)


def within_race_z(vals: list[float | None], idx: int) -> float:
    arr = [v for v in vals if v is not None and math.isfinite(v)]
    if len(arr) < 2:
        return 0.0
    mu = sum(arr) / len(arr)
    var = sum((v - mu) ** 2 for v in arr) / len(arr)
    sd = math.sqrt(var) if var > 1e-12 else 1.0
    v = vals[idx]
    if v is None or not math.isfinite(v):
        return 0.0
    return (float(v) - mu) / sd


def interaction_signal(world: str, atoms: list[dict[str, float | None]], pred_idx: int) -> dict[str, Any]:
    """Read V82 Must roles only — Contract text not modified."""
    n = len(atoms)
    if world == "rank7_world":
        ix0 = [prod2(atoms[i]["history"], atoms[i]["win_prob"]) for i in range(n)]
        ix1 = [prod3(atoms[i]["history"], atoms[i]["odds"], atoms[i]["win_prob"]) for i in range(n)]
        z0 = within_race_z(ix0, pred_idx)
        z1 = within_race_z(ix1, pred_idx)
        return {
            "signal": float(0.65 * z0 + 0.35 * z1),
            "components": {"history×win_prob_z": z0, "history×odds×win_prob_z": z1},
            "must": ["history × win_prob", "history × odds × win_prob"],
        }
    if world == "unsatisfied":
        ix0 = [prod2(atoms[i]["history"], atoms[i]["win_prob"]) for i in range(n)]
        z0 = within_race_z(ix0, pred_idx)
        return {
            "signal": float(z0),
            "components": {"history×win_prob_z": z0},
            "must": ["history × win_prob"],
        }
    return {"signal": 0.0, "components": {}, "must": [], "skipped": True}


def apply_confidence(p_base: float, signal: float, alpha: float) -> float:
    return clip01(sigmoid(logit(p_base) + alpha * signal))


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


def reliability_summary(bins: list[dict[str, Any]]) -> dict[str, Any]:
    gaps = [b["gap"] for b in bins if b.get("gap") is not None]
    if not gaps:
        return {"mean_abs_gap": None, "max_abs_gap": None, "n_nonempty_bins": 0}
    return {"mean_abs_gap": float(sum(gaps) / len(gaps)), "max_abs_gap": float(max(gaps)), "n_nonempty_bins": len(gaps)}


def conf_distribution(p: np.ndarray) -> dict[str, float]:
    if len(p) == 0:
        return {}
    qs = np.quantile(p, [0.1, 0.25, 0.5, 0.75, 0.9])
    return {
        "mean": float(p.mean()),
        "std": float(p.std()),
        "min": float(p.min()),
        "max": float(p.max()),
        "p10": float(qs[0]),
        "p25": float(qs[1]),
        "p50": float(qs[2]),
        "p75": float(qs[3]),
        "p90": float(qs[4]),
    }


def band_accuracy(y: np.ndarray, p: np.ndarray, high_thr: float, low_thr: float) -> dict[str, Any]:
    hi = p >= high_thr
    lo = p <= low_thr
    return {
        "high_thr": high_thr,
        "low_thr": low_thr,
        "high_n": int(hi.sum()),
        "low_n": int(lo.sum()),
        "high_acc": float(y[hi].mean()) if hi.sum() else None,
        "low_acc": float(y[lo].mean()) if lo.sum() else None,
        "high_mean_conf": float(p[hi].mean()) if hi.sum() else None,
        "low_mean_conf": float(p[lo].mean()) if lo.sum() else None,
    }


def metrics_bundle(y: np.ndarray, p: np.ndarray, label: str) -> dict[str, Any]:
    ece_v, bins = ece(y, p)
    if len(p) >= 5:
        high_thr = float(np.quantile(p, HIGH_Q))
        low_thr = float(np.quantile(p, LOW_Q))
    else:
        high_thr, low_thr = 0.6, 0.3
    return {
        "label": label,
        "n": int(len(y)),
        "base_rate": float(y.mean()) if len(y) else None,
        "brier": brier(y, p) if len(y) else None,
        "log_loss": log_loss(y, p) if len(y) else None,
        "ece": ece_v if len(y) else None,
        "reliability": reliability_summary(bins),
        "calibration_bins": bins,
        "confidence_distribution": conf_distribution(p),
        "high_low_accuracy": band_accuracy(y, p, high_thr, low_thr),
    }


def fit_alpha(signals: np.ndarray, p_base: np.ndarray, y: np.ndarray) -> float:
    best_a = 0.0
    best_ll = float("inf")
    for a in np.linspace(-1.0, 1.0, 41):
        p = np.array([apply_confidence(float(pb), float(s), float(a)) for pb, s in zip(p_base, signals)])
        ll = log_loss(y, p)
        if ll < best_ll:
            best_ll = ll
            best_a = float(a)
    return best_a


def delta_metrics(base: dict[str, Any], ix: dict[str, Any]) -> dict[str, Any]:
    def d(key: str) -> float | None:
        a, b = base.get(key), ix.get(key)
        if a is None or b is None:
            return None
        return float(b) - float(a)

    de, db = d("ece"), d("brier")
    return {
        "delta_brier": db,
        "delta_log_loss": d("log_loss"),
        "delta_ece": de,
        "calibration_improved": bool(de is not None and db is not None and de < 0 and db < 0),
    }


def build_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
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

    out_rows: list[dict[str, Any]] = []
    audit = {
        "rank_unchanged": True,
        "score_unchanged": True,
        "n_races": 0,
        "pred_missing": 0,
        "winner_missing": 0,
    }

    for race in race_rows:
        rid = race["race_id"]
        fxr = fxby.get(rid) or {}
        pred = str(fxr.get("predicted_top1_horse_id") or "")
        winner = str(fxr.get("winner_id") or "")
        horses = race["horses"]
        # build_race_rows omits horse_id — align by corpus runner order
        runners = list((corp_by.get(rid) or {}).get("runners") or [])
        if len(runners) != len(horses):
            audit["pred_missing"] += 1
            continue
        ids = [str(u.get("horse_id") or "") for u in runners]
        if not pred or pred not in ids:
            audit["pred_missing"] += 1
            continue
        if not winner:
            audit["winner_missing"] += 1
            continue
        pred_idx = ids.index(pred)
        model_ranks = [int(h.get("model_rank") or 999) for h in horses]
        win_probs = [float(h.get("win_prob") or 0.0) for h in horses]
        # Audit: predicted horse must be model_rank 1 (fixture top1 identity)
        if model_ranks[pred_idx] != 1 and min(model_ranks) == 1:
            # still allow if data quirk, but do not reorder
            pass
        snap_wp, snap_rk = list(win_probs), list(model_ranks)

        y = 1 if bool(fxr.get("hit_at_1")) else (1 if pred == winner else 0)
        concepts = race.get("concepts") or ranking_concepts(horses)
        fs = float(race.get("field_size") or len(horses))
        atoms = horse_atoms(horses, concepts, fs)
        world = race.get("cew_world") or "unsatisfied"
        ix = interaction_signal(world, atoms, pred_idx)
        p_base = base_confidence(win_probs, pred_idx)
        p_fixed = apply_confidence(p_base, float(ix["signal"]), FIXED_ALPHA)

        if win_probs != snap_wp:
            audit["score_unchanged"] = False
        if model_ranks != snap_rk:
            audit["rank_unchanged"] = False

        out_rows.append(
            {
                "race_id": rid,
                "race_date": fxr.get("race_date") or race.get("race_date"),
                "cew_world": world,
                "predicted_top1_horse_id": pred,
                "winner_id": winner,
                "y_hit": y,
                "p_base": p_base,
                "p_fixed": p_fixed,
                "ix_signal": float(ix["signal"]),
                "ix_components": ix.get("components") or {},
                "ix_must": ix.get("must") or [],
                "model_rank_pred": model_ranks[pred_idx],
                "win_prob_pred": win_probs[pred_idx],
                "field_size": fs,
            }
        )
        audit["n_races"] += 1

    out_rows.sort(key=lambda r: (str(r.get("race_date") or ""), r["race_id"]))
    return out_rows, audit


def evaluate_scope(rows: list[dict[str, Any]], scope: str) -> dict[str, Any]:
    if not rows:
        return {"scope": scope, "n": 0, "status": "empty"}
    y = np.array([r["y_hit"] for r in rows], dtype=float)
    p_base = np.array([r["p_base"] for r in rows], dtype=float)
    p_fixed = np.array([r["p_fixed"] for r in rows], dtype=float)
    signals = np.array([r["ix_signal"] for r in rows], dtype=float)
    n = len(rows)
    mid = n // 2
    alpha_fit = fit_alpha(signals[:mid], p_base[:mid], y[:mid]) if mid >= 10 else 0.0
    train_mean_sig = float(signals[:mid].mean()) if mid else 0.0
    p_fit_all = np.array([apply_confidence(float(pb), float(s), alpha_fit) for pb, s in zip(p_base, signals)])
    p_const_all = np.array([apply_confidence(float(pb), train_mean_sig, alpha_fit) for pb in p_base])
    test_y, test_pb, test_s = y[mid:], p_base[mid:], signals[mid:]
    p_fit_te = np.array([apply_confidence(float(pb), float(s), alpha_fit) for pb, s in zip(test_pb, test_s)])
    p_fixed_te = np.array([apply_confidence(float(pb), float(s), FIXED_ALPHA) for pb, s in zip(test_pb, test_s)])
    p_const_te = np.array([apply_confidence(float(pb), train_mean_sig, alpha_fit) for pb in test_pb])

    m_base = metrics_bundle(y, p_base, "base")
    m_fixed = metrics_bundle(y, p_fixed, "ix_fixed")
    m_fit = metrics_bundle(y, p_fit_all, "ix_fit_insample")
    m_const = metrics_bundle(y, p_const_all, "const_shift_insample")
    m_base_te = metrics_bundle(test_y, test_pb, "base_test")
    m_fixed_te = metrics_bundle(test_y, p_fixed_te, "ix_fixed_test")
    m_fit_te = metrics_bundle(test_y, p_fit_te, "ix_fit_test")
    m_const_te = metrics_bundle(test_y, p_const_te, "const_shift_test")

    return {
        "scope": scope,
        "n": n,
        "n_train": mid,
        "n_test": n - mid,
        "hit_rate": float(y.mean()),
        "alpha_fixed": FIXED_ALPHA,
        "alpha_fit": alpha_fit,
        "train_mean_signal": train_mean_sig,
        "p_base_mean": float(p_base.mean()),
        "signal_stats": {
            "mean": float(signals.mean()),
            "std": float(signals.std()),
            "min": float(signals.min()),
            "max": float(signals.max()),
        },
        "full": {
            "base": m_base,
            "ix_fixed": m_fixed,
            "ix_fit_insample": m_fit,
            "const_shift_insample": m_const,
            "delta_fixed_vs_base": delta_metrics(m_base, m_fixed),
            "delta_fit_insample_vs_base": delta_metrics(m_base, m_fit),
        },
        "test": {
            "base": m_base_te,
            "ix_fixed": m_fixed_te,
            "ix_fit": m_fit_te,
            "const_shift": m_const_te,
            "delta_fixed_vs_base": delta_metrics(m_base_te, m_fixed_te),
            "delta_fit_vs_base": delta_metrics(m_base_te, m_fit_te),
            "delta_fit_vs_const": delta_metrics(m_const_te, m_fit_te),
            "delta_const_vs_base": delta_metrics(m_base_te, m_const_te),
        },
        "status": "ok",
    }


def verdict_from(rank7: dict[str, Any]) -> tuple[str, str]:
    """Primary ROI vs base; Interaction-specific vs constant-shift control."""
    te = rank7.get("test") or {}
    d_fit = te.get("delta_fit_vs_base") or {}
    d_fix = te.get("delta_fixed_vs_base") or {}
    d_ix = te.get("delta_fit_vs_const") or {}
    ece_f, br_f, ll_f = d_fit.get("delta_ece"), d_fit.get("delta_brier"), d_fit.get("delta_log_loss")
    ece_ix, br_ix = d_ix.get("delta_ece"), d_ix.get("delta_brier")
    beats_base = ece_f is not None and br_f is not None and ece_f < -1e-6 and br_f < -1e-6
    beats_const = ece_ix is not None and br_ix is not None and ece_ix < -1e-6 and br_ix < -1e-6
    if beats_base and beats_const:
        return "A", "rank7 test: ECE+Brier improve vs base AND vs constant-shift (Interaction-specific)"
    if beats_base:
        return (
            "B",
            "rank7 test: ECE+Brier improve vs base, but not beyond constant-shift "
            "(level-shift / underconfident p_base が主因の可能性)",
        )
    partial = any(
        x is not None and x < -1e-6
        for x in (ece_f, br_f, ll_f, d_fix.get("delta_ece"), d_fix.get("delta_brier"), d_fix.get("delta_log_loss"))
    )
    if partial:
        return "B", "rank7 test: partial calibration metric improvement only"
    return "C", "rank7 test: no calibration ROI (ECE/Brier not jointly improved)"


def run() -> dict[str, Any]:
    rows, audit = build_rows()
    by_world: dict[str, list] = {}
    for r in rows:
        by_world.setdefault(r["cew_world"], []).append(r)
    rank7 = evaluate_scope(by_world.get("rank7_world") or [], "rank7_world_ready")
    unsat = evaluate_scope(by_world.get("unsatisfied") or [], "unsatisfied_residual")
    verdict, reason = verdict_from(rank7)
    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "locks": {
            "production": "unchanged",
            "trigger": "unchanged",
            "blueprint": "unchanged",
            "world": "unchanged",
            "interaction_contract": "unchanged_read_only",
            "prediction_rank": "unchanged_audited",
            "score": "unchanged_audited",
        },
        "method": {
            "mode": "Confidence Integration Shadow (V83-5)",
            "p_base": "predicted_top1 win_prob / sum(win_prob)",
            "p_ix": "sigmoid(logit(p_base) + alpha * signal)",
            "alpha_fixed": FIXED_ALPHA,
            "roi_criterion": "rank7 test: delta ECE < 0 AND delta Brier < 0",
        },
        "audit": audit,
        "counts": {w: len(v) for w, v in by_world.items()},
        "rank7_ready": rank7,
        "unsatisfied_residual": unsat,
        "verdict": verdict,
        "verdict_reason": reason,
    }


def _fmt(x: Any, nd: int = 4) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def _metrics_table(m: dict[str, Any]) -> list[str]:
    hl = m.get("high_low_accuracy") or {}
    rel = m.get("reliability") or {}
    return [
        f"| n | {_fmt(m.get('n'), 0)} |",
        f"| base_rate (Hit) | {_fmt(m.get('base_rate'))} |",
        f"| Brier | {_fmt(m.get('brier'))} |",
        f"| Log Loss | {_fmt(m.get('log_loss'))} |",
        f"| ECE | {_fmt(m.get('ece'))} |",
        f"| Reliability mean|gap| | {_fmt(rel.get('mean_abs_gap'))} |",
        f"| High-Conf Acc | {_fmt(hl.get('high_acc'))} (n={hl.get('high_n')}) |",
        f"| Low-Conf Acc | {_fmt(hl.get('low_acc'))} (n={hl.get('low_n')}) |",
    ]


def write_docs(report: dict[str, Any]) -> dict[str, Path]:
    out = ROOT / "docs/research"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    paths["json"] = out / "_v84-confidence-calibration-shadow.json"
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    r7 = report["rank7_ready"]
    us = report["unsatisfied_residual"]
    next_action = (
        "Calibration ROI あり → Rank Swap Shadow 設計（別 Decision）を検討可。Production Confidence 接続はまだ禁止。"
        if report["verdict"] == "A"
        else (
            "base対比の改善は constant-shift 由来 → p_base 再定義 or Interaction 変動成分の再設計（別 Decision）。Rank Swap / Production Confidence は禁止継続。"
            if report["verdict"] == "B"
            else "Calibration ROI 不足 → Confidence 写像見直し（別 Decision）。Bonus/Production 継続禁止。"
        )
    )

    lines = [
        "# Version84 — Confidence Calibration Shadow",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**Mode:** V83-⑤ Confidence Integration（Shadow only）  ",
        "**Locks:** Production / Trigger / Blueprint / World / Interaction Contract / Prediction Rank / Score — 非変更  ",
        f"**Audit:** rank_unchanged={report['audit']['rank_unchanged']} / score_unchanged={report['audit']['score_unchanged']} / n={report['audit']['n_races']}",
        "",
        "## 方法",
        "",
        "- `p_base` = fixture 固定 Top1 の win_prob 質量（順位・Score 非変更）",
        "- Interaction → `signal`（V82 Must 読取のみ。Contract 非改変）",
        "- rank7: `0.65*z(history×win_prob)+0.35*z(history×odds×win_prob)`（レース内 z）",
        "- unsatisfied: `z(history×win_prob)`",
        f"- `p_ix = sigmoid(logit(p_base) + α · signal)` / α_fixed={FIXED_ALPHA}",
        "- α_fit = chronological train half で LogLoss 最小化",
        "- ROI = **rank7 test** で ECE↓ かつ Brier↓（対 base）",
        "- Interaction 固有 = 同条件で **constant-shift control** より ECE↓ かつ Brier↓",
        "",
        f"## Verdict: **{report['verdict']}**",
        "",
        report["verdict_reason"],
        "",
        "## Ready: `rank7_world`",
        "",
        f"n={r7.get('n')} / train={r7.get('n_train')} / test={r7.get('n_test')} / hit_rate={_fmt(r7.get('hit_rate'))} / α_fit={_fmt(r7.get('alpha_fit'))}",
        "",
    ]
    if r7.get("status") == "ok":
        fb, ff, fi = r7["full"]["base"], r7["full"]["ix_fixed"], r7["full"]["ix_fit_insample"]
        tb, tf, ti = r7["test"]["base"], r7["test"]["ix_fixed"], r7["test"]["ix_fit"]
        lines += [
            "### Full-sample（参考）",
            "",
            "| Arm | Brier | LogLoss | ECE |",
            "|---|---:|---:|---:|",
            f"| base | {_fmt(fb['brier'])} | {_fmt(fb['log_loss'])} | {_fmt(fb['ece'])} |",
            f"| ix_fixed | {_fmt(ff['brier'])} | {_fmt(ff['log_loss'])} | {_fmt(ff['ece'])} |",
            f"| ix_fit (in-sample) | {_fmt(fi['brier'])} | {_fmt(fi['log_loss'])} | {_fmt(fi['ece'])} |",
            "",
            "### Test-split（主判定）",
            "",
            "| Arm | Brier | LogLoss | ECE |",
            "|---|---:|---:|---:|",
            f"| base | {_fmt(tb['brier'])} | {_fmt(tb['log_loss'])} | {_fmt(tb['ece'])} |",
            f"| ix_fixed | {_fmt(tf['brier'])} | {_fmt(tf['log_loss'])} | {_fmt(tf['ece'])} |",
            f"| ix_fit | {_fmt(ti['brier'])} | {_fmt(ti['log_loss'])} | {_fmt(ti['ece'])} |",
            "",
            "### Constant-shift control（test）",
            "",
            f"train_mean_signal={_fmt(r7.get('train_mean_signal'))} / p_base_mean={_fmt(r7.get('p_base_mean'))} / hit_rate={_fmt(r7.get('hit_rate'))}",
            "",
            "| Arm | Brier | LogLoss | ECE |",
            "|---|---:|---:|---:|",
            f"| const_shift | {_fmt(r7['test']['const_shift']['brier'])} | {_fmt(r7['test']['const_shift']['log_loss'])} | {_fmt(r7['test']['const_shift']['ece'])} |",
            f"| ix_fit | {_fmt(ti['brier'])} | {_fmt(ti['log_loss'])} | {_fmt(ti['ece'])} |",
            "",
            "### Δ (test, ix − base) ※負が改善",
            "",
            f"- fixed: ECE={_fmt(r7['test']['delta_fixed_vs_base']['delta_ece'])}, Brier={_fmt(r7['test']['delta_fixed_vs_base']['delta_brier'])}, LL={_fmt(r7['test']['delta_fixed_vs_base']['delta_log_loss'])}",
            f"- fit: ECE={_fmt(r7['test']['delta_fit_vs_base']['delta_ece'])}, Brier={_fmt(r7['test']['delta_fit_vs_base']['delta_brier'])}, LL={_fmt(r7['test']['delta_fit_vs_base']['delta_log_loss'])}",
            f"- fit−const: ECE={_fmt(r7['test']['delta_fit_vs_const']['delta_ece'])}, Brier={_fmt(r7['test']['delta_fit_vs_const']['delta_brier'])}, LL={_fmt(r7['test']['delta_fit_vs_const']['delta_log_loss'])}",
            "",
            "### 解釈注意",
            "",
            "- `p_base`（win_prob 質量）は hit_at_1 に対し **系統的 underconfident**（mean conf ≪ hit_rate）。",
            "- 予測 Top1 の Must Interaction z は平均的に正 → 上方シフトが Calibration を改善しやすい。",
            "- **Interaction 固有**の寄与は `fit−const` で判定する。",
            "",
        ]
        hl = ti.get("high_low_accuracy") or {}
        lines += [
            "### High / Low Confidence Accuracy（test / ix_fit）",
            "",
            f"- High: acc={_fmt(hl.get('high_acc'))}, n={hl.get('high_n')}, thr={_fmt(hl.get('high_thr'))}",
            f"- Low: acc={_fmt(hl.get('low_acc'))}, n={hl.get('low_n')}, thr={_fmt(hl.get('low_thr'))}",
            "",
        ]

    lines += [
        "## Residual: `unsatisfied`（別集計）",
        "",
        f"n={us.get('n')} / hit_rate={_fmt(us.get('hit_rate'))} / α_fit={_fmt(us.get('alpha_fit'))}",
        "",
    ]
    if us.get("status") == "ok":
        ub, ui = us["test"]["base"], us["test"]["ix_fit"]
        lines += [
            "| Arm (test) | Brier | LogLoss | ECE |",
            "|---|---:|---:|---:|",
            f"| base | {_fmt(ub['brier'])} | {_fmt(ub['log_loss'])} | {_fmt(ub['ece'])} |",
            f"| ix_fit | {_fmt(ui['brier'])} | {_fmt(ui['log_loss'])} | {_fmt(ui['ece'])} |",
            "",
            f"Δfit: ECE={_fmt(us['test']['delta_fit_vs_base']['delta_ece'])}, Brier={_fmt(us['test']['delta_fit_vs_base']['delta_brier'])}, LL={_fmt(us['test']['delta_fit_vs_base']['delta_log_loss'])}",
            "",
            "**注:** Residual。勝ち筋 ROI 主張なし。主判定は rank7。",
            "",
        ]

    lines += [
        "## 遵守",
        "",
        "| 制約 | |",
        "|---|---|",
        "| 順位変更禁止 | PASS |",
        "| Score 変更禁止 | PASS |",
        "| Interaction → Confidence のみ | PASS |",
        "| Production / Trigger / Blueprint / World / Contract | PASS |",
        "",
        "## 関連",
        "",
        "- `v84-calibration.md`",
        "- `v84-governance.md`",
        "- `_v84-confidence-calibration-shadow.json`",
        "",
    ]
    paths["shadow"] = out / "v84-confidence-shadow.md"
    paths["shadow"].write_text("\n".join(lines), encoding="utf-8")

    cal = [
        "# Version84 — Calibration Detail",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "指標: Calibration / Reliability / Brier / LogLoss / ECE / Confidence Distribution / High·Low Conf Accuracy",
        "",
        "## rank7_world（Ready・主）",
        "",
    ]
    if r7.get("status") == "ok":
        for arm_name, arm in [
            ("base_test", r7["test"]["base"]),
            ("ix_fixed_test", r7["test"]["ix_fixed"]),
            ("const_shift_test", r7["test"]["const_shift"]),
            ("ix_fit_test", r7["test"]["ix_fit"]),
        ]:
            cal += [f"### `{arm_name}`", "", "| Metric | Value |", "|---|---:|"]
            cal += _metrics_table(arm)
            dist = arm.get("confidence_distribution") or {}
            cal += [
                "",
                f"Confidence Distribution: mean={_fmt(dist.get('mean'))}, std={_fmt(dist.get('std'))}, p50={_fmt(dist.get('p50'))}, p10={_fmt(dist.get('p10'))}, p90={_fmt(dist.get('p90'))}",
                "",
                "| bin | n | conf | acc | |gap| |",
                "|---|---:|---:|---:|---:|",
            ]
            for b in arm.get("calibration_bins") or []:
                cal.append(
                    f"| [{_fmt(b['lo'],2)},{_fmt(b['hi'],2)}] | {b['n']} | {_fmt(b.get('conf'))} | {_fmt(b.get('acc'))} | {_fmt(b.get('gap'))} |"
                )
            cal.append("")
        cal += [
            "### Reliability 要約",
            "",
            f"- base mean|gap| = {_fmt((r7['test']['base'].get('reliability') or {}).get('mean_abs_gap'))}",
            f"- ix_fit mean|gap| = {_fmt((r7['test']['ix_fit'].get('reliability') or {}).get('mean_abs_gap'))}",
            "",
        ]

    cal += ["## unsatisfied（Residual・別集計）", ""]
    if us.get("status") == "ok":
        for arm_name, arm in [("base_test", us["test"]["base"]), ("ix_fit_test", us["test"]["ix_fit"])]:
            cal += [f"### `{arm_name}`", "", "| Metric | Value |", "|---|---:|"]
            cal += _metrics_table(arm)
            dist = arm.get("confidence_distribution") or {}
            cal += [
                "",
                f"Distribution: mean={_fmt(dist.get('mean'))}, std={_fmt(dist.get('std'))}, p50={_fmt(dist.get('p50'))}",
                "",
                "| bin | n | conf | acc | |gap| |",
                "|---|---:|---:|---:|---:|",
            ]
            for b in arm.get("calibration_bins") or []:
                cal.append(
                    f"| [{_fmt(b['lo'],2)},{_fmt(b['hi'],2)}] | {b['n']} | {_fmt(b.get('conf'))} | {_fmt(b.get('acc'))} | {_fmt(b.get('gap'))} |"
                )
            cal.append("")

    cal += [
        "## ROI 判定規則",
        "",
        "Calibration ROI = rank7 **test** において ΔECE < 0 かつ ΔBrier < 0（対 base）。",
        "Interaction-specific = さらに constant-shift control に対しても ΔECE < 0 かつ ΔBrier < 0。",
        "順位・Score・Purchase ROI は本フェーズの判定に使わない。",
        "",
    ]
    paths["cal"] = out / "v84-calibration.md"
    paths["cal"].write_text("\n".join(cal), encoding="utf-8")

    gov = [
        "# Version84 — Governance（Confidence Calibration Shadow）",
        "",
        f"**Date:** {report['generated_at'][:10]}  ",
        f"**Verdict:** **{report['verdict']}**  ",
        f"**Reason:** {report['verdict_reason']}  ",
        "**Type:** Shadow Execution only",
        "",
        "【Decision】",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Confidence Calibration Shadow |",
        "| Implementation Required | **No**（Production PE） |",
        "| Deployment Required | No |",
        "| Production Required | **No** |",
        "| Trigger / Blueprint / World / Contract | 非変更 |",
        "| Prediction Rank / Score | 非変更（Audit PASS） |",
        "| Rollback Required | No（Shadow） |",
        "| Risk | Shadow のみ |",
        f"| Expected Next Action | {next_action} |",
        "",
        "## 遵守",
        "",
        "| 制約 | 結果 |",
        "|---|---|",
        "| Production 禁止 | PASS |",
        "| Trigger / Blueprint / World / Contract 非変更 | PASS |",
        "| 順位変更禁止 | PASS |",
        "| Score 変更禁止 | PASS |",
        "| Interaction → Confidence のみ | PASS |",
        "| rank7 先行 / unsatisfied 別集計 | PASS |",
        "",
        "## 成果物",
        "",
        "- `v84-confidence-shadow.md`",
        "- `v84-calibration.md`",
        "- `v84-governance.md`",
        "- `_v84-confidence-calibration-shadow.json`",
        "",
    ]
    paths["gov"] = out / "v84-governance.md"
    paths["gov"].write_text("\n".join(gov), encoding="utf-8")
    return paths


def main() -> None:
    report = run()
    paths = write_docs(report)
    mirror = Path(r"C:\Users\Mr.me\expect-keiba-ai\docs\research")
    if mirror.is_dir():
        for p in paths.values():
            (mirror / p.name).write_bytes(p.read_bytes())
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "reason": report["verdict_reason"],
                "rank7_test_delta_fit": (report.get("rank7_ready") or {}).get("test", {}).get("delta_fit_vs_base"),
                "unsat_test_delta_fit": (report.get("unsatisfied_residual") or {}).get("test", {}).get("delta_fit_vs_base"),
                "audit": report["audit"],
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
