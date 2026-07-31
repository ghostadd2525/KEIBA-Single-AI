# -*- coding: utf-8 -*-
"""V9.0 Benchmark Layer — unit checks (no PE/CE/RA changes)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from app.challenge import service as svc


class V9BenchmarkLayerFlagTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("V9_BENCHMARK_LAYER", None)

    def test_flag_default_on(self):
        os.environ.pop("V9_BENCHMARK_LAYER", None)
        self.assertTrue(svc.v9_benchmark_layer_enabled())

    def test_flag_off_values(self):
        for v in ("0", "false", "FALSE", "no", "off"):
            os.environ["V9_BENCHMARK_LAYER"] = v
            self.assertFalse(svc.v9_benchmark_layer_enabled(), v)

    def test_flag_on_values(self):
        for v in ("1", "true", "TRUE", "yes", "on"):
            os.environ["V9_BENCHMARK_LAYER"] = v
            self.assertTrue(svc.v9_benchmark_layer_enabled(), v)

    def test_benchmark_strategy_meta(self):
        os.environ["V9_BENCHMARK_LAYER"] = "false"
        meta = svc.benchmark_strategy_meta()
        self.assertEqual(meta["current_strategy"], "◎単勝1点")
        self.assertEqual(meta["version"], "9.0")
        self.assertEqual(meta["since"], "2026-07")
        self.assertEqual(meta["status"], "production_standard")
        self.assertIn("last_updated", meta)
        self.assertFalse(meta["enabled"])


class V9CompareShapeTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("V9_BENCHMARK_LAYER", None)
        svc._service = None

    def _fake_ai_monthly(self, month, bet_types=None, **kwargs):
        types = list(bet_types) if bet_types is not None else list(svc.AI_DEFAULT_BET_TYPES)
        profit = -2560 if types == ["単勝"] else -54380
        purchase = 5100 if types == ["単勝"] else 74700
        return {
            "schema_version": svc.SCHEMA_V89,
            "month": month,
            "scope": "test",
            "shared": True,
            "resets_monthly": True,
            "summary": {
                "profit": profit,
                "purchase_amount": purchase,
                "payout_amount": purchase + profit,
                "recovery_rate": 50,
                "hit_rate": 16,
                "race_count": 51,
                "hit_count": 8,
            },
            "weeks": [
                {"week": w, "profit": 0, "races": 0, "hits": 0, "purchase": 0, "payout": 0}
                for w in range(1, 6)
            ],
            "races": [],
            "book": {"bet_types": types, "unit_stake": 100},
        }

    def _fake_user(self, user_id, month):
        return {
            "month": month,
            "user_id": user_id,
            "eligible_from": "2026-07-01",
            "scope": "user_personal_ledger_since_join",
            "summary": {
                "profit": 1000,
                "purchase_amount": 2000,
                "payout_amount": 3000,
                "recovery_rate": 150,
                "hit_rate": 50,
                "race_count": 2,
                "hit_count": 1,
            },
            "weeks": [
                {"week": w, "profit": 0, "races": 0, "hits": 0, "purchase": 0, "payout": 0}
                for w in range(1, 6)
            ],
            "races": [],
        }

    def test_flag_off_keeps_v89_shape(self):
        os.environ["V9_BENCHMARK_LAYER"] = "0"
        cmp = svc.ChallengeCompareService()
        with mock.patch.object(cmp, "ai_monthly", side_effect=self._fake_ai_monthly), mock.patch.object(
            cmp, "user_monthly", side_effect=self._fake_user
        ), mock.patch.object(cmp, "_safe_progress", return_value={}):
            out = cmp.compare("u1", "2026-07")
        self.assertFalse(out["feature_flags"]["v9_benchmark_layer"])
        self.assertEqual(out["schema_version"], svc.SCHEMA_V89)
        self.assertIn("ai", out)
        self.assertNotIn("benchmark", out)
        self.assertNotIn("purchase_lab", out)
        self.assertEqual(out["comparison"]["source"], "ai_legacy_book")
        self.assertEqual(out["comparison"]["ai_profit"], -54380)
        self.assertEqual(out["user_summary"]["profit"], 1000)

    def test_flag_on_uses_benchmark_win(self):
        os.environ["V9_BENCHMARK_LAYER"] = "true"
        cmp = svc.ChallengeCompareService()

        def fake_lab(month):
            return {
                "visible_by_default": False,
                "strategies": [
                    {"id": "sanrentan", "label": "三連単", "bet_types": ["三連単"], "summary": {}},
                    {"id": "umaren", "label": "馬連", "bet_types": ["馬連"], "summary": {}},
                    {"id": "wide", "label": "ワイド", "bet_types": ["ワイド"], "summary": {}},
                    {"id": "place", "label": "複勝", "bet_types": ["複勝"], "summary": {}},
                    {"id": "win_place", "label": "単勝＋複勝", "bet_types": ["単勝", "複勝"], "summary": {}},
                ],
            }

        with mock.patch.object(cmp, "ai_monthly", side_effect=self._fake_ai_monthly), mock.patch.object(
            cmp, "user_monthly", side_effect=self._fake_user
        ), mock.patch.object(cmp, "purchase_lab_monthly", side_effect=fake_lab), mock.patch.object(
            cmp, "_safe_progress", return_value={}
        ):
            out = cmp.compare("u1", "2026-07")

        self.assertTrue(out["feature_flags"]["v9_benchmark_layer"])
        self.assertEqual(out["schema_version"], svc.SCHEMA_V9)
        self.assertIn("benchmark", out)
        self.assertIn("purchase_lab", out)
        self.assertEqual(out["benchmark"]["book"]["bet_types"], ["単勝"])
        self.assertEqual(out["comparison"]["source"], "benchmark")
        self.assertEqual(out["comparison"]["ai_profit"], -2560)
        self.assertEqual(out["comparison"]["benchmark_profit"], -2560)
        # User Challenge isolated
        self.assertEqual(out["user"]["summary"]["profit"], 1000)
        self.assertEqual(out["user_summary"]["profit"], 1000)
        ids = [s["id"] for s in out["purchase_lab"]["strategies"]]
        self.assertEqual(ids, ["sanrentan", "umaren", "wide", "place", "win_place"])
        self.assertFalse(out["purchase_lab"]["visible_by_default"])


class PurchaseLabConstantsTests(unittest.TestCase):
    def test_lab_strategies_match_spec(self):
        labels = [s["label"] for s in svc.PURCHASE_LAB_STRATEGIES]
        self.assertEqual(labels, ["三連単", "馬連", "ワイド", "複勝", "単勝＋複勝"])
        self.assertEqual(svc.BENCHMARK_BET_TYPES, ["単勝"])


if __name__ == "__main__":
    unittest.main()
