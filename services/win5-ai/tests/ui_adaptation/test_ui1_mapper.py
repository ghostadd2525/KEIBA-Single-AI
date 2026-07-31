# -*- coding: utf-8 -*-
"""Phase UI1 — Single → PredictionBundle View Mapper tests."""
from __future__ import annotations

import unittest

from app.ui_adaptation.single_to_bundle import (
    assert_no_internal_terms_leaked,
    map_single_to_prediction_bundle,
)


def _core(race_id: str = "20260719_hanshin_11") -> dict:
    return {
        "schema": "core-semantic-payload/v1",
        "race_id": race_id,
        "world_id": "rank7_world",
        "prediction": {
            "ranks": [5, 3, 8, 2],
            "scores": [0.32, 0.22, 0.15, 0.1],
            "top1": 5,
        },
        "near_miss": {"residual_class": "NEAR_MISS", "near_world": "core_world"},
        "affinity": {"core_world": 0.8},
        "explanation_confidence": {"overall": 0.9},
    }


class Ui1MapperTest(unittest.TestCase):
    def test_marks_mapping(self):
        bundle = map_single_to_prediction_bundle({"core_payload": _core()})
        runners = bundle["evaluation"]["runners"]
        self.assertEqual(runners[0]["mark"], "honmei")
        self.assertEqual(runners[0]["horse_number"], 5)
        self.assertEqual(runners[1]["mark"], "taikou")
        self.assertEqual(runners[2]["mark"], "ana")
        self.assertEqual(runners[3]["mark"], "chuuken")
        self.assertEqual(bundle["schema_version"], "single-prediction-bundle/2.0")

    def test_no_internal_terms(self):
        bundle = map_single_to_prediction_bundle(
            {
                "schema": "site-integration/single/v1",
                "race_id": "20260719_hanshin_11",
                "single": {
                    "schema": "consumer-api/single/v1",
                    "race_id": "20260719_hanshin_11",
                    "core_payload": _core(),
                    "presentation": {"world": {"id": "rank7_world"}},
                    "registry": {"world_id": "rank7_world"},
                },
            }
        )
        self.assertEqual(assert_no_internal_terms_leaked(bundle), [])
        self.assertIsNone(bundle["evaluation"]["world"])
        self.assertNotIn("presentation", bundle)
        self.assertNotIn("near_miss", bundle)
        self.assertNotIn("affinity", bundle)
        self.assertNotIn("explanation_confidence", bundle)

    def test_ai_confidence_not_from_ec(self):
        base = {
            "ai_confidence": {"score": 0.7, "band": "medium", "component_scores": {"model_score": 0.7}},
            "race_info": {
                "race_id": "20260719_hanshin_11",
                "date": "2026-07-19",
                "venue": "阪神",
                "race_no": 11,
            },
            "evaluation": {
                "runners": [
                    {
                        "horse_number": 5,
                        "horse_name": "テストホース",
                        "ability_scores": {"history_score": 0.8},
                    }
                ]
            },
        }
        bundle = map_single_to_prediction_bundle(
            {"core_payload": _core()},
            base_bundle=base,
        )
        self.assertEqual(bundle["ai_confidence"]["band"], "medium")
        self.assertEqual(bundle["ai_confidence"]["score"], 0.7)
        honmei = next(r for r in bundle["evaluation"]["runners"] if r["mark"] == "honmei")
        self.assertEqual(honmei["horse_name"], "テストホース")
        self.assertEqual(honmei["ability_scores"]["history_score"], 0.8)
        self.assertEqual(bundle["race_info"]["venue"], "阪神")

    def test_handler(self):
        from app.ui_adaptation.handlers import handle_map_prediction_bundle

        status, body = handle_map_prediction_bundle(
            {"core_payload": _core(), "race_id": "20260719_hanshin_11"},
            authorized=True,
            require_api_key=False,
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["data"]["evaluation"]["runners"][0]["mark"], "honmei")
        self.assertFalse(body["meta"]["layout_changed"])

    def test_ui3_contract_guard_fields(self):
        """Mapper without base_bundle must still pass ExpectContractGuard rules."""
        bundle = map_single_to_prediction_bundle(
            {"core_payload": _core("2026-07-19-04-11")},
            race_id="2026-07-19-04-11",
            race_info={"venue": None, "date": None, "race_no": "11"},
        )
        self.assertEqual(bundle["schema_version"], "single-prediction-bundle/2.0")
        self.assertIsInstance(bundle["race_id"], str)
        self.assertTrue(bundle["race_id"])
        self.assertIsInstance(bundle["race_info"]["venue"], str)
        self.assertIsInstance(bundle["race_info"]["date"], str)
        self.assertIsInstance(bundle["race_info"]["race_no"], int)
        self.assertEqual(bundle["race_info"]["race_no"], 11)
        self.assertIsInstance(bundle["evaluation"]["runners"], list)
        self.assertIn("score", bundle["ai_confidence"])
        self.assertIsInstance(bundle["explain"]["narrative"], str)
        self.assertIsInstance(bundle["betting_recommendations"]["items"], list)
        self.assertEqual(assert_no_internal_terms_leaked(bundle), [])


if __name__ == "__main__":
    unittest.main()
