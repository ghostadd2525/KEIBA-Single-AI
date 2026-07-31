# -*- coding: utf-8 -*-
"""CLI — Version18 Research Knowledge Base."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.knowledge_base import run_and_write


def main() -> int:
    argparse.ArgumentParser(
        description="V18 Knowledge Base — research only, no product changes"
    ).parse_args()
    report = run_and_write()
    print(
        json.dumps(
            {
                "ok": True,
                "week_id": report.get("week_id"),
                "summary": report.get("summary"),
                "weekly_diff": (report.get("weekly_diff") or {}).get("counts"),
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
