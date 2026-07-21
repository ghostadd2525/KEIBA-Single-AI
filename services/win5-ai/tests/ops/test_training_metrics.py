# -*- coding: utf-8 -*-
"""Training metrics unit tests."""
from __future__ import annotations

import unittest

from app.data.training.metrics import (
    brier_score,
    expected_calibration_error,
    hit_at_k,
    log_loss,
    ndcg_at_k,
)


class TrainingMetricsTest(unittest.TestCase):
    def test_hit_at_k(self):
        self.assertEqual(hit_at_k([1.0, 0.0, 0.0], 3), 1.0)
        self.assertEqual(hit_at_k([0.0, 0.0, 0.0], 3), 0.0)

    def test_ndcg_at_k_perfect(self):
        self.assertAlmostEqual(ndcg_at_k([1.0, 0.5, 0.0], 5), 1.0, places=4)

    def test_brier_and_log_loss(self):
        y_true = [1, 0, 0]
        y_prob = [0.9, 0.2, 0.1]
        self.assertLess(brier_score(y_true, y_prob), 0.1)
        self.assertGreater(log_loss(y_true, y_prob), 0.0)

    def test_ece_zero_for_perfect_calibration(self):
        y_true = [1, 0, 1, 0]
        y_prob = [1.0, 0.0, 1.0, 0.0]
        self.assertEqual(expected_calibration_error(y_true, y_prob, n_bins=2), 0.0)


if __name__ == "__main__":
    unittest.main()
