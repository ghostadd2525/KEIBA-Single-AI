#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export Improvement Evidence for a race date (Production CLI wrapper)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data import db as app_db
from app.ops.result_automation_runner import main as runner_main


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("--force", action="store_true", default=True)
    parser.add_argument("--skip-result-sync", action="store_true")
    args = parser.parse_args()
    app_db.migrate()
    argv = ["--date", args.date, "--trigger", args.trigger, "--force"]
    if args.skip_result_sync:
        argv.append("--skip-result-sync")
    return runner_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
