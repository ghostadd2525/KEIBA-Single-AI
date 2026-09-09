# -*- coding: utf-8 -*-
"""
CLI / scheduler entry — Result Automation runner (REPAIR).

- One owner per race_date per tick (today / morning / recovery dedup)
- max_attempts enforced for recovery/morning
- NO_RACE_DAY / RETRY_EXHAUSTED do not create retry storms
- Day completeness uses catalog authority (via ra_cadence)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data import db as app_db
from app.ops import state_machine as sm
from app.ops.result_automation import get_result_automation
from app.ops.run_recovery import fail_orphan_active_runs
from app.ops import ra_cadence
from app.ops.netkeiba_results import NetkeibaResultError, fetch_pi_race_catalog
from app.ops.result_day_contract import NO_CATALOG_EXPECTED
from app.ops.result_day_contract import (
    CATALOG_EMPTY_ON_RACE_DAY,
    NO_RACE_DAY,
    RETRY_EXHAUSTED,
    classify_empty_catalog,
    default_max_attempts,
    parse_failure_class,
    retry_eligible,
)


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


def recover_orphan_runs() -> list[dict]:
    return fail_orphan_active_runs(reason="orphan_active_on_startup")


def _latest_run(race_date: str) -> dict[str, Any] | None:
    conn = app_db.connect()
    try:
        row = conn.execute(
            """
            SELECT id, race_date, status, trigger, attempt, max_attempts,
                   error_json, meta_json, parent_run_id
            FROM result_automation_runs
            WHERE race_date=?
            ORDER BY id DESC LIMIT 1
            """,
            (race_date,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _latest_failed_anywhere() -> dict[str, Any] | None:
    conn = app_db.connect()
    try:
        row = conn.execute(
            """
            SELECT id, race_date, status, trigger, attempt, max_attempts,
                   error_json, meta_json, parent_run_id
            FROM result_automation_runs
            WHERE status=?
            ORDER BY id DESC LIMIT 1
            """,
            (sm.FAILED,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def evaluate_retry_gate(row: dict[str, Any] | None, *, is_race_day: bool) -> dict[str, Any]:
    """Decide whether a FAILED/incomplete date may be retried."""
    if not row:
        return {"eligible": True, "reason": "no_prior_run"}
    status = str(row.get("status") or "")
    attempt = int(row.get("attempt") or 1)
    max_attempts = int(row.get("max_attempts") or default_max_attempts())
    fc = parse_failure_class(row.get("error_json"), row.get("meta_json"))
    if fc == CATALOG_EMPTY_ON_RACE_DAY and not is_race_day:
        fc = NO_RACE_DAY
    # Reclassify empty-catalog failures on non-race-day
    if status == sm.FAILED and fc is None:
        err = str(row.get("error_json") or "")
        if "catalog empty" in err.lower():
            fc = classify_empty_catalog(is_race_day=is_race_day)
    ok, reason = retry_eligible(
        attempt=attempt,
        max_attempts=max_attempts,
        failure_class=fc,
        status=status,
    )
    return {
        "eligible": ok,
        "reason": reason,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "failure_class": fc,
        "status": status,
        "run_id": row.get("id"),
        "race_date": row.get("race_date"),
    }


def plan_auto_jobs(
    *,
    today: str,
    yesterday: str,
    mode: str,
    race_days: set[str],
    today_should_run: bool,
    yesterday_day_complete: bool,
    latest_failed: dict[str, Any] | None,
    yesterday_latest: dict[str, Any] | None,
    is_race_day_fn: Any,
) -> list[dict[str, Any]]:
    """
    Build at most one job per race_date.
    Priority: today cadence > yesterday morning > recovery.
    """
    jobs: list[dict[str, Any]] = []
    claimed: set[str] = set()

    def claim(date: str, kind: str, **extra: Any) -> None:
        if date in claimed:
            return
        claimed.add(date)
        jobs.append({"kind": kind, "race_date": date, **extra})

    if mode in ("post", "all") and (not race_days or today in race_days):
        if today_should_run:
            claim(today, "today", trigger=sm.TRIGGER_SCHEDULED)

    if mode in ("morning", "all") and (not race_days or yesterday in race_days):
        if not yesterday_day_complete and yesterday not in claimed:
            is_rd = is_race_day_fn(yesterday)
            gate = evaluate_retry_gate(yesterday_latest, is_race_day=is_rd)
            if gate["eligible"] or (yesterday_latest is None):
                parent = (
                    int(yesterday_latest["id"])
                    if yesterday_latest and yesterday_latest.get("status") == sm.FAILED
                    else None
                )
                claim(
                    yesterday,
                    "morning",
                    trigger=sm.TRIGGER_RETRY if parent else sm.TRIGGER_SCHEDULED,
                    parent_run_id=parent,
                    retry_gate=gate,
                )
            else:
                jobs.append(
                    {
                        "kind": "morning_skipped",
                        "race_date": yesterday,
                        "run_status": "SKIPPED",
                        "status": "skipped",
                        "reason": gate["reason"],
                        "retry_gate": gate,
                        "terminal_no_retry": True,
                    }
                )

    if mode in ("recovery", "all") and latest_failed:
        rd = str(latest_failed.get("race_date") or "")
        if rd and rd not in claimed:
            is_rd = is_race_day_fn(rd)
            gate = evaluate_retry_gate(latest_failed, is_race_day=is_rd)
            if gate["eligible"]:
                claim(
                    rd,
                    "recovery",
                    trigger=sm.TRIGGER_RETRY,
                    parent_run_id=int(latest_failed["id"]),
                    retry_gate=gate,
                )
            else:
                jobs.append(
                    {
                        "kind": "recovery_skipped",
                        "race_date": rd,
                        "run_status": "SKIPPED",
                        "status": "skipped",
                        "reason": gate["reason"],
                        "retry_gate": gate,
                        "terminal_no_retry": True,
                    }
                )

    return jobs


def _pre_run_catalog_gate(race_date, is_race_day):
    """PROD_RA_NO_MEETING_PRE_RUN_GATE_V2: skip only PI success-empty + expected=0 + settled=0."""
    from app.ops.netkeiba_results import NetkeibaResultError, fetch_pi_race_catalog
    from app.ops.result_day_contract import NO_CATALOG_EXPECTED

    try:
        catalog = fetch_pi_race_catalog(race_date)
    except NetkeibaResultError:
        return {"action": "run", "reason": "pi_catalog_failure"}

    if catalog:
        return {
            "action": "run",
            "reason": "catalog_present",
            "catalog_count": len(catalog),
        }

    snap = ra_cadence.count_unsettled_races(
        race_date,
        is_race_day=is_race_day,
        catalog_races=[],
    )
    expected_n = int((snap or {}).get("EXPECTED_RACE_COUNT") or 0)
    settled_n = int((snap or {}).get("SETTLED_RACE_COUNT") or 0)
    if expected_n == 0 and settled_n == 0:
        return {
            "action": "skip",
            "reason": NO_CATALOG_EXPECTED,
            "catalog_count": 0,
            "EXPECTED_RACE_COUNT": expected_n,
            "SETTLED_RACE_COUNT": settled_n,
        }
    return {
        "action": "run",
        "reason": "local_evidence",
        "catalog_count": 0,
        "EXPECTED_RACE_COUNT": expected_n,
        "SETTLED_RACE_COUNT": settled_n,
    }


def run_auto() -> list[dict]:
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
    mode = os_environ("EXPECT_RA_AUTO_MODE", "all")

    def is_race_day_fn(d: str) -> bool:
        return (not days) or (d in days)

    today_is_rd = is_race_day_fn(today)
    decision = None
    today_should_run = False
    if mode in ("post", "all") and (not days or today in days):
        decision = ra_cadence.decide_today_run(today, is_race_day=today_is_rd)
        results.append(
            {"status": "cadence", "run_status": "CADENCE", "decision": decision}
        )
        today_should_run = bool(decision.get("run"))

    y_complete = ra_cadence.is_day_result_complete(
        yesterday, is_race_day=is_race_day_fn(yesterday)
    )
    jobs = plan_auto_jobs(
        today=today,
        yesterday=yesterday,
        mode=mode,
        race_days=days,
        today_should_run=today_should_run,
        yesterday_day_complete=y_complete,
        latest_failed=_latest_failed_anywhere(),
        yesterday_latest=_latest_run(yesterday),
        is_race_day_fn=is_race_day_fn,
    )
    results.append(
        {
            "status": "job_plan",
            "run_status": "PLAN",
            "jobs": [
                {k: j.get(k) for k in ("kind", "race_date", "trigger", "reason")}
                for j in jobs
            ],
            "DUPLICATE_DAY_RUNS": 0,
            "unique_dates": sorted({j["race_date"] for j in jobs if j.get("race_date")}),
        }
    )

    for job in jobs:
        if job.get("kind", "").endswith("_skipped"):
            results.append(job)
            continue
        if job["kind"] not in ("today", "morning", "recovery"):
            results.append(job)
            continue
        _gate = _pre_run_catalog_gate(job["race_date"], is_race_day_fn(job["race_date"]))
        if _gate.get("action") == "skip":
            results.append({
                "status": "skipped",
                "run_status": "NOOP",
                "race_date": job["race_date"],
                "reason": _gate.get("reason") or NO_CATALOG_EXPECTED,
                "result_sync": False,
                "EXPECTED_RACE_COUNT": _gate.get("EXPECTED_RACE_COUNT", 0),
                "SETTLED_RACE_COUNT": _gate.get("SETTLED_RACE_COUNT", 0),
            })
            continue
        out = svc.run(
            job["race_date"],
            trigger=job.get("trigger") or sm.TRIGGER_SCHEDULED,
            parent_run_id=job.get("parent_run_id"),
            force=True,
            max_attempts=default_max_attempts(),
        )
        if job["kind"] == "today":
            ra_cadence.mark_ran(
                today,
                {
                    "run_status": out.get("run_status"),
                    "reason": (decision or {}).get("reason"),
                    "cadence": (decision or {}).get("cadence"),
                },
            )
        # Annotate exhausted failures as non-storm for exit code
        if out.get("run_status") == sm.FAILED:
            gate = job.get("retry_gate") or evaluate_retry_gate(
                _latest_run(job["race_date"]),
                is_race_day=is_race_day_fn(job["race_date"]),
            )
            # After this run, re-check
            post = _latest_run(job["race_date"])
            post_gate = evaluate_retry_gate(
                post, is_race_day=is_race_day_fn(job["race_date"])
            )
            if not post_gate["eligible"]:
                out = {
                    **out,
                    "terminal_no_retry": True,
                    "retry_gate": post_gate,
                    "failure_class": post_gate.get("failure_class") or RETRY_EXHAUSTED,
                }
        results.append(out)

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
            if r.get("run_status") == sm.FAILED and not r.get("terminal_no_retry")
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
        max_attempts=default_max_attempts(),
    )
    if orphans:
        result = {**result, "orphans_failed": orphans}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("run_status") != sm.FAILED else 1


if __name__ == "__main__":
    raise SystemExit(main())
