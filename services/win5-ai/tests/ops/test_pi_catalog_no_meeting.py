# -*- coding: utf-8 -*-
"""NO_MEETING vs CATALOG_FAILURE classification for Result Automation."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from app.ops.netkeiba_results import (
    CATALOG_FAILURE,
    MEETING_PRESENT,
    NO_MEETING,
    classify_pi_race_catalog,
    fetch_pi_race_catalog,
)
from app.ops.result_providers import NetkeibaResultProvider, RaceResultRow


class _FakeResp:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *args) -> bool:
        return False


def _empty_catalog_doc(date: str) -> dict:
    return {"date": date, "meetings": [], "venues": [], "races": [], "count": 0}


def _meeting_doc(date: str, n: int) -> dict:
    venues = []
    for vi, venue in enumerate(("中山", "阪神", "札幌"), start=1):
        races = []
        per = n // 3
        extra = n % 3
        count = per + (1 if vi <= extra else 0)
        for i in range(1, count + 1):
            races.append(
                {
                    "race_id": f"{date}-{vi:02d}-{i:02d}",
                    "numeric_race_id": f"{date.replace('-', '')}{vi:02d}{i:02d}",
                    "race_date": date,
                    "venue": venue,
                }
            )
        venues.append({"venue": venue, "races": races})
    return {"date": date, "venues": venues, "meetings": [], "races": [], "count": n}


class ClassifyPiCatalogTest(unittest.TestCase):
    def test_case1_http200_empty_is_no_meeting(self):
        doc = json.dumps(_empty_catalog_doc("2026-09-07"))
        with patch("app.ops.netkeiba_results.urllib.request.urlopen", return_value=_FakeResp(doc)):
            state = classify_pi_race_catalog("2026-09-07")
        self.assertEqual(state["state"], NO_MEETING)
        self.assertEqual(state["count"], 0)
        self.assertEqual(state["races"], [])

    def test_case2_http200_catalog_36_is_meeting_present(self):
        doc = json.dumps(_meeting_doc("2026-09-06", 36))
        with patch("app.ops.netkeiba_results.urllib.request.urlopen", return_value=_FakeResp(doc)):
            state = classify_pi_race_catalog("2026-09-06")
            races = fetch_pi_race_catalog("2026-09-06")
        self.assertEqual(state["state"], MEETING_PRESENT)
        self.assertEqual(state["count"], 36)
        self.assertEqual(len(races), 36)

    def test_case3_http_failure_is_catalog_failure(self):
        err = urllib.error.URLError("connection refused")
        with patch("app.ops.netkeiba_results.urllib.request.urlopen", side_effect=err):
            state = classify_pi_race_catalog("2026-09-07")
            with self.assertRaises(Exception):
                fetch_pi_race_catalog("2026-09-07")
        self.assertEqual(state["state"], CATALOG_FAILURE)
        self.assertIn("PI catalog failed", state["error"] or "")

    def test_case4_invalid_json_is_catalog_failure(self):
        with patch(
            "app.ops.netkeiba_results.urllib.request.urlopen",
            return_value=_FakeResp("<html>not json</html>"),
        ):
            state = classify_pi_race_catalog("2026-09-07")
            with self.assertRaises(Exception):
                fetch_pi_race_catalog("2026-09-07")
        self.assertEqual(state["state"], CATALOG_FAILURE)
        self.assertIn("JSON invalid", state["error"] or "")

    def test_contract_invalid_is_catalog_failure(self):
        with patch(
            "app.ops.netkeiba_results.urllib.request.urlopen",
            return_value=_FakeResp("[1, 2, 3]"),
        ):
            state = classify_pi_race_catalog("2026-09-07")
        self.assertEqual(state["state"], CATALOG_FAILURE)
        self.assertIn("contract invalid", state["error"] or "")

    def test_case5_weekday_nonempty_is_meeting_present(self):
        # Monday holiday meeting — weekday must still sync when catalog is non-empty.
        doc = json.dumps(_meeting_doc("2026-09-21", 24))
        with patch("app.ops.netkeiba_results.urllib.request.urlopen", return_value=_FakeResp(doc)):
            state = classify_pi_race_catalog("2026-09-21")
        self.assertEqual(state["state"], MEETING_PRESENT)
        self.assertEqual(state["count"], 24)


class NetkeibaProviderCatalogTest(unittest.TestCase):
    def test_empty_catalog_does_not_raise_or_write(self):
        with patch(
            "app.ops.netkeiba_results.fetch_pi_race_catalog",
            return_value=[],
        ):
            rows = NetkeibaResultProvider(http=object()).fetch("2026-09-07")
        self.assertEqual(rows, [])

    def test_nonempty_catalog_still_fetches_results(self):
        catalog = _meeting_doc("2026-09-06", 36)["venues"][0]["races"][:2]
        parsed = {
            "winner_horse_number": 1,
            "field_size": 16,
            "winner_name": "A",
            "finish_order": [1, 2],
            "payouts": {},
        }

        class _Http:
            def fetch_result_html(self, numeric: str) -> str:
                return f"<html>{numeric}</html>"

        with (
            patch("app.ops.netkeiba_results.fetch_pi_race_catalog", return_value=catalog),
            patch("app.ops.netkeiba_results.parse_result_html", return_value=parsed),
        ):
            rows = NetkeibaResultProvider(http=_Http()).fetch("2026-09-06")
        self.assertEqual(len(rows), 2)
        self.assertIsInstance(rows[0], RaceResultRow)
        self.assertEqual(rows[0].winner_horse_number, 1)


class RunAutoCatalogGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        os.environ["EXPECT_AI_DB_PATH"] = str(self.db_path)
        os.environ["EXPECT_RA_AUTO_MODE"] = "post"
        from app.data import db as app_db

        app_db.migrate()
        from app.ops import result_automation as ra

        ra._service = None

    def tearDown(self):
        self.tmp.cleanup()
        for k in ("EXPECT_AI_DB_PATH", "EXPECT_RA_AUTO_MODE"):
            os.environ.pop(k, None)
        from app.ops import result_automation as ra

        ra._service = None

    def _count_runs(self, status: str | None = None) -> int:
        from app.data import db as app_db

        conn = app_db.connect()
        try:
            if status:
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM result_automation_runs WHERE status=?",
                    (status,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM result_automation_runs"
                ).fetchone()
            return int(row["n"])
        finally:
            conn.close()

    def _insert_failed(self, race_date: str) -> int:
        from app.data import db as app_db
        from app.ops import state_machine as sm

        conn = app_db.connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO result_automation_runs(
                  race_date, status, trigger, attempt, max_attempts, started_at
                ) VALUES (?, ?, 'scheduled', 1, 5, datetime('now'))
                """,
                (race_date, sm.FAILED),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def test_case1_no_meeting_is_noop_without_run(self):
        from app.ops import result_automation_runner as runner

        calls = []

        class _Svc:
            def run(self, *args, **kwargs):
                calls.append((args, kwargs))
                return {"run_status": "FAILED"}

        with (
            patch.object(runner, "_jst_today", return_value="2026-09-07"),
            patch.object(runner, "_jst_yesterday", return_value="2026-09-06"),
            patch.object(
                runner,
                "classify_pi_race_catalog",
                return_value={"state": NO_MEETING, "count": 0, "races": [], "error": None},
            ),
            patch.object(runner, "get_result_automation", return_value=_Svc()),
        ):
            out = runner.run_auto()
        self.assertTrue(any(r.get("run_status") == "NOOP" for r in out))
        self.assertTrue(all(r.get("reason") != "result_sync_failed" for r in out))
        self.assertEqual(calls, [])
        self.assertEqual(self._count_runs(), 0)
        self.assertEqual(self._count_runs("FAILED"), 0)

    def test_case2_meeting_present_reaches_result_sync(self):
        from app.ops import result_automation_runner as runner
        from app.ops import ra_cadence

        calls = []

        class _Svc:
            def run(self, race_date, **kwargs):
                calls.append(race_date)
                return {"run_status": "COMPLETED", "race_date": race_date}

        with (
            patch.object(runner, "_jst_today", return_value="2026-09-06"),
            patch.object(runner, "_jst_yesterday", return_value="2026-09-05"),
            patch.object(
                runner,
                "classify_pi_race_catalog",
                return_value={"state": MEETING_PRESENT, "count": 36, "races": [{}] * 36},
            ),
            patch.object(runner, "get_result_automation", return_value=_Svc()),
            patch.object(
                ra_cadence,
                "decide_today_run",
                return_value={"run": True, "reason": "unsettled_or_in_progress", "cadence": "active_5m"},
            ),
            patch.object(ra_cadence, "mark_ran"),
        ):
            out = runner.run_auto()
        self.assertEqual(calls, ["2026-09-06"])
        self.assertTrue(any(r.get("run_status") == "CADENCE" for r in out))
        self.assertTrue(any(r.get("run_status") == "COMPLETED" for r in out))

    def test_case5_weekday_meeting_reaches_result_sync(self):
        from app.ops import result_automation_runner as runner
        from app.ops import ra_cadence

        calls = []

        class _Svc:
            def run(self, race_date, **kwargs):
                calls.append(race_date)
                return {"run_status": "COMPLETED", "race_date": race_date}

        with (
            patch.object(runner, "_jst_today", return_value="2026-09-21"),
            patch.object(runner, "_jst_yesterday", return_value="2026-09-20"),
            patch.object(
                runner,
                "classify_pi_race_catalog",
                return_value={"state": MEETING_PRESENT, "count": 24, "races": [{}] * 24},
            ),
            patch.object(runner, "get_result_automation", return_value=_Svc()),
            patch.object(
                ra_cadence,
                "decide_today_run",
                return_value={"run": True, "reason": "unsettled_or_in_progress", "cadence": "active_5m"},
            ),
            patch.object(ra_cadence, "mark_ran"),
        ):
            out = runner.run_auto()
        self.assertEqual(calls, ["2026-09-21"])
        self.assertTrue(any(r.get("catalog_state") == MEETING_PRESENT for r in out))

    def test_case6_recovery_skips_no_meeting(self):
        from app.ops import result_automation_runner as runner

        os.environ["EXPECT_RA_AUTO_MODE"] = "recovery"
        failed_id = self._insert_failed("2026-09-07")
        calls = []

        class _Svc:
            def run(self, *args, **kwargs):
                calls.append((args, kwargs))
                return {"run_status": "FAILED"}

        with (
            patch.object(
                runner,
                "classify_pi_race_catalog",
                return_value={"state": NO_MEETING, "count": 0, "races": []},
            ),
            patch.object(runner, "get_result_automation", return_value=_Svc()),
        ):
            out = runner.run_auto()
        self.assertEqual(calls, [])
        self.assertTrue(any(r.get("recovery_skipped") for r in out))
        self.assertEqual(self._count_runs("FAILED"), 1)
        self.assertEqual(self._count_runs(), 1)
        self.assertTrue(any(r.get("parent_run_id") == failed_id for r in out))

    def test_case7_recovery_retries_real_catalog_failure(self):
        from app.ops import result_automation_runner as runner

        os.environ["EXPECT_RA_AUTO_MODE"] = "recovery"
        failed_id = self._insert_failed("2026-09-07")
        calls = []

        class _Svc:
            def run(self, race_date, **kwargs):
                calls.append({"race_date": race_date, **kwargs})
                return {"run_status": "FAILED", "race_date": race_date}

        with (
            patch.object(
                runner,
                "classify_pi_race_catalog",
                return_value={
                    "state": CATALOG_FAILURE,
                    "count": 0,
                    "races": [],
                    "error": "PI catalog failed: timeout",
                },
            ),
            patch.object(runner, "get_result_automation", return_value=_Svc()),
        ):
            out = runner.run_auto()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["race_date"], "2026-09-07")
        self.assertEqual(calls[0]["parent_run_id"], failed_id)
        self.assertTrue(any(r.get("run_status") == "FAILED" for r in out))


if __name__ == "__main__":
    unittest.main()
