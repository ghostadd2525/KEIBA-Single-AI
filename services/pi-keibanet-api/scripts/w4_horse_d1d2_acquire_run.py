#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W4-C/D Shadow — Bounded D1/D2 acquisition (cache-first).

Priority: P1 >>> W2 > C4 > W3-C > W4
Dedicated SourceHealth for db horse pages.
Timer must NOT be enabled until Owner after Shadow validation.
Rollback: W4CD_ENABLED=0.
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

from pi_keibanet.w4_horse import W4Config, run_w4cd_acquire

_DEFAULT_W2_UNIT = "expect-w2-haron-shadow.service"
_DEFAULT_C4_UNIT = "expect-c4-page-a1-calendar.service"
_DEFAULT_W3C_UNIT = "expect-w3c-page-c-maiden.service"


def _unit_busy(unit: str) -> bool:
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
        description="W4-C/D Shadow bounded D1/D2 acquisition"
    )
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--w4-root", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-horses", type=int, default=None)
    parser.add_argument("--max-requests", type=int, default=None)
    parser.add_argument("--max-runtime-sec", type=float, default=None)
    parser.add_argument("--horse-id", action="append", default=None)
    parser.add_argument("--no-d1", action="store_true")
    parser.add_argument("--no-d2", action="store_true")
    args = parser.parse_args()

    cfg = W4Config.from_env(data_root=Path(args.data_root) if args.data_root else None)
    if args.w4_root:
        cfg.w4_root = Path(args.w4_root)
    if args.dry_run:
        cfg.w4cd_dry_run = True
        cfg.w4cd_fetch_enabled = False
    if args.max_horses is not None:
        cfg.max_horses_per_run = args.max_horses
    if args.max_requests is not None:
        cfg.max_requests_per_run = args.max_requests
    if args.max_runtime_sec is not None:
        cfg.max_runtime_sec = args.max_runtime_sec
    if args.no_d1:
        cfg.fetch_d1 = False
    if args.no_d2:
        cfg.fetch_d2 = False

    w2_unit = os.environ.get("W4_W2_UNIT", _DEFAULT_W2_UNIT)
    c4_unit = os.environ.get("W4_C4_UNIT", _DEFAULT_C4_UNIT)
    w3c_unit = os.environ.get("W4_W3C_UNIT", _DEFAULT_W3C_UNIT)
    report = run_w4cd_acquire(
        cfg,
        w2_busy=_unit_busy(w2_unit),
        c4_busy=_unit_busy(c4_unit),
        w3c_busy=_unit_busy(w3c_unit),
        horse_ids=args.horse_id,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if report.stopped_block:
        return 2
    if report.paused_p1 or report.yielded_w2 or report.yielded_c4 or report.yielded_w3c:
        return 0
    if report.errors and report.http_request_count == 0 and report.d1_fetch_ok == 0 and report.d2_fetch_ok == 0:
        if not (report.d1_cache_hit or report.d2_cache_hit) and report.enabled and report.fetch_enabled:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
