# -*- coding: utf-8 -*-
"""Live Challenge / RA / GET non-write regressions. Local only."""
from __future__ import annotations

import inspect
import os
import sqlite3
import unittest
from pathlib import Path

from tests.ops.helpers import http_json, running_server


def _pred_count() -> int:
    from app.data.db import connect

    conn = connect()
    try:
        return int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
    finally:
        conn.close()


class GetRowDeltaTests(unittest.TestCase):
    def test_get_list_and_detail_predictions_row_delta_zero(self) -> None:
        os.environ.pop("PREDICTION_RUNS_ENABLED", None)
        with running_server(allow_migration_019=False, prediction_runs=False) as base:
            before = _pred_count()
            st, body = http_json(base + "/v1/predictions")
            self.assertEqual(st, 200, body)
            st2, body2 = http_json(base + "/v1/predictions/20260719_hanshin_11")
            self.assertIn(st2, (200, 404), body2)
            self.assertEqual(_pred_count(), before)


class ChallengeLifecycleNonWriteTests(unittest.TestCase):
    def test_lifecycle_read_paths_do_not_write_predictions(self) -> None:
        from app.challenge import lifecycle as life

        src = inspect.getsource(life)
        for name in ("list_active", "list_notifications"):
            fn = getattr(life, name, None) or getattr(
                getattr(life, "ChallengeLifecycleService", object), name, None
            )
            if fn is None:
                cls = None
                for obj in vars(life).values():
                    if inspect.isclass(obj) and hasattr(obj, name):
                        cls = obj
                        break
                self.assertIsNotNone(cls, name)
                fn = getattr(cls, name)
            fn_src = inspect.getsource(fn)
            self.assertNotIn("INSERT INTO predictions", fn_src)
            self.assertNotIn("save_idempotent", fn_src)
            self.assertNotIn("UPDATE predictions", fn_src)
        self.assertNotIn("PREDICTION_RUNS_ENABLED", inspect.getsource(life.get_lifecycle_service))

    def test_challenge_http_read_predictions_row_delta_zero(self) -> None:
        os.environ.pop("PREDICTION_RUNS_ENABLED", None)
        with running_server(allow_migration_019=False, prediction_runs=False) as base:
            before = _pred_count()
            st, body = http_json(base + "/v1/challenge/active")
            self.assertIn(st, (200, 401, 403), body)
            st2, body2 = http_json(base + "/v1/notifications")
            self.assertIn(st2, (200, 401, 403), body2)
            self.assertEqual(_pred_count(), before)


class ResultAutomationNonWriteTests(unittest.TestCase):
    def test_ra_status_path_does_not_write_predictions(self) -> None:
        from app.ops import result_automation as ra

        src = inspect.getsource(ra.ResultAutomationService.get_pipeline_status)
        self.assertNotIn("INSERT INTO predictions", src)
        self.assertNotIn("save_idempotent", src)
        self.assertNotIn("UPDATE predictions", src)

    def test_ra_status_http_predictions_row_delta_zero(self) -> None:
        os.environ.pop("PREDICTION_RUNS_ENABLED", None)
        with running_server(allow_migration_019=False, prediction_runs=False) as base:
            before = _pred_count()
            st, body = http_json(base + "/v1/admin/results/status")
            self.assertIn(st, (200, 401, 403), body)
            self.assertEqual(_pred_count(), before)


class DisabledPostAndEnvTests(unittest.TestCase):
    def test_prediction_runs_enabled_stays_unset_or_zero(self) -> None:
        os.environ.pop("PREDICTION_RUNS_ENABLED", None)
        self.assertNotEqual(os.environ.get("PREDICTION_RUNS_ENABLED"), "1")
        with running_server(allow_migration_019=False, prediction_runs=False) as base:
            st, body = http_json(
                base + "/v1/prediction-runs",
                method="POST",
                body={"race_id": "20260719_hanshin_11"},
            )
            self.assertEqual(st, 503, body)
            self.assertEqual(body.get("error", {}).get("code"), "PREDICTION_RUNS_DISABLED")
