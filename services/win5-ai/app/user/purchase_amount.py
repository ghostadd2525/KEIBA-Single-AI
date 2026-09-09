# -*- coding: utf-8 -*-
"""Purchase / Challenge unit stake validation (official max from app_settings)."""
from __future__ import annotations

from typing import Any

DEFAULT_MAX_PURCHASE_AMOUNT_PER_RACE = 50000
MIN_UNIT_STAKE = 100
UNIT_STAKE_STEP = 100


def validate_purchase_unit_amount(
    raw: Any,
    *,
    max_amount: int = DEFAULT_MAX_PURCHASE_AMOUNT_PER_RACE,
    field_name: str = "unit_stake",
) -> int:
    """Validate Challenge / purchase unit amount.

    Rules (official):
      - integer only (reject bool, non-integral float, non-digit strings)
      - amount >= 100
      - amount % 100 == 0
      - amount <= max_amount (default / settings: max_purchase_amount_per_race)
    """
    try:
        max_n = int(max_amount)
    except (TypeError, ValueError):
        max_n = DEFAULT_MAX_PURCHASE_AMOUNT_PER_RACE
    if max_n < MIN_UNIT_STAKE:
        max_n = DEFAULT_MAX_PURCHASE_AMOUNT_PER_RACE

    if raw is None:
        raise ValueError(f"{field_name} required")
    if isinstance(raw, bool):
        raise ValueError(f"{field_name} must be an integer")
    if isinstance(raw, float):
        if not raw.is_integer():
            raise ValueError(f"{field_name} must be an integer")
        amount = int(raw)
    elif isinstance(raw, int):
        amount = raw
    elif isinstance(raw, str):
        s = raw.strip()
        if not s:
            raise ValueError(f"{field_name} required")
        if s.startswith("-") or s.startswith("+"):
            raise ValueError(f"{field_name} must be a positive integer")
        if not s.isdigit():
            raise ValueError(f"{field_name} must be an integer")
        amount = int(s)
    else:
        raise ValueError(f"{field_name} must be an integer")

    if amount < MIN_UNIT_STAKE:
        raise ValueError(f"{field_name} must be at least {MIN_UNIT_STAKE}")
    if amount % UNIT_STAKE_STEP != 0:
        raise ValueError(f"{field_name} must be a multiple of {UNIT_STAKE_STEP}")
    if amount > max_n:
        raise ValueError(f"{field_name} exceeds max ({max_n})")
    return amount
