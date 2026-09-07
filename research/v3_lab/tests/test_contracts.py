# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.contracts import CONTRACT_IDS, validate_lab_bundle
from v3_lab.pipeline import run_lab_pipeline


class ContractsTest(unittest.TestCase):
    def setUp(self) -> None:
        flags.reset_flags_to_default()

    def test_contract_ids_present(self):
        for key in ("representation", "admission", "selection", "evaluation", "purchase", "pipeline"):
            self.assertIn(key, CONTRACT_IDS)
        self.assertEqual(CONTRACT_IDS["representation"], "v3-lab-representation/2.0")
        self.assertEqual(CONTRACT_IDS["admission"], "v3-lab-admission/2.0")
        self.assertEqual(CONTRACT_IDS["selection"], "v3-lab-selection/2.0")
        self.assertEqual(CONTRACT_IDS["evaluation"], "v3-lab-evaluation/2.0")

    def test_bundle_valid(self):
        runners = [{"horse_id": "A", "horse_number": 1, "model_rank": 1}]
        bundle = run_lab_pipeline({"race_id": "R9"}, runners)
        self.assertEqual(validate_lab_bundle(bundle), [])

    def test_bundle_valid_with_representation_on(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_REPRESENTATION=True)
        runners = [
            {"horse_id": "A", "horse_number": 1, "model_rank": 1, "win_prob": 0.2, "odds": 4.0},
        ]
        bundle = run_lab_pipeline({"race_id": "R9-on", "field_size": 1}, runners)
        self.assertEqual(validate_lab_bundle(bundle), [])
        self.assertEqual(bundle["representation"]["journal"]["contract"], "v3-lab-representation/2.0")

    def test_bundle_valid_with_admission_on(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_ADMISSION=True)
        runners = [
            {"horse_id": "A", "horse_number": 1, "model_rank": 1, "win_prob": 0.2},
            {"horse_id": "B", "horse_number": 2, "model_rank": 2, "win_prob": 0.1},
        ]
        bundle = run_lab_pipeline({"race_id": "R9-adm", "field_size": 2}, runners)
        self.assertEqual(validate_lab_bundle(bundle), [])
        self.assertEqual(bundle["admission"]["pool_journal"]["contract"], "v3-lab-admission/2.0")

    def test_bundle_valid_with_selection_on(self):
        flags.apply_v3_lab_flags(read_env=False, F_V3_SELECTION=True)
        runners = [
            {"horse_id": "A", "horse_number": 1, "model_rank": 1, "win_prob": 0.1},
            {"horse_id": "B", "horse_number": 2, "model_rank": 2, "win_prob": 0.3},
        ]
        bundle = run_lab_pipeline({"race_id": "R9-sel", "field_size": 2}, runners)
        self.assertEqual(validate_lab_bundle(bundle), [])
        self.assertEqual(bundle["selection"]["selection_journal"]["contract"], "v3-lab-selection/2.0")


if __name__ == "__main__":
    unittest.main()
