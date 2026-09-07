# -*- coding: utf-8 -*-
"""SQLite ledger for the Global HTTP budget (local disk, BEGIN IMMEDIATE)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import SCHEMA_VERSION, BudgetConfig

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reservations (
    reservation_id TEXT PRIMARY KEY,
    window_id TEXT NOT NULL,
    component TEXT NOT NULL,
    source TEXT NOT NULL,
    host TEXT NOT NULL,
    path TEXT NOT NULL,
    run_id TEXT,
    reserved_at TEXT NOT NULL,
    result TEXT NOT NULL,
    completed_at TEXT,
    http_status INTEGER,
    consumed INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_res_window ON reservations(window_id, consumed);
CREATE INDEX IF NOT EXISTS idx_res_component ON reservations(window_id, component, consumed);
CREATE INDEX IF NOT EXISTS idx_res_host ON reservations(window_id, host, consumed);
CREATE INDEX IF NOT EXISTS idx_res_reserved_at ON reservations(reserved_at);
"""


def utc_window_id(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    return current.strftime("%Y-%m-%d")


def utc_iso(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    return current.strftime("%Y-%m-%dT%H:%M:%SZ")


class StoreError(Exception):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def connect(cfg: BudgetConfig) -> sqlite3.Connection:
    path = cfg.state_path
    uri = f"file:{path.as_posix()}?mode=rw"
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=cfg.busy_timeout_sec, isolation_level=None)
        _configure(conn, cfg)
    except sqlite3.OperationalError as exc:
        if conn is not None:
            conn.close()
        msg = str(exc).lower()
        if "unable to open" in msg or "no such file" in msg:
            raise StoreError("missing_state", str(exc)) from exc
        raise StoreError("corrupt_state", str(exc)) from exc
    except sqlite3.DatabaseError as exc:
        if conn is not None:
            conn.close()
        raise StoreError("corrupt_state", str(exc)) from exc
    return conn


def bootstrap(cfg: BudgetConfig) -> sqlite3.Connection:
    path = cfg.state_path
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(str(path), timeout=cfg.busy_timeout_sec, isolation_level=None)
        _configure(conn, cfg)
        # executescript issues its own COMMIT; do not wrap it in BEGIN.
        conn.executescript(CREATE_SQL)
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
        elif str(row[0]) != str(SCHEMA_VERSION):
            conn.execute("ROLLBACK")
            conn.close()
            raise StoreError("schema_mismatch", f"have={row[0]}")
        conn.execute("COMMIT")
    except StoreError:
        raise
    except sqlite3.DatabaseError as exc:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        try:
            conn.close()
        except Exception:
            pass
        raise StoreError("corrupt_state", str(exc)) from exc
    return conn


def open_store(cfg: BudgetConfig) -> sqlite3.Connection:
    if not cfg.state_path.exists():
        if not cfg.bootstrap:
            raise StoreError("missing_state", str(cfg.state_path))
        return bootstrap(cfg)
    if cfg.state_path.stat().st_size == 0:
        raise StoreError("corrupt_state", "empty_file")
    conn = connect(cfg)
    try:
        _verify(conn)
    except StoreError:
        conn.close()
        raise
    return conn


def _configure(conn: sqlite3.Connection, cfg: BudgetConfig) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout={int(cfg.busy_timeout_ms)}")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA temp_store=MEMORY")


def _verify(conn: sqlite3.Connection) -> None:
    try:
        check = conn.execute("PRAGMA integrity_check").fetchone()
        if not check or str(check[0]).lower() != "ok":
            raise StoreError("corrupt_state", str(check[0] if check else "no_integrity"))
        tables = {
            str(r[0])
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "meta" not in tables or "reservations" not in tables:
            raise StoreError("corrupt_state", "missing_tables")
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None:
            raise StoreError("corrupt_state", "missing_schema_version")
        if str(row[0]) != str(SCHEMA_VERSION):
            raise StoreError("schema_mismatch", f"have={row[0]}")
    except StoreError:
        raise
    except sqlite3.DatabaseError as exc:
        raise StoreError("corrupt_state", str(exc)) from exc


def component_counts(conn: sqlite3.Connection, window_id: str) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT component, COALESCE(SUM(consumed), 0) AS used
        FROM reservations
        WHERE window_id = ?
        GROUP BY component
        """,
        (window_id,),
    ).fetchall()
    return {str(r["component"]): int(r["used"]) for r in rows}


def usage_snapshot(conn: sqlite3.Connection, window_id: str) -> dict[str, Any]:
    by_component = component_counts(conn, window_id)
    by_host_rows = conn.execute(
        """
        SELECT host, COALESCE(SUM(consumed), 0) AS used
        FROM reservations
        WHERE window_id = ?
        GROUP BY host
        """,
        (window_id,),
    ).fetchall()
    by_source_rows = conn.execute(
        """
        SELECT source, COALESCE(SUM(consumed), 0) AS used
        FROM reservations
        WHERE window_id = ?
        GROUP BY source
        """,
        (window_id,),
    ).fetchall()
    return {
        "window_id": window_id,
        "total": sum(by_component.values()),
        "by_component": by_component,
        "by_host": {str(r["host"]): int(r["used"]) for r in by_host_rows},
        "by_source": {str(r["source"]): int(r["used"]) for r in by_source_rows},
    }


def prune_ledger(conn: sqlite3.Connection, *, now: datetime | None, retention_days: int) -> int:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    cutoff = (current.astimezone(timezone.utc) - timedelta(days=retention_days)).strftime(
        "%Y-%m-%d"
    )
    cur = conn.execute("DELETE FROM reservations WHERE window_id < ?", (cutoff,))
    return int(cur.rowcount or 0)
