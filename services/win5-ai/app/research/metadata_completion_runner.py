# -*- coding: utf-8 -*-
"""CLI — Version16 Metadata Completion Research."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.metadata_completion import run_and_write


def main() -> int:
    argparse.ArgumentParser(
        description="V16 Metadata Completion — research unknown reduction only"
    ).parse_args()
    report = run_and_write()
    print(
        json.dumps(
            {
                "ok": True,
                "run_id": report.get("run_id"),
                "improvement": report.get("improvement"),
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
