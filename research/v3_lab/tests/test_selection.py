# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.ab_harness import run_p4_selection_ab
from v3_lab.contracts import CONTRACT_IDS, validate_selection_output
from v3_lab.pipeline import run_lab_pipeline
from v3_lab.selection_policy import POLICY_ID, SELECTION_ID


def _pool_runners() -> list[dict]:
    # Intentionally: higher win_prob on worse model_rank to force reorder
    return [
        {"horse_id": "A", "horse_number": 1, "model_rank": 1, "win_prob": 0.12, "odds": 8.0},
        {"horse_id": "B", "horse_number": 2, "model_rank": 2, "win_prob": 0.28, "odds": 3.0},
        {"horse_id": "C", "horse_number": 3, "model_rank": 3, "win_prob": 0.18, "odds": 5.5},
    ]


class SelectionP4Test(unittest.TestCase):
    def setUp(self) -> None:
        flags.reset_flags_to_default()

    def tearDown(self) -> None:
        flags.reset_flags_to_default()

    def test_flag_off_passthrough(self):
        runners = _pool_runners()
        bundle = run_lab_pipeline({"race_id": "S-off", "field_size": 3}, runners)
        sel = bundle["selection"]
        self.assertEqual(validate_selection_output(sel, pool=runners, expect_enabled=False), [])
        self.assertEqual(sel["policy_id"], "identity")
        self.assertEqual([r["horse_id"] for r in sel["selected"]], ["A", "B", "C"])
        self.assertTrue(bundle["identity"])
        self.assertFalse(bundle["flags"]["F_V3_SELECTION"])
        self.assertFalse(bundle["flags"]["selection_on"])

    def test_flag_on_reorders_without_rescue(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_SELECTION=True)
        runners = _pool_runners()
        bundle = run_lab_pipeline({"race_id": "S-on", "field_size": 3}, runners)
        sel = bundle["selection"]
        pool = bundle["admission"]["candidate_pool"]
        self.assertEqual(validate_selection_output(sel, pool=pool, expect_enabled=True), [])
        self.assertEqual(sel["policy_id"], POLICY_ID)
        self.assertEqual(sel["selection_id"], SELECTION_ID)
        self.assertEqual(sel["selection_journal"]["contract"], CONTRACT_IDS["selection"])
        self.assertTrue(sel["selection_journal"]["size_invariant"])
        self.assertEqual(sel["selection_journal"]["pool_external_adds"], 0)
        self.assertTrue(sel["selection_journal"]["rescue_forbidden"])
        selected_ids = [r["horse_id"] for r in sel["selected"]]
        self.assertEqual(sorted(selected_ids), ["A", "B", "C"])
        # Reorder should prefer higher win_prob (B) ahead of A
        self.assertEqual(selected_ids[0], "B")
        self.assertGreater(sel["selection_journal"]["swap_count"], 0)
        # Evaluation stub still ranks by model_rank → A first for pick
        self.assertEqual([r["horse_id"] for r in bundle["evaluation"]["ranked"]], ["A", "B", "C"])
        self.assertFalse(bundle["identity"])
        dbg = bundle["debug"]["selection"]
        self.assertTrue(dbg["enabled"])
        self.assertEqual(dbg["policy_id"], POLICY_ID)

    def test_no_external_rescue(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_SELECTION=True)
        runners = _pool_runners()
        bundle = run_lab_pipeline({"race_id": "S-rescue", "field_size": 3}, runners)
        selected_ids = {r["horse_id"] for r in bundle["selection"]["selected"]}
        pool_ids = {r["horse_id"] for r in bundle["admission"]["candidate_pool"]}
        self.assertTrue(selected_ids.issubset(pool_ids))
        self.assertNotIn("OUTSIDER", selected_ids)

    def test_alias_flag(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_SELECTION_ENABLED=True)
        self.assertTrue(flags.selection_enabled())
        self.assertTrue(flags.F_V3_SELECTION)

    def test_p4_ab_parity(self):
        result = run_p4_selection_ab()
        self.assertTrue(result["control_reproduces_218"])
        self.assertEqual(result["control"]["hit"], 218)
        self.assertEqual(result["treatment"]["hit"], 218)
        self.assertEqual(result["churn_hit"], 0)
        self.assertTrue(result["selection_parity"]["active"])
        self.assertTrue(result["selection_parity"]["hit_unchanged"])
        self.assertTrue(result["treatment"]["flags"]["F_V3_SELECTION"])
        self.assertFalse(result["hard_gate"]["pass"])


if __name__ == "__main__":
    unittest.main()
