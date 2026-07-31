# -*- coding: utf-8 -*-
"""A-05 Accuracy smoke tests."""
from __future__ import annotations

import unittest

from v3_lab import flags
from v3_lab.a05_accuracy import run_a05_ab
from v3_lab.admission_policy_a05 import POLICY_ID, build_candidate_pool_a05


class A05AccuracyTest(unittest.TestCase):
    def test_mutex_flags(self) -> None:
        flags.reset_flags_to_default()
        with self.assertRaises(ValueError):
            flags.apply_v3_lab_flags(
                read_env=False,
                F_V3_A03_POOL_ADMIT_ENABLED=True,
                F_V3_A05_ADM_FAVSAFE_ENABLED=True,
            )

    def test_identity_small_field(self) -> None:
        runners = [
            {"horse_id": "a", "model_rank": 1, "win_prob": 0.3, "odds": 2.5, "history_score": 0.3, "running_style": "senko"},
            {"horse_id": "b", "model_rank": 2, "win_prob": 0.2, "odds": 5.0, "history_score": 0.2, "running_style": "sashi"},
        ]
        pool, journal = build_candidate_pool_a05({"field_size": 2}, runners)
        self.assertFalse(journal["promote"])
        self.assertEqual(POLICY_ID, journal["policy_id"])
        self.assertEqual(1, pool[0]["model_rank"])

    def test_offline_hard_gate_pass(self) -> None:
        result = run_a05_ab()
        self.assertEqual("PASS", result["decision"])
        self.assertEqual(0, result["hard_gate"]["worsened_winner_rank1"])
        self.assertGreater(result["hard_gate"]["delta_hit"], 0)
        self.assertEqual(66, result["offline"]["a05"]["treatment"]["hit"])
        self.assertEqual(59, result["offline"]["control"]["hit"])


if __name__ == "__main__":
    unittest.main()
