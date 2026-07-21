# -*- coding: utf-8 -*-
"""Collector C-1 E2E — STATIC_CORE / race_meta."""
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
    CollectArtifactRepository,
    CollectJobRepository,
    CollectRunRepository,
    CollectTargetRepository,
    KeibaNetCollector,
    state,
)
from app.data.collect.keibanet.client import KeibaNetClient
from app.data.collect.raw_store import raw_root, read_race_meta
from app.data.db import migrate


def _valid_race_meta() -> dict:
    return {
        "race_id": "20260725_11_01",
        "date": "2026-07-25",
        "venue": "函館",
        "race_no": 11,
        "distance": 2000,
        "surface": "芝",
    }


def _partial_race_meta() -> dict:
    payload = _valid_race_meta()
    payload["distance"] = None
    return payload


class _RaceMetaHandler(BaseHTTPRequestHandler):
    mode = "ready"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/v1/static/race_meta":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        if self.mode == "ready":
            body = json.dumps(_valid_race_meta(), ensure_ascii=False).encode("utf-8")
        else:
            body = json.dumps(_partial_race_meta(), ensure_ascii=False).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _MockServer:
    def __init__(self, mode: str = "ready") -> None:
        _RaceMetaHandler.mode = mode
        self._httpd = HTTPServer(("127.0.0.1", 0), _RaceMetaHandler)
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


class CollectC1E2ETest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db = Path(self._tmpdir.name) / "collect_c1.db"
        self._raw = Path(self._tmpdir.name) / "raw"
        os.environ["EXPECT_AI_DB_PATH"] = str(self._db)
        os.environ["EXPECT_COLLECT_RAW_DIR"] = str(self._raw)
        migrate()

        runs = CollectRunRepository()
        targets = CollectTargetRepository()
        jobs = CollectJobRepository()

        run = runs.create(week_id="2026-07-25", calendar_version="jra-calendar-2026-w30")
        inserted = targets.insert_many(
            planner_run_id=run["planner_run_id"],
            targets=[
                {
                    "week_id": "2026-07-25",
                    "calendar_version": "jra-calendar-2026-w30",
                    "race_date": "2026-07-25",
                    "venue": "函館",
                    "race_no": 11,
                    "race_id": "20260725_11_01",
                }
            ],
        )
        self.target_id = inserted[0]["id"]
        self.planner_run_id = run["planner_run_id"]
        self.runs = runs
        self.targets = targets
        self.jobs = jobs

    def tearDown(self) -> None:
        os.environ.pop("EXPECT_AI_DB_PATH", None)
        os.environ.pop("EXPECT_COLLECT_RAW_DIR", None)
        os.environ.pop("EXPECT_KEIBANET_BASE_URL", None)
        self._tmpdir.cleanup()

    def _run_collector(self, job_id: str, mode: str) -> None:
        server = _MockServer(mode=mode)
        try:
            os.environ["EXPECT_KEIBANET_BASE_URL"] = server.base_url
            client = KeibaNetClient(
                base_url=server.base_url,
                timeout=5,
                max_retries=0,
                min_interval_sec=0,
                daily_limit=50,
            )
            collector = KeibaNetCollector(client=client)
            self.result = collector.run_job(job_id)
        finally:
            server.close()

    def test_e2e_pending_running_ready(self) -> None:
        self.jobs.create(
            job_id="job-c1-ready",
            week_id="2026-07-25",
            race_date="2026-07-25",
            race_id="20260725_11_01",
            artifact_type="race_meta",
            kind="STATIC_CORE",
            priority="P1",
            target_id=self.target_id,
            planner_run_id=self.planner_run_id,
        )
        jobs = CollectJobRepository()
        artifacts = CollectArtifactRepository()

        before = jobs.get("job-c1-ready")
        self.assertEqual(before["status"], state.PENDING)

        self._run_collector("job-c1-ready", mode="ready")

        after_job = jobs.get("job-c1-ready")
        self.assertEqual(after_job["status"], state.READY)
        self.assertIsNotNone(after_job.get("artifact_id"))

        art = artifacts.get_for_job("job-c1-ready")
        self.assertIsNotNone(art)
        assert art is not None
        self.assertEqual(art["status"], state.READY)
        self.assertEqual(art["raw_path"], "race_meta/20260725_11_01.json")
        self.assertTrue(art.get("content_hash"))

        raw_path = raw_root() / "race_meta" / "20260725_11_01.json"
        self.assertTrue(raw_path.is_file())
        saved = json.loads(read_race_meta("20260725_11_01").decode("utf-8"))
        self.assertEqual(saved["race_id"], "20260725_11_01")

        self.assertEqual(self.result.final_status, state.READY)
        self.assertTrue(self.result.validation.ok if self.result.validation else False)

    def test_e2e_pending_running_partial(self) -> None:
        partial_targets = self.targets.insert_many(
            planner_run_id=self.planner_run_id,
            targets=[
                {
                    "week_id": "2026-07-25",
                    "calendar_version": "jra-calendar-2026-w30",
                    "race_date": "2026-07-26",
                    "venue": "小倉",
                    "race_no": 10,
                    "race_id": "20260726_10_01",
                }
            ],
        )
        self.jobs.create(
            job_id="job-c1-partial",
            week_id="2026-07-25",
            race_date="2026-07-26",
            race_id="20260726_10_01",
            artifact_type="race_meta",
            kind="STATIC_CORE",
            priority="P1",
            target_id=partial_targets[0]["id"],
            planner_run_id=self.planner_run_id,
        )
        jobs = CollectJobRepository()
        artifacts = CollectArtifactRepository()

        before = jobs.get("job-c1-partial")
        self.assertEqual(before["status"], state.PENDING)

        self._run_collector("job-c1-partial", mode="partial")

        after_job = jobs.get("job-c1-partial")
        self.assertEqual(after_job["status"], state.PARTIAL)
        self.assertIsNotNone(after_job.get("validation_errors_json"))

        errors = json.loads(after_job["validation_errors_json"])
        self.assertTrue(any(e.get("code") == "required_null" for e in errors))

        art = artifacts.get_for_job("job-c1-partial")
        self.assertIsNotNone(art)
        assert art is not None
        self.assertEqual(art["status"], state.PARTIAL)
        self.assertEqual(art["raw_path"], "race_meta/20260726_10_01.json")

        self.assertEqual(self.result.final_status, state.PARTIAL)
        self.assertFalse(self.result.validation.ok if self.result.validation else True)


class CollectC1ValidatorTest(unittest.TestCase):
    def test_validate_race_meta_ready_and_partial(self) -> None:
        from app.data.collect.validator import validate_race_meta

        ok_body = json.dumps(_valid_race_meta(), ensure_ascii=False).encode("utf-8")
        ok = validate_race_meta(http_ok=True, body=ok_body)
        self.assertTrue(ok.ok)
        self.assertEqual(ok.errors, [])

        bad_body = json.dumps(_partial_race_meta(), ensure_ascii=False).encode("utf-8")
        bad = validate_race_meta(http_ok=True, body=bad_body)
        self.assertFalse(bad.ok)
        self.assertTrue(any(e["field"] == "distance" for e in bad.errors))

        http_bad = validate_race_meta(http_ok=False, body=ok_body)
        self.assertFalse(http_bad.ok)
        self.assertEqual(http_bad.errors[0]["code"], "http_error")


if __name__ == "__main__":
    unittest.main()
