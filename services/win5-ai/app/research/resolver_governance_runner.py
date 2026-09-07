# -*- coding: utf-8 -*-
"""CLI — Version10.6 Resolver Governance (shadow-only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.resolver_governance import run_and_write


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V10.6 Resolver Governance — does not change Prediction"
    )
    parser.add_argument("--governance-md", type=str, default="")
    parser.add_argument("--gate-md", type=str, default="")
    parser.add_argument("--confidence-md", type=str, default="")
    parser.add_argument("--weekly-md", type=str, default="")
    parser.add_argument("--json", type=str, default="")
    args = parser.parse_args()

    report = run_and_write(
        governance_md=Path(args.governance_md) if args.governance_md else None,
        gate_md=Path(args.gate_md) if args.gate_md else None,
        confidence_md=Path(args.confidence_md) if args.confidence_md else None,
        weekly_md=Path(args.weekly_md) if args.weekly_md else None,
        json_path=Path(args.json) if args.json else None,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "current_status": report["dashboard"]["current_status"],
                "eligible": report["dashboard"]["eligible"],
                "summary": report["cumulative"],
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
