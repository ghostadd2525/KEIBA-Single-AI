# -*- coding: utf-8 -*-
"""V27 Trigger Saturation unit tests."""
from __future__ import annotations

import unittest

from app.research.world_trigger_saturation import (
    DESIGN_SHARE,
    atomic_margin,
    evaluate_all_rules,
    first_match_world,
    normalize_signals,
)


class TriggerSaturationHelpers(unittest.TestCase):
    def test_design_sums_to_one(self):
        self.assertAlmostEqual(sum(DESIGN_SHARE.values()), 1.0, places=6)

    def test_atomic_margin(self):
        m = atomic_margin({"chaos": 0.55}, "chaos", 0.58)
        self.assertAlmostEqual(m["margin"], -0.03)
        self.assertFalse(m["pass"])

    def test_missing_chaos(self):
        m = atomic_margin({"chaos": None}, "chaos", 0.58)
        self.assertTrue(m["missing"])
        self.assertIsNone(m["margin"])

    def test_midupper_first_match(self):
        sig = normalize_signals(
            {
                "short_field_pressure": 0.70,
                "difficulty": 0.50,
                "phase": 0.0,
                "chaos": None,
                "late_stop": 0.0,
                "sustained": 0.0,
                "high_pace": 0.0,
            }
        )
        ev = evaluate_all_rules(sig)
        self.assertEqual(first_match_world(ev), "midupper_world")


if __name__ == "__main__":
    unittest.main()
