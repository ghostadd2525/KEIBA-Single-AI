# -*- coding: utf-8 -*-
"""CLI — Version11 Prediction Corpus Expansion (research-only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.prediction_corpus import run_and_write


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V11 Prediction Corpus Expansion — research only, no Prediction mutation"
    )
    parser.add_argument("--prediction-md", type=str, default="")
    parser.add_argument("--tie-md", type=str, default="")
    parser.add_argument("--young-md", type=str, default="")
    parser.add_argument("--json", type=str, default="")
    args = parser.parse_args()

    report = run_and_write(
        prediction_md=Path(args.prediction_md) if args.prediction_md else None,
        tie_md=Path(args.tie_md) if args.tie_md else None,
        young_md=Path(args.young_md) if args.young_md else None,
        json_path=Path(args.json) if args.json else None,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "prediction_count": report.get("prediction_count"),
                "tie_count": report.get("tie_count"),
                "young_horse_count": report.get("young_horse_count"),
                "gap": report.get("gap"),
                "by_source": report.get("by_source"),
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
