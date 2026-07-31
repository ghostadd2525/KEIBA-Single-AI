# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.pipeline import assert_identity_bundle, run_lab_pipeline


class FlagOffIdentityTest(unittest.TestCase):
    def setUp(self) -> None:
        flags.reset_flags_to_default()

    def test_all_flags_default_off(self):
        snap = flags.snapshot_flags()
        for k, v in snap.items():
            if k in ("any_stage_on", "representation_on", "admission_on", "selection_on", "evaluation_on"):
                self.assertFalse(v, k)
            elif k.startswith("F_V3_"):
                self.assertFalse(v, k)

    def test_pipeline_identity(self):
        runners = [
            {"horse_id": "A", "horse_number": 1, "model_rank": 2, "win_prob": 0.1},
            {"horse_id": "B", "horse_number": 2, "model_rank": 1, "win_prob": 0.2},
        ]
        bundle = run_lab_pipeline({"race_id": "R1"}, runners)
        errs = assert_identity_bundle(bundle, runners)
        self.assertEqual(errs, [])
        self.assertTrue(bundle["identity"])
        ranked_ids = [r["horse_id"] for r in bundle["evaluation"]["ranked"]]
        self.assertEqual(ranked_ids, ["B", "A"])


if __name__ == "__main__":
    unittest.main()
