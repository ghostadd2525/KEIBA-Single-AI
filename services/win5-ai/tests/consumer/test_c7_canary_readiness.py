# -*- coding: utf-8 -*-
"""Phase C7 — Canary Readiness tests."""
from __future__ import annotations

import unittest

from app.consumer.canary_readiness import run_canary_readiness


class C7CanaryReadinessTest(unittest.TestCase):
    def test_ready_with_gaps(self):
        report = run_canary_readiness()
        self.assertIn(report["verdict"], ("READY", "READY_WITH_GAPS"))
        self.assertFalse(report["production_cutover"])
        self.assertFalse(report["feature_addition"])
        for axis in report["axes"]:
            self.assertEqual(axis["status"], "PASS", axis)
        self.assertTrue(any(b["blocker_for_canary"] for b in report["blockers"]))
        self.assertEqual(report["recommendation"]["production_cutover"], "DO_NOT_EXECUTE")


if __name__ == "__main__":
    unittest.main()
