#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local rehearsal of sqlite3.Connection.backup / restore contract.

Never backs up or restores a Production DB unless both
ALLOW_LOCAL_SQLITE_BACKUP=1 and OWNER_PRODUCTION_BACKUP_APPROVED=1
are set. This pack does not set the second flag.
Restore always targets a new temp DB, never the source.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRODUCTION_DB_PATHS = (
    "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db",
    "/opt/expect-ai/current/services/win5-ai/var/expect_ai.db",
    "/var/lib/expect-ai/expect_ai.db",
)
FORBIDDEN_LOG_NEEDLES = (
    "bundle_json",
    "horse_name",
    "winner_name",
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
    line = "%s=%s" % (key, text.replace("\n", " ").replace("\r", ""))
    low = line.lower()
    for needle in FORBIDDEN_LOG_NEEDLES:
        if needle in low and not line.startswith("FORBIDDEN_"):
            raise RuntimeError("refused to emit %s" % needle)
    print(line)


def is_production_path(path: Path) -> bool:
    resolved = str(path.resolve()) if path.exists() else str(path)
    for banned in PRODUCTION_DB_PATHS:
        if resolved == banned or resolved.startswith(banned):
            return True
    if resolved.endswith("expect_ai.db") and "KEIBA-Single-AI" in resolved:
        return True
    return False


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stat_info(path: Path) -> dict[str, Any]:
    st = path.stat()
    return {
        "path": str(path.resolve()),
        "dev": st.st_dev,
        "ino": st.st_ino,
        "size": st.st_size,
        "mtime": int(st.st_mtime),
        "mode": oct(stat.S_IMODE(st.st_mode)),
    }


def schema_fingerprint(path: Path) -> dict[str, Any]:
    conn = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    try:
        conn.execute("PRAGMA query_only = ON")
        user_ver = int(conn.execute("PRAGMA user_version").fetchone()[0])
        schema_ver = int(conn.execute("PRAGMA schema_version").fetchone()[0])
        tables = [
            str(r[0])
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1"
            )
        ]
        try:
            versions = [
                str(r[0])
                for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")
            ]
        except sqlite3.Error:
            versions = []
        return {
            "user_version": user_ver,
            "schema_version": schema_ver,
            "table_count": len(tables),
            "table_names": tables,
            "schema_migrations": versions,
        }
    finally:
        conn.close()


def refuse_source(src: Path) -> None:
    if not src.is_file():
        raise SystemExit("SOURCE_MISSING")
    if is_production_path(src):
        if (os.environ.get("OWNER_PRODUCTION_BACKUP_APPROVED") or "").strip() != "1":
            raise SystemExit("REFUSED_PRODUCTION_SOURCE_NO_OWNER_APPROVAL")
    if (os.environ.get("ALLOW_LOCAL_SQLITE_BACKUP") or "").strip() != "1":
        raise SystemExit("REFUSED_ALLOW_LOCAL_SQLITE_BACKUP_UNSET")


def destination_path(dest_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = dest_dir / ("expect_ai_backup_%s.db" % stamp)
    if dest.exists():
        raise SystemExit("DEST_EXISTS_OVERWRITE_FORBIDDEN")
    return dest


def check_free_space(src: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    need = src.stat().st_size + (8 * 1024 * 1024)
    free = shutil.disk_usage(str(dest_dir)).free
    emit("DEST_FREE_BYTES", free)
    emit("BACKUP_NEED_BYTES", need)
    if free < need:
        raise SystemExit("DEST_PARENT_INSUFFICIENT_SPACE")


def run_backup(src: Path, dest: Path) -> None:
    src_conn = sqlite3.connect(str(src))
    dest_conn = sqlite3.connect(str(dest))
    try:
        src_conn.backup(dest_conn, pages=64, sleep=0.05)
        dest_conn.commit()
        check = dest_conn.execute("PRAGMA integrity_check").fetchone()
        if not check or str(check[0]) != "ok":
            raise SystemExit("INTEGRITY_CHECK_FAILED")
        emit("PRAGMA_INTEGRITY_CHECK", "ok")
    finally:
        dest_conn.close()
        src_conn.close()


def compare_schema(src: Path, dest: Path) -> bool:
    a = schema_fingerprint(src)
    b = schema_fingerprint(dest)
    emit("SOURCE_SCHEMA_VERSION", a["schema_version"])
    emit("DEST_SCHEMA_VERSION", b["schema_version"])
    emit("SOURCE_USER_VERSION", a["user_version"])
    emit("DEST_USER_VERSION", b["user_version"])
    emit("SOURCE_TABLE_COUNT", a["table_count"])
    emit("DEST_TABLE_COUNT", b["table_count"])
    emit("SOURCE_MIGRATION_COUNT", len(a["schema_migrations"]))
    emit("DEST_MIGRATION_COUNT", len(b["schema_migrations"]))
    emit("SCHEMA_VERSION_MATCH", a["schema_version"] == b["schema_version"])
    emit(
        "SCHEMA_VERSION_NOTE",
        "sqlite3.Connection.backup onto a new dest file may leave dest schema_version different; tables and schema_migrations are the apply gate",
    )
    same = (
        a["user_version"] == b["user_version"]
        and a["table_count"] == b["table_count"]
        and a["table_names"] == b["table_names"]
        and a["schema_migrations"] == b["schema_migrations"]
    )
    emit("SCHEMA_FINGERPRINT_MATCH", same)
    return same


def restore_to_temp(backup: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="restore-rehearse-"))
    restored = tmp / "restored.db"
    src = sqlite3.connect(str(backup))
    dst = sqlite3.connect(str(restored))
    try:
        src.backup(dst, pages=64, sleep=0.05)
        dst.commit()
        check = dst.execute("PRAGMA integrity_check").fetchone()
        if not check or str(check[0]) != "ok":
            raise SystemExit("RESTORE_INTEGRITY_CHECK_FAILED")
    finally:
        dst.close()
        src.close()
    emit("RESTORE_TARGET", str(restored))
    emit("RESTORE_TO_LIVE", "NO")
    emit("RESTORE_INTEGRITY_CHECK", "ok")
    return restored


def main() -> int:
    parser = argparse.ArgumentParser(description="Local SQLite backup contract (not Production)")
    parser.add_argument("--src", required=True, help="explicit single DB source path")
    parser.add_argument("--dest-dir", required=True, help="directory for a new timestamped backup")
    parser.add_argument("--restore-rehearse", action="store_true")
    args = parser.parse_args()

    src = Path(args.src)
    dest_dir = Path(args.dest_dir)
    emit("PRODUCTION_BACKUP_EXECUTED", "NO")
    emit("MIGRATION_MAY_PROCEED", "NO")
    refuse_source(src)
    if src.is_file() and is_production_path(src):
        emit("PRODUCTION_SOURCE_USED", "YES")
        emit("OWNER_PRODUCTION_BACKUP_APPROVED_EFFECTIVE", "YES")
    else:
        emit("PRODUCTION_SOURCE_USED", "NO")

    src_st = stat_info(src)
    emit("SOURCE_PATH", src_st["path"])
    emit("SOURCE_DEV", src_st["dev"])
    emit("SOURCE_INO", src_st["ino"])
    emit("SOURCE_SIZE", src_st["size"])
    emit("SOURCE_MTIME", src_st["mtime"])
    emit("SOURCE_MODE", src_st["mode"])

    check_free_space(src, dest_dir)
    dest = destination_path(dest_dir)
    emit("DEST_PATH", str(dest))
    emit("DEST_OVERWRITE", "NO")

    try:
        run_backup(src, dest)
        dest_st = stat_info(dest)
        emit("DEST_DEV", dest_st["dev"])
        emit("DEST_INO", dest_st["ino"])
        emit("DEST_SIZE", dest_st["size"])
        emit("DEST_MTIME", dest_st["mtime"])
        emit("DEST_MODE", dest_st["mode"])
        emit("DEST_SHA256", file_sha(dest))
        matched = compare_schema(src, dest)
        if not matched:
            emit("BACKUP_OK", "NO")
            emit("MIGRATION_MAY_PROCEED", "NO")
            return 2
        if args.restore_rehearse:
            restored = restore_to_temp(dest)
            if not compare_schema(dest, restored):
                emit("RESTORE_REHEARSE_OK", "NO")
                emit("MIGRATION_MAY_PROCEED", "NO")
                return 3
            emit("RESTORE_REHEARSE_OK", "YES")
        emit("BACKUP_OK", "YES")
        emit("MIGRATION_MAY_PROCEED", "NO")
        emit("PRODUCTION_BACKUP_DESIGN_COMPLETE", "YES")
        emit("PRODUCTION_APPLY_READY", "NO")
        return 0
    except Exception:
        emit("BACKUP_OK", "NO")
        emit("MIGRATION_MAY_PROCEED", "NO")
        raise


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
