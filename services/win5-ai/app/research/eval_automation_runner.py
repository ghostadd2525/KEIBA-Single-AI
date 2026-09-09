# -*- coding: utf-8 -*-
"""CLI for forward-shadow evaluation sidecar. Not collector --loop."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.eval_automation import run_once  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Forward-shadow evaluation sidecar")
    parser.add_argument("--once", action="store_true", help="Hourly-class evaluation")
    parser.add_argument("--weekly", action="store_true", help="Weekly report sidecar")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    weekly = bool(args.weekly)
    out = run_once(weekly=weekly, dry_run=bool(args.dry_run))
    print(json.dumps(out, ensure_ascii=False))
    if out.get("action") == "skipped_locked":
        return 0
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
