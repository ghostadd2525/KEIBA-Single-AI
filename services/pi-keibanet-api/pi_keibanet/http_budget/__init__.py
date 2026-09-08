# -*- coding: utf-8 -*-
"""Process-shared Global HTTP budget for Netkeiba fetches on a single EC2 disk.

This is not a per-runner env cap. Reservations are atomic in a shared SQLite
file so concurrent systemd processes share one remaining quota.
Default mode is off so a code-only deploy does not stop existing P1.
"""
from .config import (
    MODE_ENFORCE,
    MODE_INVALID,
    MODE_OBSERVE,
    MODE_OFF,
    PRODUCTION_CRITICAL,
    REMAINDER_COMPONENTS,
    WIN5_RESULTS_COMPONENT,
    BudgetConfig,
    load_budget_config,
    resolve_component,
    resolve_mode,
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
from .sanitize import public_target, public_url

__all__ = [
    "BudgetConfig",
    "BudgetDenied",
    "MODE_ENFORCE",
    "MODE_INVALID",
    "MODE_OBSERVE",
    "MODE_OFF",
    "PRODUCTION_CRITICAL",
    "REMAINDER_COMPONENTS",
    "WIN5_RESULTS_COMPONENT",
    "Reservation",
    "classify_http_result",
    "complete_reservation",
    "load_budget_config",
    "public_target",
    "public_url",
    "reserve",
    "reserve_for_request",
    "resolve_component",
    "resolve_mode",
    "window_usage",
]
