# -*- coding: utf-8 -*-
"""V10.4 Evidence Ranking Engine unit tests."""
from __future__ import annotations

import unittest

from app.research.ranking_engine import (
    cascade_resolve,
    feature_score,
    mutual_information_binary,
    resolve_by_score,
)


class ScoreTests(unittest.TestCase):
    def test_popularity_lower_better(self):
        self.assertGreater(feature_score("popularity", 1), feature_score("popularity", 5))

    def test_sale_price_higher_better(self):
        a = feature_score("sale_price", "5,720万円 (2024年 セレクトセール)")
        b = feature_score("sale_price", "1,000万円")
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertGreater(a, b)

    def test_categorical_prior(self):
        prior = {"社台ファーム": 0.4, "未知": 0.1}
        self.assertGreater(
            feature_score("breeder", "社台ファーム", cat_prior=prior),
            feature_score("breeder", "未知", cat_prior=prior),
        )


class ResolveTests(unittest.TestCase):
    def test_resolve_unique(self):
        g = [{"horse_number": 1}, {"horse_number": 2}, {"horse_number": 3}]
        pick, status = resolve_by_score(g, {1: 0.1, 2: 0.9, 3: 0.2})
        self.assertEqual(status, "resolved")
        self.assertEqual(pick, 2)

    def test_cascade(self):
        g = [{"horse_number": 1}, {"horse_number": 2}]
        vals = {
            "popularity": {1: 3, 2: 3},
            "trainer": {1: "A", 2: "B"},
        }
        priors = {"trainer": {"A": 0.2, "B": 0.8}}
        pick, status, fid = cascade_resolve(
            g, ["popularity", "trainer"], vals, priors
        )
        self.assertEqual(status, "resolved")
        self.assertEqual(pick, 2)
        self.assertEqual(fid, "trainer")


class MITests(unittest.TestCase):
    def test_mi_positive_when_dependent(self):
        xs = ["fav"] * 10 + ["long"] * 10
        ys = [1] * 8 + [0] * 2 + [1] * 2 + [0] * 8
        mi = mutual_information_binary(xs, ys)
        self.assertGreater(mi, 0.1)


if __name__ == "__main__":
    unittest.main()
