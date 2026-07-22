# -*- coding: utf-8 -*-
"""E2E: Prediction for all published 2026-07-25 races + Web API race catalog."""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, r"C:\win5-ai")

from pi_keibanet.service import PiKeibaNetService


TARGETS = [
    ("新潟", 6),
    ("新潟", 7),
    ("新潟", 8),
    ("中京", 6),
    ("中京", 7),
    ("中京", 8),
    ("札幌", 10),
    ("札幌", 11),
    ("札幌", 12),
]


def _pct(v: Any) -> str:
    if v is None:
        return "—"
    try:
        x = float(v)
        if x <= 1.0:
            x *= 100.0
        return f"{x:.1f}%"
    except Exception:
        return str(v)


def run_prediction(race_id: str, display: dict[str, Any]) -> dict[str, Any]:
    from ai_platform.core.candidate_evaluation import CorePipeline
    from ai_platform.core.features.feature_loader import FeatureLoader, get_last_failure_reason

    result: dict[str, Any] = {
        **display,
        "prediction_ok": False,
        "feature_loader_ok": False,
        "evaluate_ok": False,
        "ce_ok": False,
        "entries": 0,
        "candidates": 0,
        "top5": [],
        "confidence": None,
        "errors": [],
        "flags": [],
    }

    print(f"[predict] start {display.get('race_label')} race_id={race_id}")
    loader = FeatureLoader(data_root=Path(r"C:\win5-ai\data"))
    loaded = loader.load(race_id)
    if loaded is None:
        reason = get_last_failure_reason() or "FeatureLoader returned None"
        result["errors"].append(f"FeatureLoader: {reason}")
        print(f"[predict] FeatureLoader FAIL: {reason}")
        return result

    result["feature_loader_ok"] = True
    result["entries"] = len(loaded.frame)
    print(f"[predict] FeatureLoader OK rows={result['entries']} source={loaded.feature_source}")

    pipeline = CorePipeline(loader=loader)
    try:
        bundle = pipeline.evaluate(race_id)
    except Exception as exc:
        result["errors"].append(f"evaluate: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return result

    if bundle is None:
        result["errors"].append("evaluate returned None")
        return result

    result["evaluate_ok"] = True
    candidates = bundle.get("candidates") or []
    result["candidates"] = len(candidates)
    result["ce_ok"] = len(candidates) > 0
    result["confidence"] = bundle.get("overall_confidence")

    # Validation flags
    if len(candidates) == 0:
        result["flags"].append("candidates_empty")
    for i, c in enumerate(candidates):
        if c.get("Rank") is None:
            result["flags"].append(f"rank_missing[{i}]")
        if c.get("Confidence") is None:
            result["flags"].append(f"confidence_missing[{i}]")

    top5 = []
    for c in sorted(candidates, key=lambda x: int(x.get("Rank") or 999))[:5]:
        top5.append({
            "rank": c.get("Rank"),
            "horse": c.get("CandidateID"),
            "horse_number": c.get("HorseNumber"),
            "confidence": c.get("Confidence"),
        })
    result["top5"] = top5
    result["prediction_ok"] = (
        result["feature_loader_ok"]
        and result["evaluate_ok"]
        and result["ce_ok"]
        and not result["flags"]
        and not result["errors"]
    )
    print(
        f"[predict] evaluate OK candidates={result['candidates']} "
        f"confidence={result['confidence']} ok={result['prediction_ok']}"
    )
    return result


def main() -> None:
    out_dir = ROOT / "data" / "e2e" / "2026-07-25"
    out_dir.mkdir(parents=True, exist_ok=True)

    svc = PiKeibaNetService()
    catalog = svc.list_races(date="2026-07-25")

    # Index catalog by course + race_number
    by_key: dict[tuple[str, int], dict] = {}
    for race in catalog.get("races") or []:
        by_key[(str(race["course"]), int(race["race_number"]))] = race

    results: list[dict[str, Any]] = []
    lines: list[str] = []
    lines.append("# E2E Prediction + Web API 最終検証 (2026-07-25)")
    lines.append("")
    lines.append("## 1. Prediction 実行結果")
    lines.append("")

    for course, rno in TARGETS:
        race = by_key.get((course, rno))
        if not race:
            block = {
                "race_label": f"{course}{rno}R",
                "course": course,
                "race_number": rno,
                "prediction_ok": False,
                "errors": ["not_in_web_catalog"],
            }
            results.append(block)
            lines.append(f"### {course}{rno}R")
            lines.append("")
            lines.append("Prediction: NG（Web API 一覧に存在しない）")
            lines.append("")
            continue

        rid = race["race_id"]
        display = {
            "race_id": rid,
            "race_date": race.get("race_date"),
            "course": race.get("course"),
            "race_number": race.get("race_number"),
            "race_label": race.get("race_label"),
            "race_name": race.get("race_name") or "",
        }
        pred = run_prediction(rid, display)
        results.append(pred)

        lines.append(f"### {pred['race_label']}")
        lines.append("")
        lines.append(f"- race_id: `{pred['race_id']}`")
        lines.append(f"- race_name: {pred.get('race_name') or '—'}")
        lines.append(f"- Prediction: **{'OK' if pred['prediction_ok'] else 'NG'}**")
        lines.append(f"- FeatureLoader: {'OK' if pred['feature_loader_ok'] else 'NG'}")
        lines.append(f"- evaluate(): {'OK' if pred['evaluate_ok'] else 'NG'}")
        lines.append(f"- Candidate Evaluation: {'OK' if pred['ce_ok'] else 'NG'}")
        lines.append(f"- Entries: {pred['entries']}")
        lines.append(f"- Candidates: {pred['candidates']}件")
        lines.append(f"- Confidence: {_pct(pred.get('confidence'))}")
        if pred.get("errors"):
            lines.append(f"- Errors: {'; '.join(pred['errors'])}")
        if pred.get("flags"):
            lines.append(f"- Flags: {'; '.join(pred['flags'])}")
        lines.append("")
        lines.append("Top5:")
        lines.append("")
        if pred["top5"]:
            for t in pred["top5"]:
                hn = t.get("horse_number")
                hn_s = f"{hn}番 " if hn is not None else ""
                lines.append(
                    f"{t['rank']}位 {hn_s}{t.get('horse')} "
                    f"(Confidence {_pct(t.get('confidence'))})"
                )
        else:
            lines.append("（なし）")
        lines.append("")

    # Summary stats
    ok = [r for r in results if r.get("prediction_ok")]
    ng = [r for r in results if not r.get("prediction_ok")]
    top5_ok = [r for r in results if len(r.get("top5") or []) >= 1]

    lines.append("## 2. 妥当性チェック")
    lines.append("")
    empty_cand = [r for r in results if r.get("evaluate_ok") and r.get("candidates", 0) == 0]
    eval_fail = [r for r in results if not r.get("evaluate_ok")]
    conf_miss = [r for r in results if r.get("evaluate_ok") and r.get("confidence") is None]
    rank_miss = [r for r in results if any(str(f).startswith("rank_missing") for f in (r.get("flags") or []))]
    lines.append(f"- Candidate 0件: {len(empty_cand)}")
    lines.append(f"- evaluate 失敗: {len(eval_fail)}")
    lines.append(f"- Confidence 欠損: {len(conf_miss)}")
    lines.append(f"- Rank 欠損: {len(rank_miss)}")
    lines.append(f"- 空結果: {len([r for r in results if not r.get('top5')])}")
    lines.append("")

    lines.append("## 3. Web API レース一覧")
    lines.append("")
    lines.append(f"GET `/v1/races?date=2026-07-25` → count={catalog.get('count')}")
    lines.append("")
    for venue in catalog.get("venues") or []:
        lines.append(f"### {venue.get('course')}")
        lines.append("")
        for race in venue.get("races") or []:
            lines.append(
                f"- {race.get('race_label')} | race_id=`{race.get('race_id')}` | "
                f"name={race.get('race_name') or '—'}"
            )
        lines.append("")

    lines.append("## 最終報告")
    lines.append("")
    lines.append(f"- Prediction成功レース数: **{len(ok)}** / {len(results)}")
    lines.append(f"- Prediction失敗レース数: **{len(ng)}**")
    lines.append(f"- 推奨馬が正常出力されたレース数: **{len(top5_ok)}**")
    lines.append(f"- Web APIで利用可能なレース数: **{catalog.get('count', 0)}**")
    lines.append("")
    lines.append("### Web公開に向けて残る課題")
    lines.append("")
    lines.append("- オッズ未確定時（shutuba `---.-`）は PI 再取得で odds/popularity が空になる場合がある")
    lines.append("- Collector 形式 race_id と Win5 形式 race_id が併存（Web は Win5 `race_id` を推奨）")
    lines.append("- `/v1/predictions` は FeatureLoader の daily CSV / DB に依存（当日 features 生成が前提）")
    lines.append("- 未公開レース（1R〜5R 等）は一覧に出さない（意図的）。公開後に自動追加される")
    lines.append("")

    report_path = out_dir / "prediction_e2e_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    json_path = out_dir / "prediction_e2e_results.json"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # Console summary in requested format
    print("\n" + "=" * 60)
    for r in results:
        label = r.get("race_label") or f"{r.get('course')}{r.get('race_number')}R"
        print(f"\n{label}")
        print(f"Prediction: {'OK' if r.get('prediction_ok') else 'NG'}")
        print(f"Entries: {r.get('entries', 0)}")
        print(f"Candidates: {r.get('candidates', 0)}件")
        print("Top5:")
        for t in r.get("top5") or []:
            hn = t.get("horse_number")
            hn_s = f"{hn}番 " if hn is not None else ""
            print(f"{t.get('rank')}位 {hn_s}{t.get('horse')} (Confidence {_pct(t.get('confidence'))})")
        print(f"Confidence: {_pct(r.get('confidence'))}")
        if r.get("errors"):
            print("Errors:", "; ".join(r["errors"]))

    print("\n" + "=" * 60)
    print(f"SUCCESS {len(ok)} / FAIL {len(ng)} / TOP5_OK {len(top5_ok)} / WEB {catalog.get('count')}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
