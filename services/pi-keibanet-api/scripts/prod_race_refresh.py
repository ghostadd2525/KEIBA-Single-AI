#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production race refresh job (systemd oneshot)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.race_refresh import RefreshConfig, now_jst, run_refresh, write_report_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh published races → features")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: today JST)")
    parser.add_argument("--force", action="store_true", help="Run even outside 08:00-20:00 window")
    parser.add_argument(
        "--shadow-dir",
        default=None,
        help="Write features under this data root (demo_daily_outputs/...) instead of PI_DATA_ROOT",
    )
    args = parser.parse_args()

    run_date = args.date or now_jst().date().isoformat()
    config = RefreshConfig.from_env()
    if args.shadow_dir:
        config.features_shadow_dir = Path(args.shadow_dir)
    report = run_refresh(run_date, config=config, force=args.force)
    json_path = write_report_json(report, config)
    print(f"[race-refresh] report → {json_path}")
    if config.features_shadow_dir:
        print(f"[race-refresh] shadow features → {report.daily_features_path}")

    if report.error_count > 0 and report.updated_count == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
