# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab.lab_configuration_freeze import (
    BASELINE_V2_ID,
    CANDIDATE_REGISTRY_V2,
    LAB_CONFIGURATION,
    build_lab_baseline_v2,
    write_configuration_freeze_artifacts,
)
from v3_lab.registry import get_experiment
from v3_lab.taxonomy import CONTROL_HIT


class LabConfigurationFreezeTest(unittest.TestCase):
    def test_stack_stages(self):
        by_stage = {s["stage"]: s for s in LAB_CONFIGURATION["pipeline"]}
        self.assertEqual(by_stage["representation"]["mode"], "baseline")
        self.assertEqual(by_stage["admission"]["mode"], "A-03")
        self.assertEqual(by_stage["selection"]["mode"], "baseline")
        self.assertEqual(by_stage["evaluation"]["mode"], "A-01")
        self.assertEqual(by_stage["purchase"]["mode"], "baseline")
        self.assertFalse(LAB_CONFIGURATION["production_wiring"])

    def test_candidates(self):
        self.assertEqual(CANDIDATE_REGISTRY_V2["evaluation_primary"]["candidate_id"], "A-01")
        self.assertEqual(CANDIDATE_REGISTRY_V2["admission_primary"]["candidate_id"], "A-03")
        self.assertEqual(CANDIDATE_REGISTRY_V2["evaluation_secondary"]["candidate_id"], "A-02")
        self.assertFalse(CANDIDATE_REGISTRY_V2["evaluation_secondary"]["in_adopted_stack"])

    def test_baseline_v2(self):
        base = build_lab_baseline_v2()
        self.assertEqual(base["baseline_id"], BASELINE_V2_ID)
        self.assertEqual(base["control"]["hit"], CONTROL_HIT)
        self.assertEqual(base["stack"]["hit"], 255)
        self.assertTrue(base["invariants"]["stack_hit_255"])
        self.assertTrue(base["invariants"]["churn_vs_a01_0"])
        paths = write_configuration_freeze_artifacts(base)
        self.assertTrue(paths["baseline_v2"].is_file())

    def test_registry_entry(self):
        freeze = get_experiment("v3-lab-configuration-freeze")
        self.assertEqual(freeze["status"], "complete")
        self.assertEqual(get_experiment("v3-a01-d1-recal")["status"], "lab_primary_evaluation")
        self.assertEqual(get_experiment("v3-a03-pool-coverage")["status"], "lab_primary_admission")


if __name__ == "__main__":
    unittest.main()
