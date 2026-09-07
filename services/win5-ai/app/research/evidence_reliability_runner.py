# -*- coding: utf-8 -*-
"""CLI — Version14 Evidence Reliability Research (research-only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.evidence_reliability import run_and_write


def main() -> int:
    argparse.ArgumentParser(
        description="V14 Evidence Reliability Research — no Prediction/Resolver mutation"
    ).parse_args()
    report = run_and_write()
    feats = report.get("features") or []
    print(
        json.dumps(
            {
                "ok": True,
                "sample": report.get("sample"),
                "top_reliability": [
                    {
                        "rank": f.get("rank"),
                        "feature": f.get("label"),
                        "score": f.get("reliability_score"),
                        "coverage": f.get("coverage"),
                        "leak_risk": f.get("leak_risk"),
                    }
                    for f in feats[:5]
                ],
                "archetype_top": ((report.get("archetype_reweight") or {}).get("top") or [])[
                    :5
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
