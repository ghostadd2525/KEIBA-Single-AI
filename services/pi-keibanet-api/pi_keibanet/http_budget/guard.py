# -*- coding: utf-8 -*-
"""Atomic reserve / complete for the process-shared Global HTTP budget."""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .config import (
    KNOWN_COMPONENTS,
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
)
from .sanitize import public_target
from .store import (
    StoreError,
    open_store,
    prune_ledger,
    rolling_usage,
    usage_snapshot,
    utc_iso,
    utc_window_id,
)


class BudgetDenied(Exception):
    """Reserve failed. Callers must not send HTTP."""

    def __init__(self, reason: str, *, component: str = "", detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.component = component
        self.detail = detail


@dataclass
class Reservation:
    reservation_id: str
    window_id: str
    component: str
    source: str
    host: str
    path: str
    consumed: bool = True
    mode: str = MODE_ENFORCE
    observe_would_deny: str = ""

    def complete(self, *, result: str, http_status: int | None = None) -> None:
        if not self.reservation_id:
            return
        complete_reservation(
            self.reservation_id,
            result=result,
            http_status=http_status,
        )


def classify_http_result(*, http_status: int | None = None, timeout: bool = False) -> str:
    if timeout:
        return "timeout"
    if http_status is None:
        return "error"
    if 200 <= http_status < 300:
        return "success"
    if http_status == 403:
        return "http_403"
    if http_status == 429:
        return "http_429"
    if 500 <= http_status <= 599:
        return "http_5xx"
    if 400 <= http_status <= 499:
        return f"http_{http_status}"
    return "error"


def window_usage(*, now: datetime | None = None, cfg: BudgetConfig | None = None) -> dict[str, Any]:
    config = cfg or load_budget_config()
    conn = open_store(config)
    try:
        return usage_snapshot(conn, utc_window_id(now))
    finally:
        conn.close()


def _passthrough(url: str, component: str, mode: str) -> Reservation:
    source, host, path = public_target(url)
    return Reservation(
        reservation_id="",
        window_id="",
        component=component,
        source=source,
        host=host,
        path=path,
        consumed=False,
        mode=mode,
    )


def reserve(
    *,
    url: str,
    component: str | None = None,
    run_id: str | None = None,
    now: datetime | None = None,
    cfg: BudgetConfig | None = None,
) -> Reservation:
    config = cfg or load_budget_config()
    name = resolve_component(component)
    if name not in KNOWN_COMPONENTS:
        name = "unknown"
    if config.mode == MODE_INVALID:
        _audit_invalid_mode(config, url=url, component=name)
        raise BudgetDenied(
            "invalid_mode",
            component=name,
            detail=config.mode_invalid_reason or "invalid_mode",
        )
    if config.mode == MODE_OFF:
        return _passthrough(url, name, MODE_OFF)
    source, host, path = public_target(url)
    window_id = utc_window_id(now)
    try:
        conn = open_store(config)
    except StoreError as exc:
        if config.mode == MODE_OBSERVE:
            return _passthrough(url, name, MODE_OBSERVE)
        raise BudgetDenied(exc.reason, component=name, detail=exc.detail) from exc
    reservation_id = uuid.uuid4().hex
    reserved_at = utc_iso(now)
    try:
        reservation = _reserve_row(
            conn,
            config=config,
            reservation_id=reservation_id,
            window_id=window_id,
            component=name,
            source=source,
            host=host,
            path=path,
            run_id=run_id or config.run_id,
            reserved_at=reserved_at,
            now=now,
        )
        try:
            conn.execute("BEGIN IMMEDIATE")
            prune_ledger(conn, now=now, retention_days=config.ledger_retention_days)
            conn.execute("COMMIT")
        except sqlite3.Error:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return reservation
    finally:
        conn.close()


def reserve_for_request(
    *,
    url: str,
    component: str | None = None,
    label: str = "",
    now: datetime | None = None,
    cfg: BudgetConfig | None = None,
) -> Reservation:
    del label  # never log labels that might embed query tokens
    return reserve(url=url, component=component, now=now, cfg=cfg)


def complete_reservation(
    reservation_id: str,
    *,
    result: str,
    http_status: int | None = None,
    cfg: BudgetConfig | None = None,
) -> None:
    """Record outcome. consumed stays as reserved (crash after reserve still counts)."""
    if not reservation_id:
        return
    config = cfg or load_budget_config()
    try:
        conn = open_store(config)
    except StoreError:
        return
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT result FROM reservations WHERE reservation_id = ?",
            (reservation_id,),
        ).fetchone()
        keep = ""
        if row is not None:
            keep = str(row[0] or "")
        stored = keep if keep.startswith("observe_would_") else result
        conn.execute(
            """
            UPDATE reservations
            SET result = ?, completed_at = ?, http_status = ?
            WHERE reservation_id = ?
            """,
            (stored, utc_iso(), http_status, reservation_id),
        )
        conn.execute("COMMIT")
    except sqlite3.Error:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
    finally:
        conn.close()


def _decision(
    *,
    config: BudgetConfig,
    component: str,
    host: str,
    snap: dict[str, Any],
    short: dict[str, Any],
) -> str | None:
    """Return deny reason or None if allowed. Limits of 0 mean no quota (deny in enforce)."""
    total_used = int(snap["total"])
    by_comp = snap["by_component"]
    comp_used = int(by_comp.get(component, 0))
    p1c4_used = sum(int(by_comp.get(name, 0)) for name in PRODUCTION_CRITICAL)
    win5_used = int(by_comp.get(WIN5_RESULTS_COMPONENT, 0))
    remainder_used = sum(int(by_comp.get(name, 0)) for name in REMAINDER_COMPONENTS)

    if config.total_limit <= 0 or total_used >= config.total_limit:
        return "total_limit"
    comp_limit = int(config.component_limits.get(component, 0))
    if comp_limit <= 0 or comp_used >= comp_limit:
        return "component_limit"

    reserved_p1c4 = min(config.reserved_p1_c4, config.total_limit)
    reserved_win5 = min(
        config.reserved_win5_results,
        max(0, config.total_limit - reserved_p1c4),
    )
    remainder_cap = max(0, config.total_limit - reserved_p1c4 - reserved_win5)
    p1c4_needed = max(0, reserved_p1c4 - p1c4_used)
    win5_needed = max(0, reserved_win5 - win5_used)
    reserved_still_needed = p1c4_needed + win5_needed
    free_slots = config.total_limit - total_used

    if component in REMAINDER_COMPONENTS:
        if remainder_used >= remainder_cap or free_slots <= reserved_still_needed:
            return "reserved_capacity"
    elif component == WIN5_RESULTS_COMPONENT:
        if free_slots <= p1c4_needed and (reserved_win5 <= 0 or win5_used >= reserved_win5):
            return "reserved_capacity"
    elif component in PRODUCTION_CRITICAL:
        if free_slots <= win5_needed and (reserved_p1c4 <= 0 or p1c4_used >= reserved_p1c4):
            return "reserved_capacity"

    if config.short_window_sec > 0:
        short_reason = _short_decision(
            config=config,
            component=component,
            host=host,
            short=short,
        )
        if short_reason:
            return short_reason
    return None


def _short_decision(
    *,
    config: BudgetConfig,
    component: str,
    host: str,
    short: dict[str, Any],
) -> str | None:
    """Rolling short-window limits. 0 means the extra cap is unset (not applied)."""
    short_total = int(short["total"])
    short_by_comp = short["by_component"]
    short_host_used = int(short["by_host"].get(host, 0))
    if config.short_limit > 0 and short_total >= config.short_limit:
        return "short_limit"
    if config.short_limit_host > 0 and short_host_used >= config.short_limit_host:
        return "short_limit_host"
    if config.short_limit > 0 and (
        config.reserved_p1_c4 > 0 or config.reserved_win5_results > 0
    ):
        short_reserved_p1c4 = min(config.reserved_p1_c4, config.short_limit)
        short_reserved_win5 = min(
            config.reserved_win5_results,
            max(0, config.short_limit - short_reserved_p1c4),
        )
        short_p1c4 = sum(int(short_by_comp.get(name, 0)) for name in PRODUCTION_CRITICAL)
        short_win5 = int(short_by_comp.get(WIN5_RESULTS_COMPONENT, 0))
        short_remainder = sum(int(short_by_comp.get(name, 0)) for name in REMAINDER_COMPONENTS)
        short_remainder_cap = max(0, config.short_limit - short_reserved_p1c4 - short_reserved_win5)
        short_p1c4_needed = max(0, short_reserved_p1c4 - short_p1c4)
        short_win5_needed = max(0, short_reserved_win5 - short_win5)
        short_free = config.short_limit - short_total
        if component in REMAINDER_COMPONENTS:
            if short_remainder >= short_remainder_cap or short_free <= (
                short_p1c4_needed + short_win5_needed
            ):
                return "short_reserved_capacity"
        elif component == WIN5_RESULTS_COMPONENT:
            if short_free <= short_p1c4_needed and (
                short_reserved_win5 <= 0 or short_win5 >= short_reserved_win5
            ):
                return "short_reserved_capacity"
        elif component in PRODUCTION_CRITICAL:
            if short_free <= short_win5_needed and (
                short_reserved_p1c4 <= 0 or short_p1c4 >= short_reserved_p1c4
            ):
                return "short_reserved_capacity"
    return None


def _audit_invalid_mode(config: BudgetConfig, *, url: str, component: str) -> None:
    """Best-effort ledger row so the invalid mode reason is reviewable."""
    source, host, path = public_target(url)
    try:
        conn = open_store(config)
    except StoreError:
        return
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO reservations(
                reservation_id, window_id, component, source, host, path,
                run_id, reserved_at, result, completed_at, http_status, consumed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 0)
            """,
            (
                uuid.uuid4().hex,
                utc_window_id(),
                component,
                source,
                host,
                path,
                config.run_id,
                utc_iso(),
                config.mode_invalid_reason or "invalid_mode",
            ),
        )
        conn.execute("COMMIT")
    except sqlite3.Error:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
    finally:
        conn.close()


def _reserve_row(
    conn: sqlite3.Connection,
    *,
    config: BudgetConfig,
    reservation_id: str,
    window_id: str,
    component: str,
    source: str,
    host: str,
    path: str,
    run_id: str,
    reserved_at: str,
    now: datetime | None,
) -> Reservation:
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as exc:
        if config.mode == MODE_OBSERVE:
            return _passthrough("", component, MODE_OBSERVE)
        raise BudgetDenied("busy_timeout", component=component, detail=str(exc)) from exc
    try:
        count_all = config.mode == MODE_OBSERVE
        snap = usage_snapshot(conn, window_id, count_all=count_all)
        short = rolling_usage(
            conn, now=now, window_sec=config.short_window_sec, count_all=count_all
        )
        reason = _decision(config=config, component=component, host=host, snap=snap, short=short)
        consume = 1
        result = "pending"
        if reason:
            if config.mode == MODE_ENFORCE:
                raise BudgetDenied(
                    reason,
                    component=component,
                    detail=f"used_total={snap['total']} limit={config.total_limit}",
                )
            consume = 0
            result = f"observe_would_{reason}"
        elif config.mode == MODE_OBSERVE:
            consume = 0
            result = "observe_allow"
        conn.execute(
            """
            INSERT INTO reservations(
                reservation_id, window_id, component, source, host, path,
                run_id, reserved_at, result, completed_at, http_status, consumed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)
            """,
            (
                reservation_id,
                window_id,
                component,
                source,
                host,
                path,
                run_id,
                reserved_at,
                result,
                consume,
            ),
        )
        conn.execute("COMMIT")
    except BudgetDenied:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    except sqlite3.OperationalError as exc:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        if config.mode == MODE_OBSERVE:
            return _passthrough("", component, MODE_OBSERVE)
        raise BudgetDenied("busy_timeout", component=component, detail=str(exc)) from exc
    except sqlite3.DatabaseError as exc:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        if config.mode == MODE_OBSERVE:
            return _passthrough("", component, MODE_OBSERVE)
        raise BudgetDenied("corrupt_state", component=component, detail=str(exc)) from exc
    return Reservation(
        reservation_id=reservation_id,
        window_id=window_id,
        component=component,
        source=source,
        host=host,
        path=path,
        consumed=bool(consume),
        mode=config.mode,
        observe_would_deny=reason or "",
    )
