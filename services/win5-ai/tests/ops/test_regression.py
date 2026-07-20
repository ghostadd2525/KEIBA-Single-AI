# -*- coding: utf-8 -*-
"""F-2 Regression tests — real_ai / mock 順位・信頼度の意図しない変化を検知。"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.ops.helpers import isolated_env, running_server

BASELINE_PATH = Path(__file__).resolve().parents[1] / "regression" / "real_ai_baseline.json"


def _extract_signature(bundle: dict, meta: dict | None) -> dict:
    runners = ((bundle.get("evaluation") or {}).get("runners")) or []
    top = sorted(
        [r for r in runners if r.get("model_rank") is not None],
        key=lambda r: r.get("model_rank") or 999,
    )[:3]
    conf = (bundle.get("ai_confidence") or {}).get("score")
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
        "ai_confidence": conf,
    }


class PredictionRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        cls.tolerance = cls.baseline.get("tolerance") or {}

    def test_mock_prediction_matches_baseline(self):
        with isolated_env(engine="mock"):
            from app.engine.adapters import prediction_adapter

            for race_id, expected in self.baseline.get("races", {}).items():
                bundle, meta = prediction_adapter.get_with_meta(race_id)
                self.assertIsNotNone(bundle, f"bundle missing for {race_id}")
                sig = _extract_signature(bundle, meta)
                self.assertEqual(sig["engine_source"], expected.get("engine_source"))

                for i, exp_runner in enumerate(expected.get("top_runners") or []):
                    act_runner = sig["top_runners"][i]
                    self.assertEqual(
                        act_runner["horse_number"],
                        exp_runner["horse_number"],
                        f"{race_id} rank{i+1} horse_number",
                    )
                    self.assertEqual(
                        act_runner["model_rank"],
                        exp_runner["model_rank"],
                        f"{race_id} rank{i+1} model_rank",
                    )
                    tol = float(self.tolerance.get("win_prob") or 0.001)
                    self.assertAlmostEqual(
                        float(act_runner["win_prob"] or 0),
                        float(exp_runner["win_prob"] or 0),
                        delta=tol,
                        msg=f"{race_id} rank{i+1} win_prob",
                    )

                conf_tol = float(self.tolerance.get("ai_confidence") or 0.001)
                exp_conf = expected.get("ai_confidence")
                if exp_conf is not None and sig["ai_confidence"] is not None:
                    self.assertAlmostEqual(
                        float(sig["ai_confidence"]),
                        float(exp_conf),
                        delta=conf_tol,
                        msg=f"{race_id} ai_confidence",
                    )

    def test_real_ai_regression_when_available(self):
        """real モード + platform 利用可能時のみ baseline と比較。"""
        with isolated_env(engine="real"):
            from app.engine.adapters import single_prediction_mapper as mapper

            if mapper.locate_ai_platform_root() is None:
                self.skipTest("ai_platform not available")
            from app.engine.adapters import prediction_adapter

            real_races = self.baseline.get("real_ai_races") or {}
            if not real_races:
                self.skipTest("no real_ai baseline entries configured")

            for race_id, expected in real_races.items():
                bundle, meta = prediction_adapter.get_with_meta(race_id)
                if meta and meta.get("engine_source") != "real_ai":
                    self.fail(f"{race_id} expected real_ai got {meta.get('engine_source')}")
                sig = _extract_signature(bundle, meta)
                tol = float(self.tolerance.get("win_prob") or 0.001)
                for i, exp_runner in enumerate(expected.get("top_runners") or []):
                    act = sig["top_runners"][i]
                    self.assertEqual(act["horse_number"], exp_runner["horse_number"])
                    self.assertAlmostEqual(
                        float(act["win_prob"] or 0),
                        float(exp_runner["win_prob"] or 0),
                        delta=tol,
                    )


class CoverageRegressionTest(unittest.TestCase):
    def test_coverage_structure_stable(self):
        with running_server() as base:
            import urllib.request

            with urllib.request.urlopen(f"{base}/v1/data/coverage") as resp:
                body = json.loads(resp.read().decode("utf-8"))
            data = body["data"]
            self.assertIsInstance(data["race_total"], int)
            self.assertIsInstance(data["coverage"], (int, float))
            self.assertEqual(data["real_ai"] + data["mock"], data["race_total"])


if __name__ == "__main__":
    unittest.main()
