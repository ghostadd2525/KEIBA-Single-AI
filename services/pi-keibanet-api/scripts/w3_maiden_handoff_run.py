#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W3-A — C4 Maiden Race Handoff → Canonical Queue (HTTP 0).

Research Layer C only. Does NOT fetch PAGE-C / D1 / D2.
Does NOT modify P1 / W2 / C4 timers or SourceHealth.
Rollback: W3A_ENABLED=0 (queue artifacts remain Research-only).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.w3_maiden import W3AConfig, run_w3a_handoff


def main() -> int:
    parser = argparse.ArgumentParser(
        description="W3-A C4 maiden handoff → canonical queue (HTTP 0)"
    )
    parser.add_argument("--data-root", default=None, help="Override PI_DATA_ROOT")
    parser.add_argument(
        "--w3-root",
        default=None,
        help="Override W3_ROOT (default: {data_root}/var/w3_maiden)",
    )
    args = parser.parse_args()

    cfg = W3AConfig.from_env(data_root=Path(args.data_root) if args.data_root else None)
    if args.w3_root:
        cfg.w3_root = Path(args.w3_root)

    report = run_w3a_handoff(cfg)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if report.errors and report.queue_rows_total == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
