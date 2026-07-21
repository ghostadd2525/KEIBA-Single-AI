# -*- coding: utf-8 -*-
"""Training dataset metrics — NDCG, calibration KPIs."""
from __future__ import annotations

import math
from typing import Sequence


def hit_at_k(relevances: Sequence[float], k: int) -> float:
    """1.0 if any of top-k relevances is positive."""
    top = list(relevances[:k])
    return 1.0 if any(r > 0 for r in top) else 0.0


def dcg_at_k(relevances: Sequence[float], k: int) -> float:
    score = 0.0
    for i, rel in enumerate(relevances[:k]):
        if rel <= 0:
            continue
        score += (2**rel - 1) / math.log2(i + 2)
    return score


def ndcg_at_k(relevances: Sequence[float], k: int) -> float:
    ideal = sorted(relevances, reverse=True)
    idcg = dcg_at_k(ideal, k)
    if idcg <= 0:
        return 0.0
    return dcg_at_k(relevances, k) / idcg


def binary_relevance_from_winner(is_winner: bool) -> float:
    return 1.0 if is_winner else 0.0


def rank_relevance(finish_rank: int | None) -> float:
    if finish_rank is None or finish_rank <= 0:
        return 0.0
    if finish_rank == 1:
        return 1.0
    if finish_rank <= 3:
        return 0.5
    return 0.0


def brier_score(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    if not y_true:
        return 0.0
    n = len(y_true)
    return sum((int(a) - float(b)) ** 2 for a, b in zip(y_true, y_prob)) / n


def log_loss(y_true: Sequence[int], y_prob: Sequence[float], *, eps: float = 1e-15) -> float:
    if not y_true:
        return 0.0
    total = 0.0
    for y, p in zip(y_true, y_prob):
        p = min(max(float(p), eps), 1.0 - eps)
        total += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return total / len(y_true)


def expected_calibration_error(
    y_true: Sequence[int],
    y_prob: Sequence[float],
    *,
    n_bins: int = 10,
) -> float:
    if not y_true:
        return 0.0
    bins: list[list[tuple[int, float]]] = [[] for _ in range(n_bins)]
    for y, p in zip(y_true, y_prob):
        p = min(max(float(p), 0.0), 1.0)
        idx = min(n_bins - 1, int(p * n_bins))
        bins[idx].append((int(y), p))
    ece = 0.0
    n = len(y_true)
    for bucket in bins:
        if not bucket:
            continue
        avg_conf = sum(p for _, p in bucket) / len(bucket)
        avg_acc = sum(y for y, _ in bucket) / len(bucket)
        ece += (len(bucket) / n) * abs(avg_acc - avg_conf)
    return ece
