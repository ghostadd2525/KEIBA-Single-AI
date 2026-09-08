# -*- coding: utf-8 -*-
"""Global HTTP budget settings. Defaults never authorize live Netkeiba HTTP."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1

# Default path is local EC2 disk (not NFS). Missing file is fail-closed in enforce.
DEFAULT_STATE_PATH = Path("/var/lib/keiba-single-ai/http_budget/budget.sqlite")

# Safe rollout. Code-only deploy must default to off so existing P1 is not stopped.
MODE_OFF = "off"
MODE_OBSERVE = "observe"
MODE_ENFORCE = "enforce"
MODE_INVALID = "invalid"
VALID_MODES = frozenset({MODE_OFF, MODE_OBSERVE, MODE_ENFORCE})

# Production-critical components may use their reserved capacity.
PRODUCTION_CRITICAL = frozenset({"p1", "c4"})
WIN5_RESULTS_COMPONENT = "win5_results"
# Remainder-only: cannot consume the P1/C4 or win5_results reserved slices.
REMAINDER_COMPONENTS = frozenset(
    {"w2", "w3c", "w4", "w5", "win5_research", "unknown"}
)
KNOWN_COMPONENTS = PRODUCTION_CRITICAL | REMAINDER_COMPONENTS | {WIN5_RESULTS_COMPONENT}

_COMPONENT_ALIASES = {
    "race_refresh": "p1",
    "p1_race_refresh": "p1",
    "calendar": "c4",
    "page_a1": "c4",
    "w3-c": "w3c",
    "w3_c": "w3c",
    "w4cd": "w4",
    "w4_horse": "w4",
    "win5": "win5_results",
    "win5_result": "win5_results",
    "result_sync": "win5_results",
    "research_netkeiba": "win5_research",
    "probe": "unknown",
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


def resolve_mode(value: str | None = None) -> str:
    """Unset/empty → off. Known modes stay as-is. Explicit typos stay invalid.

    Invalid values are never rewritten to off. Callers must fail closed.
    """
    if value is not None:
        raw = value
    else:
        raw = os.environ.get("GLOBAL_HTTP_BUDGET_MODE")
        if raw is None:
            return MODE_OFF
    stripped = raw.strip().lower()
    if stripped == "":
        return MODE_OFF
    if stripped in VALID_MODES:
        return stripped
    return MODE_INVALID


@dataclass(frozen=True)
class BudgetConfig:
    mode: str
    state_path: Path
    bootstrap: bool
    total_limit: int
    reserved_p1_c4: int
    reserved_win5_results: int
    component_limits: dict[str, int]
    short_window_sec: int
    short_limit: int
    short_limit_host: int
    busy_timeout_ms: int
    ledger_retention_days: int
    run_id: str
    mode_raw: str = ""
    mode_invalid_reason: str = ""

    @property
    def busy_timeout_sec(self) -> float:
        return max(0.001, self.busy_timeout_ms / 1000.0)

    @property
    def enabled(self) -> bool:
        """True when reserve is consulted (observe or enforce)."""
        return self.mode in (MODE_OBSERVE, MODE_ENFORCE)

    @property
    def enforce(self) -> bool:
        return self.mode == MODE_ENFORCE

    @property
    def observe(self) -> bool:
        return self.mode == MODE_OBSERVE


def load_budget_config() -> BudgetConfig:
    """Safe-side defaults: mode=off, limits 0 / unset, no invented production quota."""
    path_raw = (os.environ.get("GLOBAL_HTTP_BUDGET_STATE_PATH") or "").strip()
    state_path = Path(path_raw) if path_raw else DEFAULT_STATE_PATH
    run_id = (os.environ.get("GLOBAL_HTTP_BUDGET_RUN_ID") or "").strip() or f"pid-{os.getpid()}"
    raw_mode = os.environ.get("GLOBAL_HTTP_BUDGET_MODE")
    mode = resolve_mode()
    mode_raw = "" if raw_mode is None else str(raw_mode)
    mode_invalid_reason = ""
    if mode == MODE_INVALID:
        shown = mode_raw.strip()[:64] or "<non-empty-invalid>"
        mode_invalid_reason = f"invalid_mode:{shown}"
    if os.environ.get("GLOBAL_HTTP_BUDGET_ENABLED", "") in ("0", "false", "False"):
        mode = MODE_OFF
        mode_invalid_reason = ""
    limits = {
        "p1": _int("GLOBAL_HTTP_BUDGET_LIMIT_P1", "0"),
        "c4": _int("GLOBAL_HTTP_BUDGET_LIMIT_C4", "0"),
        "w2": _int("GLOBAL_HTTP_BUDGET_LIMIT_W2", "0"),
        "w3c": _int("GLOBAL_HTTP_BUDGET_LIMIT_W3C", "0"),
        "w4": _int("GLOBAL_HTTP_BUDGET_LIMIT_W4", "0"),
        "w5": _int("GLOBAL_HTTP_BUDGET_LIMIT_W5", "0"),
        "win5_results": _int("GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESULTS", "0"),
        "win5_research": _int("GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESEARCH", "0"),
        "unknown": _int("GLOBAL_HTTP_BUDGET_LIMIT_UNKNOWN", "0"),
    }
    return BudgetConfig(
        mode=mode,
        state_path=state_path,
        bootstrap=_flag("GLOBAL_HTTP_BUDGET_BOOTSTRAP", "0"),
        total_limit=max(0, _int("GLOBAL_HTTP_BUDGET_TOTAL_LIMIT", "0")),
        reserved_p1_c4=max(0, _int("GLOBAL_HTTP_BUDGET_RESERVED_P1_C4", "0")),
        reserved_win5_results=max(0, _int("GLOBAL_HTTP_BUDGET_RESERVED_WIN5_RESULTS", "0")),
        component_limits=limits,
        short_window_sec=max(0, _int("GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC", "0")),
        short_limit=max(0, _int("GLOBAL_HTTP_BUDGET_SHORT_LIMIT", "0")),
        short_limit_host=max(0, _int("GLOBAL_HTTP_BUDGET_SHORT_LIMIT_HOST", "0")),
        busy_timeout_ms=max(1, _int("GLOBAL_HTTP_BUDGET_BUSY_TIMEOUT_MS", "5000")),
        ledger_retention_days=max(1, _int("GLOBAL_HTTP_BUDGET_LEDGER_RETENTION_DAYS", "3")),
        run_id=run_id,
        mode_raw=mode_raw,
        mode_invalid_reason=mode_invalid_reason,
    )
