#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W2 Shadow — scheduled incremental Historical Haron acquisition (Research only).

Does NOT connect to Feature / Prediction. P1 has priority via lock file.
Rollback: set W2_ENABLED=0 or disable this unit.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.w2_haron import W2Config, run_w2_shadow


def main() -> int:
    parser = argparse.ArgumentParser(
        description="W2 Shadow Historical Haron incremental acquisition"
    )
    parser.add_argument("--date", default=None, help="YYYY-MM-DD for horse_history_raw intake")
    parser.add_argument(
        "--history-csv",
        default=None,
        help="Explicit horse_history_raw.csv path (overrides --date scan)",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help="Override PI_DATA_ROOT for Layer-B / locks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Intake + cache-promote only (no PAGE-C HTTP)",
    )
    parser.add_argument(
        "--max-races",
        type=int,
        default=None,
        help="Override W2_MAX_RACES_PER_RUN",
    )
    args = parser.parse_args()

    cfg = W2Config.from_env(data_root=Path(args.data_root) if args.data_root else None)
    if args.dry_run:
        cfg.dry_run = True
        cfg.fetch_enabled = False
    if args.max_races is not None:
        cfg.max_races_per_run = args.max_races

    report = run_w2_shadow(
        cfg,
        history_csv=Path(args.history_csv) if args.history_csv else None,
        date=args.date,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if report.stopped_block:
        return 2
    if report.errors and report.http_request_count == 0 and not report.paused_p1:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
