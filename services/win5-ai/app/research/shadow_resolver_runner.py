# -*- coding: utf-8 -*-
"""CLI — Version10.5 Shadow Tie Resolver (shadow only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.shadow_resolver import run_and_write


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V10.5 Shadow Tie Resolver — does not change Prediction"
    )
    parser.add_argument("--shadow-md", type=str, default="")
    parser.add_argument("--weekly-md", type=str, default="")
    parser.add_argument("--dashboard-md", type=str, default="")
    parser.add_argument("--json", type=str, default="")
    args = parser.parse_args()

    report = run_and_write(
        shadow_md=Path(args.shadow_md) if args.shadow_md else None,
        weekly_md=Path(args.weekly_md) if args.weekly_md else None,
        dashboard_md=Path(args.dashboard_md) if args.dashboard_md else None,
        json_path=Path(args.json) if args.json else None,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "n_tie_races": report["corpus"]["n_tie_races"],
                "summary": report["summary"],
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
