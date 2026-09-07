# -*- coding: utf-8 -*-
"""CLI — Version10.2 Evidence Analyzer (shadow only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.analyzer import run_and_write


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V10.2 Evidence Analyzer — does not change Prediction ranks"
    )
    parser.add_argument("--md", type=str, default="", help="Output markdown path")
    parser.add_argument("--csv", type=str, default="", help="Output CSV path")
    parser.add_argument("--json", type=str, default="", help="Output JSON path")
    args = parser.parse_args()

    report = run_and_write(
        md_path=Path(args.md) if args.md else None,
        csv_path=Path(args.csv) if args.csv else None,
        json_path=Path(args.json) if args.json else None,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "n_races": report["corpus"]["n_races"],
                "baseline_strict_rate": report["corpus"]["baseline_strict_rate"],
                "baseline_soft_rate": report["corpus"]["baseline_soft_rate"],
                "outputs": report.get("_outputs"),
                "top3": (report.get("ranking") or [])[:3],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
