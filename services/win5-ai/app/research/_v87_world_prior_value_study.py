# -*- coding: utf-8 -*-
"""Version87 — World Prior Value Study (research only).

Compares pure empirical priors to test whether World Prior adds value
beyond Global / Course / Distance calibration.

Does NOT change: Production / PE / Trigger / Blueprint / Interaction.
Implementation forbidden (docs + research metrics only).
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

from app.research._v64_world_strategy_discovery import build_race_rows  # noqa: E402
from app.research._v74_world_strategy_validation import load_cew_labels, attach_cew  # noqa: E402
from app.research._v85_base_probability_audit import WORLDS, clip01, metrics  # noqa: E402

SCHEMA = "v87-world-prior-value-study/1.0"
MIN_CELL = 5  # backoff if train cell n < this
N_BOOT = 2000
RNG = np.random.default_rng(87)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def distance_bin(d: float | None) -> str:
    if d is None or not math.isfinite(d) or d <= 0:
        return "unk"
    # JRA-ish bands
    if d < 1400:
        return "sprint_<1400"
    if d < 1800:
        return "mile_1400_1799"
    if d < 2200:
        return "inter_1800_2199"
    if d < 2600:
        return "stayer_2200_2599"
    return "long_2600+"


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
        y = 1 if bool(fxr.get("hit_at_1")) else (1 if pred == winner else 0)
        venue = str(fxr.get("venue") or race.get("venue") or "unk")
        surface = str(fxr.get("surface") or race.get("surface") or "unk")
        dist = fxr.get("distance")
        try:
            dist_f = float(dist) if dist is not None else None
        except (TypeError, ValueError):
            dist_f = None
        course = f"{venue}|{surface}"
        dbin = distance_bin(dist_f)
        world = str(race.get("cew_world") or "unk")
        out.append(
            {
                "race_id": rid,
                "race_date": fxr.get("race_date"),
                "y_hit": y,
                "world": world,
                "course": course,
                "distance_bin": dbin,
                "venue": venue,
                "surface": surface,
                "distance": dist_f,
                "keys": {
                    "global": "ALL",
                    "course": course,
                    "distance": dbin,
                    "world": world,
                    "world_course": f"{world}||{course}",
                    "world_distance": f"{world}||{dbin}",
                    "world_course_distance": f"{world}||{course}||{dbin}",
                },
            }
        )
    out.sort(key=lambda r: (str(r.get("race_date") or ""), r["race_id"]))
    return out


def fit_rate_table(train: list[dict[str, Any]], key_fn: Callable[[dict[str, Any]], str]) -> dict[str, dict[str, float]]:
    buckets: dict[str, list[int]] = defaultdict(list)
    for r in train:
        buckets[key_fn(r)].append(int(r["y_hit"]))
    table: dict[str, dict[str, float]] = {}
    for k, ys in buckets.items():
        table[k] = {"n": float(len(ys)), "rate": float(np.mean(ys))}
    return table


def lookup_with_backoff(
    r: dict[str, Any],
    primary: str,
    tables: dict[str, dict[str, dict[str, float]]],
    chain: list[str],
    global_rate: float,
) -> tuple[float, str]:
    """Try keys in chain order until cell n >= MIN_CELL."""
    for name in chain:
        key = r["keys"][name] if name != "global" else "ALL"
        cell = tables[name].get(key)
        if cell and cell["n"] >= MIN_CELL:
            return clip01(cell["rate"]), name
    return clip01(global_rate), "global_fallback"


def prior_specs() -> list[dict[str, Any]]:
    """Each prior: name + backoff chain (first = intended granularity)."""
    return [
        {"name": "global", "chain": ["global"]},
        {"name": "course", "chain": ["course", "global"]},
        {"name": "distance", "chain": ["distance", "global"]},
        {"name": "world", "chain": ["world", "global"]},
        {"name": "world_course", "chain": ["world_course", "world", "course", "global"]},
        {"name": "world_distance", "chain": ["world_distance", "world", "distance", "global"]},
        {
            "name": "world_course_distance",
            "chain": ["world_course_distance", "world_course", "world_distance", "world", "course", "distance", "global"],
        },
    ]


def apply_prior(
    rows: list[dict[str, Any]],
    spec: dict[str, Any],
    tables: dict[str, dict[str, dict[str, float]]],
    global_rate: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    y = np.array([r["y_hit"] for r in rows], dtype=float)
    p = []
    src_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        val, src = lookup_with_backoff(r, spec["name"], tables, spec["chain"], global_rate)
        p.append(val)
        src_counts[src] += 1
    return y, np.array(p, dtype=float), dict(src_counts)


def bootstrap_delta(
    y: np.ndarray,
    p_a: np.ndarray,
    p_b: np.ndarray,
    n_boot: int = N_BOOT,
) -> dict[str, Any]:
    """Δ = metric(b) - metric(a); negative means b better for ECE/Brier/LL."""
    n = len(y)
    if n < 20:
        return {"n": n, "status": "insufficient"}
    d_brier = []
    d_ll = []
    d_ece = []
    # For ECE bootstrap on resampled indices
    from app.research._v85_base_probability_audit import brier, log_loss, ece

    for _ in range(n_boot):
        idx = RNG.integers(0, n, size=n)
        ya, pa, pb = y[idx], p_a[idx], p_b[idx]
        d_brier.append(brier(ya, pb) - brier(ya, pa))
        d_ll.append(log_loss(ya, pb) - log_loss(ya, pa))
        ece_b, _ = ece(ya, pb)
        ece_a, _ = ece(ya, pa)
        d_ece.append(ece_b - ece_a)
    def summarize(arr: list[float]) -> dict[str, float]:
        a = np.array(arr)
        return {
            "mean": float(a.mean()),
            "p025": float(np.quantile(a, 0.025)),
            "p975": float(np.quantile(a, 0.975)),
            "p_better": float(np.mean(a < 0)),  # P(Δ<0) = b better
        }

    sb, sll, se = summarize(d_brier), summarize(d_ll), summarize(d_ece)
    # meaningful if 95% CI for ΔBrier entirely < 0 (b better) OR entirely > 0
    brier_sig_better = sb["p975"] < 0
    brier_sig_worse = sb["p025"] > 0
    ece_sig_better = se["p975"] < 0
    return {
        "n": n,
        "status": "ok",
        "delta_brier": sb,
        "delta_log_loss": sll,
        "delta_ece": se,
        "brier_ci_excludes_0_better": brier_sig_better,
        "brier_ci_excludes_0_worse": brier_sig_worse,
        "ece_ci_excludes_0_better": ece_sig_better,
        "world_meaningful_vs_ref": bool(brier_sig_better or ece_sig_better),
    }


def world_slice_metrics(rows: list[dict[str, Any]], p: np.ndarray) -> dict[str, Any]:
    y = np.array([r["y_hit"] for r in rows], dtype=float)
    out = {}
    for w in WORLDS:
        idx = [i for i, r in enumerate(rows) if r["world"] == w]
        if not idx:
            out[w] = {"n": 0}
            continue
        out[w] = metrics(y[idx], p[idx])
        out[w] = {k: v for k, v in out[w].items() if k != "calibration_bins"}
    return out


def run() -> dict[str, Any]:
    rows = load_rows()
    mid = len(rows) // 2
    train, test = rows[:mid], rows[mid:]

    # fit all atomic tables on train
    key_map = {
        "global": lambda r: "ALL",
        "course": lambda r: r["keys"]["course"],
        "distance": lambda r: r["keys"]["distance"],
        "world": lambda r: r["keys"]["world"],
        "world_course": lambda r: r["keys"]["world_course"],
        "world_distance": lambda r: r["keys"]["world_distance"],
        "world_course_distance": lambda r: r["keys"]["world_course_distance"],
    }
    tables = {name: fit_rate_table(train, fn) for name, fn in key_map.items()}
    global_rate = tables["global"]["ALL"]["rate"]

    cell_stats = {
        name: {
            "n_cells": len(tbl),
            "n_cells_ge_min": sum(1 for c in tbl.values() if c["n"] >= MIN_CELL),
            "median_n": float(np.median([c["n"] for c in tbl.values()])) if tbl else 0.0,
            "min_n": float(min(c["n"] for c in tbl.values())) if tbl else 0.0,
            "max_n": float(max(c["n"] for c in tbl.values())) if tbl else 0.0,
        }
        for name, tbl in tables.items()
    }

    results_test: dict[str, Any] = {}
    probs_test: dict[str, np.ndarray] = {}
    for spec in prior_specs():
        y, p, src = apply_prior(test, spec, tables, global_rate)
        m = metrics(y, p)
        results_test[spec["name"]] = {
            "metrics": {k: v for k, v in m.items() if k != "calibration_bins"},
            "calibration_bins": m.get("calibration_bins"),
            "backoff_source_counts": src,
            "world_slice": world_slice_metrics(test, p),
        }
        probs_test[spec["name"]] = p
    y_test = np.array([r["y_hit"] for r in test], dtype=float)

    # Pairwise vs global (primary question)
    pairwise = {}
    for name in probs_test:
        if name == "global":
            continue
        pairwise[f"{name}_vs_global"] = bootstrap_delta(y_test, probs_test["global"], probs_test[name])

    # World vs course / distance (does World beat other single factors?)
    pairwise["world_vs_course"] = bootstrap_delta(y_test, probs_test["course"], probs_test["world"])
    pairwise["world_vs_distance"] = bootstrap_delta(y_test, probs_test["distance"], probs_test["world"])
    # Interactions vs world
    pairwise["world_course_vs_world"] = bootstrap_delta(y_test, probs_test["world"], probs_test["world_course"])
    pairwise["world_distance_vs_world"] = bootstrap_delta(y_test, probs_test["world"], probs_test["world_distance"])
    pairwise["wcd_vs_world"] = bootstrap_delta(y_test, probs_test["world"], probs_test["world_course_distance"])

    # Ranking by ECE then Brier on test
    ranked = sorted(
        [
            {
                "prior": name,
                "ece": results_test[name]["metrics"]["ece"],
                "brier": results_test[name]["metrics"]["brier"],
                "log_loss": results_test[name]["metrics"]["log_loss"],
                "bias": results_test[name]["metrics"]["bias"],
                "p_mean": results_test[name]["metrics"]["p_mean"],
            }
            for name in results_test
        ],
        key=lambda d: (d["ece"], d["brier"]),
    )

    w_vs_g = pairwise.get("world_vs_global") or {}
    if w_vs_g.get("status") == "ok" and w_vs_g.get("world_meaningful_vs_ref"):
        conclusion = "SUPPORTED"
        conclusion_reason = (
            "World Prior は Global より test で有意に良い "
            f"(Brier CI better={w_vs_g.get('brier_ci_excludes_0_better')}, "
            f"ECE CI better={w_vs_g.get('ece_ci_excludes_0_better')}, "
            f"P(ΔBrier<0)={w_vs_g['delta_brier']['p_better']:.3f})"
        )
    elif w_vs_g.get("status") == "ok":
        # check point estimate better but not significant
        point_better = (
            results_test["world"]["metrics"]["brier"] < results_test["global"]["metrics"]["brier"]
            or results_test["world"]["metrics"]["ece"] < results_test["global"]["metrics"]["ece"]
        )
        if point_better:
            conclusion = "INCONCLUSIVE"
            conclusion_reason = (
                "World は点推定で Global より良いが、bootstrap 95% CI は 0 を含み "
                "統計的意味は未証明（標本・World差が小さい可能性）"
            )
        else:
            conclusion = "NOT_SUPPORTED"
            conclusion_reason = "World Prior は Global に対し改善せず（Global Calibration で説明可能）"
    else:
        conclusion = "INCONCLUSIVE"
        conclusion_reason = "bootstrap 不足"

    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "locks": {
            "production": "unchanged",
            "pe": "unchanged",
            "trigger": "unchanged",
            "blueprint": "unchanged",
            "interaction": "unchanged",
        },
        "method": {
            "prior_type": "pure empirical hit_at_1 rate on chronological train half",
            "course_key": "venue|surface",
            "distance_bins": ["sprint_<1400", "mile_1400_1799", "inter_1800_2199", "stayer_2200_2599", "long_2600+"],
            "backoff": f"parent chain if cell n < {MIN_CELL}",
            "bootstrap": N_BOOT,
            "primary_question": "Is World Prior statistically better than Global Prior?",
            "significance": "95% bootstrap CI on ΔBrier or ΔECE excludes 0 in better direction",
        },
        "n_train": len(train),
        "n_test": len(test),
        "global_train_rate": global_rate,
        "cell_stats": cell_stats,
        "ranked_test": ranked,
        "results_test": {
            k: {
                "metrics": v["metrics"],
                "backoff_source_counts": v["backoff_source_counts"],
                "world_slice": v["world_slice"],
            }
            for k, v in results_test.items()
        },
        "calibration_bins_test": {k: v["calibration_bins"] for k, v in results_test.items()},
        "pairwise_bootstrap": pairwise,
        "conclusion": conclusion,
        "conclusion_reason": conclusion_reason,
    }


def _fmt(x: Any, nd: int = 4) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    if isinstance(x, bool):
        return str(x)
    return str(x)


def write_docs(report: dict[str, Any]) -> dict[str, Path]:
    out = ROOT / "docs/research"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    slim = dict(report)
    # keep bins in separate file
    bins = slim.pop("calibration_bins_test", {})
    paths["json"] = out / "_v87-world-prior-value-study.json"
    paths["json"].write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["bins"] = out / "_v87-prior-calibration-bins.json"
    paths["bins"].write_text(json.dumps(bins, ensure_ascii=False, indent=2), encoding="utf-8")

    # Study
    study = [
        "# Version87 — World Prior Value Study",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**Question:** World Prior の Calibration 改善は Global Calibration 以上の意味を持つか？  ",
        "**Locks:** Production / PE / Trigger / Blueprint / Interaction — 非変更 / 実装禁止",
        "",
        f"## Conclusion: **{report['conclusion']}**",
        "",
        report["conclusion_reason"],
        "",
        "## 方法",
        "",
        f"- Prior = chronological train half の empirical `hit_at_1` rate",
        f"- Course = `venue|surface` / Distance = 帯域ビン",
        f"- cell n < {MIN_CELL} は backoff",
        f"- 意味の判定 = bootstrap {N_BOOT} 回、ΔBrier または ΔECE の 95% CI が改善側で 0 を含まない",
        "",
        f"train={report['n_train']} / test={report['n_test']} / global_train_rate={_fmt(report['global_train_rate'])}",
        "",
        "## Cell 統計（train）",
        "",
        "| Prior key | n_cells | n≥min | median n |",
        "|---|---:|---:|---:|",
    ]
    for name, st in report["cell_stats"].items():
        study.append(
            f"| `{name}` | {st['n_cells']} | {st['n_cells_ge_min']} | {_fmt(st['median_n'], 1)} |"
        )

    study += [
        "",
        "## Test 順位（ECE → Brier）",
        "",
        "| Rank | Prior | ECE | Brier | LogLoss | bias |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for i, d in enumerate(report["ranked_test"], 1):
        study.append(
            f"| {i} | `{d['prior']}` | {_fmt(d['ece'])} | {_fmt(d['brier'])} | {_fmt(d['log_loss'])} | {_fmt(d['bias'])} |"
        )

    wvg = report["pairwise_bootstrap"].get("world_vs_global") or {}
    study += [
        "",
        "## 主比較: World vs Global",
        "",
    ]
    if wvg.get("status") == "ok":
        study += [
            f"- ΔBrier mean={_fmt(wvg['delta_brier']['mean'])} CI=[{_fmt(wvg['delta_brier']['p025'])}, {_fmt(wvg['delta_brier']['p975'])}] P(better)={_fmt(wvg['delta_brier']['p_better'])}",
            f"- ΔECE mean={_fmt(wvg['delta_ece']['mean'])} CI=[{_fmt(wvg['delta_ece']['p025'])}, {_fmt(wvg['delta_ece']['p975'])}] P(better)={_fmt(wvg['delta_ece']['p_better'])}",
            f"- ΔLL mean={_fmt(wvg['delta_log_loss']['mean'])} CI=[{_fmt(wvg['delta_log_loss']['p025'])}, {_fmt(wvg['delta_log_loss']['p975'])}]",
            f"- Brier CI excludes 0 (World better): **{wvg['brier_ci_excludes_0_better']}**",
            f"- ECE CI excludes 0 (World better): **{wvg['ece_ci_excludes_0_better']}**",
            "",
        ]

    study += [
        "## World別（test）— Global vs World Prior",
        "",
        "| World | n | Global ECE | World ECE | Global Brier | World Brier |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    g_slice = report["results_test"]["global"]["world_slice"]
    w_slice = report["results_test"]["world"]["world_slice"]
    for w in WORLDS:
        g, wv = g_slice.get(w) or {}, w_slice.get(w) or {}
        if g.get("n", 0) == 0:
            continue
        study.append(
            f"| `{w}` | {g.get('n')} | {_fmt(g.get('ece'))} | {_fmt(wv.get('ece'))} | {_fmt(g.get('brier'))} | {_fmt(wv.get('brier'))} |"
        )

    study += [
        "",
        "## 関連",
        "",
        "- `v87-prior-comparison.md`",
        "- `v87-governance.md`",
        "",
    ]
    paths["study"] = out / "v87-world-prior-study.md"
    paths["study"].write_text("\n".join(study), encoding="utf-8")

    # Comparison
    comp = [
        "# Version87 — Prior Comparison",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "",
        "## 全 Prior 指標（test）",
        "",
        "| Prior | ECE | Brier | LogLoss | p_mean | hit_rate | backoff注記 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for name in [
        "global",
        "course",
        "distance",
        "world",
        "world_course",
        "world_distance",
        "world_course_distance",
    ]:
        m = report["results_test"][name]["metrics"]
        src = report["results_test"][name]["backoff_source_counts"]
        src_s = ", ".join(f"{k}:{v}" for k, v in sorted(src.items()))
        comp.append(
            f"| `{name}` | {_fmt(m['ece'])} | {_fmt(m['brier'])} | {_fmt(m['log_loss'])} | {_fmt(m['p_mean'])} | {_fmt(m['hit_rate'])} | {src_s} |"
        )

    comp += [
        "",
        "## Pairwise bootstrap（Δ = challenger − reference；負 = challenger 改善）",
        "",
        "| Contrast | ΔBrier mean | Brier 95% CI | P(ΔBrier<0) | ΔECE mean | ECE sig better |",
        "|---|---:|---|---:|---:|---|",
    ]
    for key, pw in report["pairwise_bootstrap"].items():
        if pw.get("status") != "ok":
            comp.append(f"| `{key}` | — | insufficient | — | — | — |")
            continue
        ci = f"[{_fmt(pw['delta_brier']['p025'])}, {_fmt(pw['delta_brier']['p975'])}]"
        comp.append(
            f"| `{key}` | {_fmt(pw['delta_brier']['mean'])} | {ci} | {_fmt(pw['delta_brier']['p_better'])} | {_fmt(pw['delta_ece']['mean'])} | {pw['ece_ci_excludes_0_better']} |"
        )

    comp += [
        "",
        "## Calibration Curve（test・主要4）",
        "",
    ]
    for name in ("global", "course", "distance", "world"):
        bb = bins.get(name) or []
        comp += [
            f"### `{name}`",
            "",
            "| bin | n | conf | acc | |gap| |",
            "|---|---:|---:|---:|---:|",
        ]
        for b in bb:
            comp.append(
                f"| [{_fmt(b['lo'],2)},{_fmt(b['hi'],2)}] | {b['n']} | {_fmt(b.get('conf'))} | {_fmt(b.get('acc'))} | {_fmt(b.get('gap'))} |"
            )
        comp.append("")

    comp += [
        "## 解釈ガイド",
        "",
        "1. **Global** が強い → 改善の主因は全体ヒット率への再スケール。",
        "2. **World ≫ Global（CI）** → World 固有の情報価値あり。",
        "3. **Course/Distance ≫ World** → 空間・距離の方が説明力大。",
        "4. **World×* が World を有意に超えない** → 交差項は過分割リスク（backoff 多用）。",
        "",
    ]
    paths["comp"] = out / "v87-prior-comparison.md"
    paths["comp"].write_text("\n".join(comp), encoding="utf-8")

    # Governance
    conc = report["conclusion"]
    if conc == "SUPPORTED":
        next_a = "World Prior を Global と区別して採用候補に残す（Shadow 設計継続可）。Production/PE は別 Decision。"
        verdict = "A"
    elif conc == "INCONCLUSIVE":
        next_a = "標本拡張 or prior 平滑化の再調査（別 Decision）。World 単独の Production 根拠にはまだ不足。"
        verdict = "B"
    else:
        next_a = "Confidence は Global Calibration を主仮説に（World 必須主張は撤回）。Interaction 追加は禁止継続。"
        verdict = "C"

    gov = [
        "# Version87 — Governance（World Prior Value Study）",
        "",
        f"**Date:** {report['generated_at'][:10]}  ",
        f"**Verdict:** **{verdict}** / Conclusion=**{conc}**  ",
        f"**Reason:** {report['conclusion_reason']}  ",
        "**Type:** Research Investigation only",
        "",
        "【Decision】",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | World Prior Value Study |",
        "| Implementation Required | **No** |",
        "| PE / Production Required | **No** |",
        "| Trigger / Blueprint / Interaction | 非変更 |",
        "| Rollback Required | No |",
        f"| Expected Next Action | {next_a} |",
        "",
        "## 遵守",
        "",
        "| 制約 | 結果 |",
        "|---|---|",
        "| 実装禁止 | PASS |",
        "| Production / PE / Trigger / Blueprint / Interaction 非変更 | PASS |",
        "",
        "## 成果物",
        "",
        "- `v87-world-prior-study.md`",
        "- `v87-prior-comparison.md`",
        "- `v87-governance.md`",
        "- `_v87-world-prior-value-study.json`",
        "",
    ]
    paths["gov"] = out / "v87-governance.md"
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
                "conclusion": report["conclusion"],
                "reason": report["conclusion_reason"],
                "ranked_test": report["ranked_test"],
                "world_vs_global": report["pairwise_bootstrap"].get("world_vs_global"),
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
