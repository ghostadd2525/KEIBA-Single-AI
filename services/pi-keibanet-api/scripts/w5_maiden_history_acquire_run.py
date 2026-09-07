#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W5 Shadow — Bounded historical maiden horse-history acquisition.

Priority: P1 >>> W2 > C4 > W3-C > W4 > W5
Rollback: W5_ENABLED=0 or disable timer.
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

from pi_keibanet.w5_maiden_history import (
    W5Config,
    run_w5_acquire,
    run_w5_handoff,
    update_gate_monitor,
)

_DEFAULT_W2 = "expect-w2-haron-shadow.service"
_DEFAULT_C4 = "expect-c4-page-a1-calendar.service"
_DEFAULT_W3C = "expect-w3c-page-c-maiden.service"
_DEFAULT_W4 = "expect-w4-horse-d1d2.service"


def _busy(unit: str) -> bool:
    try:
        p = subprocess.run(
            ["systemctl", "is-active", unit],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return (p.stdout or "").strip() == "active"


def main() -> int:
    parser = argparse.ArgumentParser(description="W5 Shadow bounded horse-history acquisition")
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--w5-root", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-horses", type=int, default=None)
    parser.add_argument("--max-requests", type=int, default=None)
    parser.add_argument("--max-runtime-sec", type=float, default=None)
    parser.add_argument("--horse-id", action="append", default=None)
    args = parser.parse_args()

    cfg = W5Config.from_env(data_root=Path(args.data_root) if args.data_root else None)
    if args.w5_root:
        cfg.w5_root = Path(args.w5_root)
    if args.dry_run:
        cfg.dry_run = True
        cfg.fetch_enabled = False
    if args.max_horses is not None:
        cfg.max_horses_per_run = args.max_horses
    if args.max_requests is not None:
        cfg.max_requests_per_run = args.max_requests
    if args.max_runtime_sec is not None:
        cfg.max_runtime_sec = args.max_runtime_sec

    report = run_w5_acquire(
        cfg,
        w2_busy=lambda: _busy(os.environ.get("W5_W2_UNIT", _DEFAULT_W2)),
        c4_busy=lambda: _busy(os.environ.get("W5_C4_UNIT", _DEFAULT_C4)),
        w3c_busy=lambda: _busy(os.environ.get("W5_W3C_UNIT", _DEFAULT_W3C)),
        w4_busy=lambda: _busy(os.environ.get("W5_W4_UNIT", _DEFAULT_W4)),
        horse_ids=args.horse_id,
    )

    # HTTP0 additive W3→queue sync (does not change bounded fetch settings).
    if os.environ.get("W5_W3_HANDOFF_AFTER_ACQUIRE", "1") not in ("0", "false", "False"):
        try:
            run_w5_handoff(cfg, include_w3_runners=True)
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"w3_handoff:{type(exc).__name__}:{exc}")

    gate = update_gate_monitor(cfg, acquire_report=report.to_dict())
    out = report.to_dict()
    out["gate_monitor"] = {
        "w5_complete": gate.w5_complete,
        "w5_pending": gate.w5_pending,
        "history_class_counts": gate.history_class_counts,
        "winner_resolved": gate.winner_resolved,
        "winner_unresolved": gate.winner_unresolved,
        "winner_resolvability": gate.winner_resolvability,
        "reevaluation_ready": gate.reevaluation_ready,
        "cohort_acquisition_complete": gate.cohort_acquisition_complete,
        "w3_sync": gate.w3_sync,
        "alerts_emitted": gate.alerts_emitted,
        "state_path": str(cfg.w5_root / "gate_monitor_state.json"),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if report.stopped_block:
        return 2
    if gate.reevaluation_ready:
        # Non-zero for operator visibility; acquisition itself is not stopped.
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
