# -*- coding: utf-8 -*-
"""Global HTTP budget settings. Defaults never authorize live Netkeiba HTTP."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1

# Default path is local EC2 disk (not NFS). Missing file is fail-closed.
DEFAULT_STATE_PATH = Path("/var/lib/keiba-single-ai/http_budget/budget.sqlite")

# Production-critical components may use reserved capacity.
PRODUCTION_CRITICAL = frozenset({"p1", "c4"})
# Remainder-only: cannot consume the P1/C4 reserved slice.
REMAINDER_COMPONENTS = frozenset({"w2", "w3c", "w4", "w5", "unknown"})
KNOWN_COMPONENTS = PRODUCTION_CRITICAL | REMAINDER_COMPONENTS

_COMPONENT_ALIASES = {
    "race_refresh": "p1",
    "p1_race_refresh": "p1",
    "calendar": "c4",
    "page_a1": "c4",
    "w3-c": "w3c",
    "w3_c": "w3c",
    "w4cd": "w4",
    "w4_horse": "w4",
}


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default) in ("1", "true", "True")


def _int(name: str, default: str) -> int:
    raw = os.environ.get(name, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return int(default)


def resolve_component(value: str | None = None) -> str:
    raw = (value or os.environ.get("GLOBAL_HTTP_BUDGET_COMPONENT") or "unknown").strip().lower()
    return _COMPONENT_ALIASES.get(raw, raw) if raw else "unknown"


@dataclass(frozen=True)
class BudgetConfig:
    enabled: bool
    state_path: Path
    bootstrap: bool
    total_limit: int
    reserved_p1_c4: int
    component_limits: dict[str, int]
    busy_timeout_ms: int
    ledger_retention_days: int
    run_id: str

    @property
    def busy_timeout_sec(self) -> float:
        return max(0.001, self.busy_timeout_ms / 1000.0)


def load_budget_config() -> BudgetConfig:
    """Safe-side defaults: enabled, limits 0, no bootstrap, no live HTTP quota."""
    path_raw = (os.environ.get("GLOBAL_HTTP_BUDGET_STATE_PATH") or "").strip()
    state_path = Path(path_raw) if path_raw else DEFAULT_STATE_PATH
    run_id = (os.environ.get("GLOBAL_HTTP_BUDGET_RUN_ID") or "").strip() or f"pid-{os.getpid()}"
    limits = {
        "p1": _int("GLOBAL_HTTP_BUDGET_LIMIT_P1", "0"),
        "c4": _int("GLOBAL_HTTP_BUDGET_LIMIT_C4", "0"),
        "w2": _int("GLOBAL_HTTP_BUDGET_LIMIT_W2", "0"),
        "w3c": _int("GLOBAL_HTTP_BUDGET_LIMIT_W3C", "0"),
        "w4": _int("GLOBAL_HTTP_BUDGET_LIMIT_W4", "0"),
        "w5": _int("GLOBAL_HTTP_BUDGET_LIMIT_W5", "0"),
        "unknown": _int("GLOBAL_HTTP_BUDGET_LIMIT_UNKNOWN", "0"),
    }
    return BudgetConfig(
        enabled=_flag("GLOBAL_HTTP_BUDGET_ENABLED", "1"),
        state_path=state_path,
        bootstrap=_flag("GLOBAL_HTTP_BUDGET_BOOTSTRAP", "0"),
        total_limit=max(0, _int("GLOBAL_HTTP_BUDGET_TOTAL_LIMIT", "0")),
        reserved_p1_c4=max(0, _int("GLOBAL_HTTP_BUDGET_RESERVED_P1_C4", "0")),
        component_limits=limits,
        busy_timeout_ms=max(1, _int("GLOBAL_HTTP_BUDGET_BUSY_TIMEOUT_MS", "5000")),
        ledger_retention_days=max(1, _int("GLOBAL_HTTP_BUDGET_LEDGER_RETENTION_DAYS", "3")),
        run_id=run_id,
    )
