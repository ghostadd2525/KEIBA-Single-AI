# -*- coding: utf-8 -*-
"""CLI — Version12 Young Horse Intelligence Research (research-only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.young_horse_intelligence import run_and_write


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V12 Young Horse Intelligence Research — no Prediction/Score/Resolver mutation"
    )
    parser.parse_args()
    report = run_and_write()
    sample = report.get("sample") or {}
    print(
        json.dumps(
            {
                "ok": True,
                "young_races": sample.get("young_races_with_evidence"),
                "debut": sample.get("debut_2yo_newcomer"),
                "tie_races": sample.get("tie_races_ge2"),
                "top_features": [
                    r.get("feature_id") for r in (report.get("ranking") or [])[:5]
                ],
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
