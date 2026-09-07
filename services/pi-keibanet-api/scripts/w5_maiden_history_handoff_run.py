#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W5 — HD-5 recover + handoff seed (HTTP 0)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.w5_maiden_history import (
    W5Config,
    recover_hd5_from_existing_raw,
    run_w5_handoff,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="W5 HD-5 recover + queue handoff (HTTP 0)")
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--w5-root", default=None)
    parser.add_argument("--seed-file", default=None, help="JSON with horse_ids list")
    parser.add_argument("--skip-hd5", action="store_true")
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Enqueue seed horse_ids only (no full W3 runner scan)",
    )
    parser.add_argument(
        "--reset-queue",
        action="store_true",
        help="Replace queue with this handoff result (initial bootstrap)",
    )
    args = parser.parse_args()

    cfg = W5Config.from_env(data_root=Path(args.data_root) if args.data_root else None)
    if args.w5_root:
        cfg.w5_root = Path(args.w5_root)

    out: dict = {}
    if not args.skip_hd5:
        hd5 = recover_hd5_from_existing_raw(cfg)
        out["hd5"] = hd5.to_dict()

    seed_ids = None
    if args.seed_file:
        payload = json.loads(Path(args.seed_file).read_text(encoding="utf-8"))
        seed_ids = list(payload.get("horse_ids") or payload)
    if args.reset_queue and cfg.queue_path.is_file():
        cfg.queue_path.unlink()
    handoff = run_w5_handoff(
        cfg,
        seed_horse_ids=seed_ids,
        include_w3_runners=not args.seed_only,
    )
    out["handoff"] = handoff.to_dict()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
