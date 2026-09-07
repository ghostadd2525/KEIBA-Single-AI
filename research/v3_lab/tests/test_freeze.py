# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.freeze import (
    BASELINE_ID,
    FREEZE_ID,
    baseline_path,
    build_lab_baseline,
    validate_freeze,
    write_lab_baseline,
)
from v3_lab.registry import REGISTRY_FROZEN, get_experiment
from v3_lab.taxonomy import CONTROL_HIT


class FreezeP5Test(unittest.TestCase):
    def setUp(self) -> None:
        flags.reset_flags_to_default()

    def tearDown(self) -> None:
        flags.reset_flags_to_default()

    def test_validate_freeze_clean(self):
        self.assertEqual(validate_freeze(), [])

    def test_baseline_invariants(self):
        baseline = build_lab_baseline(run_ab=True)
        self.assertEqual(baseline["freeze_id"], FREEZE_ID)
        self.assertEqual(baseline["baseline_id"], BASELINE_ID)
        self.assertEqual(baseline["control"]["hit"], CONTROL_HIT)
        self.assertTrue(baseline["feature_flags"]["all_default_off"])
        self.assertTrue(baseline["pipeline"]["frozen"])
        self.assertTrue(baseline["contracts"]["frozen"])
        self.assertTrue(baseline["experiment_registry"]["frozen"])
        self.assertTrue(baseline["ab_harness"]["parity_all_pass"])
        self.assertTrue(baseline["ab_harness"]["hard_gate_none_claimed"])
        self.assertTrue(baseline["ready_for_accuracy_experiments"])
        self.assertEqual(baseline["pipeline"]["stubs"], ["evaluation", "purchase"])
        self.assertTrue(REGISTRY_FROZEN)
        self.assertIsNotNone(get_experiment("v3-p5-freeze"))

    def test_write_baseline_json(self):
        path = write_lab_baseline(run_ab=True)
        self.assertTrue(path.is_file())
        self.assertEqual(path, baseline_path())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["baseline_id"], BASELINE_ID)
        self.assertTrue(data["ab_harness"]["parity_all_pass"])


if __name__ == "__main__":
    unittest.main()
