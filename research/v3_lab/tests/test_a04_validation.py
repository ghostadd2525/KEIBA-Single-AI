# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.a04_validation import (
    run_a04_validation,
    run_reproducibility,
    verify_frozen_modules,
)


class A04ValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        flags.reset_flags_to_default()

    def tearDown(self) -> None:
        flags.reset_flags_to_default()

    def test_frozen_modules(self):
        result = verify_frozen_modules()
        self.assertTrue(result["pass"], result)

    def test_reproducibility(self):
        result = run_reproducibility(rounds=2)
        self.assertTrue(result["pass"])
        self.assertTrue(result["matches_expected"])
        self.assertEqual(result["reference"]["boundary_improved"], 14)
        self.assertEqual(result["reference"]["reorder_improved"], 10)

    def test_full_validation_pass(self):
        result = run_a04_validation()
        self.assertEqual(result["decision"], "PASS")
        self.assertTrue(result["hard_gate"]["pass"])
        solo = result["panels"]["a04_solo"]
        stack = result["panels"]["baseline_v2_plus_a04"]
        self.assertEqual(solo["race_diff"]["boundary_improved_count"], 14)
        self.assertEqual(solo["race_diff"]["reorder_improved_count"], 10)
        self.assertEqual(stack["race_diff"]["boundary_improved_count"], 14)
        self.assertEqual(stack["race_diff"]["reorder_improved_count"], 10)
        self.assertEqual(solo["race_diff"]["worsened_count"], 0)
        self.assertEqual(stack["race_diff"]["worsened_count"], 0)
        self.assertEqual(stack["metric_summary"]["control"]["hit"], 255)
        self.assertEqual(stack["metric_summary"]["treatment"]["hit"], 279)
        self.assertTrue(result["stage_isolation"]["a04_solo"]["pass"])
        self.assertTrue(result["stage_isolation"]["baseline_v2_plus_a04"]["pass"])


if __name__ == "__main__":
    unittest.main()
