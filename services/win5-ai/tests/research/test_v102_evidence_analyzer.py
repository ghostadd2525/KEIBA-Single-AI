# -*- coding: utf-8 -*-
"""V10.2 Evidence Analyzer unit tests (shadow only)."""
from __future__ import annotations

import unittest

from app.research.analyzer import (
    extract_runners,
    feature_sort_key,
    resolve_tie_by_feature,
    soft_hit,
    strict_hit,
    tie_group,
    unique_top_pick,
    winner_feature_rank,
)


class TieDetectionTests(unittest.TestCase):
    def test_unique_top_and_soft(self):
        runners = [
            {"horse_number": 3, "model_rank": 1, "win_prob": 0.2, "mark": "honmei"},
            {"horse_number": 1, "model_rank": 1, "win_prob": 0.2, "mark": "honmei"},
            {"horse_number": 5, "model_rank": 3, "win_prob": 0.1, "mark": "ana"},
        ]
        g = tie_group(runners)
        self.assertEqual({int(r["horse_number"]) for r in g}, {1, 3})
        # horse_number break → 1
        self.assertEqual(unique_top_pick(runners), 1)
        self.assertTrue(soft_hit(runners, 3))
        self.assertFalse(strict_hit(runners, 3))
        self.assertTrue(strict_hit(runners, 1))


class FeatureResolveTests(unittest.TestCase):
    def test_popularity_argmin(self):
        g = [
            {"horse_number": 1, "model_rank": 1},
            {"horse_number": 2, "model_rank": 1},
            {"horse_number": 3, "model_rank": 1},
        ]
        vals = {1: 5, 2: 2, 3: 8}
        pick, status = resolve_tie_by_feature(
            feature_id="popularity", group=g, values_by_hn=vals
        )
        self.assertEqual(status, "resolved")
        self.assertEqual(pick, 2)

    def test_odds_unresolved_when_tied(self):
        g = [
            {"horse_number": 1, "model_rank": 1},
            {"horse_number": 2, "model_rank": 1},
        ]
        vals = {1: 3.5, 2: 3.5}
        pick, status = resolve_tie_by_feature(
            feature_id="win_odds", group=g, values_by_hn=vals
        )
        self.assertEqual(status, "unresolved_tie")
        self.assertIsNone(pick)

    def test_categorical_not_rankable(self):
        g = [{"horse_number": 1, "model_rank": 1}, {"horse_number": 2, "model_rank": 1}]
        pick, status = resolve_tie_by_feature(
            feature_id="trainer", group=g, values_by_hn={1: "A", 2: "B"}
        )
        self.assertEqual(status, "not_rankable")
        self.assertIsNone(pick)

    def test_oikiri_rating_letter(self):
        self.assertLess(
            feature_sort_key("oikiri_rating", "A")[1],
            feature_sort_key("oikiri_rating", "C")[1],
        )
        g = [
            {"horse_number": 4, "model_rank": 1},
            {"horse_number": 7, "model_rank": 1},
        ]
        pick, status = resolve_tie_by_feature(
            feature_id="oikiri_rating",
            group=g,
            values_by_hn={4: "C", 7: "A"},
        )
        self.assertEqual(status, "resolved")
        self.assertEqual(pick, 7)

    def test_winner_rank(self):
        runners = [
            {"horse_number": 1},
            {"horse_number": 2},
            {"horse_number": 3},
        ]
        vals = {1: 10.0, 2: 3.0, 3: 5.0}
        self.assertEqual(
            winner_feature_rank(
                feature_id="win_odds",
                runners=runners,
                values_by_hn=vals,
                winner=2,
            ),
            1,
        )


class ExtractRunnersTests(unittest.TestCase):
    def test_evaluation_runners(self):
        bundle = {
            "evaluation": {
                "runners": [
                    {"horse_number": 1, "model_rank": 1, "win_prob": 0.1},
                ]
            }
        }
        rs = extract_runners(bundle)
        self.assertEqual(len(rs), 1)


if __name__ == "__main__":
    unittest.main()
