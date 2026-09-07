# -*- coding: utf-8 -*-
"""V21 Causal Evidence unit tests."""
from __future__ import annotations

import unittest

from app.research.causal_evidence import PRESET_CHAINS, _is_debut


class CausalEvidenceHelpers(unittest.TestCase):
    def test_debut(self):
        self.assertEqual(_is_debut("2yo_newcomer"), "debut")
        self.assertEqual(_is_debut("stakes"), "non_debut")

    def test_presets(self):
        self.assertTrue(any(p["feature"] == "popularity" for p in PRESET_CHAINS))
        self.assertTrue(any(p["condition"] == "surface" for p in PRESET_CHAINS))


if __name__ == "__main__":
    unittest.main()
