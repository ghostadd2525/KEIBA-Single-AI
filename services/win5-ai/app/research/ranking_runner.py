# -*- coding: utf-8 -*-
"""CLI — Version10.4 Evidence Ranking Engine (shadow only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.ranking_engine import run_and_write


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V10.4 Evidence Ranking Engine — does not change Prediction"
    )
    parser.add_argument("--ranking-md", type=str, default="")
    parser.add_argument("--importance-csv", type=str, default="")
    parser.add_argument("--tier-csv", type=str, default="")
    parser.add_argument("--shadow-md", type=str, default="")
    parser.add_argument("--json", type=str, default="")
    args = parser.parse_args()

    report = run_and_write(
        ranking_md=Path(args.ranking_md) if args.ranking_md else None,
        importance_csv=Path(args.importance_csv) if args.importance_csv else None,
        tier_csv=Path(args.tier_csv) if args.tier_csv else None,
        shadow_md=Path(args.shadow_md) if args.shadow_md else None,
        json_path=Path(args.json) if args.json else None,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "n_tie_races": report["corpus"]["n_tie_races"],
                "tiers": report["tiers"],
                "evidence_priority": report["evidence_priority"],
                "best_shadow": (report.get("shadow_strategies") or [None])[0],
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
