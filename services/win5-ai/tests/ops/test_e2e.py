# -*- coding: utf-8 -*-
"""F-1 End-to-End tests — ETL / Resolver / Prediction / Conversation / Coverage / Diagnostics."""
from __future__ import annotations

import os
import unittest

from tests.ops.helpers import http_json, import_sample_data, isolated_env, load_fixture, running_server


class E2EHealthTest(unittest.TestCase):
    def test_health_ok(self):
        with running_server() as base:
            status, body = http_json(f"{base}/health")
            self.assertEqual(status, 200)
            self.assertEqual(body.get("status"), "ok")


class E2ERaceResolverTest(unittest.TestCase):
    def test_resolve_core_id(self):
        with isolated_env():
            from app.data.db import migrate
            from app.data.race_resolver import resolve_identity

            migrate()
            import_sample_data()
            ident = resolve_identity("2026-07-19-04-11")
            self.assertIsNotNone(ident)
            assert ident is not None
            self.assertEqual(ident.core_race_id, "2026-07-19-04-11")

    def test_resolve_ui_label(self):
        with isolated_env():
            from app.data.db import migrate
            from app.data.race_resolver import resolve_identity

            migrate()
            import_sample_data()
            ident = resolve_identity("福島11R", date_hint="2026-07-19")
            self.assertIsNotNone(ident)
            assert ident is not None
            self.assertEqual(ident.race_no, 11)

    def test_resolve_unknown_returns_none(self):
        with isolated_env():
            from app.data.race_resolver import resolve_identity

            self.assertIsNone(resolve_identity("存在しないレース"))


class E2EETLTest(unittest.TestCase):
    def test_etl_import_success(self):
        with isolated_env():
            from app.data.db import migrate
            from app.data.etl import EtlPipeline
            from app.data.repository import RaceRepository

            migrate()
            pipe = EtlPipeline()
            r = pipe.import_races_csv(load_fixture("sample_races.csv"))
            self.assertGreaterEqual(r.races, 1)
            self.assertGreater(len(RaceRepository().list(limit=10)), 0)

    def test_etl_features_import(self):
        with isolated_env():
            from app.data.db import migrate
            from app.data.etl import EtlPipeline
            from app.data.repository import FeatureRepository

            migrate()
            pipe = EtlPipeline()
            pipe.import_races_csv(load_fixture("sample_races.csv"))
            f = pipe.import_features_csv(load_fixture("sample_features.csv"))
            self.assertGreaterEqual(f.features, 1)
            rows = FeatureRepository().list_for_race("2026-07-19-04-11")
            self.assertGreaterEqual(len(rows), 1)

    def test_scheduler_fails_without_data(self):
        import tempfile
        from pathlib import Path

        with isolated_env():
            from app.data.db import migrate
            from app.data.etl import run_scheduled_etl

            migrate()
            empty = Path(tempfile.mkdtemp())
            result = run_scheduled_etl("2099-01-01", source_type="csv", data_dir=empty)
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.stopped_at_step, "download")


class E2EPredictionTest(unittest.TestCase):
    def test_predictions_list(self):
        with running_server() as base:
            status, body = http_json(f"{base}/v1/predictions")
            self.assertEqual(status, 200)
            self.assertTrue(body.get("ok"))
            self.assertIn("meta", body)
            items = body.get("data") or []
            self.assertIsInstance(items, list)
            if items:
                meta_items = body["meta"].get("items") or []
                self.assertIn("engine_source", meta_items[0])

    def test_prediction_by_race_id(self):
        with running_server() as base:
            status, body = http_json(f"{base}/v1/predictions/20260719_hanshin_11")
            self.assertEqual(status, 200)
            self.assertTrue(body.get("ok"))
            self.assertEqual(body["data"].get("race_id"), "20260719_hanshin_11")

    def test_prediction_unknown_race_mock_fallback(self):
        with running_server() as base:
            status, body = http_json(f"{base}/v1/predictions/nonexistent_race_xyz")
            self.assertEqual(status, 200)
            self.assertTrue(body.get("ok"))
            meta = body.get("meta") or {}
            self.assertIn(meta.get("engine_source"), ("mock", "mock_fallback"))


class E2EConversationTest(unittest.TestCase):
    def test_conversation_with_race_id(self):
        with running_server() as base:
            status, body = http_json(
                f"{base}/v1/conversation/chat",
                method="POST",
                body={"message": "20260719_hanshin_11を予想して"},
            )
            self.assertEqual(status, 200)
            self.assertTrue(body.get("ok"))
            self.assertIn("reply", body.get("data") or {})

    def test_conversation_empty_message(self):
        with running_server() as base:
            status, body = http_json(
                f"{base}/v1/conversation/chat",
                method="POST",
                body={"message": ""},
            )
            self.assertEqual(status, 200)
            data = body.get("data") or {}
            self.assertIn("reply", data)


class E2ECoverageTest(unittest.TestCase):
    def test_coverage_api(self):
        with running_server() as base:
            status, body = http_json(f"{base}/v1/data/coverage")
            self.assertEqual(status, 200)
            data = body.get("data") or {}
            for key in (
                "race_total",
                "real_ai",
                "mock",
                "coverage",
                "missing_features",
                "missing_races",
            ):
                self.assertIn(key, data)


class E2EDiagnosticsTest(unittest.TestCase):
    def test_diagnostics_missing(self):
        with running_server() as base:
            status, body = http_json(f"{base}/v1/diagnostics/missing")
            self.assertEqual(status, 200)
            data = body.get("data") or {}
            self.assertIn("summary", data)

    def test_diagnostics_fallback_reasons(self):
        with running_server() as base:
            status, body = http_json(f"{base}/v1/diagnostics/fallback-reasons")
            self.assertEqual(status, 200)
            self.assertIn("reasons", body.get("data") or {})


class E2EMonitoringTest(unittest.TestCase):
    def test_monitoring_api(self):
        with running_server() as base:
            status, body = http_json(f"{base}/v1/admin/monitoring")
            self.assertEqual(status, 200)
            data = body.get("data") or {}
            self.assertIn("coverage", data)
            self.assertIn("etl", data)
            self.assertIn("db", data)


if __name__ == "__main__":
    unittest.main()
