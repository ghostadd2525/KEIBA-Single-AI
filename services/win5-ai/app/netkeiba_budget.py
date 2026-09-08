# -*- coding: utf-8 -*-
"""Bridge Win5 Netkeiba HTTP onto the shared PI Global HTTP budget."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PI_ROOT = Path(__file__).resolve().parents[2] / "pi-keibanet-api"
if str(_PI_ROOT) not in sys.path:
    sys.path.insert(0, str(_PI_ROOT))

from pi_keibanet.http_budget import (  # noqa: E402
    BudgetDenied,
    Reservation,
    classify_http_result,
    reserve_for_request,
)

__all__ = [
    "BudgetDenied",
    "Reservation",
    "classify_http_result",
    "reserve_win5",
]


def reserve_win5(url: str, *, component: str) -> Reservation:
    return reserve_for_request(url=url, component=component)
