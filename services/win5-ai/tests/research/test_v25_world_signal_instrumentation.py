# -*- coding: utf-8 -*-
"""V25 World Signal Instrumentation unit tests."""
from __future__ import annotations

import unittest

from app.research.world_signal_instrumentation import (
    SIGNAL_INVENTORY,
    extract_signals_from_bundle,
    extract_signals_from_core_meta,
    merge_signals,
)


class WorldSignalExtract(unittest.TestCase):
    def test_inventory_locked(self):
        self.assertIn("chaos", SIGNAL_INVENTORY)
        self.assertIn("world_line", SIGNAL_INVENTORY)
        self.assertIn("world_reason", SIGNAL_INVENTORY)
        self.assertGreaterEqual(len(SIGNAL_INVENTORY), 8)

    def test_extract_from_bundle_labels(self):
        bundle = {
            "evaluation": {
                "world": "midupper_world",
                "sub_world": "x",
            }
        }
        sig = extract_signals_from_bundle(bundle)
        self.assertEqual(sig["world"], "midupper_world")
        self.assertEqual(sig["sub_world"], "x")
        self.assertIsNone(sig["chaos"])

    def test_extract_nested_numerics(self):
        bundle = {
            "meta": {
                "chaos_score": 0.4,
                "late_stop_risk_score": 0.2,
            },
            "evaluation": {"world": "core_world"},
        }
        sig = extract_signals_from_bundle(bundle)
        self.assertEqual(sig["world"], "core_world")
        self.assertAlmostEqual(sig["chaos_score"], 0.4)
        self.assertAlmostEqual(sig["chaos"], 0.4)
        self.assertAlmostEqual(sig["late_stop"], 0.2)

    def test_core_meta_copy_no_world_judgment(self):
        meta = {
            "chaos_score": 0.5,
            "race_leg_difficulty": 0.3,
            "late_stop_risk_score": 0.1,
            "high_pace_score": 0.7,
            "sustained_run_possible_score": 0.2,
        }
        line = {
            "late_stop": 0.1,
            "sustained": 0.2,
            "high_pace": 0.7,
            "phase_transition": 0.4,
            "world_line_score": 0.55,
            "traffic": 0.3,
            "world_integrated": 0.25,
        }
        sig = extract_signals_from_core_meta(
            meta, line_scores=line, short_field_pressure=0.6
        )
        self.assertAlmostEqual(sig["chaos"], 0.5)
        self.assertAlmostEqual(sig["difficulty"], 0.3)
        self.assertAlmostEqual(sig["world_score"], 0.55)
        self.assertAlmostEqual(sig["short_field_pressure"], 0.6)
        self.assertAlmostEqual(sig["traffic_score"], 0.3)
        self.assertAlmostEqual(sig["world_load_score"], 0.25)
        self.assertIsNone(sig["world"])  # no classify

    def test_merge_prefers_first(self):
        a = extract_signals_from_bundle({"evaluation": {"world": "from_bundle"}})
        b = extract_signals_from_core_meta({"chaos_score": 0.9})
        m = merge_signals(a, b)
        self.assertEqual(m["world"], "from_bundle")
        self.assertAlmostEqual(m["chaos"], 0.9)


if __name__ == "__main__":
    unittest.main()
