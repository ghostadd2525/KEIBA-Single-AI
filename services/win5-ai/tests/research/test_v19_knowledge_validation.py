# -*- coding: utf-8 -*-
"""V19 Knowledge Validation unit tests."""
from __future__ import annotations

import unittest

from app.research.knowledge_validation import (
    KnowledgeValidationLab,
    VALIDATION_GATE,
    _parse_pattern,
    _shadow_flag_key,
)


class KnowledgeValidationHelpers(unittest.TestCase):
    def test_pattern_and_flag(self):
        self.assertEqual(
            _parse_pattern("popularity=P1|sire=SIRE_WEAK"),
            {"popularity": "P1", "sire": "SIRE_WEAK"},
        )
        self.assertTrue(_shadow_flag_key("kb-abc").startswith("shadow.knowledge."))

    def test_shadow_flag_feature(self):
        lab = KnowledgeValidationLab()
        entry = {
            "knowledge_id": "kb-test",
            "knowledge_type": "feature",
            "source_key": "feature:ALL:popularity",
            "graph": {"features": ["popularity"]},
            "meta": {},
        }
        flag = lab.generate_shadow_flag(entry)
        self.assertEqual(flag["mode"], "field_best_feature")
        self.assertEqual(flag["feature_id"], "popularity")
        self.assertFalse(flag["mutates_production"])

    def test_governance_gate_keys(self):
        self.assertIn("min_n", VALIDATION_GATE)


if __name__ == "__main__":
    unittest.main()
