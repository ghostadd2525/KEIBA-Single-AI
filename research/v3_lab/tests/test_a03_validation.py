# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.a03_validation import (
    run_a03_validation,
    run_reproducibility,
    verify_frozen_modules,
)


class A03ValidationTest(unittest.TestCase):
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

    def test_full_validation_pass(self):
        result = run_a03_validation()
        self.assertEqual(result["decision"], "PASS")
        self.assertTrue(result["hard_gate"]["pass"])
        solo = result["panels"]["a03_solo"]
        stack = result["panels"]["a01_plus_a03"]
        self.assertEqual(solo["race_diff"]["pool_improved_count"], 9)
        self.assertEqual(stack["race_diff"]["pool_improved_count"], 9)
        self.assertEqual(solo["race_diff"]["worsened_count"], 0)
        self.assertEqual(stack["race_diff"]["worsened_count"], 0)
        self.assertTrue(result["stage_isolation"]["a03_solo"]["pass"])
        self.assertTrue(result["stage_isolation"]["a01_plus_a03"]["pass"])


if __name__ == "__main__":
    unittest.main()
