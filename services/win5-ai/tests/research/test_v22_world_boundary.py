# -*- coding: utf-8 -*-
"""V22 Existing World Boundary unit tests."""
from __future__ import annotations

import unittest

from app.research.world_boundary_research import (
    EXISTING_WORLDS,
    extract_world_label,
    _race_dist_features,
)


class WorldBoundaryHelpers(unittest.TestCase):
    def test_existing_worlds_locked(self):
        self.assertEqual(len(EXISTING_WORLDS), 6)
        self.assertIn("core_world", EXISTING_WORLDS)
        self.assertNotIn("dummy_world", EXISTING_WORLDS)

    def test_extract_world(self):
        w, s = extract_world_label(
            {"evaluation": {"world": "midupper_world", "sub_world": "midupper_route"}}
        )
        self.assertEqual(w, "midupper_world")
        self.assertEqual(s, "midupper_route")

    def test_dist_features(self):
        d = _race_dist_features(
            [
                {"win_prob": 0.4},
                {"win_prob": 0.3},
                {"win_prob": 0.2},
                {"win_prob": 0.1},
            ]
        )
        self.assertAlmostEqual(d["top1_prob"], 0.4, places=3)
        self.assertAlmostEqual(d["top2_sum"], 0.7, places=3)


if __name__ == "__main__":
    unittest.main()
