# -*- coding: utf-8 -*-
"""V17 Evidence Discovery unit tests."""
from __future__ import annotations

import unittest

from app.research.evidence_discovery import (
    classify_gate,
    research_category,
    wilson_ci,
)


class EvidenceDiscoveryHelpers(unittest.TestCase):
    def test_wilson_and_gate(self):
        lo, hi = wilson_ci(15, 20)
        self.assertLessEqual(lo, 15 / 20)
        self.assertGreaterEqual(hi, 15 / 20)
        conf = classify_gate(n=30, successes=20, baseline=0.2)
        self.assertTrue(conf["confident"])
        explor = classify_gate(n=10, successes=8, baseline=0.2)
        self.assertTrue(explor["exploratory"])

    def test_category(self):
        self.assertEqual(research_category("2歳新馬", "2yo_newcomer"), "2yo_newcomer")
        self.assertEqual(research_category("3歳未勝利", None), "3yo_maiden")
        self.assertEqual(research_category("3歳以上1勝クラス", "older"), "class_1win")
        self.assertEqual(research_category("G1 高松宮記念", None), "stakes")
        self.assertEqual(research_category("招福S", None, "招福S"), "stakes")
        self.assertEqual(research_category("中山金杯", None), "stakes")


if __name__ == "__main__":
    unittest.main()
