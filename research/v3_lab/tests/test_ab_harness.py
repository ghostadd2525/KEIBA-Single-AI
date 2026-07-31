# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab.ab_harness import (
    build_control_corpus_fixture,
    run_ab,
    run_p2_representation_ab,
    run_p3_admission_ab,
    run_p4_selection_ab,
)
from v3_lab.taxonomy import CONTROL_CORPUS_SIZE, CONTROL_HIT, validate_taxonomy_lock


class AbHarnessTest(unittest.TestCase):
    def test_control_reproduces_218(self):
        corpus = build_control_corpus_fixture()
        self.assertEqual(len(corpus), CONTROL_CORPUS_SIZE)
        result = run_ab(corpus=corpus, treatment_flags={})
        self.assertTrue(result["control_reproduces_218"])
        self.assertEqual(result["control"]["hit"], CONTROL_HIT)
        self.assertEqual(result["treatment"]["hit"], CONTROL_HIT)
        self.assertEqual(result["churn_hit"], 0)
        self.assertFalse(result["hard_gate"]["pass"])

    def test_p2_representation_ab_parity(self):
        result = run_p2_representation_ab()
        self.assertEqual(result["experiment_id"], "v3-p2-representation")
        self.assertEqual(result["control"]["hit"], CONTROL_HIT)
        self.assertEqual(result["treatment"]["hit"], CONTROL_HIT)
        self.assertEqual(result["churn_hit"], 0)
        self.assertTrue(result["representation_parity"]["active"])
        self.assertTrue(result["representation_parity"]["hit_unchanged"])

    def test_p3_admission_ab_parity(self):
        result = run_p3_admission_ab()
        self.assertEqual(result["experiment_id"], "v3-p3-admission")
        self.assertEqual(result["control"]["hit"], CONTROL_HIT)
        self.assertEqual(result["treatment"]["hit"], CONTROL_HIT)
        self.assertEqual(result["churn_hit"], 0)
        self.assertTrue(result["admission_parity"]["active"])
        self.assertTrue(result["admission_parity"]["hit_unchanged"])

    def test_p4_selection_ab_parity(self):
        result = run_p4_selection_ab()
        self.assertEqual(result["experiment_id"], "v3-p4-selection")
        self.assertEqual(result["control"]["hit"], CONTROL_HIT)
        self.assertEqual(result["treatment"]["hit"], CONTROL_HIT)
        self.assertEqual(result["churn_hit"], 0)
        self.assertTrue(result["selection_parity"]["active"])
        self.assertTrue(result["selection_parity"]["hit_unchanged"])

    def test_taxonomy_lock(self):
        self.assertEqual(validate_taxonomy_lock(), [])


if __name__ == "__main__":
    unittest.main()
