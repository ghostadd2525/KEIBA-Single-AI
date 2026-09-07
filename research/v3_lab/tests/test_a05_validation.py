# -*- coding: utf-8 -*-
"""A-05 Validation smoke tests."""
from __future__ import annotations

import unittest

from v3_lab.a05_validation import run_a05_validation, verify_frozen_modules, verify_flag_defaults


class A05ValidationTest(unittest.TestCase):
    def test_sha_and_defaults(self) -> None:
        self.assertTrue(verify_frozen_modules()["pass"])
        self.assertTrue(verify_flag_defaults()["pass"])

    def test_validation_pass(self) -> None:
        result = run_a05_validation(rounds=2)
        self.assertEqual("PASS", result["decision"])
        self.assertTrue(result["reproducibility"]["pass"])
        self.assertEqual(0, result["offline_panel"]["metric_summary"]["worsened_winner_rank1"])
        self.assertEqual(7, result["offline_panel"]["race_diff"]["improved_count"])
        self.assertEqual(66, result["offline_panel"]["metric_summary"]["treatment"]["hit"])


if __name__ == "__main__":
    unittest.main()
