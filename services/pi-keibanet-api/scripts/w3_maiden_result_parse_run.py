#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W3-B — Existing PAGE-C cache → Maiden Result RAW parser (HTTP 0).

Processes only queue_status=cache_available.
Does NOT fetch PAGE-C / D1 / D2. Does NOT start W3-C / W4.
Does NOT modify P1 / W2 / C4.
Rollback: W3B_ENABLED=0.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.w3_maiden import W3AConfig, run_w3b_parse


def main() -> int:
    parser = argparse.ArgumentParser(
        description="W3-B PAGE-C cache maiden result RAW parse (HTTP 0)"
    )
    parser.add_argument("--data-root", default=None, help="Override PI_DATA_ROOT")
    parser.add_argument("--w3-root", default=None, help="Override W3_ROOT")
    args = parser.parse_args()

    cfg = W3AConfig.from_env(data_root=Path(args.data_root) if args.data_root else None)
    if args.w3_root:
        cfg.w3_root = Path(args.w3_root)

    report = run_w3b_parse(cfg)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if report.errors and report.parsed_races == 0 and report.cache_available_input > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
