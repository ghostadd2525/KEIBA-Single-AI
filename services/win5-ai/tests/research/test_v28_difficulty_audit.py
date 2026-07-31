# -*- coding: utf-8 -*-
"""V28 Difficulty Signal Audit unit tests."""
from __future__ import annotations

import unittest

from app.research.difficulty_signal_audit import (
    DIFFICULTY_COMPONENTS,
    STABLE_DEFAULT_DIFFICULTY,
    reconstruct_leg_upset,
    sensitivity_grid,
)


class DifficultyAuditHelpers(unittest.TestCase):
    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(
            sum(float(c["weight"]) for c in DIFFICULTY_COMPONENTS), 1.0, places=6
        )

    def test_default_is_half(self):
        self.assertEqual(STABLE_DEFAULT_DIFFICULTY, 0.5)

    def test_reconstruct_missing_leg_uses_0_5_base(self):
        r = reconstruct_leg_upset(
            win5_leg=None,
            horse_count=12,
            pace_collapse_risk=0.0,
            style_entropy=0.0,
            sashi_count=0.0,
            oikomi_count=0.0,
            unknown_count=0.0,
        )
        # 0.50*0.35 + 0.4*0.20 = 0.175+0.08 = 0.255
        self.assertAlmostEqual(r["reconstructed_difficulty"], 0.255, places=3)

    def test_sensitivity_has_horse_count(self):
        s = sensitivity_grid()
        self.assertIn("horse_count", s)
        self.assertGreater(s["horse_count_range"]["delta"], 0)


if __name__ == "__main__":
    unittest.main()
