# -*- coding: utf-8 -*-
"""V18 Knowledge Base unit tests."""
from __future__ import annotations

import unittest

from app.research.knowledge_base import (
    KnowledgeBaseBuilder,
    _confidence_level,
    _hypothesis_text,
    _recommended_action,
)


class KnowledgeBaseHelpers(unittest.TestCase):
    def test_confidence_and_action(self):
        self.assertEqual(
            _confidence_level(gate={"confident": True}, n=25, reliability=70),
            "High",
        )
        self.assertEqual(
            _confidence_level(gate={}, n=5, exploratory_corpus=True),
            "Exploratory",
        )
        self.assertEqual(
            _recommended_action(confidence="High", knowledge_type="feature"),
            "Candidate",
        )
        self.assertEqual(
            _recommended_action(confidence="Exploratory", knowledge_type="feature"),
            "Research",
        )

    def test_hypothesis_non_definitive(self):
        h = _hypothesis_text("feature", feature="Popularity")
        self.assertIn("may", h)
        self.assertNotIn("must", h)

    def test_diff(self):
        b = KnowledgeBaseBuilder()
        prev = [
            {
                "source_key": "a",
                "confidence": "Low",
                "recommended_action": "Research",
                "evidence": {"hit_rate": 0.1},
            }
        ]
        curr = [
            {
                "source_key": "a",
                "confidence": "High",
                "recommended_action": "Candidate",
                "evidence": {"hit_rate": 0.3},
            },
            {"source_key": "b", "confidence": "Low", "recommended_action": "Watch"},
        ]
        diff = b.compute_diff(curr, prev)
        self.assertEqual(diff["counts"]["added"], 1)
        self.assertEqual(diff["counts"]["changed"], 1)


if __name__ == "__main__":
    unittest.main()
