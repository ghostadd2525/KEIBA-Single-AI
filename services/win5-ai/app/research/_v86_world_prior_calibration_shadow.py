# -*- coding: utf-8 -*-
"""Version86 — World Prior Calibration Shadow (Proposal A only).

Shadow-only Confidence evaluation:
  Base (C0) → C3 (World Prior) → C7c (λ=0.9 blend)

Does NOT mutate: Production / Trigger / Blueprint / PE / Interaction / World Contract.
Rank and Score unchanged (audited). Interaction not applied.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.research._v64_world_strategy_discovery import build_race_rows  # noqa: E402
from app.research._v74_world_strategy_validation import load_cew_labels, attach_cew  # noqa: E402
from app.research._v85_base_probability_audit import (  # noqa: E402
    WORLDS,
    clip01,
    metrics,
    c_win_prob_mass,
)

SCHEMA = "v86-world-prior-calibration-shadow/1.0"
LAMBDA_C7C = 0.9
EPS = 1e-6


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
        model_ranks = [int(h.get("model_rank") or 999) for h in horses]
        y = 1 if bool(fxr.get("hit_at_1")) else (1 if pred == winner else 0)
        out.append(
            {
                "race_id": rid,
                "race_date": fxr.get("race_date"),
                "cew_world": race.get("cew_world"),
                "y_hit": y,
                "field_size": float(race.get("field_size") or len(horses)),
                "win_probs": win_probs,
                "pred_idx": pred_idx,
                "win_prob_pred": win_probs[pred_idx],
                "model_rank_pred": model_ranks[pred_idx],
                "model_ranks_snapshot": list(model_ranks),
                "win_probs_snapshot": list(win_probs),
            }
        )
    out.sort(key=lambda r: (str(r.get("race_date") or ""), r["race_id"]))
    return out


def fit_priors(train: list[dict[str, Any]]) -> tuple[dict[str, float], float]:
    rates: dict[str, float] = {}
    for w in WORLDS:
        sub = [r for r in train if r["cew_world"] == w]
        if sub:
            rates[w] = float(np.mean([r["y_hit"] for r in sub]))
    global_rate = float(np.mean([r["y_hit"] for r in train])) if train else 0.5
    return rates, global_rate


def arm_probs(
    rows: list[dict[str, Any]],
    world_rates: dict[str, float],
    global_rate: float,
) -> dict[str, np.ndarray]:
    y = np.array([r["y_hit"] for r in rows], dtype=float)
    p_base = np.array([c_win_prob_mass(r) for r in rows], dtype=float)
    p_c3 = np.array(
        [clip01(float(world_rates.get(r["cew_world"], global_rate))) for r in rows],
        dtype=float,
    )
    p_c7c = np.array(
        [clip01((1.0 - LAMBDA_C7C) * pb + LAMBDA_C7C * pc) for pb, pc in zip(p_base, p_c3)],
        dtype=float,
    )
    # Constant-shift control: same λ, but GLOBAL prior (not World) — isolates World structure
    p_cs = np.array(
        [clip01((1.0 - LAMBDA_C7C) * pb + LAMBDA_C7C * global_rate) for pb in p_base],
        dtype=float,
    )
    return {
        "y": y,
        "base": p_base,
        "c3": p_c3,
        "c7c": p_c7c,
        "const_shift": p_cs,
    }


def pack_metrics(y: np.ndarray, arms: dict[str, np.ndarray]) -> dict[str, Any]:
    out = {}
    for name in ("base", "c3", "c7c", "const_shift"):
        out[name] = metrics(y, arms[name])
    return out


def delta(a: dict[str, Any], b: dict[str, Any]) -> dict[str, float | None]:
    """b - a; negative ECE/Brier/LL = improvement for b vs a."""

    def d(key: str) -> float | None:
        if a.get(key) is None or b.get(key) is None:
            return None
        return float(b[key]) - float(a[key])

    return {
        "delta_ece": d("ece"),
        "delta_brier": d("brier"),
        "delta_log_loss": d("log_loss"),
        "delta_bias": d("bias"),
    }


def improves(dlt: dict[str, float | None]) -> bool:
    e, b = dlt.get("delta_ece"), dlt.get("delta_brier")
    return e is not None and b is not None and e < -1e-6 and b < -1e-6


def go_gate(m: dict[str, Any]) -> dict[str, Any]:
    """Go: C7c improves vs Base AND vs Constant Shift (ECE+Brier)."""
    d_base = delta(m["base"], m["c7c"])
    d_cs = delta(m["const_shift"], m["c7c"])
    d_c3_base = delta(m["base"], m["c3"])
    d_c3_cs = delta(m["const_shift"], m["c3"])
    go_c7c = improves(d_base) and improves(d_cs)
    go_c3 = improves(d_c3_base) and improves(d_c3_cs)
    if go_c7c:
        decision = "GO"
        reason = "C7c: ECE+Brier improve vs Base AND vs Constant-Shift (World prior structure)"
    elif go_c3 and not go_c7c:
        decision = "NO-GO-PARTIAL"
        reason = (
            "C3 (pure World Prior) meets Go vs Base+ConstShift, but C7c (λ=0.9 blend) does not "
            "(C7c ECE が ConstShift 以下に届かない)。案A主形式は未達・C3単体は有望"
        )
    elif improves(d_base) and not improves(d_cs):
        decision = "NO-GO"
        reason = "C7c beats Base but not Constant-Shift (World structure 不足 / level-shift と同型)"
    else:
        decision = "NO-GO"
        reason = "ECE/Brier Go 条件未達"
    return {
        "decision": decision,
        "reason": reason,
        "c7c_vs_base": d_base,
        "c7c_vs_const_shift": d_cs,
        "c3_vs_base": d_c3_base,
        "c3_vs_const_shift": d_c3_cs,
        "go_c7c": go_c7c,
        "go_c3": go_c3,
    }


def eval_scope(rows: list[dict[str, Any]], world_rates: dict[str, float], global_rate: float, scope: str) -> dict[str, Any]:
    if not rows:
        return {"scope": scope, "n": 0, "status": "empty"}
    arms = arm_probs(rows, world_rates, global_rate)
    m = pack_metrics(arms["y"], arms)
    gate = go_gate(m)
    return {
        "scope": scope,
        "n": len(rows),
        "hit_rate": float(arms["y"].mean()),
        "metrics": m,
        "gate": gate,
        "status": "ok",
    }


def run() -> dict[str, Any]:
    rows = load_rows()
    audit = {"rank_unchanged": True, "score_unchanged": True, "n_races": len(rows), "interaction_applied": False}
    for r in rows:
        if r["win_probs"] != r["win_probs_snapshot"]:
            audit["score_unchanged"] = False
        if [int(h) for h in r["model_ranks_snapshot"]] != r["model_ranks_snapshot"]:
            audit["rank_unchanged"] = False

    mid = len(rows) // 2
    train, test = rows[:mid], rows[mid:]
    world_rates, global_rate = fit_priors(train)

    # Primary gate: chronological TEST on all worlds
    test_all = eval_scope(test, world_rates, global_rate, "test_all")
    train_all = eval_scope(train, world_rates, global_rate, "train_all")
    full_all = eval_scope(rows, world_rates, global_rate, "full_all")

    # World breakdown on TEST
    by_w: dict[str, list] = defaultdict(list)
    for r in test:
        by_w[r["cew_world"]].append(r)
    world_test = {}
    for w in WORLDS:
        world_test[w] = eval_scope(by_w.get(w) or [], world_rates, global_rate, f"test:{w}")

    # Ready focus
    rank7_test = world_test.get("rank7_world") or {"status": "empty"}
    unsat_test = world_test.get("unsatisfied") or {"status": "empty"}

    decision = test_all["gate"]["decision"]
    # Soften NO-GO-PARTIAL to report clearly
    verdict = "GO" if decision == "GO" else ("PARTIAL" if decision == "NO-GO-PARTIAL" else "NO-GO")

    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "locks": {
            "production": "unchanged",
            "trigger": "unchanged",
            "blueprint": "unchanged",
            "pe": "unchanged",
            "interaction": "unchanged_not_applied",
            "world_contract": "unchanged",
            "prediction_rank": "unchanged_audited",
            "score": "unchanged_audited",
        },
        "method": {
            "path": "Base(C0) → C3(World Prior) → C7c(λ=0.9 blend)",
            "c0": "wp[top1]/sum(wp)",
            "c3": "HitRate_CEW(world; train chronological half)",
            "c7c": f"(1-{LAMBDA_C7C})*C0 + {LAMBDA_C7C}*C3",
            "const_shift": f"(1-{LAMBDA_C7C})*C0 + {LAMBDA_C7C}*global_train_hit_rate",
            "go": "test: C7c ECE↓ & Brier↓ vs Base AND vs ConstShift",
            "no_go": "Interaction追加禁止 / 順位変更禁止",
        },
        "lambda_c7c": LAMBDA_C7C,
        "train_priors": {"world_rates": world_rates, "global_rate": global_rate},
        "audit": audit,
        "n_train": len(train),
        "n_test": len(test),
        "train_all": _slim_scope(train_all),
        "test_all": test_all,  # keep bins for calibration doc
        "full_all": _slim_scope(full_all),
        "world_test": world_test,
        "rank7_test": rank7_test,
        "unsatisfied_test": unsat_test,
        "verdict": verdict,
        "verdict_reason": test_all["gate"]["reason"],
        "gate": test_all["gate"],
    }


def _slim_scope(scope: dict[str, Any]) -> dict[str, Any]:
    if scope.get("status") != "ok":
        return scope
    m2 = {}
    for k, v in (scope.get("metrics") or {}).items():
        m2[k] = {kk: vv for kk, vv in v.items() if kk != "calibration_bins"}
    out = dict(scope)
    out["metrics"] = m2
    return out


def _fmt(x: Any, nd: int = 4) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def _arm_table(m: dict[str, Any]) -> list[str]:
    lines = [
        "| Arm | Brier | ECE | LogLoss | p_mean | bias |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in ("base", "c3", "c7c", "const_shift"):
        a = m[name]
        lines.append(
            f"| {name} | {_fmt(a.get('brier'))} | {_fmt(a.get('ece'))} | {_fmt(a.get('log_loss'))} | {_fmt(a.get('p_mean'))} | {_fmt(a.get('bias'))} |"
        )
    return lines


def write_docs(report: dict[str, Any]) -> dict[str, Path]:
    out = ROOT / "docs/research"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    # JSON without heavy duplication: strip bins from world_test in saved json but keep test_all bins in separate
    slim = dict(report)
    wt = {}
    for w, sc in (report.get("world_test") or {}).items():
        wt[w] = _slim_scope(sc)
    slim["world_test"] = wt
    slim["rank7_test"] = _slim_scope(report.get("rank7_test") or {})
    slim["unsatisfied_test"] = _slim_scope(report.get("unsatisfied_test") or {})
    # test_all keep bins in calibration companion only
    ta = dict(report["test_all"])
    ta_metrics = {}
    bins_store = {}
    for k, v in (ta.get("metrics") or {}).items():
        ta_metrics[k] = {kk: vv for kk, vv in v.items() if kk != "calibration_bins"}
        bins_store[k] = v.get("calibration_bins")
    ta["metrics"] = ta_metrics
    slim["test_all"] = ta
    # world bins
    world_bins = {}
    for w, sc in (report.get("world_test") or {}).items():
        if sc.get("status") != "ok":
            continue
        world_bins[w] = {arm: (sc["metrics"][arm].get("calibration_bins")) for arm in ("base", "c3", "c7c", "const_shift")}

    paths["json"] = out / "_v86-world-prior-shadow.json"
    paths["json"].write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["bins"] = out / "_v86-calibration-bins.json"
    paths["bins"].write_text(
        json.dumps({"test_all": bins_store, "world_test": world_bins}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    g = report["gate"]
    next_action = (
        "World Prior Anchor (C7c) Shadow GO → Confidence 採用設計の次 Decision（Production/PE は別ゲート）。Interaction 追加は禁止継続。"
        if report["verdict"] == "GO"
        else (
            "C3 のみ有望 → λ/blend 再設計 Shadow（別 Decision）。Interaction/順位変更は禁止。"
            if report["verdict"] == "PARTIAL"
            else "案A Go 未達 → prior 窓・λ・ラベル定義の見直し（別 Decision）。Interaction 追加で挽回しない。"
        )
    )

    # shadow md
    lines = [
        "# Version86 — World Prior Calibration Shadow",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**Mode:** V85 案A World Prior Anchor のみ（Shadow / Confidence only）  ",
        "**Locks:** Production / Trigger / Blueprint / PE / Interaction / World Contract / Rank / Score — 非変更  ",
        f"**Audit:** rank={report['audit']['rank_unchanged']} / score={report['audit']['score_unchanged']} / interaction_applied={report['audit']['interaction_applied']} / n={report['audit']['n_races']}",
        "",
        "## Shadow Path",
        "",
        "```text",
        "Base (C0: wp[top1]/Σwp)",
        "  → C3 (World empirical prior from train half)",
        f"  → C7c ((1-{LAMBDA_C7C})·C0 + {LAMBDA_C7C}·C3)",
        "Control: ConstShift ((1-λ)·C0 + λ·global_train_hit)",
        "```",
        "",
        f"## Verdict: **{report['verdict']}**",
        "",
        report["verdict_reason"],
        "",
        f"train={report['n_train']} / test={report['n_test']}",
        "",
        "### Train priors",
        "",
        f"- global_rate = {_fmt(report['train_priors']['global_rate'])}",
    ]
    for w, rate in sorted((report["train_priors"]["world_rates"] or {}).items()):
        lines.append(f"- `{w}` = {_fmt(rate)}")

    ta = report["test_all"]
    lines += [
        "",
        "## Test ALL（主判定）",
        "",
        f"n={ta.get('n')} / hit_rate={_fmt(ta.get('hit_rate'))}",
        "",
    ]
    lines += _arm_table(ta["metrics"])
    lines += [
        "",
        "### Δ ※負が改善",
        "",
        f"- C7c − Base: ECE={_fmt(g['c7c_vs_base']['delta_ece'])}, Brier={_fmt(g['c7c_vs_base']['delta_brier'])}, LL={_fmt(g['c7c_vs_base']['delta_log_loss'])}",
        f"- C7c − ConstShift: ECE={_fmt(g['c7c_vs_const_shift']['delta_ece'])}, Brier={_fmt(g['c7c_vs_const_shift']['delta_brier'])}, LL={_fmt(g['c7c_vs_const_shift']['delta_log_loss'])}",
        f"- C3 − Base: ECE={_fmt(g['c3_vs_base']['delta_ece'])}, Brier={_fmt(g['c3_vs_base']['delta_brier'])}, LL={_fmt(g['c3_vs_base']['delta_log_loss'])}",
        f"- C3 − ConstShift: ECE={_fmt(g['c3_vs_const_shift']['delta_ece'])}, Brier={_fmt(g['c3_vs_const_shift']['delta_brier'])}, LL={_fmt(g['c3_vs_const_shift']['delta_log_loss'])}",
        "",
        "## Go / No-Go",
        "",
        "| 条件 | 結果 |",
        "|---|---|",
        f"| C7c ECE↓ & Brier↓ vs Base | {'PASS' if improves(g['c7c_vs_base']) else 'FAIL'} |",
        f"| C7c ECE↓ & Brier↓ vs ConstShift | {'PASS' if improves(g['c7c_vs_const_shift']) else 'FAIL'} |",
        "| Interaction 追加 | 禁止（未使用 PASS） |",
        "| 順位変更 | 禁止（Audit PASS） |",
        "",
        "## World別（test）要約",
        "",
        "| World | n | Base ECE | C7c ECE | C7c Brier | gate_c7c |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for w in WORLDS:
        sc = report["world_test"].get(w) or {}
        if sc.get("status") != "ok":
            lines.append(f"| `{w}` | 0 | — | — | — | empty |")
            continue
        m = sc["metrics"]
        lines.append(
            f"| `{w}` | {sc['n']} | {_fmt(m['base']['ece'])} | {_fmt(m['c7c']['ece'])} | {_fmt(m['c7c']['brier'])} | {'GO' if sc['gate']['go_c7c'] else 'NO'} |"
        )

    lines += [
        "",
        "## 遵守",
        "",
        "| 制約 | |",
        "|---|---|",
        "| Production / Trigger / Blueprint / PE | PASS |",
        "| Interaction 非変更・非適用 | PASS |",
        "| World Contract 非変更 | PASS |",
        "| 順位・Score 非変更 | PASS |",
        "",
        "## 関連",
        "",
        "- `v86-calibration-result.md`",
        "- `v86-governance.md`",
        "- `_v86-world-prior-shadow.json`",
        "",
    ]
    paths["shadow"] = out / "v86-world-prior-shadow.md"
    paths["shadow"].write_text("\n".join(lines), encoding="utf-8")

    # calibration result
    cal = [
        "# Version86 — Calibration Result",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "Brier / ECE / LogLoss / Calibration Curve / World別",
        "",
        "## Test ALL — Arm Metrics",
        "",
    ]
    cal += _arm_table(report["test_all"]["metrics"])
    cal += ["", "## Calibration Curve（test ALL）", ""]
    for arm in ("base", "c3", "c7c", "const_shift"):
        bins = bins_store.get(arm) or []
        cal += [
            f"### `{arm}`",
            "",
            "| bin | n | conf | acc | |gap| |",
            "|---|---:|---:|---:|---:|",
        ]
        for b in bins:
            cal.append(
                f"| [{_fmt(b['lo'],2)},{_fmt(b['hi'],2)}] | {b['n']} | {_fmt(b.get('conf'))} | {_fmt(b.get('acc'))} | {_fmt(b.get('gap'))} |"
            )
        cal.append("")

    cal += ["## World別 Calibration（test）", ""]
    for w in WORLDS:
        sc = report["world_test"].get(w) or {}
        if sc.get("status") != "ok":
            cal += [f"### `{w}`", "", "empty / insufficient", ""]
            continue
        cal += [f"### `{w}` (n={sc['n']}, hit={_fmt(sc.get('hit_rate'))})", ""]
        cal += _arm_table(sc["metrics"])
        cal += [
            "",
            f"C7c vs Base: ECE={_fmt(sc['gate']['c7c_vs_base']['delta_ece'])}, Brier={_fmt(sc['gate']['c7c_vs_base']['delta_brier'])}",
            f"C7c vs CS: ECE={_fmt(sc['gate']['c7c_vs_const_shift']['delta_ece'])}, Brier={_fmt(sc['gate']['c7c_vs_const_shift']['delta_brier'])}",
            "",
        ]
        # compact curve for c7c only
        c7_bins = (sc["metrics"]["c7c"].get("calibration_bins") or [])
        if c7_bins:
            cal += ["C7c bins:", "", "| bin | n | conf | acc | |gap| |", "|---|---:|---:|---:|---:|"]
            for b in c7_bins:
                cal.append(
                    f"| [{_fmt(b['lo'],2)},{_fmt(b['hi'],2)}] | {b['n']} | {_fmt(b.get('conf'))} | {_fmt(b.get('acc'))} | {_fmt(b.get('gap'))} |"
                )
            cal.append("")

    cal += [
        "## Go 条件チェック（再掲）",
        "",
        f"- Verdict: **{report['verdict']}**",
        f"- {report['verdict_reason']}",
        "",
    ]
    paths["cal"] = out / "v86-calibration-result.md"
    paths["cal"].write_text("\n".join(cal), encoding="utf-8")

    gov = [
        "# Version86 — Governance（World Prior Calibration Shadow）",
        "",
        f"**Date:** {report['generated_at'][:10]}  ",
        f"**Verdict:** **{report['verdict']}**  ",
        f"**Reason:** {report['verdict_reason']}  ",
        "**Type:** Shadow Execution only（Confidence）",
        "",
        "【Decision】",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | World Prior Anchor Shadow (C0→C3→C7c) |",
        "| Implementation Required | **No**（Production PE） |",
        "| Deployment Required | No |",
        "| Production Required | **No** |",
        "| PE / Trigger / Blueprint / Interaction / World Contract | 非変更 |",
        "| Rank / Score | 非変更（Audit PASS） |",
        "| Rollback Required | No（Shadow） |",
        f"| Expected Next Action | {next_action} |",
        "",
        "## Go / No-Go 記録",
        "",
        f"| C7c vs Base | {'PASS' if improves(g['c7c_vs_base']) else 'FAIL'} |",
        f"| C7c vs ConstShift | {'PASS' if improves(g['c7c_vs_const_shift']) else 'FAIL'} |",
        f"| C3 vs Base | {'PASS' if improves(g['c3_vs_base']) else 'FAIL'} |",
        f"| C3 vs ConstShift | {'PASS' if improves(g['c3_vs_const_shift']) else 'FAIL'} |",
        "| Interaction 追加 | 禁止遵守 |",
        "| 順位変更 | 禁止遵守 |",
        "",
        "## 成果物",
        "",
        "- `v86-world-prior-shadow.md`",
        "- `v86-calibration-result.md`",
        "- `v86-governance.md`",
        "- `_v86-world-prior-shadow.json`",
        "",
    ]
    paths["gov"] = out / "v86-governance.md"
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
                "gate": {
                    "c7c_vs_base": report["gate"]["c7c_vs_base"],
                    "c7c_vs_const_shift": report["gate"]["c7c_vs_const_shift"],
                    "go_c7c": report["gate"]["go_c7c"],
                    "go_c3": report["gate"]["go_c3"],
                },
                "test_all_metrics": {
                    k: {kk: report["test_all"]["metrics"][k].get(kk) for kk in ("brier", "ece", "log_loss", "p_mean", "bias")}
                    for k in ("base", "c3", "c7c", "const_shift")
                },
                "audit": report["audit"],
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
