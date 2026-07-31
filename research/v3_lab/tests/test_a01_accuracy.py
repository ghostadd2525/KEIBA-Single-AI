# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.a01_accuracy import build_a01_accuracy_corpus, run_a01_ab
from v3_lab.contracts import CONTRACT_IDS, validate_evaluation_output
from v3_lab.evaluation_policy import EVALUATION_ID, POLICY_ID
from v3_lab.pipeline import run_lab_pipeline
from v3_lab.taxonomy import CONTROL_HIT


class AccuracyA01Test(unittest.TestCase):
    def setUp(self) -> None:
        flags.reset_flags_to_default()

    def tearDown(self) -> None:
        flags.reset_flags_to_default()

    def test_flag_off_identity_rank(self):
        runners = [
            {"horse_id": "A", "horse_number": 1, "model_rank": 2, "win_prob": 0.4, "odds": 3.0},
            {"horse_id": "B", "horse_number": 2, "model_rank": 1, "win_prob": 0.2, "odds": 5.0},
        ]
        bundle = run_lab_pipeline({"race_id": "E-off"}, runners)
        self.assertEqual(
            [r["horse_id"] for r in bundle["evaluation"]["ranked"]],
            ["B", "A"],
        )
        self.assertEqual(validate_evaluation_output(bundle["evaluation"], expect_enabled=False), [])
        self.assertTrue(bundle["identity"])

    def test_d1_reorders_by_calibrated_score(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_RANK_D1_ENABLED=True)
        runners = [
            {"horse_id": "A", "horse_number": 1, "model_rank": 1, "win_prob": 0.15, "odds": 4.8},
            {"horse_id": "B", "horse_number": 2, "model_rank": 2, "win_prob": 0.40, "odds": 3.1},
        ]
        bundle = run_lab_pipeline({"race_id": "E-on", "field_size": 2}, runners)
        ev = bundle["evaluation"]
        self.assertEqual(validate_evaluation_output(ev, expect_enabled=True), [])
        self.assertEqual(ev["policy_id"], POLICY_ID)
        self.assertEqual(ev["evaluation_id"], EVALUATION_ID)
        self.assertEqual(ev["eval_journal"]["contract"], CONTRACT_IDS["evaluation"])
        self.assertEqual(ev["ranked"][0]["horse_id"], "B")
        self.assertFalse(bundle["identity"])

    def test_a01_ab_hard_gate(self):
        result = run_a01_ab()
        self.assertTrue(result["control_reproduces_218"])
        self.assertEqual(result["control"]["hit"], CONTROL_HIT)
        self.assertGreater(result["treatment"]["hit"], CONTROL_HIT)
        self.assertEqual(result["churn_hit"], 0)
        self.assertTrue(result["hard_gate"]["pass"])
        self.assertEqual(result["decision"], "PASS")
        self.assertTrue(result["adopt"])
        # Secondary metrics present
        for key in ("purchase", "rank710", "other", "roi"):
            self.assertIn(key, result["control"])
            self.assertIn(key, result["treatment"])

    def test_a01_corpus_size(self):
        corpus = build_a01_accuracy_corpus()
        self.assertEqual(len(corpus), 285)


if __name__ == "__main__":
    unittest.main()
