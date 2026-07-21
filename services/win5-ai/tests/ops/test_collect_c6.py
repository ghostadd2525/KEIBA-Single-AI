# -*- coding: utf-8 -*-
"""
C-6 E2E — DYNAMIC odds lifecycle + STATIC isolation.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.data.collect import (
    AvailabilityContext,
    CollectBudget,
    CollectJobRepository,
    CollectPlanner,
    CollectScheduler,
    DYNAMIC_READY,
    DYNAMIC_REFRESHING,
    KeibaNetCollector,
    RaceCalendar,
    STATIC_READY,
    classify_dynamic_state,
    evaluate_collect_ops,
    read_manifest,
    state,
)
from app.data.collect.contracts.dynamic import (
    STALE_INTERVAL,
    STALE_ON_CHANGE,
    get_dynamic_contract,
)
from app.data.collect.keibanet.client import KeibaNetClient
from app.data.db import migrate
from app.data.collect import state as sm


def _calendar_race_day() -> RaceCalendar:
    return RaceCalendar.from_dict(
        {
            "calendar_version": "jra-calendar-2026-w29-c6",
            "week_id": "2026-07-18",
            "days": [
                {
                    "race_date": "2026-07-19",
                    "venues": {"福島": 11},
                    "venue_races": {"福島": [11]},
                }
            ],
        }
    )


def _odds_payload(date: str, venue: str, race_no: int) -> dict:
    return {
        "race_id": f"{date.replace('-', '')}_{race_no:02d}_{venue}",
        "date": date,
        "venue": venue,
        "race_no": race_no,
        "odds": [
            {"horse_number": 7, "win": 3.2},
            {"horse_number": 3, "win": 5.1},
        ],
    }


def _track_payload(date: str, venue: str, race_no: int) -> dict:
    return {
        "race_id": f"{date.replace('-', '')}_{race_no:02d}_{venue}",
        "date": date,
        "venue": venue,
        "race_no": race_no,
        "condition": "良",
    }


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        date = params.get("date", [""])[0]
        venue = params.get("venue", [""])[0]
        race_no = int(params.get("race_no", ["0"])[0])
        if parsed.path == "/v1/dynamic/odds":
            payload = _odds_payload(date, venue, race_no)
        elif parsed.path == "/v1/dynamic/track":
            payload = _track_payload(date, venue, race_no)
        else:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _MockServer:
    def __init__(self) -> None:
        self._httpd = HTTPServer(("127.0.0.1", 0), _Handler)
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


class DynamicContractTest(unittest.TestCase):
    def test_odds_and_track_contract(self):
        odds = get_dynamic_contract("odds")
        self.assertEqual(odds.kind, "DYNAMIC")
        self.assertFalse(odds.prediction_required)
        self.assertEqual(odds.stale_condition, STALE_INTERVAL)
        self.assertTrue(odds.auto_refresh)
        self.assertGreaterEqual(odds.refresh_interval_sec or 0, 300)

        track = get_dynamic_contract("track")
        self.assertEqual(track.stale_condition, STALE_ON_CHANGE)
        self.assertFalse(track.auto_refresh)
        self.assertIsNone(track.refresh_interval_sec)


class StaticDynamicIsolationTest(unittest.TestCase):
    def test_static_cannot_stale(self):
        self.assertFalse(
            sm.can_transition(sm.READY, sm.STALE_DYNAMIC, kind="STATIC_CORE")
        )
        self.assertTrue(
            sm.can_transition(sm.READY, sm.STALE_DYNAMIC, kind="DYNAMIC")
        )


class CollectC6OddsLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        root = Path(self._tmpdir.name)
        os.environ["EXPECT_AI_DB_PATH"] = str(root / "c6.db")
        os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(root / "manifests")
        os.environ["EXPECT_COLLECT_RAW_DIR"] = str(root / "raw")
        os.environ["EXPECT_COLLECT_DAILY_LIMIT"] = "20"
        os.environ["EXPECT_COLLECT_ODDS_REFRESH_SEC"] = "60"
        migrate()

    def tearDown(self) -> None:
        for key in (
            "EXPECT_AI_DB_PATH",
            "EXPECT_COLLECT_MANIFEST_DIR",
            "EXPECT_COLLECT_RAW_DIR",
            "EXPECT_COLLECT_DAILY_LIMIT",
            "EXPECT_COLLECT_ODDS_REFRESH_SEC",
            "EXPECT_KEIBANET_BASE_URL",
        ):
            os.environ.pop(key, None)
        self._tmpdir.cleanup()

    def test_odds_ready_stale_pending_ready(self):
        calendar = _calendar_race_day()
        # Race day → DYNAMIC enqueue（STATIC は weekday ではないので race_meta 未生成）
        plan = CollectPlanner(budget=CollectBudget(daily_limit=20)).run(
            calendar,
            availability=AvailabilityContext(
                as_of_date="2026-07-19",
                draw_confirmed=False,  # entries_core 未生成 → DYNAMIC のみ
            ),
            scheduled_for="2026-07-19",
        )
        self.assertIn("odds", plan.enqueued_types)
        self.assertIn("track", plan.enqueued_types)
        self.assertNotIn("race_meta", plan.enqueued_types)
        self.assertNotIn("entries_core", plan.enqueued_types)

        jobs = CollectJobRepository()
        odds_jobs = [
            j for j in jobs.list_by_week(calendar.week_id) if j["artifact_type"] == "odds"
        ]
        track_jobs = [
            j for j in jobs.list_by_week(calendar.week_id) if j["artifact_type"] == "track"
        ]
        self.assertEqual(len(odds_jobs), 1)
        self.assertEqual(len(track_jobs), 1)
        odds_id = odds_jobs[0]["job_id"]
        track_id = track_jobs[0]["job_id"]

        server = _MockServer()
        try:
            os.environ["EXPECT_KEIBANET_BASE_URL"] = server.base_url
            client = KeibaNetClient(
                base_url=server.base_url,
                max_retries=0,
                min_interval_sec=0,
            )
            collector = KeibaNetCollector(client=client)
            scheduler = CollectScheduler(
                week_id=calendar.week_id,
                as_of_date="2026-07-19",
                budget=CollectBudget(daily_limit=20),
            )

            # 1) odds: PENDING → RUNNING → READY（E2E 対象は odds 1件）
            batch = [j for j in scheduler.dequeue_pending() if j["job_id"] == odds_id]
            self.assertEqual(len(batch), 1)
            result = collector.run_job(odds_id)
            self.assertEqual(result.final_status, state.READY)
            self.assertEqual(jobs.get(odds_id)["status"], state.READY)

            # track は READY にして Manifest dynamic_ready を成立（refresh 対象外）
            collector.run_job(track_id)
            self.assertEqual(jobs.get(track_id)["status"], state.READY)

            # STATIC ジョブが無いことを確認（分離）
            static_jobs = [
                j
                for j in jobs.list_by_week(calendar.week_id)
                if j["kind"] != "DYNAMIC"
            ]
            self.assertEqual(static_jobs, [])

            # 2) refresh_interval 経過 → STALE_DYNAMIC → PENDING（odds のみ）
            from app.data.db import connect

            past = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
            conn = connect()
            try:
                conn.execute(
                    "UPDATE collect_jobs SET updated_at = ? WHERE job_id = ?",
                    (past, odds_id),
                )
                conn.commit()
            finally:
                conn.close()

            refresh = scheduler.process_dynamic_refresh(
                now=datetime.now(timezone.utc)
            )
            self.assertIn(odds_id, refresh.marked_stale)
            self.assertIn(odds_id, refresh.requeued)
            self.assertNotIn(track_id, refresh.marked_stale)
            self.assertEqual(jobs.get(odds_id)["status"], state.PENDING)
            self.assertEqual(jobs.get(track_id)["status"], state.READY)

            # 3) 再取得 → READY
            batch2 = scheduler.dequeue_pending()
            self.assertTrue(any(j["job_id"] == odds_id for j in batch2))
            result2 = collector.run_job(odds_id)
            self.assertEqual(result2.final_status, state.READY)

            scheduler.finish()
            manifest = read_manifest(calendar.week_id)
            assert manifest is not None
            self.assertTrue(manifest["status"]["dynamic_ready"])
            self.assertFalse(manifest["status"]["dynamic_stale"])
            # Prediction Ready は独立（Gate 未実行 → false）
            self.assertFalse(manifest["status"]["prediction_ready"])

            ops = evaluate_collect_ops(calendar.week_id)
            self.assertEqual(ops.dynamic_state, DYNAMIC_READY)
            self.assertFalse(ops.prediction_ready)
        finally:
            server.close()


class DynamicOpsClassifyTest(unittest.TestCase):
    def test_dynamic_states(self):
        self.assertEqual(
            classify_dynamic_state(dynamic_ready=False, dynamic_stale=False),
            STATIC_READY,
        )
        self.assertEqual(
            classify_dynamic_state(dynamic_ready=False, dynamic_stale=True),
            DYNAMIC_REFRESHING,
        )
        self.assertEqual(
            classify_dynamic_state(dynamic_ready=True, dynamic_stale=False),
            DYNAMIC_READY,
        )


if __name__ == "__main__":
    unittest.main()
