# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab.accuracy_candidate_registry import (
    CANDIDATE_REGISTRY,
    build_phase1_close_snapshot,
    write_phase1_close_artifacts,
)
from v3_lab.registry import get_experiment


class Phase1CloseTest(unittest.TestCase):
    def test_candidate_ranks(self):
        self.assertEqual(CANDIDATE_REGISTRY["primary"]["candidate_id"], "A-01")
        self.assertEqual(CANDIDATE_REGISTRY["secondary"]["candidate_id"], "A-02")
        self.assertFalse(CANDIDATE_REGISTRY["decision"]["simultaneous_on"])
        self.assertFalse(CANDIDATE_REGISTRY["decision"]["production_wiring"])
        self.assertFalse(CANDIDATE_REGISTRY["baseline"]["updated"])

    def test_registry_status(self):
        a01 = get_experiment("v3-a01-d1-recal")
        a02 = get_experiment("v3-a02-d2-rerank")
        close = get_experiment("v3-accuracy-phase1-close")
        self.assertEqual(a01["status"], "lab_primary_candidate")
        self.assertEqual(a02["status"], "lab_secondary_candidate")
        self.assertEqual(close["status"], "complete")
        self.assertTrue(close["baseline_unchanged"])

    def test_write_artifacts(self):
        snap = build_phase1_close_snapshot()
        self.assertEqual(snap["status"], "CLOSED")
        paths = write_phase1_close_artifacts(snap)
        for p in paths.values():
            self.assertTrue(p.is_file())


if __name__ == "__main__":
    unittest.main()
