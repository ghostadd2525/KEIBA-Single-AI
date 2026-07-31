# -*- coding: utf-8 -*-
"""Settle strategy tickets against official finish order + payouts.

Does not change Prediction Engine. Pure P&L math for user ledger.
"""
from __future__ import annotations

from itertools import combinations, permutations
from typing import Any


def _int(v: Any, default: int = 0) -> int:
    try:
        n = int(v)
        return n if n >= 0 else default
    except (TypeError, ValueError):
        return default


def _nums(vals: Any) -> list[int]:
    out: list[int] = []
    for v in vals or []:
        try:
            n = int(v)
            if n >= 1:
                out.append(n)
        except (TypeError, ValueError):
            continue
    return out


def combo_key(nums: list[int], ordered: bool = False) -> str:
    xs = [int(n) for n in nums]
    if not ordered:
        xs = sorted(xs)
    return "-".join(str(x) for x in xs)


def _ticket_count_for(bet_type: str, axis: int | None, rivals: list[int]) -> int:
    rivals = _nums(rivals)
    if axis is None:
        return 0
    if bet_type in ("単勝", "複勝"):
        return 1
    if bet_type == "馬連":
        return len([r for r in (rivals[:3] or rivals) if r != axis])
    if bet_type == "馬単":
        return len([r for r in (rivals[:3] or rivals) if r != axis])
    if bet_type == "ワイド":
        return len([r for r in (rivals[:2] or rivals) if r != axis])
    if bet_type == "三連複":
        pool = [axis] + [r for r in rivals[:3] if r != axis]
        uniq = list(dict.fromkeys(pool))
        if len(uniq) < 3:
            return 0
        return len(list(combinations(uniq, 3)))
    if bet_type == "三連単":
        partners = [r for r in rivals[:3] if r != axis]
        if len(partners) < 2:
            return 0
        return len(partners) * (len(partners) - 1)
    return 0


def expand_bet_tickets(
    bet_type: str,
    amount: int,
    axis: int | None,
    rivals: list[int],
    *,
    unit_stake: int | None = None,
) -> list[dict[str, Any]]:
    """Expand formation into concrete tickets.

    If unit_stake is set, each point gets that stake (preferred for purchase register).
    Otherwise amount is split across points (legacy).
    """
    amount = max(0, _int(amount))
    rivals = _nums(rivals)
    tickets: list[dict[str, Any]] = []
    if axis is None:
        return tickets

    def per_point(n: int) -> int:
        if n <= 0:
            return 0
        if unit_stake is not None:
            return max(100, (_int(unit_stake) // 100) * 100)
        if amount <= 0:
            return 0
        return max(100, (amount // n // 100) * 100)

    if bet_type == "単勝":
        unit = per_point(1)
        if unit <= 0:
            return tickets
        tickets.append({"legs": [axis], "stake": unit, "key": str(axis)})
    elif bet_type == "複勝":
        unit = per_point(1)
        if unit <= 0:
            return tickets
        tickets.append({"legs": [axis], "stake": unit, "key": str(axis)})
    elif bet_type == "馬連":
        partners = [r for r in (rivals[:3] or rivals) if r != axis]
        if not partners:
            return tickets
        unit = per_point(len(partners))
        for p in partners:
            tickets.append(
                {
                    "legs": sorted([axis, p]),
                    "stake": unit,
                    "key": combo_key([axis, p]),
                }
            )
    elif bet_type == "馬単":
        partners = [r for r in (rivals[:3] or rivals) if r != axis]
        if not partners:
            return tickets
        unit = per_point(len(partners))
        for p in partners:
            tickets.append(
                {
                    "legs": [axis, p],
                    "stake": unit,
                    "key": combo_key([axis, p], ordered=True),
                    "ordered": True,
                }
            )
    elif bet_type == "ワイド":
        partners = [r for r in (rivals[:2] or rivals) if r != axis]
        if not partners:
            return tickets
        unit = per_point(len(partners))
        for p in partners:
            tickets.append(
                {
                    "legs": sorted([axis, p]),
                    "stake": unit,
                    "key": combo_key([axis, p]),
                }
            )
    elif bet_type == "三連複":
        pool = [axis] + [r for r in rivals[:3] if r != axis]
        uniq = list(dict.fromkeys(pool))
        if len(uniq) < 3:
            return tickets
        combos = list(combinations(uniq, 3))
        unit = per_point(len(combos))
        for c in combos:
            tickets.append(
                {
                    "legs": sorted(c),
                    "stake": unit,
                    "key": combo_key(list(c)),
                }
            )
    elif bet_type == "三連単":
        partners = [r for r in rivals[:3] if r != axis]
        if len(partners) < 2:
            return tickets
        perms = []
        for a, b in permutations(partners, 2):
            perms.append((axis, a, b))
        unit = per_point(len(perms))
        for p in perms:
            tickets.append(
                {
                    "legs": list(p),
                    "stake": unit,
                    "key": combo_key(list(p), ordered=True),
                    "ordered": True,
                }
            )
    return tickets


def build_purchase_snapshot(
    *,
    axis: dict[str, Any] | None,
    rivals: list[dict[str, Any]] | None,
    bet_types: list[str],
    unit_stake: int,
    prediction_version: str | None = None,
) -> dict[str, Any]:
    """Build frozen strategy snapshot from selected AI bets + unit stake."""
    axis = axis or {}
    try:
        axis_n = int(axis.get("num") or axis.get("horse_number"))
    except (TypeError, ValueError):
        axis_n = None
    rival_rows = []
    rival_nums: list[int] = []
    for r in rivals or []:
        if not isinstance(r, dict):
            continue
        try:
            n = int(r.get("num") or r.get("horse_number"))
        except (TypeError, ValueError):
            continue
        rival_rows.append(r)
        rival_nums.append(n)
    unit = max(100, (_int(unit_stake) // 100) * 100)
    bets: dict[str, Any] = {}
    total = 0
    point_total = 0
    for bt in bet_types or []:
        t = str(bt)
        tickets = expand_bet_tickets(t, 0, axis_n, rival_nums, unit_stake=unit)
        if not tickets:
            continue
        spent = sum(_int(x.get("stake")) for x in tickets)
        bets[t] = {"amount": spent, "tickets": tickets, "points": len(tickets)}
        total += spent
        point_total += len(tickets)
    return {
        "axis": {"num": axis_n, "name": axis.get("name"), "role": axis.get("role")},
        "rivals": rival_rows,
        "prediction_version": prediction_version,
        "unit_stake": unit,
        "selected_bet_types": list(bets.keys()),
        "ticket_points": point_total,
        "theoretical_amount": point_total * unit,
        "bets": bets,
        "purchase_amount": total,
    }


def normalize_strategy_snapshot(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize UI strategy into {bet_type: {amount, tickets[]}}."""
    raw = raw or {}
    if raw.get("bets") and isinstance(raw["bets"], dict):
        bets = raw["bets"]
    else:
        bets = {k: v for k, v in raw.items() if isinstance(v, dict) and "amount" in v}

    axis = None
    rivals: list[int] = []
    axis_raw = raw.get("axis") or {}
    if isinstance(axis_raw, dict):
        try:
            axis = int(axis_raw.get("num") or axis_raw.get("horse_number"))
        except (TypeError, ValueError):
            axis = None
    for r in raw.get("rivals") or []:
        if isinstance(r, dict):
            try:
                rivals.append(int(r.get("num") or r.get("horse_number")))
            except (TypeError, ValueError):
                pass

    out: dict[str, Any] = {
        "axis": {"num": axis, "name": (axis_raw or {}).get("name")} if axis else raw.get("axis"),
        "rivals": raw.get("rivals") or [],
        "prediction_version": raw.get("prediction_version"),
        "bets": {},
    }
    total = 0
    for bet_type, spec in (bets or {}).items():
        if not isinstance(spec, dict):
            continue
        amount = _int(spec.get("amount") or spec.get("stakeYen") or 0)
        tickets = spec.get("tickets")
        if not isinstance(tickets, list) or not tickets:
            tickets = expand_bet_tickets(str(bet_type), amount, axis, rivals)
        else:
            norm_t = []
            for t in tickets:
                if not isinstance(t, dict):
                    continue
                legs = _nums(t.get("legs") or [])
                stake = _int(t.get("stake") or t.get("stakeYen") or 0)
                ordered = bool(t.get("ordered")) or str(bet_type) == "三連単"
                if not legs or stake <= 0:
                    continue
                norm_t.append(
                    {
                        "legs": legs if ordered else sorted(legs),
                        "stake": stake,
                        "key": t.get("key") or combo_key(legs, ordered=ordered),
                        "ordered": ordered,
                    }
                )
            tickets = norm_t
        spent = sum(_int(t.get("stake")) for t in tickets) or amount
        out["bets"][str(bet_type)] = {
            "amount": spent,
            "tickets": tickets,
        }
        total += spent
    out["purchase_amount"] = total
    return out


def lookup_payout(payouts: dict[str, Any], bet_type: str, key: str) -> int | None:
    bucket = (payouts or {}).get(bet_type) or (payouts or {}).get(bet_type.replace("三連", "3連"))
    if not isinstance(bucket, dict):
        return None
    if key in bucket:
        return _int(bucket[key], default=-1)
    # try reversed unordered
    parts = key.split("-")
    if len(parts) == 2:
        alt = f"{parts[1]}-{parts[0]}"
        if alt in bucket:
            return _int(bucket[alt], default=-1)
    return None


def settle_strategy(
    strategy_snapshot: dict[str, Any],
    *,
    finish_order: list[int],
    payouts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Returns purchase/payout/profit/hit and per-bet breakdown.
    payouts values are yen per ¥100 ticket (JRA style).
    """
    snap = normalize_strategy_snapshot(strategy_snapshot)
    order = _nums(finish_order)
    payouts = payouts or {}
    top1 = order[0] if len(order) >= 1 else None
    top2 = set(order[:2]) if len(order) >= 2 else set()
    top3 = set(order[:3]) if len(order) >= 3 else set()

    bet_results: dict[str, Any] = {}
    purchase = 0
    payout_total = 0
    any_hit = False

    for bet_type, spec in (snap.get("bets") or {}).items():
        amount = _int(spec.get("amount"))
        tickets = spec.get("tickets") or []
        purchase += amount
        hit_tickets = []
        miss_tickets = []
        bet_payout = 0
        pending = False

        for t in tickets:
            legs = _nums(t.get("legs"))
            stake = _int(t.get("stake"))
            ordered = bool(t.get("ordered")) or bet_type == "三連単"
            key = str(t.get("key") or combo_key(legs, ordered=ordered))
            hit = False
            if bet_type == "単勝":
                if len(order) < 1:
                    pending = True
                else:
                    hit = len(legs) == 1 and legs[0] == top1
            elif bet_type == "複勝":
                if len(order) < 3:
                    pending = True
                else:
                    hit = len(legs) == 1 and legs[0] in top3
            elif bet_type == "馬単":
                if len(order) < 2:
                    pending = True
                else:
                    hit = legs == order[:2]
            elif bet_type in ("馬連", "ワイド"):
                if len(order) < 2:
                    pending = True
                else:
                    hit = set(legs) <= top2 and len(legs) == 2
                    if bet_type == "馬連":
                        hit = set(legs) == top2
            elif bet_type == "三連複":
                if len(order) < 3:
                    pending = True
                else:
                    hit = set(legs) == top3
            elif bet_type == "三連単":
                if len(order) < 3:
                    pending = True
                else:
                    hit = legs == order[:3]
            else:
                pending = True

            unit_pay = lookup_payout(payouts, bet_type, key)
            yen = 0
            if hit and unit_pay is not None and unit_pay >= 0:
                yen = int(round(unit_pay * (stake / 100.0)))
            elif hit and unit_pay is None:
                pending = True

            row = {
                "key": key,
                "legs": legs,
                "stake": stake,
                "hit": hit,
                "payout": yen,
                "pending": pending and not hit,
            }
            if hit:
                hit_tickets.append(row)
                bet_payout += yen
                any_hit = True
            else:
                miss_tickets.append(row)

        bet_results[bet_type] = {
            "amount": amount,
            "payout": bet_payout,
            "profit": bet_payout - amount,
            "hit": bool(hit_tickets),
            "pending": pending and not hit_tickets,
            "hit_tickets": hit_tickets,
            "miss_tickets": miss_tickets,
        }
        payout_total += bet_payout

    # AI marks vs finish (optional display)
    marks_result = {}
    axis = snap.get("axis") or {}
    try:
        axis_n = int(axis.get("num")) if axis.get("num") is not None else None
    except (TypeError, ValueError):
        axis_n = None
    if axis_n is not None and order:
        place = order.index(axis_n) + 1 if axis_n in order else None
        marks_result["honmei"] = {"mark": "◎", "horse_number": axis_n, "place": place}
    for r in snap.get("rivals") or []:
        if not isinstance(r, dict):
            continue
        try:
            n = int(r.get("num") or r.get("horse_number"))
        except (TypeError, ValueError):
            continue
        role = str(r.get("role") or "")
        mark = "○" if "対抗" in role else ("▲" if "穴" in role else "△")
        place = order.index(n) + 1 if n in order else None
        marks_result.setdefault("others", []).append(
            {"mark": mark, "horse_number": n, "name": r.get("name"), "place": place, "role": role}
        )

    settled = bool(order) and not any(
        (v.get("pending") for v in bet_results.values())
    )

    return {
        "purchase_amount": purchase or _int(snap.get("purchase_amount")),
        "payout_amount": payout_total,
        "profit": payout_total - (purchase or _int(snap.get("purchase_amount"))),
        "hit": 1 if any_hit else 0,
        "settled": 1 if settled else 0,
        "bet_results": bet_results,
        "marks_result": marks_result,
        "strategy_snapshot": snap,
        "finish_order": order,
        "top1": top1,
    }
