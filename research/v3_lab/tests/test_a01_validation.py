# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab.a01_validation import (
    EXPECTED_A01,
    run_a01_validation,
    run_reproducibility,
    verify_frozen_modules,
    verify_stage_isolation,
    write_validation_artifacts,
)


class A01ValidationTest(unittest.TestCase):
    def test_frozen_modules(self):
        self.assertTrue(verify_frozen_modules()["pass"])

    def test_stage_isolation(self):
        self.assertTrue(verify_stage_isolation()["pass"])

    def test_reproducibility(self):
        repro = run_reproducibility(rounds=2)
        self.assertTrue(repro["pass"])
        self.assertTrue(repro["matches_expected_a01"])

    def test_full_validation_pass(self):
        result = run_a01_validation()
        self.assertEqual(result["decision"], "PASS")
        self.assertTrue(result["hard_gate"]["pass"])
        self.assertEqual(result["metric_summary"]["control"]["hit"], EXPECTED_A01["control_hit"])
        self.assertEqual(result["metric_summary"]["treatment"]["hit"], EXPECTED_A01["treatment_hit"])
        self.assertEqual(result["metric_summary"]["churn_hit"], 0)
        self.assertEqual(result["race_diff"]["worsened_count"], 0)
        self.assertEqual(result["race_diff"]["improved_count"], EXPECTED_A01["delta_hit"])
        paths = write_validation_artifacts(result)
        self.assertTrue(paths["full"].is_file())
        self.assertTrue(paths["summary"].is_file())
        self.assertTrue(paths["race_diff"].is_file())


if __name__ == "__main__":
    unittest.main()
