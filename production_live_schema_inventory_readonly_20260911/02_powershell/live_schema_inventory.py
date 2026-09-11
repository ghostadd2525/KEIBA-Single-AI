#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Owner read-only live schema inventory. No Production writes. No HTTP.

Collects sqlite_master / PRAGMA only. Does not print row bodies,
bundle_json values, race_id values, or horse names.
"""
from __future__ import annotations

import os
import sqlite3
import stat
import subprocess
import sys
from typing import Any

PACK_NAME = "production_live_schema_inventory_readonly_20260911"
DB_CANDIDATES = (
    "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db",
    "/opt/expect-ai/current/services/win5-ai/var/expect_ai.db",
    "/var/lib/expect-ai/expect_ai.db",
)
ENV_KEYS = (
    "EXPECT_AI_DB_PATH",
    "PREDICTION_RUNS_ENABLED",
    "EXPECT_AI_ALLOW_MIGRATION_019",
    "EXPECT_AI_ALLOW_MIGRATION_022",
)
SECRET_PREFIXES = (
    "AWS_",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "API_KEY",
    "EXPECT_AI_API",
    "X-AI-Key",
    "AI_API_KEY",
)
DDL_TABLES = (
    "predictions",
    "conversation_history",
    "race_results",
    "race_evaluations",
)
FORBIDDEN_SELECT_COLS = (
    "bundle_json",
    "horse_name",
    "winner_name",
    "payload_json",
)


def emit(key: str, value: Any) -> None:
    if value is True:
        text = "YES"
    elif value is False:
        text = "NO"
    elif value is None:
        text = "UNKNOWN"
    else:
        text = str(value)
    print("%s=%s" % (key, text.replace("\n", " ").replace("\r", "")))


def redact_line(line: str) -> str:
    for prefix in SECRET_PREFIXES:
        if prefix.lower() in line.lower():
            return "REDACTED_SECRET_LINE"
    return line


def run_cmd(args: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
            check=False,
        )
        text = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        return int(p.returncode), text
    except Exception as exc:
        return 1, "%s: %s" % (type(exc).__name__, exc)


def parse_systemd_show(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip()
    return out


def parse_environ_blob(blob: str) -> dict[str, str]:
    out: dict[str, str] = {}
    raw = blob.replace("\n", "\0")
    for part in raw.split("\0"):
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        if key in ENV_KEYS:
            out[key] = val
    return out


def open_db_ro(path: str) -> sqlite3.Connection:
    uri = "file:%s?mode=ro" % path
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    conn.execute("PRAGMA query_only = ON")
    conn.row_factory = sqlite3.Row
    return conn


def discover_db_path(hinted: str | None) -> str | None:
    if hinted and os.path.isfile(hinted):
        return hinted
    env_path = (os.environ.get("EXPECT_AI_DB_PATH") or "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path
    for cand in DB_CANDIDATES:
        if os.path.isfile(cand):
            return cand
    return None


def one_sql(conn: sqlite3.Connection, name: str, typ: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name=? AND type=?",
        (name, typ),
    ).fetchone()
    if not row or row[0] is None:
        return ""
    return " ".join(str(row[0]).split())


def dump_block(title: str, body: str) -> None:
    print("----- %s -----" % title)
    print(body if body else "(absent)")


def main() -> int:
    emit("PACK", PACK_NAME)
    emit("HTTP_CALLED", "NO")
    emit("HEALTH_GET_CALLED", "NO")
    emit("POST_CALLED", "NO")
    emit("PRODUCTION_CHANGED", "NO")
    emit("DB_CHANGED", "NO")
    emit("BACKUP_COPY_EXECUTED", "NO")
    emit("MIGRATION_019_APPLY", "NO")
    emit("MIGRATION_022_APPLY", "NO")
    emit("ROW_BODIES_EMITTED", "NO")
    emit("BUNDLE_JSON_EMITTED", "NO")
    emit("RACE_ID_VALUES_EMITTED", "NO")
    emit("HORSE_NAMES_EMITTED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("PRODUCTION_SCHEMA_EXACTLY_REHEARSED", "NO")

    show_rc, show_out = run_cmd(
        [
            "systemctl",
            "show",
            "expect-ai.service",
            "--no-pager",
            "-p",
            "ActiveState",
            "-p",
            "MainPID",
            "-p",
            "WorkingDirectory",
            "-p",
            "Environment",
            "-p",
            "FragmentPath",
        ]
    )
    sd = parse_systemd_show(show_out)
    emit("SYSTEMD_SHOW_RC", show_rc)
    emit("SYSTEMD_ACTIVE_STATE", sd.get("ActiveState") or "")
    env_systemd = parse_environ_blob((sd.get("Environment") or "").replace(" ", "\0"))
    proc_env: dict[str, str] = {}
    pid = str(sd.get("MainPID") or "0").strip()
    if pid.isdigit() and int(pid) > 0:
        try:
            with open("/proc/%s/environ" % pid, "rb") as fh:
                proc_env = parse_environ_blob(fh.read().decode("utf-8", errors="replace"))
        except OSError:
            proc_env = {}
    hinted = proc_env.get("EXPECT_AI_DB_PATH") or env_systemd.get("EXPECT_AI_DB_PATH")
    db_path = discover_db_path(hinted)
    emit("DB_PATH", db_path or "NOT_FOUND")
    emit("DB_EXISTS", bool(db_path and os.path.isfile(db_path)))

    if not db_path or not os.path.isfile(db_path):
        emit("AUDIT_STATUS", "FAILED")
        emit("ERROR", "DB_NOT_FOUND")
        return 1

    st = os.stat(db_path)
    emit("DB_DEV", st.st_dev)
    emit("DB_INO", st.st_ino)
    emit("DB_SIZE_BYTES", st.st_size)
    emit("DB_MTIME_EPOCH", int(st.st_mtime))
    emit("DB_MODE", oct(stat.S_IMODE(st.st_mode)))
    emit("SQLITE_PYTHON_VERSION", sqlite3.sqlite_version)

    conn = open_db_ro(db_path)
    try:
        user_ver = conn.execute("PRAGMA user_version").fetchone()
        schema_ver = conn.execute("PRAGMA schema_version").fetchone()
        emit("PRAGMA_USER_VERSION", int(user_ver[0]) if user_ver else None)
        emit("PRAGMA_SCHEMA_VERSION", int(schema_ver[0]) if schema_ver else None)
        try:
            versions = [
                str(r[0])
                for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")
            ]
        except sqlite3.Error:
            versions = []
        emit("SCHEMA_MIGRATIONS", ",".join(versions) if versions else "ABSENT")
        emit("SCHEMA_MIGRATIONS_COUNT", len(versions))
        emit("HAS_019_FINAL_PREDICTIONS", any(v.startswith("019_final") or v == "019_final_predictions" for v in versions))
        emit("HAS_020_SERIES", any(v.startswith("020_") for v in versions))
        emit("HAS_021_SERIES", any(v.startswith("021_") for v in versions))
        emit("HAS_PERSIST_019", "019_prediction_run_idempotency" in versions)
        emit("HAS_PERSIST_022", "022_prediction_run_idempotency" in versions)

        pred_sql = one_sql(conn, "predictions", "table")
        emit("PREDICTIONS_CREATE_PRESENT", bool(pred_sql))
        dump_block("PREDICTIONS_CREATE_TABLE", pred_sql)

        cols = conn.execute("PRAGMA table_info(predictions)").fetchall()
        col_names = [str(r[1]) for r in cols]
        emit("PREDICTIONS_COLUMNS", ",".join(col_names))
        emit("PREDICTIONS_COLUMN_COUNT", len(col_names))
        print("----- PRAGMA_TABLE_INFO_PREDICTIONS -----")
        for r in cols:
            print(
                "cid=%s name=%s type=%s notnull=%s dflt=%s pk=%s"
                % (r[0], r[1], r[2], r[3], r[4], r[5])
            )

        idx_rows = conn.execute("PRAGMA index_list(predictions)").fetchall()
        idx_names = [str(r[1]) for r in idx_rows]
        emit("PREDICTIONS_INDEX_LIST", ",".join(idx_names))
        print("----- PRAGMA_INDEX_LIST_PREDICTIONS -----")
        for r in idx_rows:
            print("seq=%s name=%s unique=%s origin=%s partial=%s" % (r[0], r[1], r[2], r[3], r[4] if len(r) > 4 else ""))
        print("----- PRAGMA_INDEX_INFO_PREDICTIONS -----")
        for name in idx_names:
            for r in conn.execute("PRAGMA index_info(%s)" % name).fetchall():
                print("index=%s seqno=%s cid=%s name=%s" % (name, r[0], r[1], r[2]))

        master_rows = conn.execute(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE tbl_name=? AND type IN ('index','trigger') ORDER BY type, name",
            ("predictions",),
        ).fetchall()
        emit("PREDICTIONS_RELATED_MASTER_COUNT", len(master_rows))
        print("----- SQLITE_MASTER_PREDICTIONS_INDEX_TRIGGER -----")
        for r in master_rows:
            sql = " ".join(str(r[2] or "").split())
            print("type=%s name=%s sql=%s" % (r[0], r[1], sql or "(null)"))

        for tbl in DDL_TABLES:
            sql = one_sql(conn, tbl, "table")
            emit("%s_CREATE_PRESENT" % tbl.upper(), bool(sql))
            dump_block("%s_CREATE_TABLE" % tbl.upper(), sql)

        tables = [
            str(r[0])
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1"
            )
        ]
        emit("TABLE_COUNT", len(tables))
        emit("TABLE_NAMES", ",".join(tables))
    finally:
        conn.close()

    emit("AUDIT_STATUS", "SUCCESS")
    emit("PRODUCTION_BACKUP_EXECUTED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
