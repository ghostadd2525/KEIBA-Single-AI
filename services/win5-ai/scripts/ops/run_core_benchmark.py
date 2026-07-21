#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prediction Core accuracy benchmark — hit@1, hit@3, MRR vs labeled results.

Usage:
  cd services/win5-ai
  python scripts/ops/run_core_benchmark.py
  python scripts/ops/run_core_benchmark.py --baseline tests/benchmark/core_kpi_baseline.json
  python scripts/ops/run_core_benchmark.py --write-baseline tests/benchmark/core_kpi_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_platform = Path(__import__("os").environ.get("AI_PLATFORM_ROOT") or "")
if not _platform.is_dir():
    for candidate in (ROOT.parents[2], ROOT.parents[1], ROOT.parent):
        if (candidate / "ai_platform").is_dir():
            _platform = candidate
            break

_overlay = ROOT / "platform" / "core-overlay"
if _platform.is_dir() and _overlay.is_dir():
    from app.core.platform_overlay import apply_platform_overlay

    apply_platform_overlay(_platform, _overlay)

if _platform.is_dir() and str(_platform) not in sys.path:
    sys.path.insert(0, str(_platform))

try:
    import app.core  # noqa: F401
except ImportError:
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Prediction Core KPI benchmark")
    parser.add_argument(
        "--baseline",
        default=str(ROOT / "tests" / "benchmark" / "core_kpi_baseline.json"),
        help="Baseline JSON for regression compare",
    )
    parser.add_argument(
        "--write-baseline",
        metavar="PATH",
        help="Write current KPI as new frozen baseline",
    )
    parser.add_argument("--race-id", action="append", dest="race_ids", default=[])
    parser.add_argument(
        "--result-csv",
        action="append",
        dest="result_paths",
        type=Path,
        default=[],
    )
    parser.add_argument("--no-compare", action="store_true")
    args = parser.parse_args()

    from app.data.core_benchmark import (
        compare_to_baseline,
        run_core_benchmark,
        save_benchmark_report,
    )

    summary = run_core_benchmark(
        race_ids=args.race_ids or None,
        result_paths=args.result_paths or None,
    )
    report_path = save_benchmark_report(summary)
    payload = {
        "schema_version": "core-kpi-baseline/1.0",
        "generated_at": summary.as_dict()["generated_at"],
        "kpi": {
            "hit_at_1": summary.hit_at_1,
            "hit_at_3": summary.hit_at_3,
            "hit_at_5": summary.hit_at_5,
            "mrr": summary.mrr,
            "ndcg_at_5": summary.ndcg_at_5,
            "brier_score": summary.brier_score,
            "log_loss": summary.log_loss,
            "ece": summary.ece,
            "races_evaluated": summary.races_evaluated,
            "avg_field_size": summary.avg_field_size,
        },
        "tolerance": {
            "hit_at_1": 0.05,
            "hit_at_3": 0.05,
            "hit_at_5": 0.05,
            "mrr": 0.05,
            "ndcg_at_5": 0.05,
            "brier_score": 0.05,
            "log_loss": 0.05,
            "ece": 0.05,
        },
    }

    print(json.dumps(payload["kpi"], ensure_ascii=False, indent=2))
    print(f"report: {report_path}", file=sys.stderr)

    if args.write_baseline:
        out = Path(args.write_baseline)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"baseline written: {out}", file=sys.stderr)
        return 0

    if args.no_compare:
        return 0

    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        print(f"baseline missing: {baseline_path} (use --write-baseline to create)", file=sys.stderr)
        return 0

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    cmp = compare_to_baseline(summary, baseline)
    print(json.dumps(cmp, ensure_ascii=False, indent=2))
    return 0 if cmp["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
