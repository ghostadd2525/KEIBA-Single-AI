# -*- coding: utf-8 -*-
"""SQLite connection + migrations (PostgreSQL-ready via DATABASE_URL later)."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parent / "migrations"
_PREDICTION_RUN_COLUMNS = (
    "idempotency_key",
    "persist_source",
    "input_snapshot_hash",
    "prediction_semantic_hash",
)
_IDEMPOTENCY_INDEX = "uq_predictions_idempotency_key_not_null"
_IDEMPOTENCY_INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_predictions_idempotency_key_not_null "
    "ON predictions(idempotency_key) WHERE idempotency_key IS NOT NULL"
)
PERSIST_MIGRATION = "022_prediction_run_idempotency"
SUPERSEDED_019 = "019_prediction_run_idempotency"


def _flag_on(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes")


def _allow_migration_022() -> bool:
    return _flag_on("EXPECT_AI_ALLOW_MIGRATION_022")


def _allow_migration_019() -> bool:
    """Superseded persist 019 gate. Must stay unused for apply."""
    return _flag_on("EXPECT_AI_ALLOW_MIGRATION_019")


def _normalize_sql(sql: str) -> str:
    return " ".join((sql or "").split()).lower()


def inspect_idempotency_index(conn: sqlite3.Connection) -> str:
    """ok | missing | mismatch。名前だけでなく UNIQUE / 列 / WHERE を検証する。"""
    listed = {
        str(r[1]): int(r[2] or 0)
        for r in conn.execute("PRAGMA index_list(predictions)").fetchall()
    }
    master = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
        (_IDEMPOTENCY_INDEX,),
    ).fetchone()
    if _IDEMPOTENCY_INDEX not in listed and master is None:
        return "missing"
    unique = listed.get(_IDEMPOTENCY_INDEX, 0) == 1
    cols = [
        str(r[2] or "")
        for r in conn.execute("PRAGMA index_info(%s)" % _IDEMPOTENCY_INDEX).fetchall()
    ]
    sql = _normalize_sql(master[0] if master and master[0] else "")
    compact = sql.replace(" ", "")
    has_unique = unique and ("createuniqueindex" in compact or " unique " in " %s " % sql)
    single_key = cols == ["idempotency_key"]
    has_predicate = "whereidempotency_keyisnotnull" in compact
    on_predictions = "onpredictions(idempotency_key)" in compact
    if has_unique and single_key and has_predicate and on_predictions:
        return "ok"
    return "mismatch"


def prediction_run_schema_status(conn: sqlite3.Connection | None = None) -> str:
    """complete | partial | error | absent。同名でも契約外 index は error。"""
    own = False
    if conn is None:
        conn = connect()
        own = True
    try:
        cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(predictions)").fetchall()}
        have_cols = set(_PREDICTION_RUN_COLUMNS) <= cols
        any_col = bool(set(_PREDICTION_RUN_COLUMNS) & cols)
        idx_state = inspect_idempotency_index(conn)
        if have_cols and idx_state == "ok":
            return "complete"
        if idx_state == "mismatch":
            return "error"
        if any_col or idx_state != "missing":
            return "partial"
        return "absent"
    except sqlite3.Error:
        return "absent"
    finally:
        if own:
            conn.close()


def prediction_run_schema_ready(conn: sqlite3.Connection | None = None) -> bool:
    """022 列と partial UNIQUE が揃っているか。未適用なら POST は persist しない。"""
    return prediction_run_schema_status(conn) == "complete"


def repair_prediction_run_schema(conn: sqlite3.Connection) -> str:
    """途中適用の 022 を完了する。既存列は ALTER しない。DROP COLUMN しない。

    同名だが契約外の index は DROP INDEX して作り直す。
    検証に失敗したら complete を返さない。
    """
    cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(predictions)").fetchall()}
    for col in _PREDICTION_RUN_COLUMNS:
        if col not in cols:
            conn.execute("ALTER TABLE predictions ADD COLUMN %s TEXT" % col)
    idx_state = inspect_idempotency_index(conn)
    if idx_state == "mismatch":
        conn.execute("DROP INDEX IF EXISTS %s" % _IDEMPOTENCY_INDEX)
        idx_state = "missing"
    if idx_state == "missing":
        conn.execute(_IDEMPOTENCY_INDEX_SQL)
    status = prediction_run_schema_status(conn)
    if status == "complete":
        conn.execute(
            "INSERT OR REPLACE INTO schema_migrations(version, applied_at) "
            "VALUES (?, datetime('now'))",
            (PERSIST_MIGRATION,),
        )
    return status


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
            if version == SUPERSEDED_019:
                # Old persist 019 is not-apply. Keep archived copy only.
                continue
            if version == PERSIST_MIGRATION:
                if not _allow_migration_022():
                    continue
                status = prediction_run_schema_status(conn)
                if status == "complete":
                    if version not in done:
                        conn.execute(
                            "INSERT OR REPLACE INTO schema_migrations(version, applied_at) "
                            "VALUES (?, datetime('now'))",
                            (version,),
                        )
                    continue
                if status in ("partial", "error"):
                    repair_prediction_run_schema(conn)
                    applied.append("%s:repair" % PERSIST_MIGRATION)
                    continue
                if version in done:
                    repair_prediction_run_schema(conn)
                    applied.append("%s:repair" % PERSIST_MIGRATION)
                    continue
            elif version in done:
                continue
            if version == PERSIST_MIGRATION and not _allow_migration_022():
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
