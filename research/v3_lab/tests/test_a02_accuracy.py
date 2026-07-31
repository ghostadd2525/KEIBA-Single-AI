# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.a02_accuracy import build_a02_accuracy_corpus, run_a02_ab
from v3_lab.contracts import validate_evaluation_output
from v3_lab.evaluation_policy_d2 import CONTRACT_ID, EVALUATION_ID, POLICY_ID
from v3_lab.pipeline import run_lab_pipeline
from v3_lab.taxonomy import CONTROL_HIT


class AccuracyA02Test(unittest.TestCase):
    def setUp(self) -> None:
        flags.reset_flags_to_default()

    def tearDown(self) -> None:
        flags.reset_flags_to_default()

    def test_flag_off_identity(self):
        runners = [
            {"horse_id": "A", "horse_number": 1, "model_rank": 2, "win_prob": 0.4, "odds": 3.0},
            {"horse_id": "B", "horse_number": 2, "model_rank": 1, "win_prob": 0.2, "odds": 5.0},
        ]
        bundle = run_lab_pipeline({"race_id": "D2-off"}, runners)
        self.assertEqual(
            [r["horse_id"] for r in bundle["evaluation"]["ranked"]],
            ["B", "A"],
        )
        self.assertEqual(validate_evaluation_output(bundle["evaluation"], expect_enabled=False), [])

    def test_d2_recovers_crowded_boundary(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_RANK_D2_ENABLED=True)
        runners = [
            {
                "horse_id": "A",
                "horse_number": 1,
                "model_rank": 1,
                "win_prob": 0.190,
                "odds": 3.5,
                "history_score": 0.12,
            },
            {
                "horse_id": "B",
                "horse_number": 2,
                "model_rank": 2,
                "win_prob": 0.185,
                "odds": 3.8,
                "history_score": 0.13,
            },
            {
                "horse_id": "C",
                "horse_number": 3,
                "model_rank": 3,
                "win_prob": 0.180,
                "odds": 4.2,
                "history_score": 0.48,
            },
        ]
        bundle = run_lab_pipeline({"race_id": "D2-on", "field_size": 3}, runners)
        ev = bundle["evaluation"]
        self.assertEqual(validate_evaluation_output(ev, expect_enabled=True), [])
        self.assertEqual(ev["policy_id"], POLICY_ID)
        self.assertEqual(ev["evaluation_id"], EVALUATION_ID)
        self.assertEqual(ev["eval_journal"]["contract"], CONTRACT_ID)
        self.assertEqual(ev["ranked"][0]["horse_id"], "C")
        self.assertIn("evaluation", bundle["debug"])
        self.assertEqual(bundle["debug"]["evaluation"]["policy_id"], POLICY_ID)

    def test_d1_preferred_when_both_on(self):
        flags.apply_v3_lab_flags(
            read_env=False,
            F_V3_RANK_D1_ENABLED=True,
            F_V3_RANK_D2_ENABLED=True,
        )
        runners = [
            {"horse_id": "A", "horse_number": 1, "model_rank": 1, "win_prob": 0.15, "odds": 4.8},
            {"horse_id": "B", "horse_number": 2, "model_rank": 2, "win_prob": 0.40, "odds": 3.1},
        ]
        bundle = run_lab_pipeline({"race_id": "both"}, runners)
        self.assertEqual(bundle["evaluation"]["eval_journal"]["mode"], "d1_recalibrator")

    def test_a02_ab_hard_gate(self):
        result = run_a02_ab()
        self.assertTrue(result["control_reproduces_218"])
        self.assertEqual(result["control"]["hit"], CONTROL_HIT)
        self.assertGreater(result["treatment"]["hit"], CONTROL_HIT)
        self.assertEqual(result["churn_hit"], 0)
        self.assertTrue(result["hard_gate"]["pass"])
        self.assertEqual(result["decision"], "PASS")
        self.assertTrue(result["adopt"])
        self.assertEqual(result["comparison"]["lab_baseline_hit"], 218)
        self.assertEqual(result["comparison"]["a01_reference_hit"], 246)
        for key in ("purchase", "rank710", "rank46", "other", "roi"):
            self.assertIn(key, result["control"])
            self.assertIn(key, result["treatment"])

    def test_a02_corpus_size(self):
        corpus = build_a02_accuracy_corpus()
        self.assertEqual(len(corpus), 285)


if __name__ == "__main__":
    unittest.main()
