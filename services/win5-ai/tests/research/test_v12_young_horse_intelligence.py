# -*- coding: utf-8 -*-
"""V12 Young Horse Intelligence unit tests."""
from __future__ import annotations

import unittest

from app.research.young_horse_intelligence import DEBUT_AGE_GROUPS, V12_FEATURES, _safe_div


class YoungHorseIntelHelpers(unittest.TestCase):
    def test_features_include_requested(self):
        for f in (
            "popularity",
            "win_odds",
            "trainer",
            "sire",
            "damsire",
            "breeder",
            "oikiri_time",
            "oikiri_rating",
        ):
            self.assertIn(f, V12_FEATURES)

    def test_debut_group(self):
        self.assertIn("2yo_newcomer", DEBUT_AGE_GROUPS)

    def test_safe_div(self):
        self.assertEqual(_safe_div(1, 2), 0.5)
        self.assertIsNone(_safe_div(1, 0))


if __name__ == "__main__":
    unittest.main()
