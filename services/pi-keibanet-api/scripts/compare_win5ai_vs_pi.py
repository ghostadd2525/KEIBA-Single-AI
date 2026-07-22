# -*- coding: utf-8 -*-
"""
Phase X: Compare Win5AI legacy vs PI API pipeline outputs.

Usage:
  python scripts/compare_win5ai_vs_pi.py \\
    --date 2026-07-19 --venue 福島 --race-no 10 \\
    --legacy-dir C:/win5-ai/data \\
    --pi-dir data/pipeline/2026-07-19

  # Generate PI output first, then compare:
  python scripts/compare_win5ai_vs_pi.py \\
    --date 2026-07-19 --venue 福島 --race-no 10 \\
    --legacy-dir C:/win5-ai/data \\
    --run-pi

Output:
  {output-dir}/compare_report.md
  {output-dir}/compare_diff.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pi_keibanet.compare import (
    compare_all,
    load_baseline,
    result_to_metrics,
    write_diff_csv,
    write_report_md,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Win5AI vs PI API output comparison")
    parser.add_argument("--date", required=True, help="Race date YYYY-MM-DD")
    parser.add_argument("--venue", required=True, help="Venue name (e.g. 福島)")
    parser.add_argument("--race-no", type=int, required=True, help="Race number")
    parser.add_argument(
        "--legacy-dir",
        default=None,
        help="Legacy Win5AI data dir (default: C:/win5-ai/data)",
    )
    parser.add_argument(
        "--pi-dir",
        default=None,
        help="PI pipeline output dir (default: data/pipeline/{date})",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Report output dir (default: data/compare/{date}_{venue}_{race_no}R)",
    )
    parser.add_argument(
        "--run-pi",
        action="store_true",
        help="Run PI pipeline before comparing",
    )
    parser.add_argument(
        "--no-normalize-legacy",
        action="store_true",
        help="Skip legacy history re-fetch normalization (Phase Y-2)",
    )
    parser.add_argument(
        "--numeric-race-id",
        default=None,
        help="Override numeric_race_id (auto-resolved from legacy runners.csv)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    legacy_dir = Path(args.legacy_dir) if args.legacy_dir else Path("C:/win5-ai/data")
    pi_dir = Path(args.pi_dir) if args.pi_dir else root / "data" / "pipeline" / args.date

    if args.run_pi:
        print(f"[compare] Running PI pipeline → {pi_dir}")
        from scripts.run_pipeline import run_pipeline
        run_pipeline(args.date, args.venue, args.race_no, pi_dir)

    race_token = f"{args.date}_{args.venue}_{args.race_no:02d}R"
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else root / "data" / "compare" / race_token
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[compare] Legacy: {legacy_dir}")
    print(f"[compare] PI:     {pi_dir}")
    print(f"[compare] Race:   {args.date} {args.venue} {args.race_no}R")

    result = compare_all(
        date=args.date,
        venue=args.venue,
        race_no=args.race_no,
        legacy_dir=legacy_dir,
        pi_dir=pi_dir,
        numeric_race_id=args.numeric_race_id,
        normalize_legacy=not args.no_normalize_legacy,
    )

    report_path = output_dir / "compare_report.md"
    diff_path = output_dir / "compare_diff.csv"
    baseline_path = output_dir / "baseline_before.json"

    baseline = load_baseline(baseline_path)
    if baseline is None:
        root_baseline = root / "data" / "compare" / race_token / "baseline_before.json"
        baseline = load_baseline(root_baseline)

    write_report_md(
        result,
        report_path,
        legacy_dir=legacy_dir,
        pi_dir=pi_dir,
        baseline=baseline,
    )
    write_diff_csv(result, diff_path)

    after_metrics = result_to_metrics(result)
    (output_dir / "baseline_after.json").write_text(
        __import__("json").dumps(after_metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[compare] numeric_race_id: {result.numeric_race_id}")
    print(f"[compare] Overall match rate: {result.overall_match_rate:.2%}")
    print(f"[compare] Adjusted match rate (excl. netkeiba odds/pop): {result.adjusted_match_rate:.2%}")
    print(f"[compare] Target (99%): {'PASS' if result.passes_target else 'FAIL'}")
    print(f"[compare] Diff rows: {len(result.all_diffs)}")
    print(f"[compare] Report: {report_path}")
    print(f"[compare] Diff CSV: {diff_path}")

    for name, ds in result.datasets.items():
        print(f"  {name}: {ds.legacy_rows}L / {ds.pi_rows}P rows, match={ds.match_rate:.2%}, diffs={len(ds.diffs)}")


if __name__ == "__main__":
    main()
