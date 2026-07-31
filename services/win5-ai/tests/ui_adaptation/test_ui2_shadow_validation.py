# -*- coding: utf-8 -*-
"""Phase UI2 — Existing UI Shadow Validation tests."""
from __future__ import annotations

import unittest

from app.ui_adaptation.shadow_validation import run_shadow_validation


class Ui2ShadowValidationTest(unittest.TestCase):
    def test_shadow_validation_pass(self):
        report = run_shadow_validation(write_artifacts=True)
        self.assertEqual(report["verdict"], "PASS", report["checks"])
        self.assertEqual(report["prediction_bundle_compat_pct"], 100.0)
        self.assertFalse(report["ui_changed"])
        self.assertTrue(report["visual_diff"]["identical_slots"])
        failed = [c for c in report["checks"] if not c["pass"]]
        self.assertEqual(failed, [])


if __name__ == "__main__":
    unittest.main()
