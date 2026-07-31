# -*- coding: utf-8 -*-
"""V23 Corpus Growth unit tests."""
from __future__ import annotations

import unittest

from app.research.corpus_growth import diff_metrics, snapshot_metrics


class CorpusGrowthHelpers(unittest.TestCase):
    def test_diff_metrics(self):
        before = {
            "prediction": 100,
            "evidence": 10,
            "knowledge": 50,
            "tie": 5,
            "young_horse": 20,
            "confidence": {"High": 1, "Medium": 2, "Low": 0, "Exploratory": 3},
            "coverage": {"with_evidence_snapshot": 10, "mean_metadata_after": 0.5},
            "segments": {
                "young_horse": 20,
                "maiden": 5,
                "stakes": 2,
                "turf": 40,
                "dirt": 30,
                "distance": {"mile": 10},
                "going": {"良": 8},
                "pop_band": {"pop_1": 4},
            },
        }
        after = {
            "prediction": 120,
            "evidence": 15,
            "knowledge": 55,
            "tie": 6,
            "young_horse": 25,
            "confidence": {"High": 3, "Medium": 2, "Low": 0, "Exploratory": 2},
            "coverage": {"with_evidence_snapshot": 15, "mean_metadata_after": 0.7},
            "segments": {
                "young_horse": 25,
                "maiden": 7,
                "stakes": 2,
                "turf": 50,
                "dirt": 35,
                "distance": {"mile": 12, "sprint": 3},
                "going": {"良": 10},
                "pop_band": {"pop_1": 5},
            },
        }
        d = diff_metrics(before, after)
        self.assertEqual(d["scalar"]["prediction"], 20)
        self.assertEqual(d["scalar"]["evidence"], 5)
        self.assertEqual(d["confidence"]["High"], 2)
        self.assertEqual(d["segments"]["turf"], 10)
        self.assertEqual(d["segments"]["distance"]["sprint"], 3)


if __name__ == "__main__":
    unittest.main()
