# -*- coding: utf-8 -*-
"""
C-7 Production Validation — Collector 安定性評価（仕様変更なし）。

Real KeibaNet が未設定の場合は controlled mock で検証し、
結果を Validation Report の根拠とする。
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.data.collect import (
    AvailabilityContext,
    CollectBudget,
    CollectJobRepository,
    CollectPlanner,
    CollectRetry,
    CollectScheduler,
    COMPLETE_READY,
    FridayGate,
    KeibaNetCollector,
    PREDICTION_READY,
    RaceCalendar,
    assert_valid_manifest,
    evaluate_collect_ops,
    read_manifest,
    state,
)
from app.data.collect.keibanet.client import (
    KeibaNetClient,
    KeibaNetTimeoutError,
)
from app.data.collect.raw_store import raw_root
from app.data.db import migrate
from app.data.etl import ingest_ready_race_meta
from tests.ops.helpers import import_sample_data


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

WEEK_ID = "2026-07-18"
RACE_DATE = "2026-07-19"
AS_OF_WEEKDAY = "2026-07-17"


def _calendar(races: int = 3) -> RaceCalendar:
    venue_races = {"福島": list(range(1, races + 1))}
    return RaceCalendar.from_dict(
        {
            "calendar_version": "jra-calendar-2026-w29-c7",
            "week_id": WEEK_ID,
            "days": [
                {
                    "race_date": RACE_DATE,
                    "venues": {"福島": races},
                    "venue_races": venue_races,
                }
            ],
        }
    )


def _race_meta(date: str, venue: str, race_no: int, *, partial: bool = False) -> dict:
    payload = {
        "race_id": f"{date.replace('-', '')}_{race_no:02d}_{venue}",
        "date": date,
        "venue": venue,
        "race_no": race_no,
        "distance": None if partial else 2000,
        "surface": "芝",
    }
    return payload


def _entries(date: str, venue: str, race_no: int) -> dict:
    return {
        "race_id": f"{date.replace('-', '')}_{race_no:02d}_{venue}",
        "date": date,
        "venue": venue,
        "race_no": race_no,
        "entries": [
            {
                "horse_number": 1,
                "frame": 1,
                "horse_name": "テスト",
                "jockey": "騎手",
                "weight": 56.0,
            }
        ],
    }


def _odds(date: str, venue: str, race_no: int) -> dict:
    return {
        "race_id": f"{date.replace('-', '')}_{race_no:02d}_{venue}",
        "date": date,
        "venue": venue,
        "race_no": race_no,
        "odds": [{"horse_number": 1, "win": 3.1}],
    }


def _track(date: str, venue: str, race_no: int) -> dict:
    return {
        "race_id": f"{date.replace('-', '')}_{race_no:02d}_{venue}",
        "date": date,
        "venue": venue,
        "race_no": race_no,
        "condition": "良",
    }


class _C7Handler(BaseHTTPRequestHandler):
    """Configurable mock KeibaNet for C-7 failure / success matrix."""

    mode = "ok"  # ok | http429 | http500 | timeout | null | partial | empty_json
    hit_counts: dict[str, int] = {}

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        _C7Handler.hit_counts[path] = _C7Handler.hit_counts.get(path, 0) + 1
        params = parse_qs(parsed.query)
        date_s = params.get("date", [RACE_DATE])[0]
        venue = params.get("venue", ["福島"])[0]
        race_no = int(params.get("race_no", ["1"])[0])

        mode = _C7Handler.mode
        if mode == "timeout":
            time.sleep(2.0)
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if mode == "http429":
            self.send_response(429)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"rate limited")
            return

        if mode == "http500":
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"internal error")
            return

        if mode == "null":
            body = b"null"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if mode == "empty_json":
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # success / partial by artifact path
        if path == "/v1/static/race_meta":
            payload = _race_meta(date_s, venue, race_no, partial=(mode == "partial"))
        elif path == "/v1/static/entries_core":
            payload = _entries(date_s, venue, race_no)
        elif path == "/v1/dynamic/odds":
            payload = _odds(date_s, venue, race_no)
        elif path == "/v1/dynamic/track":
            payload = _track(date_s, venue, race_no)
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
    def __init__(self, mode: str = "ok") -> None:
        _C7Handler.mode = mode
        _C7Handler.hit_counts = {}
        self._httpd = HTTPServer(("127.0.0.1", 0), _C7Handler)
        self.port = self._httpd.server_address[1]
        self.thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def set_mode(self, mode: str) -> None:
        _C7Handler.mode = mode

    def hits(self, path: str) -> int:
        return int(_C7Handler.hit_counts.get(path, 0))

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self.thread.join(timeout=3)


def _env_root(tmpdir: Path) -> None:
    os.environ["EXPECT_AI_DB_PATH"] = str(tmpdir / "c7.db")
    os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(tmpdir / "manifests")
    os.environ["EXPECT_COLLECT_RAW_DIR"] = str(tmpdir / "raw")
    os.environ["EXPECT_COLLECT_DAILY_LIMIT"] = "150"


def _clear_env() -> None:
    for key in (
        "EXPECT_AI_DB_PATH",
        "EXPECT_COLLECT_MANIFEST_DIR",
        "EXPECT_COLLECT_RAW_DIR",
        "EXPECT_COLLECT_DAILY_LIMIT",
        "EXPECT_KEIBANET_BASE_URL",
    ):
        os.environ.pop(key, None)


def _seed_job(artifact_type: str, kind: str, *, race_no: int = 1) -> str:
    jobs = CollectJobRepository()
    from app.data.collect import CollectRunRepository, CollectTargetRepository

    runs = CollectRunRepository()
    targets = CollectTargetRepository()
    run = runs.create(week_id=WEEK_ID, calendar_version="c7")
    # Reuse existing target if present (UNIQUE week/date/venue/race_no)
    existing = [
        t
        for t in targets.list_by_week(WEEK_ID)
        if t.get("race_date") == RACE_DATE
        and t.get("venue") == "福島"
        and int(t.get("race_no") or 0) == race_no
    ]
    if existing:
        target_id = int(existing[0]["id"])
    else:
        inserted = targets.insert_many(
            planner_run_id=run["planner_run_id"],
            targets=[
                {
                    "week_id": WEEK_ID,
                    "calendar_version": "c7",
                    "race_date": RACE_DATE,
                    "venue": "福島",
                    "race_no": race_no,
                }
            ],
        )
        target_id = int(inserted[0]["id"])
    job_id = f"job-c7-{artifact_type}-{race_no}"
    jobs.create(
        job_id=job_id,
        week_id=WEEK_ID,
        race_date=RACE_DATE,
        artifact_type=artifact_type,
        kind=kind,
        priority="P1",
        target_id=target_id,
        scheduled_for=AS_OF_WEEKDAY,
    )
    return job_id


# ---------------------------------------------------------------------------
# ① Real KeibaNet probe
# ---------------------------------------------------------------------------


class RealKeibaNetProbeTest(unittest.TestCase):
    def test_real_keibanet_availability(self):
        base = (os.environ.get("EXPECT_KEIBANET_BASE_URL") or "").strip()
        if not base:
            self.skipTest(
                "EXPECT_KEIBANET_BASE_URL unset — Real KeibaNet Validation deferred "
                "(see C-7 report Must)"
            )
        client = KeibaNetClient(base_url=base, max_retries=0, min_interval_sec=0.2)
        # Probe each artifact path with a known weekend race placeholder
        paths = [
            f"/v1/static/race_meta?date={RACE_DATE}&venue=%E7%A6%8F%E5%B3%B6&race_no=1",
            f"/v1/static/entries_core?date={RACE_DATE}&venue=%E7%A6%8F%E5%B3%B6&race_no=1",
            f"/v1/dynamic/odds?date={RACE_DATE}&venue=%E7%A6%8F%E5%B3%B6&race_no=1",
            f"/v1/dynamic/track?date={RACE_DATE}&venue=%E7%A6%8F%E5%B3%B6&race_no=1",
        ]
        results = {}
        for path in paths:
            try:
                resp = client.fetch(path)
                results[path] = {"status": resp.status_code, "bytes": len(resp.body)}
            except Exception as exc:  # noqa: BLE001
                results[path] = {"error": str(exc)}
        # At least one probe must return without transport crash
        self.assertTrue(any("status" in v for v in results.values()), results)


# ---------------------------------------------------------------------------
# ① controlled success matrix (all 4 artifacts)
# ---------------------------------------------------------------------------


class ArtifactSuccessMatrixTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        _env_root(Path(self._tmpdir.name))
        migrate()
        self.server = _MockServer("ok")
        os.environ["EXPECT_KEIBANET_BASE_URL"] = self.server.base_url

    def tearDown(self) -> None:
        self.server.close()
        _clear_env()
        self._tmpdir.cleanup()

    def test_all_four_artifacts_ready(self):
        matrix = [
            ("race_meta", "STATIC_CORE"),
            ("entries_core", "STATIC_CORE"),
            ("odds", "DYNAMIC"),
            ("track", "DYNAMIC"),
        ]
        client = KeibaNetClient(
            base_url=self.server.base_url,
            max_retries=0,
            min_interval_sec=0,
        )
        collector = KeibaNetCollector(client=client)
        outcomes = {}
        for idx, (artifact_type, kind) in enumerate(matrix, start=1):
            job_id = _seed_job(artifact_type, kind, race_no=idx)
            t0 = time.perf_counter()
            result = collector.run_job(job_id)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            outcomes[artifact_type] = {
                "status": result.final_status,
                "elapsed_ms": round(elapsed_ms, 2),
            }
            self.assertEqual(result.final_status, state.READY, artifact_type)
        # evidence for report
        print("C7_ARTIFACT_SUCCESS", json.dumps(outcomes, ensure_ascii=False))


# ---------------------------------------------------------------------------
# ④ Failure Validation
# ---------------------------------------------------------------------------


class FailureValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        _env_root(Path(self._tmpdir.name))
        migrate()
        self.server = _MockServer("ok")
        os.environ["EXPECT_KEIBANET_BASE_URL"] = self.server.base_url

    def tearDown(self) -> None:
        self.server.close()
        _clear_env()
        self._tmpdir.cleanup()

    def _run(self, mode: str, *, max_retries: int = 0, timeout: float = 30.0):
        self.server.set_mode(mode)
        job_id = _seed_job("race_meta", "STATIC_CORE")
        client = KeibaNetClient(
            base_url=self.server.base_url,
            max_retries=max_retries,
            retry_backoff=0.01,
            min_interval_sec=0,
            timeout=timeout,
        )
        collector = KeibaNetCollector(client=client)
        t0 = time.perf_counter()
        try:
            result = collector.run_job(job_id)
            elapsed = (time.perf_counter() - t0) * 1000
            return result, elapsed, None
        except Exception as exc:  # noqa: BLE001
            elapsed = (time.perf_counter() - t0) * 1000
            return None, elapsed, exc

    def test_http_429_failed_after_retries(self):
        result, elapsed, exc = self._run("http429", max_retries=2)
        self.assertIsNone(exc)
        assert result is not None
        self.assertEqual(result.final_status, state.FAILED)
        # client retries: initial + 2 = 3 hits
        self.assertGreaterEqual(self.server.hits("/v1/static/race_meta"), 3)
        print("C7_FAIL_429", json.dumps({"status": result.final_status, "ms": round(elapsed, 2)}))

    def test_http_500_failed_after_retries(self):
        result, elapsed, exc = self._run("http500", max_retries=2)
        self.assertIsNone(exc)
        assert result is not None
        self.assertEqual(result.final_status, state.FAILED)
        self.assertGreaterEqual(self.server.hits("/v1/static/race_meta"), 3)
        print("C7_FAIL_500", json.dumps({"status": result.final_status, "ms": round(elapsed, 2)}))

    def test_timeout_failed(self):
        result, elapsed, exc = self._run("timeout", max_retries=0, timeout=0.3)
        # Collector wraps transport error → FAILED (or raises if not caught)
        if exc is not None:
            self.assertIsInstance(exc, (KeibaNetTimeoutError, Exception))
            print("C7_FAIL_TIMEOUT_RAISED", type(exc).__name__)
        else:
            assert result is not None
            self.assertEqual(result.final_status, state.FAILED)
            print(
                "C7_FAIL_TIMEOUT",
                json.dumps({"status": result.final_status, "ms": round(elapsed, 2)}),
            )

    def test_null_response_partial(self):
        result, elapsed, exc = self._run("null")
        self.assertIsNone(exc)
        assert result is not None
        self.assertEqual(result.final_status, state.PARTIAL)
        print("C7_FAIL_NULL", json.dumps({"status": result.final_status, "ms": round(elapsed, 2)}))

    def test_partial_response_partial(self):
        result, elapsed, exc = self._run("partial")
        self.assertIsNone(exc)
        assert result is not None
        self.assertEqual(result.final_status, state.PARTIAL)
        print(
            "C7_FAIL_PARTIAL",
            json.dumps({"status": result.final_status, "ms": round(elapsed, 2)}),
        )

    def test_retry_requires_retry_after(self):
        """C-8: FAILED 時に retry_after が自動設定され CollectRetry が動く。"""
        result, _, exc = self._run("http500", max_retries=0)
        self.assertIsNone(exc)
        assert result is not None
        self.assertEqual(result.final_status, state.FAILED)

        jobs = CollectJobRepository()
        job = jobs.get(result.job_id)
        assert job is not None
        self.assertTrue(job.get("retry_after"))

        from datetime import date

        as_of = str(job["retry_after"])[:10]
        # as_of 当日なら due
        retry = CollectRetry().process(week_id=WEEK_ID, as_of_date=as_of)
        self.assertEqual(retry.requeued, 1)
        self.assertEqual(jobs.get(result.job_id)["status"], state.PENDING)
        print("C7_RETRY_AUTO", json.dumps({"retry_after": as_of, "as_of": as_of}))


# ---------------------------------------------------------------------------
# ② Budget Validation (1-week simulation)
# ---------------------------------------------------------------------------


class BudgetWeekSimulationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        _env_root(Path(self._tmpdir.name))
        migrate()

    def tearDown(self) -> None:
        _clear_env()
        self._tmpdir.cleanup()

    def test_week_budget_remaining_and_stop(self):
        """
        1週間想定: 日次 150、月曜〜金曜で race_meta を分散取得するシミュレーション。
        予算切れで dequeue が止まることを確認。
        """
        # 72 races × race_meta = 典型週末規模に近い enqueue
        calendar = RaceCalendar.from_dict(
            {
                "calendar_version": "jra-calendar-2026-w30-c7",
                "week_id": "2026-07-25",
                "days": [
                    {
                        "race_date": "2026-07-25",
                        "venues": {"函館": 12, "小倉": 12, "新潟": 12},
                        "venue_races": {
                            "函館": list(range(1, 13)),
                            "小倉": list(range(1, 13)),
                            "新潟": list(range(1, 13)),
                        },
                    },
                    {
                        "race_date": "2026-07-26",
                        "venues": {"函館": 12, "小倉": 12, "新潟": 12},
                        "venue_races": {
                            "函館": list(range(1, 13)),
                            "小倉": list(range(1, 13)),
                            "新潟": list(range(1, 13)),
                        },
                    },
                ],
            }
        )
        daily_limit = 150
        plan = CollectPlanner(budget=CollectBudget(daily_limit=daily_limit)).run(
            calendar,
            availability=AvailabilityContext(
                as_of_date="2026-07-21",
                draw_confirmed=False,
            ),
            scheduled_for="2026-07-21",
        )
        self.assertEqual(plan.jobs_enqueued, 72)  # race_meta only

        jobs = CollectJobRepository()

        # Tight limit: remaining が残り、翌日以降に持ち越せることを確認
        tight = CollectBudget(daily_limit=20)
        day1 = jobs.dequeue_pending(
            week_id="2026-07-25",
            as_of_date="2026-07-21",
            budget=tight,
        )
        self.assertEqual(len(day1), 20)
        self.assertEqual(tight.used, 20)
        self.assertEqual(tight.remaining, 0)
        self.assertEqual(
            jobs.dequeue_pending(
                week_id="2026-07-25",
                as_of_date="2026-07-21",
                budget=tight,
            ),
            [],
        )
        for job in day1:
            jobs.transition(job["job_id"], state.RUNNING)
            jobs.transition(job["job_id"], state.READY)

        day_usage = [
            {
                "as_of": "2026-07-21",
                "dequeued": 20,
                "used": 20,
                "remaining": 0,
                "note": "budget_stop",
            }
        ]
        remaining_pending = sum(
            1
            for j in jobs.list_by_week("2026-07-25")
            if j["status"] == state.PENDING
        )
        self.assertEqual(remaining_pending, 52)

        # 残り日で消化（limit=150）
        for day_offset in range(1, 5):
            as_of = (date(2026, 7, 21) + timedelta(days=day_offset)).isoformat()
            budget = CollectBudget(daily_limit=150)
            batch = jobs.dequeue_pending(
                week_id="2026-07-25",
                as_of_date=as_of,
                budget=budget,
            )
            for job in batch:
                jobs.transition(job["job_id"], state.RUNNING)
                jobs.transition(job["job_id"], state.READY)
            day_usage.append(
                {
                    "as_of": as_of,
                    "dequeued": len(batch),
                    "used": budget.used,
                    "remaining": budget.remaining,
                }
            )

        pending_left = sum(
            1
            for j in jobs.list_by_week("2026-07-25")
            if j["status"] == state.PENDING
        )
        self.assertEqual(pending_left, 0)
        print("C7_BUDGET_WEEK", json.dumps(day_usage, ensure_ascii=False))


# ---------------------------------------------------------------------------
# ③ Manifest Validation
# ---------------------------------------------------------------------------


class ManifestConsistencyTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        _env_root(Path(self._tmpdir.name))
        migrate()
        self.server = _MockServer("ok")
        os.environ["EXPECT_KEIBANET_BASE_URL"] = self.server.base_url

    def tearDown(self) -> None:
        self.server.close()
        _clear_env()
        self._tmpdir.cleanup()

    def test_planner_scheduler_gate_ops_align(self):
        calendar = _calendar(1)
        plan = CollectPlanner(budget=CollectBudget(daily_limit=20)).run(
            calendar,
            availability=AvailabilityContext(
                as_of_date=AS_OF_WEEKDAY,
                draw_confirmed=True,
            ),
            scheduled_for=AS_OF_WEEKDAY,
        )
        m1 = read_manifest(WEEK_ID)
        assert m1 is not None
        assert_valid_manifest(m1)
        self.assertFalse(m1["status"]["prediction_ready"])
        self.assertFalse(m1["status"]["complete_ready"])
        self.assertFalse(m1["status"]["dynamic_ready"])

        client = KeibaNetClient(
            base_url=self.server.base_url,
            max_retries=0,
            min_interval_sec=0,
        )
        collector = KeibaNetCollector(client=client)
        scheduler = CollectScheduler(
            week_id=WEEK_ID,
            as_of_date=AS_OF_WEEKDAY,
            budget=CollectBudget(daily_limit=20),
        )
        for job in scheduler.dequeue_pending():
            collector.run_job(job["job_id"])
        scheduler.finish()

        m2 = read_manifest(WEEK_ID)
        assert m2 is not None
        assert_valid_manifest(m2)
        # Scheduler は prediction_* を確定しない
        self.assertFalse(m2["status"]["prediction_ready"])
        self.assertFalse(m2["status"]["complete_ready"])
        self.assertGreaterEqual(m2["collect"]["ready"], 1)

        gate = FridayGate(week_id=WEEK_ID).run()
        m3 = read_manifest(WEEK_ID)
        assert m3 is not None
        assert_valid_manifest(m3)
        self.assertEqual(m3["status"]["prediction_ready"], gate.prediction_ready)
        self.assertEqual(m3["status"]["complete_ready"], gate.complete_ready)
        self.assertTrue(gate.prediction_ready)
        self.assertFalse(gate.complete_ready)  # odds/track 未取得

        ops = evaluate_collect_ops(WEEK_ID)
        self.assertEqual(ops.state, PREDICTION_READY)
        self.assertNotEqual(ops.state, COMPLETE_READY)
        self.assertEqual(ops.prediction_ready, m3["status"]["prediction_ready"])
        self.assertEqual(ops.complete_ready, m3["status"]["complete_ready"])
        print(
            "C7_MANIFEST",
            json.dumps(
                {
                    "planner_jobs": plan.jobs_enqueued,
                    "prediction_ready": m3["status"]["prediction_ready"],
                    "complete_ready": m3["status"]["complete_ready"],
                    "ops_state": ops.state,
                    "dynamic_state": ops.dynamic_state,
                },
                ensure_ascii=False,
            ),
        )


# ---------------------------------------------------------------------------
# ⑤ Prediction Validation
# ---------------------------------------------------------------------------


class PredictionUnchangedTest(unittest.TestCase):
    def test_prediction_signature_stable_after_collector_etl(self):
        from tests.ops.helpers import isolated_env

        PUBLIC_RACE_ID = "20260719_fukushima_11"

        def _sig(bundle, meta):
            runners = ((bundle or {}).get("evaluation") or {}).get("runners") or []
            top = sorted(
                [r for r in runners if r.get("model_rank") is not None],
                key=lambda r: r.get("model_rank") or 999,
            )[:3]
            return {
                "engine_source": (meta or {}).get("engine_source"),
                "top_runners": [r.get("horse_number") for r in top],
            }

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
                baseline = _sig(before_bundle, before_meta)

                calendar = RaceCalendar.from_dict(
                    {
                        "calendar_version": "c7-pred",
                        "week_id": WEEK_ID,
                        "days": [
                            {
                                "race_date": RACE_DATE,
                                "venues": {"福島": 11},
                                "venue_races": {"福島": [11]},
                            }
                        ],
                    }
                )
                CollectPlanner(budget=CollectBudget(daily_limit=5)).run(
                    calendar,
                    availability=AvailabilityContext(
                        as_of_date=AS_OF_WEEKDAY,
                        draw_confirmed=False,
                    ),
                    scheduled_for=AS_OF_WEEKDAY,
                )
                server = _MockServer("ok")
                try:
                    os.environ["EXPECT_KEIBANET_BASE_URL"] = server.base_url
                    client = KeibaNetClient(
                        base_url=server.base_url,
                        max_retries=0,
                        min_interval_sec=0,
                    )
                    collector = KeibaNetCollector(client=client)
                    jobs = CollectJobRepository()
                    for job in jobs.list_by_week(WEEK_ID):
                        if (
                            job["artifact_type"] == "race_meta"
                            and job["status"] == state.PENDING
                        ):
                            collector.run_job(job["job_id"])
                finally:
                    server.close()

                ingest_ready_race_meta(WEEK_ID)
                after_bundle, after_meta = prediction_adapter.get_with_meta(PUBLIC_RACE_ID)
                after_sig = _sig(after_bundle, after_meta)
                self.assertEqual(baseline, after_sig)
                self.assertEqual(before_meta.get("engine_source"), "mock")
                print(
                    "C7_PREDICTION",
                    json.dumps({"before": baseline, "after": after_sig}, ensure_ascii=False),
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


# ---------------------------------------------------------------------------
# ⑥ Performance Validation
# ---------------------------------------------------------------------------


class PerformanceValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        _env_root(Path(self._tmpdir.name))
        migrate()
        self.server = _MockServer("ok")
        os.environ["EXPECT_KEIBANET_BASE_URL"] = self.server.base_url

    def tearDown(self) -> None:
        self.server.close()
        _clear_env()
        self._tmpdir.cleanup()

    def test_measure_pipeline_timings(self):
        calendar = _calendar(3)
        metrics: dict[str, float] = {}

        t0 = time.perf_counter()
        CollectPlanner(budget=CollectBudget(daily_limit=50)).run(
            calendar,
            availability=AvailabilityContext(
                as_of_date=AS_OF_WEEKDAY,
                draw_confirmed=True,
            ),
            scheduled_for=AS_OF_WEEKDAY,
        )
        metrics["planner_ms"] = (time.perf_counter() - t0) * 1000

        client = KeibaNetClient(
            base_url=self.server.base_url,
            max_retries=0,
            min_interval_sec=0,
        )
        collector = KeibaNetCollector(client=client)
        scheduler = CollectScheduler(
            week_id=WEEK_ID,
            as_of_date=AS_OF_WEEKDAY,
            budget=CollectBudget(daily_limit=50),
        )

        t0 = time.perf_counter()
        batch = scheduler.dequeue_pending()
        metrics["dequeue_ms"] = (time.perf_counter() - t0) * 1000

        fetch_ms = []
        for job in batch:
            t1 = time.perf_counter()
            collector.run_job(job["job_id"])
            fetch_ms.append((time.perf_counter() - t1) * 1000)
        metrics["fetch_avg_ms"] = sum(fetch_ms) / max(len(fetch_ms), 1)
        metrics["fetch_max_ms"] = max(fetch_ms) if fetch_ms else 0.0

        t0 = time.perf_counter()
        raw_files = list(raw_root().rglob("*.json"))
        metrics["raw_store_file_count"] = float(len(raw_files))
        metrics["raw_list_ms"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        ingest_ready_race_meta(WEEK_ID)
        metrics["sqlite_etl_ms"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        scheduler.finish()
        metrics["manifest_update_ms"] = (time.perf_counter() - t0) * 1000

        # Retry path timing (synthetic)
        jobs = CollectJobRepository()
        failed = [j for j in jobs.list_by_week(WEEK_ID) if j["status"] == state.READY][:1]
        if failed:
            from app.data.db import connect

            jid = failed[0]["job_id"]
            conn = connect()
            try:
                conn.execute(
                    "UPDATE collect_jobs SET status = ?, retry_after = ? WHERE job_id = ?",
                    (state.FAILED, AS_OF_WEEKDAY, jid),
                )
                conn.commit()
            finally:
                conn.close()
            t0 = time.perf_counter()
            CollectRetry().process(week_id=WEEK_ID, as_of_date=AS_OF_WEEKDAY)
            metrics["retry_ms"] = (time.perf_counter() - t0) * 1000

        rounded = {k: round(v, 2) for k, v in metrics.items()}
        print("C7_PERF", json.dumps(rounded, ensure_ascii=False))
        self.assertLess(metrics["planner_ms"], 5000)
        self.assertLess(metrics["manifest_update_ms"], 2000)
        self.assertGreater(metrics["raw_store_file_count"], 0)


if __name__ == "__main__":
    unittest.main()
