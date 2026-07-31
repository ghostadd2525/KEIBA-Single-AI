# -*- coding: utf-8 -*-
"""CLI — Version15 Weakness Atlas (research-only quantification)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.weakness_atlas import run_and_write


def main() -> int:
    argparse.ArgumentParser(
        description="V15 Weakness Atlas — research quantification only, no product changes"
    ).parse_args()
    report = run_and_write()
    sample = report.get("sample") or {}
    top = (report.get("priority_map") or [])[:5]
    print(
        json.dumps(
            {
                "ok": True,
                "sample": sample,
                "top_priority": [
                    {
                        "axis": t.get("axis"),
                        "segment": t.get("segment"),
                        "weakness_index": t.get("weakness_index"),
                        "priority_score": t.get("priority_score"),
                        "strict_rate": t.get("strict_rate"),
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
