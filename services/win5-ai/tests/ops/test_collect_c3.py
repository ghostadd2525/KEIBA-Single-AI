# -*- coding: utf-8 -*-
"""
C-3 E2E — calendar → Collector → Raw → EtlFromRaw → SQLite → FeatureLoader → Prediction.

Prediction / FeatureLoader / PredictionAdapter / Core は変更しない。
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
    CollectBudget,
    CollectPlanner,
    CollectRetry,
    CollectScheduler,
    KeibaNetCollector,
    RaceCalendar,
    state,
)
from app.data.collect.keibanet.client import KeibaNetClient
from app.data.db import migrate
from app.data.etl import EtlFromRaw, ingest_ready_race_meta
from tests.ops.helpers import import_sample_data, isolated_env, load_fixture


CORE_RACE_ID = "2026-07-19-04-11"
PUBLIC_RACE_ID = "20260719_fukushima_11"


def _race_meta_payload(date: str, venue: str, race_no: int) -> dict:
    return {
        "race_id": f"{date.replace('-', '')}_{race_no:02d}_{venue}",
        "date": date,
        "venue": venue,
        "race_no": race_no,
        "distance": 2000,
        "surface": "芝",
        "race_name": "テストステークス",
        "horse_count": 12,
    }


def _prediction_signature(bundle: dict | None, meta: dict | None) -> dict:
    runners = ((bundle or {}).get("evaluation") or {}).get("runners") or []
    top = sorted(
        [r for r in runners if r.get("model_rank") is not None],
        key=lambda r: r.get("model_rank") or 999,
    )[:3]
    return {
        "engine_source": (meta or {}).get("engine_source"),
        "feature_source": (meta or {}).get("feature_source"),
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


def _c3_calendar() -> RaceCalendar:
    return RaceCalendar.from_dict(
        {
            "calendar_version": "jra-calendar-2026-w29-c3",
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


class EtlFromRawTest(unittest.TestCase):
    def test_ingest_race_meta_bytes(self):
        with isolated_env():
            from app.data.repository import RaceRepository

            migrate()
            payload = _race_meta_payload("2026-07-19", "福島", 11)
            result = EtlFromRaw().ingest_race_meta_bytes(
                json.dumps(payload, ensure_ascii=False).encode("utf-8")
            )
            self.assertEqual(result.races, 1)
            self.assertEqual(result.skipped, 0)

            row = RaceRepository().get("2026-07-19-福島-11")
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.get("core_race_id"), CORE_RACE_ID)
            self.assertEqual(row.get("distance"), 2000)


class CollectC3PipelineE2ETest(unittest.TestCase):
    """Collector + EtlFromRaw（Prediction 不要）。"""

    def test_calendar_through_etl_sqlite(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        os.environ["EXPECT_AI_DB_PATH"] = str(root / "c3.db")
        os.environ["EXPECT_COLLECT_RAW_DIR"] = str(root / "raw")
        os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(root / "manifests")
        os.environ["EXPECT_COLLECT_DAILY_LIMIT"] = "10"

        try:
            migrate()
            calendar = _c3_calendar()
            planner = CollectPlanner(budget=CollectBudget(daily_limit=10))
            plan = planner.run(calendar, scheduled_for="2026-07-17")
            self.assertEqual(plan.targets_count, 1)
            self.assertEqual(plan.jobs_enqueued, 1)

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
                self.assertEqual(len(batch), 1)
                result = collector.run_job(str(batch[0]["job_id"]))
                self.assertEqual(result.final_status, state.READY)
                scheduler.finish()
            finally:
                server.close()

            etl_result = ingest_ready_race_meta(calendar.week_id)
            self.assertEqual(etl_result.races, 1)

            from app.data.repository import RaceRepository

            row = RaceRepository().get("2026-07-19-福島-11")
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.get("core_race_id"), CORE_RACE_ID)
        finally:
            for key in (
                "EXPECT_AI_DB_PATH",
                "EXPECT_COLLECT_RAW_DIR",
                "EXPECT_COLLECT_MANIFEST_DIR",
                "EXPECT_COLLECT_DAILY_LIMIT",
                "EXPECT_KEIBANET_BASE_URL",
            ):
                os.environ.pop(key, None)
            tmp.cleanup()


class CollectC3MockPredictionTest(unittest.TestCase):
    """mock エンジンでも Collector 導入前後で Prediction 署名が一致すること。"""

    def test_mock_prediction_unchanged_after_collector_etl(self):
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

                calendar = _c3_calendar()
                CollectPlanner(budget=CollectBudget(daily_limit=10)).run(
                    calendar, scheduled_for="2026-07-17"
                )

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
                        budget=CollectBudget(daily_limit=10),
                    )
                    for job in scheduler.dequeue_pending():
                        collector.run_job(str(job["job_id"]))
                    scheduler.finish()
                finally:
                    server.close()

                ingest_ready_race_meta(calendar.week_id)

                after_bundle, after_meta = prediction_adapter.get_with_meta(PUBLIC_RACE_ID)
                after_sig = _prediction_signature(after_bundle, after_meta)
                self.assertEqual(after_sig, baseline)
                self.assertEqual(before_meta.get("engine_source"), "mock")
            finally:
                for key in (
                    "EXPECT_COLLECT_RAW_DIR",
                    "EXPECT_COLLECT_MANIFEST_DIR",
                    "EXPECT_COLLECT_DAILY_LIMIT",
                    "EXPECT_KEIBANET_BASE_URL",
                ):
                    os.environ.pop(key, None)
                tmp.cleanup()


class CollectC3E2ETest(unittest.TestCase):
    def test_full_pipeline_prediction_unchanged(self):
        from app.engine.adapters import single_prediction_mapper as mapper

        if mapper.locate_ai_platform_root() is None:
            self.skipTest("ai_platform not available")

        with isolated_env(engine="real"):
            try:
                import app.core  # noqa: F401
            except ModuleNotFoundError:
                self.skipTest("ai_platform not importable")

            from ai_platform.core.features import FeatureLoader
            from app.engine.adapters import prediction_adapter

            tmp = tempfile.TemporaryDirectory()
            root = Path(tmp.name)
            os.environ["EXPECT_COLLECT_RAW_DIR"] = str(root / "raw")
            os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(root / "manifests")
            os.environ["EXPECT_COLLECT_DAILY_LIMIT"] = "10"
            os.environ["EXPECT_KEIBANET_BASE_URL"] = "http://127.0.0.1:1"

            try:
                migrate()
                import_sample_data()

                before_bundle, before_meta = prediction_adapter.get_with_meta(PUBLIC_RACE_ID)
                self.assertIsNotNone(before_bundle)
                if before_meta and before_meta.get("engine_source") != "real_ai":
                    self.skipTest(
                        f"real_ai unavailable: {before_meta.get('engine_source')}"
                    )
                baseline = _prediction_signature(before_bundle, before_meta)

                loader_before = FeatureLoader().load(CORE_RACE_ID)
                self.assertIsNotNone(loader_before)
                assert loader_before is not None
                self.assertEqual(loader_before.feature_source, "db")

                calendar = _c3_calendar()
                planner = CollectPlanner(budget=CollectBudget(daily_limit=10))
                plan = planner.run(calendar, scheduled_for="2026-07-17")
                self.assertEqual(plan.targets_count, 1)
                self.assertEqual(plan.jobs_enqueued, 1)

                server = _MockServer()
                try:
                    os.environ["EXPECT_KEIBANET_BASE_URL"] = server.base_url
                    client = KeibaNetClient(
                        base_url=server.base_url,
                        max_retries=0,
                        min_interval_sec=0,
                    )
                    collector = KeibaNetCollector(client=client)
                    CollectRetry().process(week_id=calendar.week_id, as_of_date="2026-07-17")
                    scheduler = CollectScheduler(
                        week_id=calendar.week_id,
                        as_of_date="2026-07-17",
                        budget=CollectBudget(daily_limit=10),
                    )
                    batch = scheduler.dequeue_pending()
                    self.assertEqual(len(batch), 1)
                    result = collector.run_job(str(batch[0]["job_id"]))
                    self.assertEqual(result.final_status, state.READY)
                    scheduler.finish()
                finally:
                    server.close()

                etl_result = ingest_ready_race_meta(calendar.week_id)
                self.assertEqual(etl_result.races, 1)

                loader_after = FeatureLoader().load(CORE_RACE_ID)
                self.assertIsNotNone(loader_after)
                assert loader_after is not None
                self.assertEqual(loader_after.feature_source, "db")
                self.assertEqual(len(loader_after.frame), len(loader_before.frame))

                after_bundle, after_meta = prediction_adapter.get_with_meta(PUBLIC_RACE_ID)
                self.assertIsNotNone(after_bundle)
                after_sig = _prediction_signature(after_bundle, after_meta)
                self.assertEqual(after_sig["engine_source"], baseline["engine_source"])
                self.assertEqual(after_sig["feature_source"], baseline["feature_source"])

                tol = 0.001
                for i, exp in enumerate(baseline["top_runners"]):
                    act = after_sig["top_runners"][i]
                    self.assertEqual(act["horse_number"], exp["horse_number"])
                    self.assertEqual(act["model_rank"], exp["model_rank"])
                    self.assertAlmostEqual(
                        float(act["win_prob"] or 0),
                        float(exp["win_prob"] or 0),
                        delta=tol,
                    )
                if baseline["ai_confidence"] is not None:
                    self.assertAlmostEqual(
                        float(after_sig["ai_confidence"] or 0),
                        float(baseline["ai_confidence"] or 0),
                        delta=tol,
                    )
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
