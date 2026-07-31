# -*- coding: utf-8 -*-
"""CLI — Version10.7 Resolver Governance Backfill Replay (research-only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.resolver_governance_backfill import run_and_write


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V10.7 Resolver Governance Backfill Replay — shadow only"
    )
    parser.add_argument("--perm-shuffles", type=int, default=5)
    parser.add_argument("--max-tie-races", type=int, default=150)
    parser.add_argument("--backfill-md", type=str, default="")
    parser.add_argument("--governance-history-md", type=str, default="")
    parser.add_argument("--sample-expansion-md", type=str, default="")
    parser.add_argument("--json", type=str, default="")
    args = parser.parse_args()

    report = run_and_write(
        backfill_md=Path(args.backfill_md) if args.backfill_md else None,
        governance_history_md=Path(args.governance_history_md) if args.governance_history_md else None,
        sample_expansion_md=Path(args.sample_expansion_md) if args.sample_expansion_md else None,
        json_path=Path(args.json) if args.json else None,
        perm_shuffles=args.perm_shuffles,
        max_tie_races=args.max_tie_races,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "tie_races_evaluated": report.get("tie_races_evaluated"),
                "monthly": report.get("monthly")[-3:] if report.get("monthly") else [],
                "yearly": report.get("yearly")[-3:] if report.get("yearly") else [],
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

