#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W3-C Shadow — Shared PAGE-C bounded maiden result acquisition.

Priority: P1 >>> W2 > C4 > W3-C.
Uses shared netkeiba_page_c (W2 SourceHealth + RESULT_URL + NetkeibaClient).
Reuses W3-B parser after HTML on disk.
Rollback: W3C_ENABLED=0 or disable timer (timer must NOT be enabled until Owner).
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

from pi_keibanet.w3_maiden import W3AConfig, run_w3c_acquire

_DEFAULT_W2_UNIT = "expect-w2-haron-shadow.service"
_DEFAULT_C4_UNIT = "expect-c4-page-a1-calendar.service"


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
        description="W3-C Shadow shared PAGE-C bounded acquisition"
    )
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--w3-root", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-races", type=int, default=None)
    parser.add_argument("--max-requests", type=int, default=None)
    parser.add_argument("--max-runtime-sec", type=float, default=None)
    args = parser.parse_args()

    cfg = W3AConfig.from_env(data_root=Path(args.data_root) if args.data_root else None)
    if args.w3_root:
        cfg.w3_root = Path(args.w3_root)
    if args.dry_run:
        cfg.w3c_dry_run = True
        cfg.w3c_fetch_enabled = False
    if args.max_races is not None:
        cfg.max_races_per_run = args.max_races
    if args.max_requests is not None:
        cfg.max_requests_per_run = args.max_requests
    if args.max_runtime_sec is not None:
        cfg.max_runtime_sec = args.max_runtime_sec

    w2_unit = os.environ.get("W3C_W2_UNIT", _DEFAULT_W2_UNIT)
    c4_unit = os.environ.get("W3C_C4_UNIT", _DEFAULT_C4_UNIT)
    report = run_w3c_acquire(
        cfg,
        w2_busy=_unit_busy(w2_unit),
        c4_busy=_unit_busy(c4_unit),
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if report.stopped_block:
        return 2
    if report.paused_p1 or report.yielded_w2 or report.yielded_c4:
        return 0
    if report.errors and report.http_request_count == 0 and report.fetch_ok == 0:
        if not report.cache_hit_no_http and report.enabled and report.fetch_enabled:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
