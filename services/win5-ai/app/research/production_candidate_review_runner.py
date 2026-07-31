# -*- coding: utf-8 -*-
"""CLI — Version20 Production Candidate Review."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.production_candidate_review import run_and_write


def main() -> int:
    argparse.ArgumentParser(
        description="V20 Production Candidate Review — design review only, no AI changes"
    ).parse_args()
    report = run_and_write()
    print(
        json.dumps(
            {
                "ok": True,
                "run_id": report.get("run_id"),
                "summary": report.get("summary"),
                "v21_ids": [r.get("knowledge_id") for r in (report.get("v21_candidates") or [])],
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
