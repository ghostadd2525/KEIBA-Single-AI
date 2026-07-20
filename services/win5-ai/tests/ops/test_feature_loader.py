# -*- coding: utf-8 -*-
"""FeatureLoader integration tests — DB is canonical source for Core."""
from __future__ import annotations

import os
import unittest

from tests.ops.helpers import import_sample_data, isolated_env, load_fixture


class FeatureLoaderTest(unittest.TestCase):
    def test_load_from_db_after_etl(self):
        with isolated_env(engine="real"):
            import app.core  # noqa: F401 — register bridge

            from app.data.db import migrate
            from app.data.etl import EtlPipeline
            from ai_platform.core.features import FeatureLoader

            migrate()
            pipe = EtlPipeline()
            pipe.import_races_csv(load_fixture("sample_races.csv"))
            pipe.import_features_csv(load_fixture("sample_features.csv"))

            loaded = FeatureLoader().load("2026-07-19-04-11")
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.feature_source, "db")
            self.assertGreaterEqual(len(loaded.frame), 1)

    def test_classify_matches_core_pipeline(self):
        with isolated_env(engine="real"):
            import app.core  # noqa: F401

            from app.data.db import migrate
            from ai_platform.core.candidate_evaluation import CorePipeline
            from ai_platform.core.features import FeatureLoader

            migrate()
            import_sample_data()

            loader = FeatureLoader()
            self.assertIsNone(loader.classify_unavailable("2026-07-19-04-11"))
            ce = CorePipeline(loader=loader).evaluate("2026-07-19-04-11")
            self.assertIsNotNone(ce)
            assert ce is not None
            self.assertEqual(ce["context"]["feature_source"], "db")

    def test_diagnose_classifies_db_features_available(self):
        with isolated_env(engine="real"):
            import app.core  # noqa: F401

            from app.data.db import migrate
            from app.engine.adapters import single_prediction_mapper as mapper

            migrate()
            import_sample_data()

            reason = mapper.classify_feature_availability("2026-07-19-04-11")
            self.assertIsNone(reason)


class CoreValidationGateTest(unittest.TestCase):
    def test_deployment_gate_ok_on_first_run(self):
        with isolated_env():
            from app.data.core_validation import check_deployment_gate, validate_core

            core = {"real_ai_rate": 0.5, "race_total": 2, "real_ai": 1}
            gate = check_deployment_gate(core, race_date="2099-01-01")
            self.assertTrue(gate["ok"])

    def test_deployment_gate_ng_on_regression(self):
        with isolated_env():
            from app.data.core_validation import check_deployment_gate
            from app.data.repository.supply import SupplyRepository

            SupplyRepository().save_validation(
                run_id=None,
                race_date="2026-07-19",
                coverage={"race_total": 4, "real_ai": 4, "mock": 0, "coverage": 100.0},
                items=[],
                by_reason={},
            )
            core = {"real_ai_rate": 0.25, "race_total": 4, "real_ai": 1}
            gate = check_deployment_gate(core, race_date="2026-07-19")
            self.assertFalse(gate["ok"])
            self.assertEqual(gate["deployment"], "ng")


if __name__ == "__main__":
    unittest.main()
