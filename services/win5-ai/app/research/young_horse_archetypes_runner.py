# -*- coding: utf-8 -*-
"""CLI — Version13 Young Horse Archetype Research (research-only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.young_horse_archetypes import run_and_write


def main() -> int:
    argparse.ArgumentParser(
        description="V13 Young Horse Archetype Research — no Score/Prediction/Resolver mutation"
    ).parse_args()
    report = run_and_write()
    sample = report.get("sample") or {}
    top = (report.get("ranking") or [])[:5]
    print(
        json.dumps(
            {
                "ok": True,
                "young_races": sample.get("young_races"),
                "debut_races": sample.get("debut_races"),
                "archetypes": len(report.get("archetypes") or []),
                "top": [
                    {
                        "rank": t.get("rank"),
                        "label": t.get("label"),
                        "win_rate": t.get("win_rate"),
                        "place_rate": t.get("place_rate"),
                        "roi": t.get("roi"),
                    }
                    for t in top
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
