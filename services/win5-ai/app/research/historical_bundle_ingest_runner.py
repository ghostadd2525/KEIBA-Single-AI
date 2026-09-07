# -*- coding: utf-8 -*-
"""CLI — Version11.1 Historical Bundle Ingest (research-only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.historical_bundle_ingest import run_and_write


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V11.1 Historical Bundle Ingest — research only, no Prediction mutation"
    )
    parser.add_argument(
        "--no-rebuild-corpus",
        action="store_true",
        help="Skip Prediction Corpus rebuild after ingest",
    )
    args = parser.parse_args()
    report = run_and_write(rebuild_corpus=not args.no_rebuild_corpus)
    print(
        json.dumps(
            {
                "ok": True,
                "unique_races_with_bundle": report.get("unique_races_with_bundle"),
                "unique_tie_races": report.get("unique_tie_races"),
                "unique_unrecoverable_races": report.get("unique_unrecoverable_races"),
                "ingested_bundles": report.get("ingested_bundles"),
                "corpus_before": report.get("_corpus_before"),
                "corpus_after": report.get("_corpus_after"),
                "outputs": report.get("_outputs"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
