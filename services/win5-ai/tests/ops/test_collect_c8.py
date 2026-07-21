# -*- coding: utf-8 -*-
"""
C-8 Validation — Retry Automation / Budget SoT / Weekday Distribution.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app.data.collect import (
    AvailabilityContext,
    CollectBudget,
    CollectJobRepository,
    CollectPlanner,
    CollectRetry,
    CollectScheduler,
    KeibaNetCollector,
    RaceCalendar,
    read_manifest,
    state,
)
from app.data.collect.budget import DEFAULT_DAILY_LIMIT, resolve_daily_limit
from app.data.collect.contracts.retry import compute_retry_after, next_business_day
from app.data.collect.contracts.weekday_distribution import (
    plan_scheduled_dates,
    summarize_distribution,
    weekday_window_for_week,
    EnqueueSlot,
)
from app.data.collect.keibanet.client import KeibaNetClient
from app.data.db import migrate


WEEK_ID = "2026-07-25"  # Saturday


def _calendar_72() -> RaceCalendar:
    venues = {"函館": 12, "小倉": 12, "新潟": 12}
    return RaceCalendar.from_dict(
        {
            "calendar_version": "jra-calendar-2026-w30-c8",
            "week_id": WEEK_ID,
            "days": [
                {
                    "race_date": "2026-07-25",
                    "venues": venues,
                    "venue_races": {k: list(range(1, 13)) for k in venues},
                },
                {
                    "race_date": "2026-07-26",
                    "venues": venues,
                    "venue_races": {k: list(range(1, 13)) for k in venues},
                },
            ],
        }
    )


class _FailHandler(BaseHTTPRequestHandler):
    mode = "500"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if _FailHandler.mode == "partial":
            body = json.dumps(
                {
                    "race_id": "x",
                    "date": "2026-07-25",
                    "venue": "函館",
                    "race_no": 1,
                    "distance": None,
                    "surface": "芝",
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(500)
        self.end_headers()
        self.wfile.write(b"error")


class _MockServer:
    def __init__(self, mode: str = "500") -> None:
        _FailHandler.mode = mode
        self._httpd = HTTPServer(("127.0.0.1", 0), _FailHandler)
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


class RetryPolicyTest(unittest.TestCase):
    def test_next_business_day_skips_weekend(self):
        # Friday → Monday
        self.assertEqual(next_business_day("2026-07-17"), date(2026, 7, 20))
        # Saturday → Monday
        self.assertEqual(next_business_day("2026-07-18"), date(2026, 7, 20))


class RetryAutomationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        root = Path(self._tmpdir.name)
        os.environ["EXPECT_AI_DB_PATH"] = str(root / "c8.db")
        os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(root / "manifests")
        os.environ["EXPECT_COLLECT_RAW_DIR"] = str(root / "raw")
        os.environ["EXPECT_COLLECT_DAILY_LIMIT"] = "150"
        migrate()
        self.server = _MockServer("500")
        os.environ["EXPECT_KEIBANET_BASE_URL"] = self.server.base_url

    def tearDown(self) -> None:
        self.server.close()
        for key in (
            "EXPECT_AI_DB_PATH",
            "EXPECT_COLLECT_MANIFEST_DIR",
            "EXPECT_COLLECT_RAW_DIR",
            "EXPECT_COLLECT_DAILY_LIMIT",
            "EXPECT_KEIBANET_BASE_URL",
        ):
            os.environ.pop(key, None)
        self._tmpdir.cleanup()

    def test_failed_sets_retry_after_then_collect_retry(self):
        calendar = RaceCalendar.from_dict(
            {
                "calendar_version": "c8-retry",
                "week_id": "2026-07-18",
                "days": [
                    {
                        "race_date": "2026-07-19",
                        "venues": {"福島": 1},
                        "venue_races": {"福島": [1]},
                    }
                ],
            }
        )
        CollectPlanner(budget=CollectBudget(daily_limit=10)).run(
            calendar,
            availability=AvailabilityContext(
                as_of_date="2026-07-17",
                draw_confirmed=False,
            ),
            scheduled_for="2026-07-17",
        )
        jobs = CollectJobRepository()
        job = next(j for j in jobs.list_by_week("2026-07-18") if j["artifact_type"] == "race_meta")
        client = KeibaNetClient(
            base_url=self.server.base_url,
            max_retries=0,
            min_interval_sec=0,
            budget=CollectBudget(daily_limit=10),
        )
        result = KeibaNetCollector(client=client).run_job(job["job_id"])
        self.assertEqual(result.final_status, state.FAILED)

        updated = jobs.get(job["job_id"])
        assert updated is not None
        self.assertTrue(updated.get("retry_after"))
        expected = compute_retry_after(attempt=int(updated.get("attempt") or 1))
        self.assertEqual(updated["retry_after"], expected)

        retry = CollectRetry().process(
            week_id="2026-07-18",
            as_of_date=str(updated["retry_after"])[:10],
        )
        self.assertEqual(retry.requeued, 1)
        self.assertEqual(jobs.get(job["job_id"])["status"], state.PENDING)
        self.assertIsNone(jobs.get(job["job_id"]).get("retry_after"))

    def test_partial_sets_retry_after(self):
        self.server.close()
        self.server = _MockServer("partial")
        os.environ["EXPECT_KEIBANET_BASE_URL"] = self.server.base_url

        calendar = RaceCalendar.from_dict(
            {
                "calendar_version": "c8-partial",
                "week_id": "2026-07-18",
                "days": [
                    {
                        "race_date": "2026-07-19",
                        "venues": {"福島": 1},
                        "venue_races": {"福島": [1]},
                    }
                ],
            }
        )
        CollectPlanner(budget=CollectBudget(daily_limit=10)).run(
            calendar,
            availability=AvailabilityContext(
                as_of_date="2026-07-17",
                draw_confirmed=False,
            ),
            scheduled_for="2026-07-17",
        )
        jobs = CollectJobRepository()
        job = next(j for j in jobs.list_by_week("2026-07-18") if j["artifact_type"] == "race_meta")
        client = KeibaNetClient(
            base_url=self.server.base_url,
            max_retries=0,
            min_interval_sec=0,
            budget=CollectBudget(daily_limit=10),
        )
        result = KeibaNetCollector(client=client).run_job(job["job_id"])
        self.assertEqual(result.final_status, state.PARTIAL)
        updated = jobs.get(job["job_id"])
        assert updated is not None
        self.assertTrue(updated.get("retry_after"))

        retry = CollectRetry().process(
            week_id="2026-07-18",
            as_of_date=str(updated["retry_after"])[:10],
        )
        self.assertEqual(retry.requeued, 1)
        self.assertEqual(jobs.get(job["job_id"])["status"], state.PENDING)


class BudgetSotTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        root = Path(self._tmpdir.name)
        os.environ["EXPECT_AI_DB_PATH"] = str(root / "c8b.db")
        os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(root / "manifests")
        os.environ["EXPECT_COLLECT_DAILY_LIMIT"] = "120"
        os.environ.pop("EXPECT_KEIBANET_DAILY_LIMIT", None)
        migrate()

    def tearDown(self) -> None:
        for key in (
            "EXPECT_AI_DB_PATH",
            "EXPECT_COLLECT_MANIFEST_DIR",
            "EXPECT_COLLECT_DAILY_LIMIT",
            "EXPECT_KEIBANET_BASE_URL",
        ):
            os.environ.pop(key, None)
        self._tmpdir.cleanup()

    def test_manifest_scheduler_client_share_budget(self):
        budget = CollectBudget.from_env()
        self.assertEqual(budget.daily_limit, 120)
        self.assertEqual(resolve_daily_limit(), 120)

        calendar = RaceCalendar.from_dict(
            {
                "calendar_version": "c8-budget",
                "week_id": "2026-07-18",
                "days": [
                    {
                        "race_date": "2026-07-19",
                        "venues": {"福島": 1},
                        "venue_races": {"福島": [1]},
                    }
                ],
            }
        )
        CollectPlanner(budget=budget).run(
            calendar,
            availability=AvailabilityContext(
                as_of_date="2026-07-17",
                draw_confirmed=False,
            ),
            scheduled_for="2026-07-17",
        )
        manifest = read_manifest("2026-07-18")
        assert manifest is not None
        self.assertEqual(manifest["budget"]["daily_limit"], budget.daily_limit)

        scheduler = CollectScheduler(
            week_id="2026-07-18",
            as_of_date="2026-07-17",
            budget=budget,
        )
        client = KeibaNetClient(
            base_url="http://127.0.0.1:9",
            budget=budget,
            max_retries=0,
        )
        self.assertIs(scheduler.budget, budget)
        self.assertIs(client.budget, budget)
        self.assertEqual(client.daily_limit, manifest["budget"]["daily_limit"])

        batch = scheduler.dequeue_pending()
        self.assertEqual(len(batch), 1)
        self.assertEqual(budget.used, 1)
        self.assertEqual(client.budget.used, 1)
        self.assertEqual(budget.remaining, 119)

        scheduler.finish()
        after = read_manifest("2026-07-18")
        assert after is not None
        self.assertEqual(after["budget"]["daily_limit"], 120)
        self.assertEqual(after["budget"]["used"], 1)
        self.assertEqual(after["budget"]["remaining"], 119)

    def test_default_limit_is_collect_sot(self):
        os.environ.pop("EXPECT_COLLECT_DAILY_LIMIT", None)
        os.environ.pop("EXPECT_KEIBANET_DAILY_LIMIT", None)
        self.assertEqual(resolve_daily_limit(), DEFAULT_DAILY_LIMIT)


class WeekdayDistributionTest(unittest.TestCase):
    def test_window_mon_fri(self):
        days = weekday_window_for_week(WEEK_ID)
        self.assertEqual(len(days), 5)
        self.assertEqual(days[0].weekday(), 0)
        self.assertEqual(days[-1].weekday(), 4)
        self.assertEqual(days[0].isoformat(), "2026-07-20")
        self.assertEqual(days[-1].isoformat(), "2026-07-24")

    def test_even_distribution_under_cap(self):
        slots = [
            EnqueueSlot(artifact_type="race_meta", race_date="2026-07-25")
            for _ in range(72)
        ]
        dates = plan_scheduled_dates(
            slots,
            week_id=WEEK_ID,
            context_as_of="2026-07-17",
            daily_limit=150,
        )
        dist = summarize_distribution(dates)
        self.assertEqual(sum(dist.values()), 72)
        # Mon-Fri only
        for d in dist:
            self.assertIn(d, {x.isoformat() for x in weekday_window_for_week(WEEK_ID)})
        # roughly even: 14 or 15 each
        counts = list(dist.values())
        self.assertLessEqual(max(counts) - min(counts), 1)
        self.assertTrue(all(c <= 150 for c in counts))

    def test_planner_distributes_without_fixed_scheduled_for(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        os.environ["EXPECT_AI_DB_PATH"] = str(root / "c8w.db")
        os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(root / "manifests")
        os.environ["EXPECT_COLLECT_DAILY_LIMIT"] = "150"
        try:
            migrate()
            calendar = _calendar_72()
            # scheduled_for 未指定 → 自動分散
            plan = CollectPlanner(budget=CollectBudget(daily_limit=150)).run(
                calendar,
                availability=AvailabilityContext(
                    as_of_date="2026-07-21",
                    draw_confirmed=False,
                ),
            )
            self.assertEqual(plan.jobs_enqueued, 72)
            jobs = CollectJobRepository().list_by_week(WEEK_ID)
            dates = [str(j["scheduled_for"])[:10] for j in jobs]
            dist = summarize_distribution(dates)
            window = {d.isoformat() for d in weekday_window_for_week(WEEK_ID)}
            self.assertEqual(set(dist.keys()), window)
            counts = list(dist.values())
            self.assertLessEqual(max(counts) - min(counts), 1)
            print("C8_WEEKDAY_DIST", json.dumps(dist, ensure_ascii=False))
        finally:
            for key in (
                "EXPECT_AI_DB_PATH",
                "EXPECT_COLLECT_MANIFEST_DIR",
                "EXPECT_COLLECT_DAILY_LIMIT",
            ):
                os.environ.pop(key, None)
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
