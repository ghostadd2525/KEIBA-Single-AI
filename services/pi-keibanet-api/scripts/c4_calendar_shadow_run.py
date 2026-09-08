#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C4 Shadow — Historical PAGE-A1 Hybrid Calendar Recovery (Research only).

Does NOT connect to Feature / Prediction / PAGE-C.
P1 has priority via lock file. W2 busy → yield (P1 >>> W2 > C4).
Rollback: C4_ENABLED=0 or disable timer.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.c4_calendar import C4Config, run_c4_shadow

_DEFAULT_W2_UNIT = "expect-w2-haron-shadow.service"


def _w2_service_busy() -> bool:
    """True when W2 oneshot is actively running (eligible/execution contention)."""
    unit = os.environ.get("C4_W2_UNIT", _DEFAULT_W2_UNIT)
    try:
        proc = subprocess.run(
            ["systemctl", "is-active", unit],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return (proc.stdout or "").strip() == "active"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="C4 Shadow PAGE-A1 Hybrid Calendar Recovery"
    )
    parser.add_argument("--data-root", default=None, help="Override PI_DATA_ROOT")
    parser.add_argument("--dry-run", action="store_true", help="Seed/queue only; no HTTP")
    parser.add_argument("--max-dates", type=int, default=None)
    parser.add_argument("--max-requests", type=int, default=None)
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Ensure queue seeded and exit (no fetch)",
    )
    args = parser.parse_args()

    cfg = C4Config.from_env(data_root=Path(args.data_root) if args.data_root else None)
    if args.dry_run or args.seed_only:
        cfg.dry_run = True
        cfg.fetch_enabled = False
    if args.max_dates is not None:
        cfg.max_dates_per_run = args.max_dates
    if args.max_requests is not None:
        cfg.max_requests_per_run = args.max_requests

    report = run_c4_shadow(cfg, w2_busy=_w2_service_busy())
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if report.stopped_block:
        return 2
    if report.paused_p1 or report.yielded_w2:
        return 0
    if report.errors and report.http_request_count == 0 and not report.dry_run:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
