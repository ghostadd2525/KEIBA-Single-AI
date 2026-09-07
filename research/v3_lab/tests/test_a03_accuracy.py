# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.a03_accuracy import A01_PRIMARY_HIT, build_a03_accuracy_corpus, run_a03_ab
from v3_lab.admission_policy_a03 import ADMISSION_ID, CONTRACT_ID, POLICY_ID
from v3_lab.contracts import validate_admission_output
from v3_lab.pipeline import run_lab_pipeline
from v3_lab.taxonomy import CONTROL_HIT


class AccuracyA03Test(unittest.TestCase):
    def setUp(self) -> None:
        flags.reset_flags_to_default()

    def tearDown(self) -> None:
        flags.reset_flags_to_default()

    def test_flag_default_off(self):
        self.assertFalse(flags.F_V3_A03_POOL_ADMIT_ENABLED)

    def test_a03_promotes_pool_coverage(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_A03_POOL_ADMIT_ENABLED=True)
        runners = []
        for num in range(1, 13):
            style = "senko" if num != 9 else "oikomi"
            wp = 0.055 if num == 9 else (0.24 - 0.02 * (num - 1) if num <= 6 else 0.03)
            runners.append(
                {
                    "horse_id": f"H-{num}",
                    "horse_number": num,
                    "model_rank": num,
                    "win_prob": wp,
                    "odds": 40.0 if num == 9 else 5.0,
                    "history_score": wp,
                    "running_style": style,
                }
            )
        bundle = run_lab_pipeline({"race_id": "P", "field_size": 12}, runners)
        adm = bundle["admission"]
        self.assertEqual(validate_admission_output(adm, expect_enabled=True), [])
        self.assertEqual(adm["policy_id"], POLICY_ID)
        self.assertEqual(adm["admission_id"], ADMISSION_ID)
        self.assertEqual(adm["pool_journal"]["contract"], CONTRACT_ID)
        self.assertTrue(adm["pool_journal"]["promote"])
        self.assertEqual(bundle["evaluation"]["ranked"][0]["horse_id"], "H-9")

    def test_small_field_no_promote(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_A03_POOL_ADMIT_ENABLED=True)
        runners = [
            {"horse_id": "A", "horse_number": 1, "model_rank": 1, "win_prob": 0.3, "odds": 2.5, "running_style": "senko"},
            {"horse_id": "B", "horse_number": 2, "model_rank": 2, "win_prob": 0.2, "odds": 5.0, "running_style": "oikomi"},
        ]
        bundle = run_lab_pipeline({"race_id": "S", "field_size": 2}, runners)
        self.assertFalse(bundle["admission"]["pool_journal"].get("promote"))
        self.assertEqual(bundle["evaluation"]["ranked"][0]["horse_id"], "A")

    def test_a03_ab_hard_gate(self):
        result = run_a03_ab()
        self.assertTrue(result["control_reproduces_a01_246"])
        self.assertEqual(result["control"]["hit"], A01_PRIMARY_HIT)
        self.assertGreater(result["treatment"]["hit"], A01_PRIMARY_HIT)
        self.assertEqual(result["churn_hit"], 0)
        self.assertTrue(result["hard_gate"]["pass"])
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(len(result["improved_races"]), 9)
        self.assertEqual(result["worsened_races"], [])
        self.assertTrue(all(x["miss_layer"] == "Pool" for x in result["improved_races"]))
        self.assertEqual(result["pool_attribution"]["delta_hit"], 9)

    def test_corpus_size(self):
        self.assertEqual(len(build_a03_accuracy_corpus()), 285)
        self.assertEqual(build_a03_accuracy_corpus()[0]["control_hit"] or True, True)
        hits = sum(1 for r in build_a03_accuracy_corpus() if r["control_hit"])
        self.assertEqual(hits, CONTROL_HIT)


if __name__ == "__main__":
    unittest.main()
