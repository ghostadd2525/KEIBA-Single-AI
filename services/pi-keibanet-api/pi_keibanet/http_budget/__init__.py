# -*- coding: utf-8 -*-
"""Process-shared Global HTTP budget for Netkeiba fetches on a single EC2 disk.

This is not a per-runner env cap. Reservations are atomic in a shared SQLite
file so concurrent systemd processes share one remaining quota.
"""
from .config import (
    PRODUCTION_CRITICAL,
    REMAINDER_COMPONENTS,
    BudgetConfig,
    load_budget_config,
    resolve_component,
)
from .guard import (
    BudgetDenied,
    Reservation,
    classify_http_result,
    complete_reservation,
    reserve,
    reserve_for_request,
    window_usage,
)
from .sanitize import public_target

__all__ = [
    "BudgetConfig",
    "BudgetDenied",
    "PRODUCTION_CRITICAL",
    "REMAINDER_COMPONENTS",
    "Reservation",
    "classify_http_result",
    "complete_reservation",
    "load_budget_config",
    "public_target",
    "reserve",
    "reserve_for_request",
    "resolve_component",
    "window_usage",
]
