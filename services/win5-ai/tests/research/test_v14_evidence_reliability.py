# -*- coding: utf-8 -*-
"""V14 Evidence Reliability unit tests."""
from __future__ import annotations

import unittest

from app.research.evidence_reliability import (
    V14_FEATURES,
    EvidenceReliabilityResearch,
    _clamp01,
)


class ReliabilityHelpers(unittest.TestCase):
    def test_features(self):
        self.assertIn("sale_price", V14_FEATURES)
        self.assertIn("owner", V14_FEATURES)
        self.assertIn("oikiri_rating", V14_FEATURES)

    def test_score_bounds(self):
        eng = EvidenceReliabilityResearch()
        s = eng._reliability_score(
            {
                "coverage": 1.0,
                "availability": 1.0,
                "selection_bias": 0.0,
                "temporal_bias": 0.0,
                "leak_risk": 0.0,
                "variance_penalty": 0.0,
                "stability": 1.0,
                "weekly_drift": 0.0,
            }
        )
        self.assertGreaterEqual(s, 99.0)
        self.assertLessEqual(s, 100.0)
        s2 = eng._reliability_score(
            {
                "coverage": 0.0,
                "availability": 0.0,
                "selection_bias": 1.0,
                "temporal_bias": 1.0,
                "leak_risk": 1.0,
                "variance_penalty": 1.0,
                "stability": 0.0,
                "weekly_drift": 1.0,
            }
        )
        self.assertEqual(s2, 0.0)
        self.assertEqual(_clamp01(2.0), 1.0)


if __name__ == "__main__":
    unittest.main()
