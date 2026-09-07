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

from pi_keibanet.w3_maiden import W3AConfig, run_w3a_handoff, run_w3c_acquire

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

    os.environ.setdefault("GLOBAL_HTTP_BUDGET_COMPONENT", "w3c")
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

    # Fail-closed live HTTP. W3W5_LIVE_HTTP default 0; Production units do not set it.
    # Turning real HTTP on is a later phase, after a Global HTTP budget exists.
    if os.environ.get("W3W5_LIVE_HTTP", "0") not in ("1", "true", "True"):
        cfg.w3c_fetch_enabled = False

    # W3-A connection default OFF. Production units do not set W3A_BEFORE_W3C.
    if os.environ.get("W3A_BEFORE_W3C", "0") in ("1", "true", "True"):
        try:
            handoff = run_w3a_handoff(cfg)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"w3a_handoff_error": f"{type(exc).__name__}:{exc}"}, ensure_ascii=False))
            return 1
        print(json.dumps({"w3a_handoff": handoff.to_dict()}, ensure_ascii=False, indent=2))
        if handoff.errors and handoff.queue_rows_total == 0 and not handoff.supply_skipped_reason:
            return 1

    w2_unit = os.environ.get("W3C_W2_UNIT", _DEFAULT_W2_UNIT)
    c4_unit = os.environ.get("W3C_C4_UNIT", _DEFAULT_C4_UNIT)
    report = run_w3c_acquire(
        cfg,
        w2_busy=_unit_busy(w2_unit),
        c4_busy=_unit_busy(c4_unit),
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if report.stopped_global_budget:
        return 5
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
