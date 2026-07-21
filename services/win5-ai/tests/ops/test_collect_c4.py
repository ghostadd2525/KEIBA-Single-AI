# -*- coding: utf-8 -*-
"""
C-4 E2E — Data Availability + entries_core.

開催カレンダー → Planner (Availability) → Queue → Scheduler → Collector
→ Raw Store → ETL → SQLite → Prediction
"""
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
    AFTER_DRAW,
    AvailabilityContext,
    CollectBudget,
    CollectJobRepository,
    CollectPlanner,
    CollectScheduler,
    KeibaNetCollector,
    RACE_DAY,
    RaceCalendar,
    WEEKDAY,
    get_availability,
    is_available,
    state,
    validate_entries_core,
)
from app.data.collect.keibanet.client import KeibaNetClient
from app.data.collect.raw_store import raw_root
from app.data.db import migrate
from app.data.etl import ingest_ready_entries_core
from tests.ops.helpers import import_sample_data, isolated_env


CORE_RACE_ID = "2026-07-19-04-11"
PUBLIC_RACE_ID = "20260719_fukushima_11"
CATALOG_RACE_ID = "2026-07-19-福島-11"


def _entries_core_payload(date: str, venue: str, race_no: int) -> dict:
    race_id = f"{date.replace('-', '')}_{race_no:02d}_{venue}"
    return {
        "race_id": race_id,
        "date": date,
        "venue": venue,
        "race_no": race_no,
        "entries": [
            {
                "horse_number": 7,
                "frame": 4,
                "horse_name": "テストホースA",
                "jockey": "騎手A",
                "weight": 56.0,
            },
            {
                "horse_number": 3,
                "frame": 2,
                "horse_name": "テストホースB",
                "jockey": "騎手B",
                "weight": 54.0,
            },
            {
                "horse_number": 12,
                "frame": 8,
                "horse_name": "テストホースC",
                "jockey": "騎手C",
                "weight": 57.0,
            },
        ],
    }


def _race_meta_payload(date: str, venue: str, race_no: int) -> dict:
    return {
        "race_id": f"{date.replace('-', '')}_{race_no:02d}_{venue}",
        "date": date,
        "venue": venue,
        "race_no": race_no,
        "distance": 2000,
        "surface": "芝",
    }


def _c4_calendar() -> RaceCalendar:
    return RaceCalendar.from_dict(
        {
            "calendar_version": "jra-calendar-2026-w29-c4",
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


def _prediction_signature(bundle: dict | None, meta: dict | None) -> dict:
    runners = ((bundle or {}).get("evaluation") or {}).get("runners") or []
    top = sorted(
        [r for r in runners if r.get("model_rank") is not None],
        key=lambda r: r.get("model_rank") or 999,
    )[:3]
    return {
        "engine_source": (meta or {}).get("engine_source"),
        "top_runners": [
            {
                "horse_number": r.get("horse_number"),
                "model_rank": r.get("model_rank"),
                "win_prob": r.get("win_prob"),
            }
            for r in top
        ],
        "ai_confidence": ((bundle or {}).get("ai_confidence") or {}).get("score"),
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

        if parsed.path == "/v1/static/entries_core":
            body = json.dumps(
                _entries_core_payload(date, venue, race_no),
                ensure_ascii=False,
            ).encode("utf-8")
        elif parsed.path == "/v1/static/race_meta":
            body = json.dumps(
                _race_meta_payload(date, venue, race_no),
                ensure_ascii=False,
            ).encode("utf-8")
        else:
            self.send_response(404)
            self.end_headers()
            return

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


class AvailabilityContractTest(unittest.TestCase):
    def test_contract_defines_required_artifacts(self):
        for name, avail in (
            ("race_meta", WEEKDAY),
            ("entries_core", AFTER_DRAW),
            ("odds", RACE_DAY),
            ("track", RACE_DAY),
        ):
            spec = get_availability(name)
            self.assertEqual(spec.availability, avail)

        self.assertTrue(get_availability("race_meta").prediction_required)
        self.assertTrue(get_availability("entries_core").prediction_required)

    def test_race_meta_weekday_only(self):
        race_date = "2026-07-19"  # Sunday
        # Friday before race → available
        self.assertTrue(
            is_available(
                "race_meta",
                context=AvailabilityContext(as_of_date="2026-07-17", draw_confirmed=False),
                race_date=race_date,
            )
        )
        # Race day (Sunday) → not WEEKDAY
        self.assertFalse(
            is_available(
                "race_meta",
                context=AvailabilityContext(as_of_date="2026-07-19", draw_confirmed=True),
                race_date=race_date,
            )
        )

    def test_entries_core_after_draw_only(self):
        race_date = "2026-07-19"
        self.assertFalse(
            is_available(
                "entries_core",
                context=AvailabilityContext(as_of_date="2026-07-17", draw_confirmed=False),
                race_date=race_date,
            )
        )
        self.assertTrue(
            is_available(
                "entries_core",
                context=AvailabilityContext(as_of_date="2026-07-17", draw_confirmed=True),
                race_date=race_date,
            )
        )


class EntriesCoreValidatorTest(unittest.TestCase):
    def test_ok_and_empty_array(self):
        ok = validate_entries_core(
            http_ok=True,
            body=json.dumps(_entries_core_payload("2026-07-19", "福島", 11), ensure_ascii=False),
        )
        self.assertTrue(ok.ok)

        bad = validate_entries_core(
            http_ok=True,
            body=json.dumps(
                {
                    "race_id": "x",
                    "date": "2026-07-19",
                    "venue": "福島",
                    "race_no": 11,
                    "entries": [],
                },
                ensure_ascii=False,
            ),
        )
        self.assertFalse(bad.ok)
        self.assertTrue(any(e["code"] == "empty_array" for e in bad.errors))


class AvailabilityQueueTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ["EXPECT_AI_DB_PATH"] = str(Path(self._tmpdir.name) / "c4.db")
        os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(Path(self._tmpdir.name) / "m")
        migrate()

    def tearDown(self) -> None:
        os.environ.pop("EXPECT_AI_DB_PATH", None)
        os.environ.pop("EXPECT_COLLECT_MANIFEST_DIR", None)
        self._tmpdir.cleanup()

    def test_without_draw_only_race_meta_enqueued(self):
        calendar = _c4_calendar()
        plan = CollectPlanner(budget=CollectBudget(daily_limit=10)).run(
            calendar,
            availability=AvailabilityContext(as_of_date="2026-07-17", draw_confirmed=False),
        )
        self.assertEqual(plan.targets_count, 1)
        self.assertEqual(plan.enqueued_types, ["race_meta"])
        self.assertIn("entries_core", plan.not_generated_types)
        jobs = CollectJobRepository().list_by_week(calendar.week_id)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["artifact_type"], "race_meta")

    def test_with_draw_entries_core_enqueued(self):
        calendar = _c4_calendar()
        plan = CollectPlanner(budget=CollectBudget(daily_limit=10)).run(
            calendar,
            availability=AvailabilityContext(as_of_date="2026-07-17", draw_confirmed=True),
        )
        self.assertEqual(sorted(plan.enqueued_types), ["entries_core", "race_meta"])
        jobs = CollectJobRepository().list_by_week(calendar.week_id)
        types = sorted({j["artifact_type"] for j in jobs})
        self.assertEqual(types, ["entries_core", "race_meta"])
        # 未生成ではない — SKIPPED ジョブも無い
        self.assertFalse(any(j["status"] == state.SKIPPED for j in jobs))


class CollectC4EntriesE2ETest(unittest.TestCase):
    def test_entries_core_pipeline_to_prediction(self):
        with isolated_env(engine="mock"):
            tmp = tempfile.TemporaryDirectory()
            root = Path(tmp.name)
            os.environ["EXPECT_COLLECT_RAW_DIR"] = str(root / "raw")
            os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(root / "manifests")
            os.environ["EXPECT_COLLECT_DAILY_LIMIT"] = "10"

            try:
                migrate()
                import_sample_data()

                from app.engine.adapters import prediction_adapter

                before_bundle, before_meta = prediction_adapter.get_with_meta(PUBLIC_RACE_ID)
                baseline = _prediction_signature(before_bundle, before_meta)

                calendar = _c4_calendar()
                # entries_core only: draw confirmed, but race_meta also available on weekday
                # For focused E2E we still allow both; filter dequeue to entries_core
                plan = CollectPlanner(budget=CollectBudget(daily_limit=10)).run(
                    calendar,
                    availability=AvailabilityContext(
                        as_of_date="2026-07-17",
                        draw_confirmed=True,
                    ),
                )
                self.assertIn("entries_core", plan.enqueued_types)

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
                        as_of_date="2026-07-17",
                        budget=CollectBudget(daily_limit=10),
                    )
                    batch = scheduler.dequeue_pending()
                    entries_jobs = [j for j in batch if j["artifact_type"] == "entries_core"]
                    self.assertEqual(len(entries_jobs), 1)
                    result = collector.run_job(str(entries_jobs[0]["job_id"]))
                    self.assertEqual(result.final_status, state.READY)
                    self.assertTrue(str(result.raw_path or "").startswith("entries_core/"))
                    scheduler.finish()
                finally:
                    server.close()

                raw_file = raw_root() / "entries_core"
                self.assertTrue(any(raw_file.glob("*.json")))

                etl = ingest_ready_entries_core(calendar.week_id)
                self.assertEqual(etl.entries, 3)

                # entries table populated
                from app.data.db import connect

                conn = connect()
                try:
                    rows = conn.execute(
                        "SELECT horse_number, frame_number, horse_name, jockey, extra_json "
                        "FROM entries WHERE race_id = ? ORDER BY horse_number",
                        (CATALOG_RACE_ID,),
                    ).fetchall()
                finally:
                    conn.close()
                self.assertEqual(len(rows), 3)
                self.assertEqual(rows[0]["horse_number"], 3)
                self.assertEqual(rows[0]["frame_number"], 2)

                after_bundle, after_meta = prediction_adapter.get_with_meta(PUBLIC_RACE_ID)
                after_sig = _prediction_signature(after_bundle, after_meta)
                self.assertEqual(after_sig, baseline)
            finally:
                for key in (
                    "EXPECT_COLLECT_RAW_DIR",
                    "EXPECT_COLLECT_MANIFEST_DIR",
                    "EXPECT_COLLECT_DAILY_LIMIT",
                    "EXPECT_KEIBANET_BASE_URL",
                ):
                    os.environ.pop(key, None)
                tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
