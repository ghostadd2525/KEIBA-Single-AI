# -*- coding: utf-8 -*-
"""CLI — Version17 Evidence Discovery Research."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.evidence_discovery import run_and_write


def main() -> int:
    argparse.ArgumentParser(
        description="V17 Evidence Discovery — research only, no product changes"
    ).parse_args()
    report = run_and_write()
    disc = report.get("evidence_discovery") or {}
    print(
        json.dumps(
            {
                "ok": True,
                "sample": report.get("sample"),
                "confident": (disc.get("counts") or {}).get("confident"),
                "exploratory": (disc.get("counts") or {}).get("exploratory"),
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
