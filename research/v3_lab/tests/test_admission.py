# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.ab_harness import run_p3_admission_ab
from v3_lab.admission_policy import ADMISSION_ID, POLICY_ID
from v3_lab.contracts import CONTRACT_IDS, validate_admission_output
from v3_lab.pipeline import run_lab_pipeline


def _large_field_runners(n: int = 14) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        rows.append(
            {
                "horse_id": f"L{i}",
                "horse_number": i,
                "model_rank": i,
                "win_prob": max(0.01, 0.25 - 0.015 * (i - 1)),
                "odds": 2.0 + i * 1.2,
                "popularity": i,
                "history_score": max(0.05, 0.2 - 0.01 * i),
                "history_count": max(1, 10 - i),
                "running_style": ["nige", "senko", "sashi", "oikomi"][i % 4],
            }
        )
    return rows


class AdmissionP3Test(unittest.TestCase):
    def setUp(self) -> None:
        flags.reset_flags_to_default()

    def tearDown(self) -> None:
        flags.reset_flags_to_default()

    def test_flag_off_identity_pool(self):
        runners = _large_field_runners(10)
        bundle = run_lab_pipeline({"race_id": "A-off", "field_size": 10}, runners)
        adm = bundle["admission"]
        self.assertEqual(validate_admission_output(adm, expect_enabled=False), [])
        self.assertEqual(len(adm["candidate_pool"]), 10)
        self.assertEqual(adm["policy_id"], "identity")
        self.assertTrue(bundle["identity"])
        self.assertFalse(bundle["flags"]["F_V3_ADMISSION"])
        self.assertFalse(bundle["flags"]["admission_on"])

    def test_flag_on_builds_capacity_pool(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_ADMISSION=True)
        runners = _large_field_runners(14)
        bundle = run_lab_pipeline({"race_id": "A-on", "field_size": 14}, runners)
        adm = bundle["admission"]
        self.assertEqual(validate_admission_output(adm, expect_enabled=True), [])
        self.assertEqual(adm["policy_id"], POLICY_ID)
        self.assertEqual(adm["admission_id"], ADMISSION_ID)
        self.assertEqual(adm["pool_journal"]["contract"], CONTRACT_IDS["admission"])
        self.assertLess(len(adm["candidate_pool"]), 14)
        self.assertLessEqual(len(adm["candidate_pool"]), adm["capacity_max"])
        self.assertGreaterEqual(adm["pool_journal"]["deep_extra"], 1)
        # Core top ranks preserved
        pool_ranks = [r["model_rank"] for r in adm["candidate_pool"]]
        self.assertIn(1, pool_ranks)
        self.assertFalse(bundle["identity"])
        dbg = bundle["debug"]["admission"]
        self.assertTrue(dbg["enabled"])
        self.assertEqual(dbg["policy_id"], POLICY_ID)

    def test_uses_representation_when_both_on(self):
        flags.apply_v3_lab_flags(
            read_env=False,
            F_V3_REPRESENTATION=True,
            F_V3_ADMISSION=True,
        )
        runners = _large_field_runners(14)
        bundle = run_lab_pipeline({"race_id": "A-rep", "field_size": 14}, runners)
        # Representation unchanged contract; admission consumes features
        self.assertTrue(bundle["representation"]["journal"]["enabled"])
        self.assertTrue(bundle["admission"]["pool_journal"]["used_representation"])
        for row in bundle["admission"]["candidate_pool"]:
            self.assertTrue(any(k.startswith("F_V3_") for k in (row.get("features") or {})))

    def test_alias_flag(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_ADMISSION_ENABLED=True)
        self.assertTrue(flags.admission_enabled())
        self.assertTrue(flags.F_V3_ADMISSION)

    def test_p3_ab_parity(self):
        result = run_p3_admission_ab()
        self.assertTrue(result["control_reproduces_218"])
        self.assertEqual(result["control"]["hit"], 218)
        self.assertEqual(result["treatment"]["hit"], 218)
        self.assertEqual(result["churn_hit"], 0)
        self.assertTrue(result["admission_parity"]["active"])
        self.assertTrue(result["admission_parity"]["hit_unchanged"])
        self.assertTrue(result["treatment"]["flags"]["F_V3_ADMISSION"])
        self.assertFalse(result["hard_gate"]["pass"])


if __name__ == "__main__":
    unittest.main()
