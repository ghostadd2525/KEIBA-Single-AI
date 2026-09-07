# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[2]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from v3_lab.accuracy_candidate_review import (
    build_candidate_review_corpus,
    run_candidate_review,
)
from v3_lab.taxonomy import CONTROL_HIT


class CandidateReviewTest(unittest.TestCase):
    def test_corpus_size(self):
        self.assertEqual(len(build_candidate_review_corpus()), 285)

    def test_review_ranking(self):
        result = run_candidate_review()
        unified = result["primary_panel"]
        self.assertEqual(unified["baseline"]["hit"], CONTROL_HIT)
        self.assertEqual(unified["a01"]["churn_hit"], 0)
        self.assertEqual(unified["a02"]["churn_hit"], 0)
        self.assertGreater(unified["a01"]["hit"], CONTROL_HIT)
        self.assertGreater(unified["a02"]["hit"], CONTROL_HIT)
        self.assertEqual(result["ranking"]["rank_1"], "A-01")
        self.assertEqual(result["ranking"]["rank_2"], "A-02")
        rc = unified["race_comparison"]
        self.assertEqual(rc["overlap_count"], 0)
        self.assertEqual(rc["worsened_a01"], [])
        self.assertEqual(rc["worsened_a02"], [])


if __name__ == "__main__":
    unittest.main()
