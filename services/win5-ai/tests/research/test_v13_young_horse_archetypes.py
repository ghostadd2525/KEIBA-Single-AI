# -*- coding: utf-8 -*-
"""V13 Young Horse Archetype unit tests."""
from __future__ import annotations

import unittest

from app.research.young_horse_archetypes import (
    V13_FEATURES,
    _matches_rules,
    discretize_horse,
)


class ArchetypeHelpers(unittest.TestCase):
    def test_features_include_owner_sale(self):
        self.assertIn("owner", V13_FEATURES)
        self.assertIn("sale_price", V13_FEATURES)

    def test_discretize_popularity(self):
        bins = discretize_horse(
            values={"popularity": 1, "win_odds": 2.5},
            cat_priors={},
            race_oikiri_times=[],
        )
        self.assertEqual(bins["popularity"], "P1")
        self.assertEqual(bins["win_odds"], "O_SHORT")

    def test_matches_rules(self):
        bins = {"popularity": "P1", "win_odds": "O_SHORT"}
        self.assertTrue(_matches_rules(bins, {"popularity": "P1"}))
        self.assertTrue(_matches_rules(bins, {"popularity": ["P1", "P2-3"]}))
        self.assertFalse(_matches_rules(bins, {"popularity": "P7+"}))


if __name__ == "__main__":
    unittest.main()
