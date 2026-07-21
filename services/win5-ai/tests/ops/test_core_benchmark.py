# -*- coding: utf-8 -*-
"""Prediction Core KPI benchmark tests."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.ops.helpers import import_sample_data, isolated_env, load_fixture


class CoreBenchmarkUnitTest(unittest.TestCase):
    def test_load_labeled_races_from_fixture(self):
        from app.data.core_benchmark import load_labeled_races

        labels = load_labeled_races(result_paths=[load_fixture("sample_results.csv")])
        self.assertIn("2026-07-19-04-11", labels)
        self.assertEqual(labels["2026-07-19-04-11"].by_number[2], 1)

    def test_compare_to_baseline_pass(self):
        from app.data.core_benchmark import CoreKpiSummary, compare_to_baseline

        summary = CoreKpiSummary(
            races_evaluated=1,
            hit_at_1=0.5,
            hit_at_3=0.8,
            hit_at_5=0.9,
            mrr=0.6,
            ndcg_at_5=0.7,
            brier_score=0.1,
            log_loss=0.4,
            ece=0.05,
        )
        baseline = {
            "schema_version": "core-kpi-baseline/1.1",
            "kpi": {
                "hit_at_1": 0.4,
                "hit_at_3": 0.7,
                "hit_at_5": 0.8,
                "mrr": 0.5,
                "ndcg_at_5": 0.6,
                "brier_score": 0.2,
                "log_loss": 0.6,
                "ece": 0.1,
            },
            "tolerance": {
                "hit_at_1": 0.05,
                "hit_at_3": 0.05,
                "hit_at_5": 0.05,
                "mrr": 0.05,
                "ndcg_at_5": 0.05,
                "brier_score": 0.05,
                "log_loss": 0.05,
                "ece": 0.05,
            },
        }
        cmp = compare_to_baseline(summary, baseline)
        self.assertTrue(cmp["ok"])

    def test_compare_to_baseline_fail_on_regression(self):
        from app.data.core_benchmark import CoreKpiSummary, compare_to_baseline

        summary = CoreKpiSummary(races_evaluated=1, hit_at_1=0.2, hit_at_3=0.5, mrr=0.3)
        baseline = {
            "kpi": {"hit_at_1": 0.4, "hit_at_3": 0.7, "mrr": 0.5},
            "tolerance": {"hit_at_1": 0.05, "hit_at_3": 0.05, "mrr": 0.05},
        }
        cmp = compare_to_baseline(summary, baseline)
        self.assertFalse(cmp["ok"])
        self.assertFalse(cmp["checks"]["hit_at_1"]["passed"])

    def test_ranked_horse_numbers(self):
        from app.data.core_benchmark import _ranked_horse_numbers

        cands = [
            {"Rank": 2, "HorseNumber": 5},
            {"Rank": 1, "HorseNumber": 3},
            {"Rank": 3, "HorseNumber": 1},
        ]
        self.assertEqual(_ranked_horse_numbers(cands), [3, 5, 1])


class CoreBenchmarkIntegrationTest(unittest.TestCase):
    def test_run_core_benchmark_with_mock_evaluate(self):
        from app.data.core_benchmark import run_core_benchmark

        def fake_evaluate(race_id: str, **_opts):
            if race_id != "2026-07-19-04-11":
                return None
            return {
                "context": {"feature_source": "db"},
                "candidates": [
                    {"Rank": 1, "HorseNumber": None, "CandidateID": "テスト馬B", "Confidence": 0.7},
                    {"Rank": 2, "HorseNumber": None, "CandidateID": "テスト馬C", "Confidence": 0.2},
                    {"Rank": 3, "HorseNumber": None, "CandidateID": "テスト馬A", "Confidence": 0.1},
                ],
            }

        with patch("app.data.core_benchmark.evaluate_candidates", side_effect=fake_evaluate):
            summary = run_core_benchmark(result_paths=[load_fixture("sample_results.csv")])
        self.assertEqual(summary.races_total, 1)
        self.assertEqual(summary.races_evaluated, 1)
        self.assertEqual(summary.hit_at_1, 1.0)
        self.assertEqual(summary.hit_at_3, 1.0)
        self.assertEqual(summary.hit_at_5, 1.0)
        self.assertEqual(summary.mrr, 1.0)
        self.assertGreater(summary.ndcg_at_5, 0.0)
        self.assertGreaterEqual(summary.brier_score, 0.0)

    def test_benchmark_gate_in_core_validation(self):
        with isolated_env():
            from app.data.core_benchmark import CoreKpiSummary
            from app.data.core_validation import check_benchmark_gate

            baseline = {
                "kpi": {
                    "hit_at_1": 0.0,
                    "hit_at_3": 0.0,
                    "hit_at_5": 0.0,
                    "mrr": 0.0,
                    "ndcg_at_5": 0.0,
                    "brier_score": 1.0,
                    "log_loss": 2.0,
                    "ece": 1.0,
                },
                "tolerance": {
                    "hit_at_1": 0.05,
                    "hit_at_3": 0.05,
                    "hit_at_5": 0.05,
                    "mrr": 0.05,
                    "ndcg_at_5": 0.05,
                    "brier_score": 0.05,
                    "log_loss": 0.05,
                    "ece": 0.05,
                },
            }
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "baseline.json"
                path.write_text(json.dumps(baseline), encoding="utf-8")
                os.environ["CORE_KPI_BASELINE_PATH"] = str(path)

                fake_summary = CoreKpiSummary(
                    hit_at_1=0.5,
                    hit_at_3=0.8,
                    hit_at_5=0.85,
                    mrr=0.6,
                    ndcg_at_5=0.7,
                    brier_score=0.1,
                    log_loss=0.4,
                    ece=0.05,
                    races_evaluated=1,
                )
                with patch("app.data.core_benchmark.run_core_benchmark", return_value=fake_summary):
                    gate = check_benchmark_gate()
                self.assertTrue(gate["ok"])
                self.assertEqual(gate["deployment"], "ok")


class ModelRegistryTest(unittest.TestCase):
    def test_field_size_temperature_increases_for_large_fields(self):
        overlay = Path(__file__).resolve().parents[2] / "platform" / "core-overlay"
        platform = Path(os.environ.get("AI_PLATFORM_ROOT") or "")
        if not platform.is_dir():
            for candidate in (
                Path(__file__).resolve().parents[4],
                Path(__file__).resolve().parents[3],
            ):
                if (candidate / "ai_platform").is_dir():
                    platform = candidate
                    break
        self.assertTrue(platform.is_dir(), "AI platform root not found")
        from app.core.platform_overlay import apply_platform_overlay

        apply_platform_overlay(platform, overlay)
        if str(platform) not in sys.path:
            sys.path.insert(0, str(platform))

        import importlib

        import ai_platform.core.scoring as scoring

        importlib.reload(scoring)
        small = scoring._field_size_temperature(10)
        large = scoring._field_size_temperature(16)
        self.assertGreater(large, small)


class ConfidenceBuilderTest(unittest.TestCase):
    def test_pc4_confidence_overlay(self):
        overlay = Path(__file__).resolve().parents[2] / "platform" / "core-overlay"
        platform = Path(os.environ.get("AI_PLATFORM_ROOT") or "")
        if not platform.is_dir():
            for candidate in (
                Path(__file__).resolve().parents[4],
                Path(__file__).resolve().parents[3],
            ):
                if (candidate / "ai_platform").is_dir():
                    platform = candidate
                    break
        from app.core.platform_overlay import apply_platform_overlay

        apply_platform_overlay(platform, overlay)
        if str(platform) not in sys.path:
            sys.path.insert(0, str(platform))

        import importlib

        for mod in list(sys.modules):
            if mod.startswith("ai_platform.core.confidence"):
                del sys.modules[mod]
        import ai_platform.core.confidence as confidence

        importlib.reload(confidence)
        builder = confidence.ConfidenceBuilder()
        bundle = {
            "race_id": "test-race",
            "candidate_ids": ["A", "B", "C"],
            "win_prob": __import__("pandas").Series([0.5, 0.3, 0.2]),
            "_source_frame": __import__("pandas").DataFrame(index=[0, 1, 2]),
        }
        out = builder.build_confidence(bundle, {"field_size": 3})
        self.assertIn("band", out)
        self.assertAlmostEqual(sum(out["per_horse"].values()), 1.0, places=4)
        self.assertGreater(out["overall"], 0.0)


if __name__ == "__main__":
    unittest.main()
