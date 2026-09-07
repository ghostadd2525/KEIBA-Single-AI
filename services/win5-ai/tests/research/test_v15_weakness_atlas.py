# -*- coding: utf-8 -*-
"""V15 Weakness Atlas unit tests."""
from __future__ import annotations

import unittest

from app.research.weakness_atlas import (
    _class_family,
    _distance_bucket,
    _surface_key,
    weakness_index,
)


class WeaknessAtlasHelpers(unittest.TestCase):
    def test_surface_and_distance(self):
        self.assertEqual(_surface_key("芝"), "turf")
        self.assertEqual(_surface_key("ダート"), "dirt")
        self.assertEqual(_distance_bucket(1200), "sprint")
        self.assertEqual(_distance_bucket(2000), "middle")

    def test_class_family(self):
        self.assertEqual(_class_family("2歳新馬", "2yo_newcomer"), "newcomer")
        self.assertEqual(_class_family("3歳未勝利", "3yo_maiden"), "maiden")

    def test_weakness_index_bounds(self):
        hi = weakness_index(
            strict_rate=0.0,
            soft_rate=0.0,
            roi=-1.0,
            tie_rate=1.0,
            reliability=0.0,
            resolver_lose_rate=1.0,
            evidence_coverage=0.0,
        )
        lo = weakness_index(
            strict_rate=1.0,
            soft_rate=1.0,
            roi=1.0,
            tie_rate=0.0,
            reliability=100.0,
            resolver_lose_rate=0.0,
            evidence_coverage=1.0,
        )
        self.assertGreaterEqual(hi, 80.0)
        self.assertLessEqual(lo, 20.0)


if __name__ == "__main__":
    unittest.main()
