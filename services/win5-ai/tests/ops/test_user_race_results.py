# -*- coding: utf-8 -*-
"""Unit tests for user race result settlement (no Prediction Engine)."""
from __future__ import annotations

from app.user.race_result_settle import (
    expand_bet_tickets,
    normalize_strategy_snapshot,
    settle_strategy,
)


def test_expand_umaren_and_wide():
    tickets = expand_bet_tickets("馬連", 600, 5, [1, 3, 7])
    assert len(tickets) == 3
    assert all(t["stake"] == 200 for t in tickets)
    assert tickets[0]["key"] == "1-5"

    wide = expand_bet_tickets("ワイド", 400, 5, [1, 3, 7])
    assert len(wide) == 2


def test_settle_umaren_hit_with_payout():
    snap = {
        "axis": {"num": 5, "name": "A"},
        "rivals": [
            {"num": 1, "role": "対抗"},
            {"num": 3, "role": "単穴"},
            {"num": 7, "role": "連下"},
        ],
        "bets": {
            "馬連": {"amount": 600},
            "ワイド": {"amount": 200},
        },
    }
    snap = normalize_strategy_snapshot(snap)
    result = settle_strategy(
        snap,
        finish_order=[1, 5, 9],
        payouts={"馬連": {"1-5": 2430}, "ワイド": {"1-5": 480}},
    )
    assert result["hit"] == 1
    assert result["bet_results"]["馬連"]["hit"] is True
    # 200yen ticket → 2430 * 2 = 4860
    assert result["bet_results"]["馬連"]["payout"] == 4860
    assert result["purchase_amount"] > 0
    assert result["payout_amount"] >= 4860


def test_settle_miss():
    snap = normalize_strategy_snapshot(
        {
            "axis": {"num": 5},
            "rivals": [{"num": 1}, {"num": 3}],
            "bets": {"馬連": {"amount": 400}},
        }
    )
    result = settle_strategy(
        snap,
        finish_order=[2, 8, 4],
        payouts={"馬連": {"2-8": 1200}},
    )
    assert result["hit"] == 0
    assert result["payout_amount"] == 0
    assert result["profit"] < 0


def test_snapshot_frozen_shape():
    snap = normalize_strategy_snapshot(
        {
            "axis": {"num": 4, "name": "X"},
            "rivals": [{"num": 2, "role": "対抗"}, {"num": 6, "role": "単穴"}],
            "prediction_version": "test-v1",
            "馬連": {"amount": 300},
        }
    )
    assert "bets" in snap
    assert "馬連" in snap["bets"]
    assert snap["bets"]["馬連"]["tickets"]
    assert snap["purchase_amount"] > 0
