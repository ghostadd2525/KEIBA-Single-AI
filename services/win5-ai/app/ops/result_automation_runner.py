# -*- coding: utf-8 -*-
"""
CLI / scheduler entry — Result Automation runner (Production).

Usage:
  python -m app.ops.result_automation_runner --date 2026-07-19 --trigger manual
  python -m app.ops.result_automation_runner --mode auto
  python -m app.ops.result_automation_runner --date 2026-07-19 --force --trigger retry --parent-run-id 3
  python -m app.ops.result_automation_runner --date 2026-07-19 --evidence-only
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data import db as app_db
from app.ops import state_machine as sm
from app.ops.result_automation import get_result_automation
from app.ops.run_recovery import fail_orphan_active_runs
from app.ops import ra_cadence


def _jst_today() -> str:
    return datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()


def _jst_yesterday() -> str:
    return (datetime.now(ZoneInfo("Asia/Tokyo")).date() - timedelta(days=1)).isoformat()


def _load_race_days() -> set[str]:
    candidates = [
        Path(os_environ("EXPECT_OPS_CALENDAR", "")),
        ROOT.parents[0] / "public" / "config" / "ops-calendar.json",
        ROOT.parents[0] / "config" / "ops-calendar.json",
    ]
    days: set[str] = set()
    for p in candidates:
        if not p or not str(p) or not p.is_file():
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            for d in doc.get("race_days") or []:
                days.add(str(d))
        except (OSError, json.JSONDecodeError):
            continue
    return days


def os_environ(key: str, default: str = "") -> str:
    import os

    return (os.environ.get(key) or default).strip()


def _latest_failed_parent(race_date: str) -> int | None:
    conn = app_db.connect()
    try:
        row = conn.execute(
            """
            SELECT id FROM result_automation_runs
            WHERE race_date=? AND status=?
            ORDER BY id DESC LIMIT 1
            """,
            (race_date, sm.FAILED),
        ).fetchone()
        return int(row["id"]) if row else None
    finally:
        conn.close()


def _has_terminal_success(race_date: str) -> bool:
    conn = app_db.connect()
    try:
        row = conn.execute(
            """
            SELECT id FROM result_automation_runs
            WHERE race_date=? AND status IN (?,?)
            ORDER BY id DESC LIMIT 1
            """,
            (race_date, sm.COMPLETED, sm.DEGRADED),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def recover_orphan_runs() -> list[dict]:
    """起動時: ACTIVE 残存を FAILED 化し、parent_run_id 付き retry を可能にする。"""
    return fail_orphan_active_runs(reason="orphan_active_on_startup")


def run_auto() -> list[dict]:
    """
    Scheduler modes:
    - post-meeting: today if race day (grace handled by timer schedule)
    - next-morning: yesterday catch-up if no COMPLETED/DEGRADED
    - monitor-recovery: retry last FAILED with trigger=retry
    """
    app_db.migrate()
    orphans = recover_orphan_runs()
    days = _load_race_days()
    results: list[dict] = []
    if orphans:
        results.append(
            {
                "status": "orphan_recovery",
                "run_status": "ORPHAN_RECOVERY",
                "orphans_failed": orphans,
            }
        )
    svc = get_result_automation()
    today = _jst_today()
    yesterday = _jst_yesterday()

    mode = os_environ("EXPECT_RA_AUTO_MODE", "all")  # post|morning|recovery|all

    if mode in ("post", "all") and (not days or today in days):
        is_race_day = (not days) or (today in days)
        decision = ra_cadence.decide_today_run(today, is_race_day=is_race_day)
        results.append(
            {
                "status": "cadence",
                "run_status": "CADENCE",
                "decision": decision,
            }
        )
        if decision.get("run"):
            out = svc.run(today, trigger=sm.TRIGGER_SCHEDULED, force=True)
            ra_cadence.mark_ran(
                today,
                {
                    "run_status": out.get("run_status"),
                    "reason": decision.get("reason"),
                    "cadence": decision.get("cadence"),
                },
            )
            results.append(out)
        else:
            results.append(
                {
                    "status": "skipped",
                    "run_status": "SKIPPED",
                    "race_date": today,
                    "reason": decision.get("reason"),
                    "cadence": decision.get("cadence"),
                    "unsettled": decision.get("unsettled"),
                }
            )

    if mode in ("morning", "all") and (not days or yesterday in days):
        if not _has_terminal_success(yesterday):
            parent = _latest_failed_parent(yesterday)
            results.append(
                svc.run(
                    yesterday,
                    trigger=sm.TRIGGER_RETRY if parent else sm.TRIGGER_SCHEDULED,
                    parent_run_id=parent,
                    force=True,
                )
            )

    if mode in ("recovery", "all"):
        # OPS-Monitor recovery: retry most recent FAILED date
        conn = app_db.connect()
        try:
            row = conn.execute(
                """
                SELECT id, race_date FROM result_automation_runs
                WHERE status=? ORDER BY id DESC LIMIT 1
                """,
                (sm.FAILED,),
            ).fetchone()
        finally:
            conn.close()
        if row:
            results.append(
                svc.run(
                    row["race_date"],
                    trigger=sm.TRIGGER_RETRY,
                    parent_run_id=int(row["id"]),
                    force=True,
                )
            )

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Result Automation runner")
    parser.add_argument("--mode", choices=["auto", "date", "recover"], default="date")
    parser.add_argument("--date", help="YYYY-MM-DD")
    parser.add_argument(
        "--trigger",
        choices=[sm.TRIGGER_SCHEDULED, sm.TRIGGER_RETRY, sm.TRIGGER_MANUAL],
        default=sm.TRIGGER_MANUAL,
    )
    parser.add_argument("--parent-run-id", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-result-sync", action="store_true")
    parser.add_argument("--evidence-only", action="store_true")
    args = parser.parse_args(argv)

    app_db.migrate()
    # 起動時 Hardening: ACTIVE orphan → FAILED（date / auto / recover 共通）
    orphans = recover_orphan_runs()

    if args.mode == "recover":
        print(json.dumps({"orphans_failed": orphans}, ensure_ascii=False, indent=2))
        return 0

    if args.mode == "auto":
        out = run_auto()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        bad = [
            r
            for r in out
            if r.get("run_status") == sm.FAILED
        ]
        return 1 if bad else 0

    if not args.date:
        parser.error("--date required unless --mode auto|recover")
    result = get_result_automation().run(
        args.date,
        trigger=args.trigger,
        parent_run_id=args.parent_run_id,
        force=args.force,
        skip_result_sync=args.skip_result_sync,
        evidence_only=args.evidence_only,
    )
    if orphans:
        result = {**result, "orphans_failed": orphans}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("run_status") != sm.FAILED else 1


if __name__ == "__main__":
    raise SystemExit(main())
