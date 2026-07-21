# -*- coding: utf-8 -*-
"""Collector C-2 E2E — calendar → Planner → Queue → Scheduler → Collector → READY."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.data.collect import (
    CollectBudget,
    CollectJobRepository,
    CollectPlanner,
    CollectRetry,
    CollectRunRepository,
    CollectScheduler,
    CollectTargetRepository,
    KeibaNetCollector,
    RaceCalendar,
    read_manifest,
    state,
)
from app.data.collect.keibanet.client import KeibaNetClient
from app.data.db import migrate


def _race_meta_payload(date: str, venue: str, race_no: int) -> dict:
    race_id = f"{date.replace('-', '')}_{race_no:02d}_{venue}"
    return {
        "race_id": race_id,
        "date": date,
        "venue": venue,
        "race_no": race_no,
        "distance": 2000,
        "surface": "芝",
    }


class _DynamicRaceMetaHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/v1/static/race_meta":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        date = params.get("date", [""])[0]
        venue = params.get("venue", [""])[0]
        race_no = int(params.get("race_no", ["0"])[0])
        body = json.dumps(
            _race_meta_payload(date, venue, race_no),
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _MockServer:
    def __init__(self) -> None:
        self._httpd = HTTPServer(("127.0.0.1", 0), _DynamicRaceMetaHandler)
        self.port = self._httpd.server_address[1]
        self.thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self.thread.join(timeout=3)


def _sample_calendar() -> RaceCalendar:
    return RaceCalendar.from_dict(
        {
            "calendar_version": "jra-calendar-2026-w30-c2",
            "week_id": "2026-07-25",
            "days": [
                {"race_date": "2026-07-25", "venues": {"函館": 1}},
                {"race_date": "2026-07-26", "venues": {"小倉": 1}},
            ],
        }
    )


class CollectC2E2ETest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        root = Path(self._tmpdir.name)
        os.environ["EXPECT_AI_DB_PATH"] = str(root / "collect_c2.db")
        os.environ["EXPECT_COLLECT_RAW_DIR"] = str(root / "raw")
        os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(root / "manifests")
        os.environ["EXPECT_COLLECT_DAILY_LIMIT"] = "10"
        migrate()

    def tearDown(self) -> None:
        for key in (
            "EXPECT_AI_DB_PATH",
            "EXPECT_COLLECT_RAW_DIR",
            "EXPECT_COLLECT_MANIFEST_DIR",
            "EXPECT_COLLECT_DAILY_LIMIT",
            "EXPECT_KEIBANET_BASE_URL",
        ):
            os.environ.pop(key, None)
        self._tmpdir.cleanup()

    def _run_pipeline(self) -> None:
        calendar = _sample_calendar()
        budget = CollectBudget(daily_limit=10)

        planner = CollectPlanner(budget=budget)
        plan = planner.run(calendar, scheduled_for="2026-07-21")

        self.assertEqual(plan.targets_count, 2)
        self.assertEqual(plan.jobs_enqueued, 2)

        targets = CollectTargetRepository().list_by_week("2026-07-25")
        self.assertEqual(len(targets), 2)

        jobs = CollectJobRepository().list_by_week("2026-07-25")
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.assertEqual(job["artifact_type"], "race_meta")
            self.assertEqual(job["kind"], "STATIC_CORE")
            self.assertEqual(job["priority"], "P1")
            self.assertEqual(job["status"], state.PENDING)

        manifest = read_manifest("2026-07-25")
        assert manifest is not None
        self.assertEqual(manifest["races"]["total_races_expected"], 2)
        self.assertEqual(manifest["collect"]["ready"], 0)

        server = _MockServer()
        try:
            os.environ["EXPECT_KEIBANET_BASE_URL"] = server.base_url
            client = KeibaNetClient(base_url=server.base_url, max_retries=0, min_interval_sec=0)
            collector = KeibaNetCollector(client=client)

            CollectRetry().process(week_id="2026-07-25", as_of_date="2026-07-21")

            scheduler = CollectScheduler(
                week_id="2026-07-25",
                as_of_date="2026-07-21",
                budget=CollectBudget(daily_limit=10),
            )

            processed = 0
            while True:
                batch = scheduler.dequeue_pending()
                if not batch:
                    break
                for job in batch:
                    result = collector.run_job(str(job["job_id"]))
                    processed += 1
                    self.assertIn(result.final_status, (state.READY, state.PARTIAL))

            self.assertEqual(processed, 2)
            sched_result = scheduler.finish()
            self.assertTrue(Path(sched_result.manifest_path).is_file())
        finally:
            server.close()

        final_manifest = read_manifest("2026-07-25")
        assert final_manifest is not None
        self.assertEqual(final_manifest["collect"]["ready"], 2)
        self.assertEqual(final_manifest["races"]["total_races_ready"], 2)
        self.assertEqual(final_manifest["budget"]["used"], 2)
        self.assertEqual(final_manifest["budget"]["remaining"], 8)

        ready_jobs = CollectJobRepository().list_by_week("2026-07-25", status=state.READY)
        self.assertEqual(len(ready_jobs), 2)

    def test_e2e_calendar_to_ready(self) -> None:
        self._run_pipeline()

    def test_planner_expands_all_venues_and_races(self) -> None:
        calendar = RaceCalendar.from_dict(
            {
                "calendar_version": "jra-calendar-2026-w30-full",
                "week_id": "2026-07-25",
                "days": [
                    {"race_date": "2026-07-25", "venues": {"函館": 12, "新潟": 12}},
                    {"race_date": "2026-07-26", "venues": {"函館": 12, "新潟": 12}},
                ],
            }
        )
        self.assertEqual(calendar.total_races_expected(), 48)
        planner = CollectPlanner(budget=CollectBudget(daily_limit=200))
        result = planner.run(calendar)
        self.assertEqual(result.targets_count, 48)
        self.assertEqual(result.jobs_enqueued, 48)


class CollectC2BudgetTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        root = Path(self._tmpdir.name)
        os.environ["EXPECT_AI_DB_PATH"] = str(root / "budget.db")
        migrate()

    def tearDown(self) -> None:
        os.environ.pop("EXPECT_AI_DB_PATH", None)
        self._tmpdir.cleanup()

    def test_dequeue_stops_on_budget(self) -> None:
        jobs = CollectJobRepository()
        runs = CollectRunRepository()
        targets = CollectTargetRepository()

        run = runs.create(week_id="2026-07-25", calendar_version="test")
        inserted = targets.insert_many(
            planner_run_id=run["planner_run_id"],
            targets=[
                {
                    "week_id": "2026-07-25",
                    "calendar_version": "test",
                    "race_date": "2026-07-25",
                    "venue": "函館",
                    "race_no": 1,
                },
                {
                    "week_id": "2026-07-25",
                    "calendar_version": "test",
                    "race_date": "2026-07-25",
                    "venue": "函館",
                    "race_no": 2,
                },
            ],
        )
        for i, t in enumerate(inserted):
            jobs.create(
                job_id=f"job-budget-{i}",
                week_id="2026-07-25",
                race_date="2026-07-25",
                artifact_type="race_meta",
                kind="STATIC_CORE",
                priority="P1",
                target_id=t["id"],
                scheduled_for="2026-07-21",
            )

        budget = CollectBudget(daily_limit=1)
        batch = jobs.dequeue_pending(
            week_id="2026-07-25",
            as_of_date="2026-07-21",
            budget=budget,
        )
        self.assertEqual(len(batch), 1)
        self.assertEqual(budget.used, 1)
        self.assertEqual(budget.remaining, 0)

        batch2 = jobs.dequeue_pending(
            week_id="2026-07-25",
            as_of_date="2026-07-21",
            budget=budget,
        )
        self.assertEqual(len(batch2), 0)


class CollectC2RetryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ["EXPECT_AI_DB_PATH"] = str(Path(self._tmpdir.name) / "retry.db")
        migrate()

    def tearDown(self) -> None:
        os.environ.pop("EXPECT_AI_DB_PATH", None)
        self._tmpdir.cleanup()

    def test_retry_after_requeues_pending(self) -> None:
        jobs = CollectJobRepository()
        runs = CollectRunRepository()
        targets = CollectTargetRepository()

        run = runs.create(week_id="2026-07-25", calendar_version="test")
        inserted = targets.insert_many(
            planner_run_id=run["planner_run_id"],
            targets=[
                {
                    "week_id": "2026-07-25",
                    "calendar_version": "test",
                    "race_date": "2026-07-25",
                    "venue": "函館",
                    "race_no": 5,
                }
            ],
        )
        jobs.create(
            job_id="job-retry-1",
            week_id="2026-07-25",
            race_date="2026-07-25",
            artifact_type="race_meta",
            kind="STATIC_CORE",
            priority="P1",
            target_id=inserted[0]["id"],
            scheduled_for="2026-07-21",
        )
        jobs.transition(
            "job-retry-1",
            state.RUNNING,
            attempt=1,
        )
        jobs.transition(
            "job-retry-1",
            state.PARTIAL,
            retry_after="2026-07-20",
            validation_errors=[{"code": "required_null", "field": "distance"}],
        )

        result = CollectRetry().process(week_id="2026-07-25", as_of_date="2026-07-21")
        self.assertEqual(result.requeued, 1)

        job = jobs.get("job-retry-1")
        assert job is not None
        self.assertEqual(job["status"], state.PENDING)
        self.assertIsNone(job.get("retry_after"))


if __name__ == "__main__":
    unittest.main()
