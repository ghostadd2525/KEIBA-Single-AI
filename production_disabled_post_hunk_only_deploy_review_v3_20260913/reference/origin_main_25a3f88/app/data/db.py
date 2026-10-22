# -*- coding: utf-8 -*-
"""SQLite connection + migrations (PostgreSQL-ready via DATABASE_URL later)."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def db_path() -> Path:
    env = (os.environ.get("EXPECT_AI_DB_PATH") or "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "var" / "expect_ai.db"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection | None = None) -> list[str]:
    own = False
    if conn is None:
        conn = connect()
        own = True
    applied: list[str] = []
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        done = {
            r[0]
            for r in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for sql_path in sorted(_MIGRATIONS.glob("*.sql")):
            version = sql_path.stem
            if version in done:
                continue
            script = sql_path.read_text(encoding="utf-8")
            conn.executescript(script)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, datetime('now'))",
                (version,),
            )
            # 001_init already creates schema_migrations; ensure row exists
            conn.execute(
                "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES (?, datetime('now'))",
                (version,),
            )
            applied.append(version)
        conn.commit()
        return applied
    finally:
        if own:
            conn.close()
