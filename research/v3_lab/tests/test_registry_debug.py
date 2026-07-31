# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab import flags
from v3_lab.debug import build_debug_view, write_debug_json
from v3_lab.pipeline import run_lab_pipeline
from v3_lab.registry import get_experiment, list_experiments


class RegistryDebugTest(unittest.TestCase):
    def setUp(self) -> None:
        flags.reset_flags_to_default()

    def test_registry_p1_p2_p3_p4_p5(self):
        p1 = list_experiments(phase="P1")
        self.assertTrue(any(x["experiment_id"] == "v3-p1-lab-harness" for x in p1))
        p2 = list_experiments(phase="P2")
        self.assertTrue(any(x["experiment_id"] == "v3-p2-representation" for x in p2))
        p3 = list_experiments(phase="P3")
        self.assertTrue(any(x["experiment_id"] == "v3-p3-admission" for x in p3))
        p4 = list_experiments(phase="P4")
        self.assertTrue(any(x["experiment_id"] == "v3-p4-selection" for x in p4))
        p5 = list_experiments(phase="P5")
        self.assertTrue(any(x["experiment_id"] == "v3-p5-freeze" for x in p5))
        self.assertIsNotNone(get_experiment("v3-a01-d1-recal"))
        self.assertIsNotNone(get_experiment("v3-rank-d1-recal-285r-ab"))
        self.assertIsNotNone(get_experiment("v3-a02-d2-rerank"))
        self.assertEqual(get_experiment("v3-a02-d2-rerank")["flag"], "F_V3_RANK_D2_ENABLED")

    def test_debug_write(self):
        bundle = run_lab_pipeline(
            {"race_id": "R-debug"},
            [{"horse_id": "X", "horse_number": 3, "model_rank": 1}],
        )
        view = build_debug_view(bundle)
        self.assertEqual(view["race_id"], "R-debug")
        with tempfile.TemporaryDirectory() as tmp:
            path = write_debug_json(bundle, Path(tmp) / "debug.json")
            self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
