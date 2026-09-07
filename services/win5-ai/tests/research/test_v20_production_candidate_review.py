# -*- coding: utf-8 -*-
"""V20 Production Candidate Review unit tests."""
from __future__ import annotations

import unittest

from app.research.production_candidate_review import (
    PE_CE_CORE_FEATURES,
    ProductionCandidateReview,
    _worst,
)


class ProductionCandidateReviewHelpers(unittest.TestCase):
    def test_worst(self):
        self.assertEqual(_worst("PASS", "WARNING"), "WARNING")
        self.assertEqual(_worst("WARNING", "FAIL"), "FAIL")
        self.assertEqual(_worst("PASS", "PASS"), "PASS")

    def test_pe_ce_core(self):
        self.assertIn("popularity", PE_CE_CORE_FEATURES)
        self.assertIn("win_odds", PE_CE_CORE_FEATURES)

    def test_pe_ce_alignment_warns_on_market_only(self):
        lab = ProductionCandidateReview()
        d = lab._dim_pe_ce_alignment(
            ["popularity", "win_odds"],
            {"knowledge_type": "feature"},
        )
        self.assertEqual(d["verdict"], "WARNING")


if __name__ == "__main__":
    unittest.main()
