# -*- coding: utf-8 -*-
"""V26 World Fitness unit tests."""
from __future__ import annotations

import unittest

from app.research.world_fitness_research import trigger_proximity_fitness
from app.research.world_boundary_research import EXISTING_WORLDS


class WorldFitnessHelpers(unittest.TestCase):
    def test_worlds_complete(self):
        soft = trigger_proximity_fitness(
            {
                "short_field_pressure": 0.7,
                "difficulty": 0.5,
                "phase": 0.1,
                "chaos": 0.1,
                "late_stop": 0.1,
                "sustained": 0.1,
                "high_pace": 0.1,
            }
        )["soft"]
        for w in EXISTING_WORLDS:
            self.assertIn(w, soft)

    def test_midupper_high_when_sf_and_diff(self):
        r = trigger_proximity_fitness(
            {
                "short_field_pressure": 0.7,
                "difficulty": 0.5,
                "phase": 0.0,
                "chaos": 0.0,
                "late_stop": 0.0,
                "sustained": 0.0,
                "high_pace": 0.0,
            }
        )
        self.assertGreaterEqual(r["soft"]["midupper_world"], 0.9)

    def test_chaos_missing_flag(self):
        r = trigger_proximity_fitness({"difficulty": 0.5, "short_field_pressure": 0.6})
        self.assertTrue(r["chaos_missing"])
        self.assertEqual(r["soft"]["rank7_world"], 0.0)


if __name__ == "__main__":
    unittest.main()
