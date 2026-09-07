# -*- coding: utf-8 -*-
"""V24 World Activation unit tests."""
from __future__ import annotations

import unittest

from app.research.world_activation_research import (
    EXISTING_WORLDS,
    WORLD_TRIGGER_RULES,
    _proxy_short_field_pressure,
)


class WorldActivationHelpers(unittest.TestCase):
    def test_worlds_locked(self):
        self.assertEqual(len(EXISTING_WORLDS), 6)

    def test_triggers_cover_all_worlds(self):
        covered = {t["world"] for t in WORLD_TRIGGER_RULES}
        for w in EXISTING_WORLDS:
            self.assertIn(w, covered)

    def test_proxy_short_field(self):
        # long distance → 0
        self.assertEqual(_proxy_short_field_pressure(2000, 16), 0.0)
        # short + large field → positive
        p = _proxy_short_field_pressure(1400, 16)
        self.assertIsNotNone(p)
        self.assertGreater(p, 0.5)


if __name__ == "__main__":
    unittest.main()
