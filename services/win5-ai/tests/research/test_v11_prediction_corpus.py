# -*- coding: utf-8 -*-
"""V11 Prediction Corpus unit tests."""
from __future__ import annotations

import unittest

from app.research.prediction_corpus import (
    _age_group,
    _is_young_horse,
    _parse_catalog_race_id,
    _parse_coded_race_id,
)


class CorpusHelperTests(unittest.TestCase):
    def test_parse_coded_race_id(self):
        parsed = _parse_coded_race_id("2026-07-26-03-05")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["race_date"], "2026-07-26")
        self.assertEqual(parsed["venue_code"], "03")
        self.assertEqual(parsed["race_no"], 5)

    def test_parse_catalog_race_id(self):
        parsed = _parse_catalog_race_id("2024-01-06-京都-10")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["venue"], "京都")
        self.assertEqual(parsed["race_no"], 10)

    def test_young_horse_age_group(self):
        self.assertEqual(_age_group("2歳新馬"), "2yo_newcomer")
        self.assertEqual(_age_group("3歳未勝利"), "3yo_maiden")
        self.assertEqual(_age_group("ジュニアC"), "2yo_other")
        self.assertEqual(_age_group("3歳以上1勝クラス"), "older")
        self.assertTrue(_is_young_horse("2yo_maiden"))
        self.assertFalse(_is_young_horse("older"))


if __name__ == "__main__":
    unittest.main()
