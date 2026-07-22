# -*- coding: utf-8 -*-
"""Unit tests for CE-V2 Facet A (temperature)."""
from __future__ import annotations

import math
import unittest

import pandas as pd

import v2_ce_v2 as ce


class TestCeV2A(unittest.TestCase):
    def setUp(self) -> None:
        ce.apply_win5_ce_v2_flags(False)

    def tearDown(self) -> None:
        ce.apply_win5_ce_v2_flags(False)

    def test_flag_default_off_identity_list(self) -> None:
        horses = [
            {"horse_name": "A", "win_prob": 0.5, "model_rank": 1},
            {"horse_name": "B", "win_prob": 0.3, "model_rank": 2},
            {"horse_name": "C", "win_prob": 0.2, "model_rank": 3},
        ]
        meta: dict = {}
        out = ce.apply_win5_ce_v2(horses, meta)
        self.assertEqual([h["win_prob"] for h in out], [0.5, 0.3, 0.2])
        self.assertEqual([h["model_rank"] for h in out], [1, 2, 3])
        self.assertEqual(meta["_win5_ce_v2_journal"]["reason"], "disabled")
        self.assertFalse(meta["_win5_ce_v2_journal"]["fired"])

    def test_flag_off_race_df_identity(self) -> None:
        df = pd.DataFrame(
            {
                "horse_name": ["A", "B", "C"],
                "win_prob": [0.5, 0.3, 0.2],
                "model_rank": [1, 2, 3],
                "gap_to_top_prob": [0.0, 0.2, 0.3],
            }
        )
        meta: dict = {}
        out = ce.apply_win5_ce_v2_to_race_df(df, meta)
        self.assertTrue(out["win_prob"].tolist() == [0.5, 0.3, 0.2])
        self.assertEqual(meta["_win5_ce_v2_journal"]["reason"], "disabled")

    def test_flag_on_changes_probs_and_renormalizes(self) -> None:
        ce.apply_win5_ce_v2_flags(True)
        horses = [
            {"horse_name": "A", "win_prob": 0.5, "model_rank": 1},
            {"horse_name": "B", "win_prob": 0.3, "model_rank": 2},
            {"horse_name": "C", "win_prob": 0.2, "model_rank": 3},
        ]
        meta: dict = {}
        out = ce.apply_win5_ce_v2(horses, meta)
        probs = [h["win_prob"] for h in out]
        self.assertAlmostEqual(sum(probs), 1.0, places=5)
        self.assertNotEqual(probs, [0.5, 0.3, 0.2])
        # T<1 sharpens → top rises
        self.assertGreater(probs[0], 0.5)
        self.assertTrue(meta["_win5_ce_v2_journal"]["fired"])
        self.assertEqual(meta["_win5_ce_v2_journal"]["facet"], "CE-V2-A")

    def test_temperature_t1_matches_renorm(self) -> None:
        probs = [0.4, 0.35, 0.25]
        out = ce.temperature_rescale_probs(probs, 1.0)
        self.assertAlmostEqual(sum(out), 1.0, places=9)
        for a, b in zip(out, probs):
            self.assertAlmostEqual(a, b, places=9)

    def test_no_facet_c_in_module(self) -> None:
        with open(ce.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("MID_LIFT", src)
        self.assertNotIn("CE-V2-C", src)
        self.assertNotIn("CE_V2_C", src)


if __name__ == "__main__":
    unittest.main()
