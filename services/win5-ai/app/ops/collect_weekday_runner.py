# -*- coding: utf-8 -*-
"""
CLI / scheduler entry — Collector weekday runner (Production).

既存 CollectPlanner / CollectScheduler / KeibaNetCollector / EtlFromRaw を
平日（月〜金 JST）にオーケストレーションする。新規基盤は作らない。

Usage:
  python -m app.ops.collect_weekday_runner --mode auto
  python -m app.ops.collect_weekday_runner --mode date --date 2026-07-21
  python -m app.ops.collect_weekday_runner --week-id 2026-07-25 --force
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.collect import (
    AvailabilityContext,
    CollectBudget,
    CollectJobRepository,
    CollectPlanner,
    CollectQueue,
    CollectRetry,
    CollectScheduler,
    CollectTargetRepository,
    KeibaNetCollector,
    RaceCalendar,
    evaluate_collect_ops,
    read_manifest,
    run_friday_gate,
)
from app.data.collect.keibanet.client import KeibaNetClient
from app.data.db import connect, migrate
from app.data.etl import ingest_ready_entries_core, ingest_ready_race_meta

JST = ZoneInfo("Asia/Tokyo")


def _env(key: str, default: str = "") -> str:
    return (os.environ.get(key) or default).strip()


def _jst_today() -> date:
    return datetime.now(JST).date()


def _week_id_for_date(d: date) -> str:
    """開催週の土曜（week_id）を返す。"""
    if d.weekday() == 5:
        return d.isoformat()
    if d.weekday() == 6:
        return (d - timedelta(days=1)).isoformat()
    days_until_sat = (5 - d.weekday()) % 7
    if days_until_sat == 0:
        days_until_sat = 7
    saturday = d + timedelta(days=days_until_sat)
    return saturday.isoformat()


def _calendar_paths(week_id: str) -> list[Path]:
    token = week_id.replace("-", "_")
    names = [
        f"week_{token}.json",
        f"{week_id}.json",
        f"calendar_{token}.json",
    ]
    dirs: list[Path] = []
    custom = _env("EXPECT_COLLECT_CALENDAR_DIR")
    if custom:
        dirs.append(Path(custom))
    repo = ROOT.parents[1]
    dirs.extend(
        [
            repo / "config" / "collect-calendars",
            repo / "public" / "config" / "collect-calendars",
        ]
    )
    paths: list[Path] = []
    single = _env("EXPECT_COLLECT_CALENDAR")
    if single:
        paths.append(Path(single))
    for d in dirs:
        for name in names:
            paths.append(d / name)
    return paths


def load_calendar(week_id: str) -> RaceCalendar:
    for path in _calendar_paths(week_id):
        if not path.is_file():
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        cal = RaceCalendar.from_dict(raw)
        if cal.week_id[:10] != week_id[:10]:
            raise ValueError(
                f"calendar week_id mismatch: file={cal.week_id!r} expected={week_id!r}"
            )
        return cal
    tried = ", ".join(str(p) for p in _calendar_paths(week_id)[:6])
    raise FileNotFoundError(
        f"collect calendar not found for week_id={week_id!r}. Tried: {tried}"
    )


def _latest_planner_run_id(week_id: str) -> str | None:
    manifest = read_manifest(week_id)
    if manifest and manifest.get("planner_run_id"):
        return str(manifest["planner_run_id"])
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT planner_run_id FROM collect_runs
            WHERE week_id = ?
            ORDER BY started_at DESC LIMIT 1
            """,
            (week_id,),
        ).fetchone()
        return str(row["planner_run_id"]) if row else None
    finally:
        conn.close()


def _draw_confirmed(as_of: date) -> bool:
    if _env("EXPECT_COLLECT_DRAW_CONFIRMED").lower() in ("1", "true", "yes"):
        return True
    # 木曜以降は枠順確定後とみなす（entries_core enqueue 用）
    return as_of.weekday() >= 3


def ensure_planner(calendar: RaceCalendar, *, as_of: str, draw_confirmed: bool) -> dict[str, Any]:
    week_id = calendar.week_id
    if read_manifest(week_id):
        out: dict[str, Any] = {"action": "planner_skip", "week_id": week_id}
    else:
        plan = CollectPlanner().run(
            calendar,
            availability=AvailabilityContext(
                as_of_date=as_of,
                draw_confirmed=draw_confirmed,
            ),
        )
        out = {
            "action": "planner_run",
            "week_id": week_id,
            "planner_run_id": plan.planner_run_id,
            "jobs_enqueued": plan.jobs_enqueued,
            "enqueued_types": plan.enqueued_types,
        }

    if draw_confirmed:
        planner_run_id = _latest_planner_run_id(week_id)
        targets = CollectTargetRepository().list_by_week(week_id)
        if planner_run_id and targets:
            eq = CollectQueue().enqueue_available(
                planner_run_id=planner_run_id,
                week_id=week_id,
                targets=targets,
                context=AvailabilityContext(
                    as_of_date=as_of,
                    draw_confirmed=True,
                ),
            )
            out["draw_enqueue"] = {
                "jobs_created": eq.jobs_created,
                "jobs_skipped": eq.jobs_skipped,
                "enqueued_types": eq.enqueued_types,
            }
    return out


def _coverage_dir() -> Path:
    custom = _env("EXPECT_COLLECT_COVERAGE_DIR")
    if custom:
        return Path(custom)
    return ROOT / "var" / "collect" / "coverage"


def write_coverage_report(week_id: str, as_of: str, payload: dict[str, Any]) -> str:
    out_dir = _coverage_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"coverage_{week_id.replace('-', '_')}_{as_of.replace('-', '')}.json"
    doc = {
        "schema_version": "expect-collect-coverage/1.0",
        "week_id": week_id,
        "as_of_date": as_of,
        "generated_at": datetime.now(JST).isoformat(),
        **payload,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = out_dir / f"coverage_{week_id.replace('-', '_')}_latest.json"
    latest.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def run_collect_day(*, as_of: str, week_id: str | None = None, force: bool = False) -> dict[str, Any]:
    migrate()
    as_of_date = datetime.strptime(as_of[:10], "%Y-%m-%d").date()
    if as_of_date.weekday() >= 5 and not force:
        return {
            "status": "skipped",
            "reason": "weekend",
            "as_of_date": as_of,
        }

    base_url = _env("EXPECT_KEIBANET_BASE_URL")
    if not base_url:
        return {
            "status": "failed",
            "reason": "EXPECT_KEIBANET_BASE_URL not set",
            "as_of_date": as_of,
        }

    wid = week_id or _week_id_for_date(as_of_date)
    calendar = load_calendar(wid)
    draw = _draw_confirmed(as_of_date)

    result: dict[str, Any] = {
        "status": "ok",
        "as_of_date": as_of,
        "week_id": wid,
        "draw_confirmed": draw,
        "budget_daily_limit": CollectBudget.from_env().daily_limit,
    }

    result["planner"] = ensure_planner(calendar, as_of=as_of, draw_confirmed=draw)

    retry = CollectRetry().process(week_id=wid, as_of_date=as_of)
    result["retry"] = {"requeued": retry.requeued, "job_ids": retry.job_ids}

    budget = CollectBudget.from_env()
    scheduler = CollectScheduler(week_id=wid, as_of_date=as_of, budget=budget)
    client = KeibaNetClient(base_url=base_url)
    collector = KeibaNetCollector(client=client)

    batch = scheduler.dequeue_pending()
    collect_results: list[dict[str, Any]] = []
    for job in batch:
        jr = collector.run_job(str(job["job_id"]))
        collect_results.append(
            {
                "job_id": jr.job_id,
                "final_status": jr.final_status,
                "error": jr.error,
            }
        )
    sched_finish = scheduler.finish()
    result["collect"] = {
        "dequeued": len(batch),
        "budget": budget.as_dict(),
        "manifest_path": sched_finish.manifest_path,
        "jobs": collect_results,
    }

    etl_rm = ingest_ready_race_meta(wid)
    etl_ec = ingest_ready_entries_core(wid)
    result["etl"] = {
        "race_meta": etl_rm.as_dict(),
        "entries_core": etl_ec.as_dict(),
    }

    if as_of_date.weekday() == 4:
        gate = run_friday_gate(wid)
        result["friday_gate"] = gate.as_dict()

    jobs = CollectJobRepository()
    stats = jobs.count_by_status(wid)
    ops = evaluate_collect_ops(wid)
    manifest = read_manifest(wid)
    pending = int(stats.get("PENDING") or 0)
    failed = int(stats.get("FAILED") or 0)
    ready = int(stats.get("READY") or 0)
    partial = int(stats.get("PARTIAL") or 0)

    result["coverage"] = {
        "prediction_ready": ops.prediction_ready,
        "prediction_ready_races": ops.prediction_ready_races,
        "total_races_expected": ops.total_races_expected,
        "jobs_ready": ready,
        "jobs_pending": pending,
        "jobs_failed": failed,
        "jobs_partial": partial,
        "ops_state": ops.state,
        "manifest_budget": (manifest or {}).get("budget"),
    }
    result["coverage_path"] = write_coverage_report(wid, as_of, result["coverage"])
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collector weekday runner (Production)")
    parser.add_argument("--mode", choices=["auto", "date"], default="auto")
    parser.add_argument("--date", help="YYYY-MM-DD (JST as_of)")
    parser.add_argument("--week-id", help="Override week_id (Saturday)")
    parser.add_argument("--force", action="store_true", help="Run even on weekend")
    args = parser.parse_args(argv)

    as_of = args.date or _jst_today().isoformat()
    if args.mode == "auto" and not args.date:
        as_of = _jst_today().isoformat()

    try:
        out = run_collect_day(as_of=as_of, week_id=args.week_id, force=args.force)
    except FileNotFoundError as exc:
        out = {"status": "failed", "reason": str(exc), "as_of_date": as_of}
    except Exception as exc:
        out = {"status": "failed", "reason": repr(exc), "as_of_date": as_of}

    print(json.dumps(out, ensure_ascii=False, indent=2))
    if out.get("status") == "failed":
        return 1
    if out.get("status") == "skipped":
        return 0
    cov = out.get("coverage") or {}
    if int(cov.get("jobs_failed") or 0) > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
