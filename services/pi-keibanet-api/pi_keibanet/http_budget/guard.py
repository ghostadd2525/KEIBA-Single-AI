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
    PRODUCTION_CRITICAL,
    REMAINDER_COMPONENTS,
    BudgetConfig,
    load_budget_config,
    resolve_component,
)
from .sanitize import public_target
from .store import (
    StoreError,
    open_store,
    prune_ledger,
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

    def complete(self, *, result: str, http_status: int | None = None) -> None:
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
    if not config.enabled:
        raise BudgetDenied("disabled", component=name, detail="GLOBAL_HTTP_BUDGET_ENABLED=0")
    source, host, path = public_target(url)
    window_id = utc_window_id(now)
    try:
        conn = open_store(config)
    except StoreError as exc:
        raise BudgetDenied(exc.reason, component=name, detail=exc.detail) from exc
    reservation_id = uuid.uuid4().hex
    reserved_at = utc_iso(now)
    try:
        _reserve_row(
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
    finally:
        conn.close()
    return Reservation(
        reservation_id=reservation_id,
        window_id=window_id,
        component=name,
        source=source,
        host=host,
        path=path,
        consumed=True,
    )


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
    """Record outcome. consumed stays 1 (crash after reserve still counts)."""
    config = cfg or load_budget_config()
    try:
        conn = open_store(config)
    except StoreError:
        return
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            UPDATE reservations
            SET result = ?, completed_at = ?, http_status = ?
            WHERE reservation_id = ?
            """,
            (result, utc_iso(), http_status, reservation_id),
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
) -> None:
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as exc:
        raise BudgetDenied("busy_timeout", component=component, detail=str(exc)) from exc
    try:
        snap = usage_snapshot(conn, window_id)
        total_used = int(snap["total"])
        by_comp = snap["by_component"]
        comp_used = int(by_comp.get(component, 0))
        p1c4_used = sum(int(by_comp.get(name, 0)) for name in PRODUCTION_CRITICAL)
        remainder_used = sum(int(by_comp.get(name, 0)) for name in REMAINDER_COMPONENTS)

        if config.total_limit <= 0 or total_used >= config.total_limit:
            raise BudgetDenied(
                "total_limit",
                component=component,
                detail=f"used={total_used} limit={config.total_limit}",
            )
        comp_limit = int(config.component_limits.get(component, 0))
        if comp_limit <= 0 or comp_used >= comp_limit:
            raise BudgetDenied(
                "component_limit",
                component=component,
                detail=f"used={comp_used} limit={comp_limit}",
            )
        reserved = min(config.reserved_p1_c4, config.total_limit)
        if component in REMAINDER_COMPONENTS:
            remainder_cap = max(0, config.total_limit - reserved)
            reserved_still_needed = max(0, reserved - p1c4_used)
            free_slots = config.total_limit - total_used
            if remainder_used >= remainder_cap or free_slots <= reserved_still_needed:
                raise BudgetDenied(
                    "reserved_capacity",
                    component=component,
                    detail=(
                        f"remainder_used={remainder_used} remainder_cap={remainder_cap} "
                        f"reserved_needed={reserved_still_needed}"
                    ),
                )
        conn.execute(
            """
            INSERT INTO reservations(
                reservation_id, window_id, component, source, host, path,
                run_id, reserved_at, result, completed_at, http_status, consumed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, NULL, 1)
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
        raise BudgetDenied("busy_timeout", component=component, detail=str(exc)) from exc
    except sqlite3.DatabaseError as exc:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise BudgetDenied("corrupt_state", component=component, detail=str(exc)) from exc
