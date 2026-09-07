# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.ab_harness import run_p2_representation_ab
from v3_lab.contracts import CONTRACT_IDS, validate_representation_output
from v3_lab.feature_generator import FEATURE_KEYS, REPRESENTATION_ID
from v3_lab.pipeline import run_lab_pipeline


class RepresentationP2Test(unittest.TestCase):
    def setUp(self) -> None:
        flags.reset_flags_to_default()

    def tearDown(self) -> None:
        flags.reset_flags_to_default()

    def test_flag_off_no_features(self):
        runners = [
            {"horse_id": "A", "horse_number": 1, "model_rank": 1, "win_prob": 0.3, "odds": 4.0},
            {"horse_id": "B", "horse_number": 2, "model_rank": 2, "win_prob": 0.1, "odds": 10.0},
        ]
        bundle = run_lab_pipeline({"race_id": "R-off", "field_size": 2}, runners)
        rep = bundle["representation"]
        self.assertEqual(validate_representation_output(rep, expect_enabled=False), [])
        self.assertEqual(rep["representation_id"], "identity")
        self.assertEqual(rep["embedding_dim"], 0)
        for row in rep["runners"]:
            self.assertNotIn("embedding", row)
            # no V3 features injected
            feats = row.get("features") or {}
            self.assertFalse(any(k.startswith("F_V3_") for k in feats))
        self.assertTrue(bundle["identity"])
        self.assertFalse(bundle["flags"]["F_V3_REPRESENTATION"])
        self.assertFalse(bundle["flags"]["representation_on"])

    def test_flag_on_attaches_features_and_embedding(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_REPRESENTATION=True)
        runners = [
            {
                "horse_id": "A",
                "horse_number": 1,
                "model_rank": 1,
                "win_prob": 0.25,
                "odds": 3.2,
                "popularity": 1,
                "history_score": 0.2,
                "history_count": 6,
                "running_style": "nige",
            },
            {
                "horse_id": "B",
                "horse_number": 2,
                "model_rank": 2,
                "win_prob": 0.12,
                "odds": 9.5,
                "popularity": 4,
                "history_score": 0.1,
                "history_count": 3,
                "running_style": "oikomi",
            },
        ]
        bundle = run_lab_pipeline({"race_id": "R-on", "field_size": 2}, runners)
        rep = bundle["representation"]
        self.assertEqual(validate_representation_output(rep, expect_enabled=True), [])
        self.assertEqual(rep["representation_id"], REPRESENTATION_ID)
        self.assertEqual(rep["journal"]["contract"], CONTRACT_IDS["representation"])
        self.assertEqual(rep["embedding_dim"], len(FEATURE_KEYS))
        self.assertEqual(rep["feature_keys"], list(FEATURE_KEYS))
        self.assertFalse(bundle["identity"])
        self.assertTrue(bundle["flags"]["representation_on"])
        for row in rep["runners"]:
            for key in FEATURE_KEYS:
                self.assertIn(key, row["features"])
            self.assertEqual(len(row["embedding"]), len(FEATURE_KEYS))
        # Evaluation still model_rank passthrough
        self.assertEqual(
            [r["horse_id"] for r in bundle["evaluation"]["ranked"]],
            ["A", "B"],
        )
        dbg = bundle["debug"]["representation"]
        self.assertTrue(dbg["enabled"])
        self.assertIsNotNone(dbg["sample_features"])
        self.assertEqual(len(dbg["sample_embedding"]), len(FEATURE_KEYS))

    def test_alias_flag_enables_representation(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_REPRESENTATION_ENABLED=True)
        self.assertTrue(flags.representation_enabled())
        self.assertTrue(flags.F_V3_REPRESENTATION)

    def test_p2_ab_parity(self):
        result = run_p2_representation_ab()
        self.assertTrue(result["control_reproduces_218"])
        self.assertEqual(result["control"]["hit"], 218)
        self.assertEqual(result["treatment"]["hit"], 218)
        self.assertEqual(result["churn_hit"], 0)
        self.assertTrue(result["representation_parity"]["hit_unchanged"])
        self.assertTrue(result["treatment"]["flags"]["F_V3_REPRESENTATION"])
        self.assertFalse(result["hard_gate"]["pass"])  # Hit>218 not claimed


if __name__ == "__main__":
    unittest.main()
