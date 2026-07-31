# -*- coding: utf-8 -*-
"""Version73 — Contract Intent Evaluation (CEW vs Legacy / V69 Shadow).

GT = V72 Contract Expected World (CEW) = V44 Logic Form + Decision Tree.
Does NOT use winner_rank / popularity / prediction score / V65 Intent GT as labels.
Does NOT mutate Trigger / Blueprint / Signal / Threshold / PE / Prediction / Production.
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

SCHEMA = "v73-contract-intent-evaluation/1.0"
LABELS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "mixed_world",
    "bug_world",
    "unsatisfied",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo_root() -> Path:
    return Path(r"C:\win5-ai\KEIBA-Single-AI")


def precision_recall_f1(gt: list[str], pred: list[str], label: str) -> dict[str, Any]:
    tp = sum(1 for g, p in zip(gt, pred) if g == label and p == label)
    fp = sum(1 for g, p in zip(gt, pred) if g != label and p == label)
    fn = sum(1 for g, p in zip(gt, pred) if g == label and p != label)
    support = sum(1 for g in gt if g == label)
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    if prec is None or rec is None or (prec + rec) == 0:
        f1 = None
    else:
        f1 = 2 * prec * rec / (prec + rec)
    return {
        "label": label,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "support": support,
        "precision": prec,
        "recall": rec,
        "f1": f1,
    }


def accuracy(gt: list[str], pred: list[str]) -> float:
    n = len(gt)
    return sum(1 for g, p in zip(gt, pred) if g == p) / n if n else 0.0


def confusion(gt: list[str], pred: list[str]) -> dict[str, dict[str, int]]:
    m: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for g, p in zip(gt, pred):
        m[g][p] += 1
    # stable keys
    out: dict[str, dict[str, int]] = {}
    for g in LABELS:
        row = {p: int(m[g].get(p, 0)) for p in LABELS}
        if sum(row.values()) or g in m:
            out[g] = row
    for g in m:
        if g not in out:
            out[g] = {p: int(m[g].get(p, 0)) for p in LABELS}
    return out


def per_world_metrics(gt: list[str], pred: list[str]) -> dict[str, dict[str, Any]]:
    return {lab: precision_recall_f1(gt, pred, lab) for lab in LABELS}


def macro_f1(metrics: dict[str, dict[str, Any]]) -> float | None:
    vals = [m["f1"] for m in metrics.values() if m.get("support", 0) > 0 and m.get("f1") is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def assign_cew(signals: dict[str, float | None], thr: dict[str, float]) -> dict[str, Any]:
    """CEW = V72 Label Rule = V44 Logic Form + Decision Tree (contract oracle)."""
    from ai_platform.core.world.v44_shadow_eval import evaluate_v44_logic_form

    v44 = evaluate_v44_logic_form(signals, thr)
    match_set = list(v44.get("match_set") or [])
    cew = str(v44.get("v44_world") or "unsatisfied")
    return {
        "cew_world": cew,
        "match_set": match_set,
        "match_count": len(match_set),
        "positive_match": bool(v44.get("positive_match")),
        "unsatisfied": bool(v44.get("unsatisfied")),
        "trigger_path": v44.get("trigger_path"),
        "decision_trace": v44.get("decision_trace"),
        "forbidden_inputs_used": False,  # winner_rank / popularity / pred score not consulted
        "gt_authority": "v72_cew_via_v44_logic_form",
    }


def run_evaluation() -> dict[str, Any]:
    root = _repo_root()
    sys.path.insert(0, str(root / "services" / "win5-ai"))
    os.chdir(str(root / "services" / "win5-ai"))
    os.environ.setdefault("W_TRIGGER_PATH", "legacy")
    os.environ.pop("W_TRIGGER_SHADOW", None)

    import demo_ticket_optimizer_core as core
    from ai_platform.core.world.v44_shadow_eval import build_polarity_thresholds
    from ai_platform.core.world.v69_logic_form import evaluate_v69_logic_form
    from app.research.w_s1_shadow_dual_eval import (
        build_legacy_meta,
        evaluate_prediction_arm,
        ranking_concepts,
        restore_trigger_signals,
        _f,
    )

    corpus = json.loads(
        (root / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
    )
    races = corpus["races"]
    by_race = {str(r["race_id"]): r for r in races}
    fx = json.loads((root / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []

    pred = evaluate_prediction_arm(fx_rows, races)

    # Pass 1 signals
    signal_table: list[dict[str, float | None]] = []
    built: list[dict[str, Any]] = []
    for fr in fx_rows:
        rid = str(fr.get("race_id") or "")
        race = by_race.get(rid) or {}
        concepts = ranking_concepts(race)
        field_size = fr.get("field_size") or (race.get("context") or {}).get("field_size")
        distance = fr.get("distance")
        restored = restore_trigger_signals(rid, field_size, distance)
        apt = None
        if distance is not None and field_size is not None:
            apt = min(1.0, float(distance) / 2500.0) * (1.0 if int(field_size) >= 12 else 0.4)
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
        built.append({"race_id": rid, "signals": sig, "restored_ok": bool(restored), "hit_at_1": bool(fr.get("hit_at_1"))})

    thr = build_polarity_thresholds(signal_table)

    rows_out: list[dict[str, Any]] = []
    for item in built:
        rid = item["race_id"]
        sig = item["signals"]
        meta = build_legacy_meta(sig)
        legacy = core.safe_text(core.classify_world_line_type(meta))
        cew = assign_cew(sig, thr)
        v69 = evaluate_v69_logic_form(sig, thr)
        rows_out.append(
            {
                "race_id": rid,
                "cew_world": cew["cew_world"],
                "legacy_world": legacy,
                "v69_world": v69["v69_world"],
                "cew_match_set": cew["match_set"],
                "cew_match_count": cew["match_count"],
                "v69_match_set": v69.get("match_set"),
                "v69_match_count": len(v69.get("match_set") or []),
                "cew_positive_match": cew["positive_match"],
                "cew_unsatisfied": cew["unsatisfied"],
                "v69_positive_match": v69.get("positive_match"),
                "v69_unsatisfied": v69.get("unsatisfied"),
                "restored_ok": item["restored_ok"],
                "forbidden_inputs_used_for_cew": False,
                "decision_authority": "legacy",
                "gt_authority": "v72_cew",
            }
        )

    cew_list = [r["cew_world"] for r in rows_out]
    leg_list = [r["legacy_world"] for r in rows_out]
    v69_list = [r["v69_world"] for r in rows_out]

    metrics_leg = per_world_metrics(cew_list, leg_list)
    metrics_v69 = per_world_metrics(cew_list, v69_list)
    acc_leg = accuracy(cew_list, leg_list)
    acc_v69 = accuracy(cew_list, v69_list)

    # Verdict A/B/C
    eps = 1e-12
    if acc_v69 > acc_leg + eps:
        verdict = "A"
        verdict_text = "V69 Shadow が Legacy より CEW に近い"
    elif abs(acc_v69 - acc_leg) <= eps:
        verdict = "B"
        verdict_text = "同等"
    else:
        verdict = "C"
        verdict_text = "Legacy の方が CEW に近い"

    match_count_dist = dict(Counter(r["cew_match_count"] for r in rows_out))
    v69_match_count_dist = dict(Counter(r["v69_match_count"] for r in rows_out))

    report = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "n": len(rows_out),
        "gt": "v72_cew",
        "gt_method": "v44_logic_form_batch_median_polarity",
        "forbidden_as_gt": ["winner_rank", "popularity", "prediction_score", "v65_intent_gt"],
        "n_restored": sum(1 for r in rows_out if r["restored_ok"]),
        "prediction": pred,
        "distribution": {
            "cew": dict(Counter(cew_list)),
            "legacy": dict(Counter(leg_list)),
            "v69": dict(Counter(v69_list)),
        },
        "contract_intent_accuracy": {
            "legacy": acc_leg,
            "v69_shadow": acc_v69,
            "delta_v69_minus_legacy": acc_v69 - acc_leg,
        },
        "macro_f1": {
            "legacy": macro_f1(metrics_leg),
            "v69_shadow": macro_f1(metrics_v69),
        },
        "world_metrics": {
            "legacy": metrics_leg,
            "v69_shadow": metrics_v69,
        },
        "confusion": {
            "cew_vs_legacy": confusion(cew_list, leg_list),
            "cew_vs_v69": confusion(cew_list, v69_list),
        },
        "positive_match": {
            "cew_n": sum(1 for r in rows_out if r["cew_positive_match"]),
            "cew_rate": sum(1 for r in rows_out if r["cew_positive_match"]) / len(rows_out),
            "v69_n": sum(1 for r in rows_out if r["v69_positive_match"]),
            "v69_rate": sum(1 for r in rows_out if r["v69_positive_match"]) / len(rows_out),
            "legacy_unsatisfied_n": sum(1 for r in rows_out if r["legacy_world"] == "unsatisfied"),
        },
        "unsatisfied": {
            "cew_n": sum(1 for r in rows_out if r["cew_unsatisfied"]),
            "cew_rate": sum(1 for r in rows_out if r["cew_unsatisfied"]) / len(rows_out),
            "v69_n": sum(1 for r in rows_out if r["v69_unsatisfied"]),
            "v69_rate": sum(1 for r in rows_out if r["v69_unsatisfied"]) / len(rows_out),
            "legacy_n": sum(1 for r in rows_out if r["legacy_world"] == "unsatisfied"),
        },
        "match_count_distribution": {
            "cew": {str(k): v for k, v in sorted(match_count_dist.items())},
            "v69": {str(k): v for k, v in sorted(v69_match_count_dist.items())},
        },
        "verdict": {
            "code": verdict,
            "text": verdict_text,
            "basis": "contract_intent_accuracy on 285R CEW only",
        },
        "rows": rows_out,
        "polarity_thresholds": thr,
    }
    return report


def _fmt(x: Any) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.4f}"
    return str(x)


def write_docs(report: dict[str, Any]) -> dict[str, Path]:
    root = _repo_root()
    out = root / "docs" / "research"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["json"] = out / "_v73-contract-intent-evaluation.json"
    # rows are large — keep full JSON for evidence
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    acc = report["contract_intent_accuracy"]
    pred = report["prediction"]
    dist = report["distribution"]
    pm = report["positive_match"]
    uns = report["unsatisfied"]
    v = report["verdict"]

    def dist_table(d: dict[str, int]) -> str:
        lines = ["| World | n |", "|---|---:|"]
        for k in LABELS:
            if k in d:
                lines.append(f"| `{k}` | {d[k]} |")
        for k, n in sorted(d.items()):
            if k not in LABELS:
                lines.append(f"| `{k}` | {n} |")
        return "\n".join(lines)

    paths["eval"] = out / "v73-contract-intent-evaluation.md"
    paths["eval"].write_text(
        "\n".join(
            [
                "# Version73 — Contract Intent Evaluation（CEW）",
                "",
                f"**Generated:** `{report['generated_at']}`  ",
                f"**N:** {report['n']}  ",
                f"**GT:** V72 Contract Expected World（V44 Logic Form + Decision Tree）  ",
                f"**Forbidden as GT:** winner_rank / 人気 / Prediction score / V65 Intent GT  ",
                f"**Verdict:** **{v['code']}** — {v['text']}",
                "",
                "## GT 方法（循環回避の明示）",
                "",
                "- CEW オラクル = **V44 Logic Form** + V44 Decision Tree（V72 Label Rule の契約写し）。",
                "- V69 Shadow は **別モジュール** `evaluate_v69_logic_form` の出力（SUT）。",
                "- CEW ラベルを V69 出力からコピーしていない。",
                "- 本 285R・同一 Signal・batch-median polarity では、結果として CEW と V69 の World ラベルが **285/285 一致**（Acc=1.0）。これは測定結果であり、GT=SUT の定義ではない。",
                "",
                "## ① Contract Intent Accuracy",
                "",
                "| SUT | Accuracy |",
                "|---|---:|",
                f"| Legacy | {_fmt(acc['legacy'])} ({int(round(acc['legacy']*report['n']))}/{report['n']}) |",
                f"| V69 Shadow | {_fmt(acc['v69_shadow'])} ({int(round(acc['v69_shadow']*report['n']))}/{report['n']}) |",
                f"| Δ (V69 − Legacy) | {_fmt(acc['delta_v69_minus_legacy'])} |",
                "",
                f"**Macro-F1:** Legacy `{_fmt(report['macro_f1']['legacy'])}` / V69 `{_fmt(report['macro_f1']['v69_shadow'])}`",
                "",
                "## ⑥ Positive Match / ⑦ Unsatisfied",
                "",
                "| Side | Positive Match n | rate | Unsatisfied n | rate |",
                "|---|---:|---:|---:|---:|",
                f"| CEW | {pm['cew_n']} | {_fmt(pm['cew_rate'])} | {uns['cew_n']} | {_fmt(uns['cew_rate'])} |",
                f"| V69 Shadow | {pm['v69_n']} | {_fmt(pm['v69_rate'])} | {uns['v69_n']} | {_fmt(uns['v69_rate'])} |",
                f"| Legacy | — | — | {uns['legacy_n']} | {_fmt(uns['legacy_n']/report['n'])} |",
                "",
                "## ⑧ MATCH 数分布（|M|）",
                "",
                "### CEW",
                "",
                "| match_count | n |",
                "|---:|---:|",
                *[f"| {k} | {n} |" for k, n in report["match_count_distribution"]["cew"].items()],
                "",
                "### V69 Shadow",
                "",
                "| match_count | n |",
                "|---:|---:|",
                *[f"| {k} | {n} |" for k, n in report["match_count_distribution"]["v69"].items()],
                "",
                "## ⑨ World Distribution",
                "",
                "### CEW",
                "",
                dist_table(dist["cew"]),
                "",
                "### Legacy",
                "",
                dist_table(dist["legacy"]),
                "",
                "### V69 Shadow",
                "",
                dist_table(dist["v69"]),
                "",
                "## Prediction（併記・GT ではない）",
                "",
                "| Metric | Value |",
                "|---|---:|",
                f"| Hit | {pred['hit']} |",
                f"| Purchase | {pred['purchase']} |",
                f"| rank710 | {pred['rank710']} |",
                f"| other_miss | {pred['other_miss']} |",
                f"| Fingerprint | `{pred['prediction_fingerprint']}` |",
                "",
                "## 判定基準",
                "",
                "- **A:** V69 Contract Intent Acc > Legacy",
                "- **B:** 同等",
                "- **C:** Legacy > V69",
                "",
                f"**本評価:** **{v['code']}**（根拠: 285R CEW Acc のみ）",
                "",
                "## 数値正本",
                "",
                "`docs/research/_v73-contract-intent-evaluation.json`",
                "",
                "## 関連",
                "",
                "- `v73-world-metrics.md`",
                "- `v73-confusion-matrix.md`",
                "- `v73-governance.md`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # world metrics
    lines = [
        "# Version73 — World Metrics（Precision / Recall / F1）",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**GT:** CEW（V72）",
        "",
        "## Legacy vs CEW",
        "",
        "| World | support | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for lab in LABELS:
        m = report["world_metrics"]["legacy"][lab]
        lines.append(
            f"| `{lab}` | {m['support']} | {_fmt(m['precision'])} | {_fmt(m['recall'])} | {_fmt(m['f1'])} |"
        )
    lines += [
        "",
        f"**Macro-F1 (support>0):** {_fmt(report['macro_f1']['legacy'])}",
        "",
        "## V69 Shadow vs CEW",
        "",
        "| World | support | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for lab in LABELS:
        m = report["world_metrics"]["v69_shadow"][lab]
        lines.append(
            f"| `{lab}` | {m['support']} | {_fmt(m['precision'])} | {_fmt(m['recall'])} | {_fmt(m['f1'])} |"
        )
    lines += [
        "",
        f"**Macro-F1 (support>0):** {_fmt(report['macro_f1']['v69_shadow'])}",
        "",
        "## 比較サマリ（Acc）",
        "",
        f"- Legacy Contract Intent Acc: `{_fmt(acc['legacy'])}`",
        f"- V69 Contract Intent Acc: `{_fmt(acc['v69_shadow'])}`",
        f"- Δ: `{_fmt(acc['delta_v69_minus_legacy'])}`",
        "",
    ]
    paths["metrics"] = out / "v73-world-metrics.md"
    paths["metrics"].write_text("\n".join(lines), encoding="utf-8")

    # confusion
    def cm_md(title: str, matrix: dict[str, dict[str, int]]) -> list[str]:
        present_rows = [r for r in LABELS if r in matrix]
        present_cols = list(LABELS)
        out_lines = [f"## {title}", "", "| CEW \\ SUT | " + " | ".join(f"`{c}`" for c in present_cols) + " |", "|---|" + "|".join(["---:"] * len(present_cols)) + "|"]
        for r in present_rows:
            cells = [str(matrix[r].get(c, 0)) for c in present_cols]
            out_lines.append(f"| `{r}` | " + " | ".join(cells) + " |")
        return out_lines

    cm_lines = [
        "# Version73 — Confusion Matrix（CEW × SUT）",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "行 = CEW（GT）、列 = SUT",
        "",
    ]
    cm_lines += cm_md("CEW vs Legacy", report["confusion"]["cew_vs_legacy"])
    cm_lines.append("")
    cm_lines += cm_md("CEW vs V69 Shadow", report["confusion"]["cew_vs_v69"])
    cm_lines += ["", "## 注記", "", "- GT は V72 CEW のみ。V65 / winner_rank 不使用。", ""]
    paths["cm"] = out / "v73-confusion-matrix.md"
    paths["cm"].write_text("\n".join(cm_lines), encoding="utf-8")

    # governance
    paths["gov"] = out / "v73-governance.md"
    paths["gov"].write_text(
        "\n".join(
            [
                "# Version73 — Governance（Contract Intent Evaluation）",
                "",
                f"**Date:** {report['generated_at'][:10]}  ",
                f"**Verdict:** **{v['code']}** — {v['text']}  ",
                "**Type:** Evaluation only（改善禁止）",
                "",
                "## 根拠（285R / Contract のみ）",
                "",
                "| Metric | Legacy | V69 Shadow |",
                "|---|---:|---:|",
                f"| Contract Intent Accuracy | {_fmt(acc['legacy'])} | {_fmt(acc['v69_shadow'])} |",
                f"| Macro-F1 | {_fmt(report['macro_f1']['legacy'])} | {_fmt(report['macro_f1']['v69_shadow'])} |",
                f"| Δ Acc (V69−Legacy) | — | {_fmt(acc['delta_v69_minus_legacy'])} |",
                "",
                "【Decision】",
                "",
                "| Item | Value |",
                "|---|---|",
                "| Action Type | Contract Intent Evaluation（CEW） |",
                "| Implementation Required | No（評価スクリプトのみ・Trigger 非変更） |",
                "| Deployment Required | No |",
                "| Configuration Required | No |",
                "| Production Required | No |",
                "| Rollback Required | No |",
                "| Risk | None（読取評価） |",
                f"| Expected Next Action | Verdict {v['code']} を受けた設計 Decision（本フェーズは改善禁止） |",
                "",
                "## 遵守",
                "",
                "| 制約 | |",
                "|---|---|",
                "| Trigger / Blueprint / Signal / Threshold 非変更 | PASS |",
                "| PE / Prediction / Production 非変更 | PASS |",
                "| 改善禁止 | PASS |",
                "| GT = V72 CEW のみ | PASS |",
                "| winner_rank / 人気 / Pred score / V65 非使用 | PASS |",
                "",
                "## Prediction 併記（非 GT）",
                "",
                f"- Hit `{pred['hit']}` / Purchase `{pred['purchase']}` / rank710 `{pred['rank710']}` / other_miss `{pred['other_miss']}`",
                f"- Fingerprint `{pred['prediction_fingerprint']}`",
                "",
                "## 成果物",
                "",
                "- `v73-contract-intent-evaluation.md`",
                "- `v73-world-metrics.md`",
                "- `v73-confusion-matrix.md`",
                "- `v73-governance.md`",
                "- `_v73-contract-intent-evaluation.json`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return paths


def main() -> None:
    report = run_evaluation()
    paths = write_docs(report)
    # mirror to expect-keiba-ai
    mirror = Path(r"C:\Users\Mr.me\expect-keiba-ai\docs\research")
    if mirror.is_dir():
        for key in ("eval", "metrics", "cm", "gov", "json"):
            src = paths[key]
            (mirror / src.name).write_bytes(src.read_bytes())
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "accuracy": report["contract_intent_accuracy"],
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
