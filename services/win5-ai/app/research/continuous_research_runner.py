# -*- coding: utf-8 -*-
"""CLI — Version22 Continuous Research Operation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.continuous_research_operation import run_and_write


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V22 Continuous Research Operation (orchestrate existing platform)"
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Assemble docs from existing reports without re-running pipeline",
    )
    args = parser.parse_args()
    report = run_and_write(report_only=bool(args.report_only))
    print(
        json.dumps(
            {
                "ok": True,
                "week_id": report.get("week_id"),
                "review_queue_n": len(report.get("review_queue") or []),
                "notifications_n": len(report.get("notifications") or []),
                "notifications": report.get("notifications") or [],
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
