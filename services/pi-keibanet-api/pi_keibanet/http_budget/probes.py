# -*- coding: utf-8 -*-
"""Refuse direct Netkeiba probe scripts in Production; otherwise require budget."""
from __future__ import annotations

import os
from typing import NoReturn

from ..netkeiba.client import NetkeibaClient


class ProbeRefused(RuntimeError):
    """Probe must not open Netkeiba from this environment."""


def production_env() -> bool:
    if os.environ.get("EXPECT_PRODUCTION", "") in ("1", "true", "True"):
        return True
    data_root = os.environ.get("PI_DATA_ROOT", "")
    if data_root.startswith("/opt/expect-ai"):
        return True
    return False


def probes_allowed() -> bool:
    return os.environ.get("GLOBAL_HTTP_BUDGET_ALLOW_PROBES", "0") in ("1", "true", "True")


def refuse_if_blocked() -> None:
    if production_env():
        raise ProbeRefused("production_probe_refused")
    if not probes_allowed():
        raise ProbeRefused("probes_not_allowed")


def budgeted_probe_client(*, component: str = "unknown") -> NetkeibaClient:
    refuse_if_blocked()
    return NetkeibaClient(component=component)


def exit_refused(exc: ProbeRefused) -> NoReturn:
    raise SystemExit(f"probe refused: {exc}")
