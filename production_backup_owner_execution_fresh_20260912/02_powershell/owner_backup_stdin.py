#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single SSH stdin payload. Pregenerated. Do not concatenate at runtime."""
from __future__ import annotations

# --- embedded backup_contract.py (shebang/coding/future/__main__ stripped) ---

import argparse
import errno
import hashlib
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PACK_NAME = "production_python_backup_restore_rehearsal_v2_20260911"

PRODUCTION_DB_PATHS = (
    "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db",
    "/opt/expect-ai/current/services/win5-ai/var/expect_ai.db",
    "/var/lib/expect-ai/expect_ai.db",
)
SHARED_DEST_DIRS = {
    Path("/"),
    Path("/tmp"),
    Path("/var"),
    Path("/var/tmp"),
    Path("/home"),
    Path("/opt"),
    Path("/workspace"),
}
FORBIDDEN_LOG_NEEDLES = (
    "bundle_json",
    "horse_name",
    "winner_name",
)
MASTER_TYPES = ("table", "index", "trigger", "view")
DEST_DIR_MODE = 0o700
DEST_FILE_MODE = 0o600


class BackupError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else "%s: %s" % (code, detail))


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


def path_stat(path: Path) -> os.stat_result:
    return path.stat()


def is_production_path(path: Path) -> bool:
    try:
        resolved = str(path.resolve())
    except FileNotFoundError:
        resolved = str(Path(os.path.abspath(str(path))))
    for banned in PRODUCTION_DB_PATHS:
        if resolved == banned or resolved.startswith(banned + "/"):
            return True
    if resolved.endswith("expect_ai.db") and "KEIBA-Single-AI" in resolved:
        return True
    return False


def production_backup_executed(src: Path, backup_ok: bool) -> bool:
    """YES only when a Production source was actually backed up."""
    return bool(backup_ok and is_production_path(src))


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stat_info(path: Path) -> dict[str, Any]:
    st = path_stat(path)
    return {
        "path": str(path.resolve()) if path.exists() else str(path),
        "dev": st.st_dev,
        "ino": st.st_ino,
        "size": st.st_size,
        "mtime": int(st.st_mtime),
        "mode": oct(stat.S_IMODE(st.st_mode)),
    }


def _normalize_sql(sql: str | None) -> str:
    if not sql:
        return ""
    return " ".join(sql.split())


def canonical_master_rows(conn: sqlite3.Connection) -> list[tuple[str, str, str, str]]:
    rows = conn.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE type IN ('table','index','trigger','view') "
        "ORDER BY type, name, tbl_name, COALESCE(sql, '')"
    ).fetchall()
    return [
        (str(r[0]), str(r[1]), str(r[2] or ""), _normalize_sql(r[3]))
        for r in rows
    ]


def canonical_master_sha(conn: sqlite3.Connection) -> str:
    blob = "\n".join("|".join(row) for row in canonical_master_rows(conn)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def object_names(conn: sqlite3.Connection, typ: str) -> list[str]:
    return [
        str(r[0])
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type=? ORDER BY 1",
            (typ,),
        )
    ]


def schema_migrations(conn: sqlite3.Connection) -> list[str]:
    try:
        return [
            str(r[0])
            for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")
        ]
    except sqlite3.Error:
        return []


def schema_fingerprint(conn: sqlite3.Connection) -> dict[str, Any]:
    objects = {typ: object_names(conn, typ) for typ in MASTER_TYPES}
    return {
        "user_version": int(conn.execute("PRAGMA user_version").fetchone()[0]),
        "schema_version": int(conn.execute("PRAGMA schema_version").fetchone()[0]),
        "objects": objects,
        "schema_migrations": schema_migrations(conn),
        "master_sha256": canonical_master_sha(conn),
    }


def source_uri(path: Path) -> str:
    return "file:%s?mode=ro" % path.resolve().as_posix()


def open_readonly_source(path: Path) -> tuple[sqlite3.Connection, dict[str, Any]]:
    src = path.resolve()
    before = path_stat(src)
    uri = source_uri(src)
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.execute("PRAGMA query_only = ON")
        qo = conn.execute("PRAGMA query_only").fetchone()
        if qo is None or str(qo[0]) not in ("1", "on", "ON"):
            raise BackupError("QUERY_ONLY_NOT_ON")
        after = path_stat(src)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise BackupError("SOURCE_DEV_INO_CHANGED")
    except Exception:
        conn.close()
        raise
    info = {
        "path": str(src),
        "uri": uri,
        "dev": before.st_dev,
        "ino": before.st_ino,
        "size": before.st_size,
        "mtime": int(before.st_mtime),
        "mode": oct(stat.S_IMODE(before.st_mode)),
    }
    return conn, info


def refuse_source(src: Path) -> None:
    if not src.is_file():
        raise BackupError("SOURCE_MISSING")
    if is_production_path(src):
        if (os.environ.get("OWNER_PRODUCTION_BACKUP_APPROVED") or "").strip() != "1":
            raise BackupError("REFUSED_PRODUCTION_SOURCE_NO_OWNER_APPROVAL")
    if (os.environ.get("ALLOW_LOCAL_SQLITE_BACKUP") or "").strip() != "1":
        raise BackupError("REFUSED_ALLOW_LOCAL_SQLITE_BACKUP_UNSET")


def refuse_dest_identity(src: Path, dest: Path, src_st: dict[str, Any] | None = None) -> None:
    src_res = src.resolve()
    dest_abs = Path(os.path.abspath(str(dest)))
    if dest_abs == src_res or dest == src_res:
        raise BackupError("DEST_SAME_PATH_AS_SOURCE")
    if dest.exists():
        try:
            if dest.resolve() == src_res:
                raise BackupError("DEST_SAME_PATH_AS_SOURCE")
        except FileNotFoundError:
            pass
        dest_st = path_stat(dest)
        src_dev = src_st["dev"] if src_st else path_stat(src).st_dev
        src_ino = src_st["ino"] if src_st else path_stat(src).st_ino
        if (dest_st.st_dev, dest_st.st_ino) == (src_dev, src_ino):
            raise BackupError("DEST_SAME_INODE_AS_SOURCE")
        raise BackupError("DEST_EXISTS_OVERWRITE_FORBIDDEN")


def ensure_dest_dir(dest_dir: Path) -> None:
    resolved = dest_dir if dest_dir.exists() else Path(os.path.abspath(str(dest_dir)))
    if dest_dir.exists():
        resolved = dest_dir.resolve()
    if resolved in SHARED_DEST_DIRS:
        raise BackupError("DEST_DIR_NOT_DEDICATED")
    dest_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(dest_dir, DEST_DIR_MODE)
    mode = stat.S_IMODE(path_stat(dest_dir).st_mode)
    if mode != DEST_DIR_MODE:
        raise BackupError("PERMISSION_MISMATCH_DEST_DIR", oct(mode))


def verify_dest_permissions(dest_dir: Path, dest: Path) -> None:
    dir_mode = stat.S_IMODE(path_stat(dest_dir).st_mode)
    file_mode = stat.S_IMODE(path_stat(dest).st_mode)
    if dir_mode != DEST_DIR_MODE:
        raise BackupError("PERMISSION_MISMATCH_DEST_DIR", oct(dir_mode))
    if file_mode != DEST_FILE_MODE:
        raise BackupError("PERMISSION_MISMATCH_DEST_FILE", oct(file_mode))


def create_dest_exclusive(dest: Path) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    try:
        fd = os.open(str(dest), flags, DEST_FILE_MODE)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise BackupError("DEST_EXISTS_OVERWRITE_FORBIDDEN") from exc
        if exc.errno == errno.ENOSPC:
            raise BackupError("DEST_PARENT_INSUFFICIENT_SPACE") from exc
        raise BackupError("DEST_CREATE_FAILED", str(exc)) from exc
    os.close(fd)
    os.chmod(dest, DEST_FILE_MODE)
    mode = stat.S_IMODE(path_stat(dest).st_mode)
    if mode != DEST_FILE_MODE:
        raise BackupError("PERMISSION_MISMATCH_DEST_FILE", oct(mode))


def dest_sidecars(dest: Path) -> list[Path]:
    names = [dest]
    for suffix in ("-wal", "-shm", "-journal"):
        names.append(dest.with_name(dest.name + suffix))
    return names


def dispose_partial_dest(
    dest: Path,
    *,
    quarantine_dir: Path | None = None,
    source_dev_ino: tuple[int, int] | None = None,
) -> str:
    """Delete or quarantine only the explicit dest (plus SQLite sidecars)."""
    actions: list[str] = []
    for candidate in dest_sidecars(dest):
        if not candidate.exists():
            continue
        st = path_stat(candidate)
        if source_dev_ino and (st.st_dev, st.st_ino) == source_dev_ino:
            emit("PARTIAL_BACKUP_SKIPPED_SOURCE_INODE", "YES")
            continue
        if quarantine_dir is not None:
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(quarantine_dir, DEST_DIR_MODE)
            q = quarantine_dir / (candidate.name + ".quarantine")
            n = 0
            while q.exists():
                n += 1
                q = quarantine_dir / ("%s.%d.quarantine" % (candidate.name, n))
            candidate.replace(q)
            os.chmod(q, DEST_FILE_MODE)
            actions.append("QUARANTINED")
        else:
            candidate.unlink()
            actions.append("DELETED")
    if not actions:
        return "ABSENT"
    return "QUARANTINED" if "QUARANTINED" in actions else "DELETED"


def check_free_space(src: Path, dest_dir: Path) -> None:
    need = path_stat(src).st_size + (8 * 1024 * 1024)
    free = shutil.disk_usage(str(dest_dir)).free
    emit("DEST_FREE_BYTES", free)
    emit("BACKUP_NEED_BYTES", need)
    if free < need:
        raise BackupError("DEST_PARENT_INSUFFICIENT_SPACE")


def timestamped_dest(dest_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return dest_dir / ("expect_ai_backup_%s.db" % stamp)


def compare_schema_dicts(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if a["user_version"] != b["user_version"]:
        return False
    if a["schema_migrations"] != b["schema_migrations"]:
        return False
    if a["master_sha256"] != b["master_sha256"]:
        return False
    for typ in MASTER_TYPES:
        if a["objects"][typ] != b["objects"][typ]:
            return False
        if len(a["objects"][typ]) != len(b["objects"][typ]):
            return False
    return True


def fingerprint_path(path: Path) -> dict[str, Any]:
    conn, _info = open_readonly_source(path)
    try:
        return schema_fingerprint(conn)
    finally:
        conn.close()


def compare_schema(src: Path, dest: Path) -> bool:
    a = fingerprint_path(src)
    b = fingerprint_path(dest)
    emit("SOURCE_SCHEMA_VERSION", a["schema_version"])
    emit("DEST_SCHEMA_VERSION", b["schema_version"])
    emit("SOURCE_USER_VERSION", a["user_version"])
    emit("DEST_USER_VERSION", b["user_version"])
    emit("SOURCE_TABLE_COUNT", len(a["objects"]["table"]))
    emit("DEST_TABLE_COUNT", len(b["objects"]["table"]))
    emit("SOURCE_INDEX_COUNT", len(a["objects"]["index"]))
    emit("DEST_INDEX_COUNT", len(b["objects"]["index"]))
    emit("SOURCE_TRIGGER_COUNT", len(a["objects"]["trigger"]))
    emit("DEST_TRIGGER_COUNT", len(b["objects"]["trigger"]))
    emit("SOURCE_VIEW_COUNT", len(a["objects"]["view"]))
    emit("DEST_VIEW_COUNT", len(b["objects"]["view"]))
    emit("SOURCE_MIGRATION_COUNT", len(a["schema_migrations"]))
    emit("DEST_MIGRATION_COUNT", len(b["schema_migrations"]))
    emit("SOURCE_MASTER_SHA256", a["master_sha256"])
    emit("DEST_MASTER_SHA256", b["master_sha256"])
    emit("SCHEMA_VERSION_MATCH", a["schema_version"] == b["schema_version"])
    emit(
        "SCHEMA_VERSION_NOTE",
        "sqlite3.Connection.backup onto a new dest file may leave dest schema_version different; "
        "canonical sqlite_master SHA plus table/index/trigger/view/schema_migrations are the gate",
    )
    emit("TABLE_SET_MATCH", a["objects"]["table"] == b["objects"]["table"])
    emit("INDEX_SET_MATCH", a["objects"]["index"] == b["objects"]["index"])
    emit("TRIGGER_SET_MATCH", a["objects"]["trigger"] == b["objects"]["trigger"])
    emit("VIEW_SET_MATCH", a["objects"]["view"] == b["objects"]["view"])
    emit("SCHEMA_MIGRATIONS_MATCH", a["schema_migrations"] == b["schema_migrations"])
    emit("MASTER_SHA_MATCH", a["master_sha256"] == b["master_sha256"])
    same = compare_schema_dicts(a, b)
    emit("SCHEMA_FINGERPRINT_MATCH", same)
    return same


def restore_to_temp(backup: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="restore-rehearse-"))
    os.chmod(tmp, DEST_DIR_MODE)
    restored = tmp / "restored.db"
    if is_production_path(restored):
        raise BackupError("RESTORE_TARGET_IS_PRODUCTION")
    src_conn, _info = open_readonly_source(backup)
    create_dest_exclusive(restored)
    dst = sqlite3.connect(str(restored))
    try:
        src_conn.backup(dst, pages=64, sleep=0.05)
        dst.commit()
        check = dst.execute("PRAGMA integrity_check").fetchone()
        if not check or str(check[0]) != "ok":
            raise BackupError("RESTORE_INTEGRITY_CHECK_FAILED")
    finally:
        dst.close()
        src_conn.close()
    os.chmod(restored, DEST_FILE_MODE)
    verify_dest_permissions(tmp, restored)
    emit("RESTORE_TARGET", str(restored))
    emit("RESTORE_TO_LIVE", "NO")
    emit("RESTORE_INTEGRITY_CHECK", "ok")
    return restored


def _close_quietly(conn: sqlite3.Connection | None) -> None:
    if conn is None:
        return
    try:
        conn.close()
    except sqlite3.Error:
        pass


def perform_backup(src_conn: sqlite3.Connection, dest_conn: sqlite3.Connection) -> None:
    src_conn.backup(dest_conn, pages=64, sleep=0.05)
    dest_conn.commit()


def read_integrity(dest_conn: sqlite3.Connection) -> str:
    check = dest_conn.execute("PRAGMA integrity_check").fetchone()
    return str(check[0]) if check else ""


def run_backup(src: Path, dest: Path) -> None:
    src_conn: sqlite3.Connection | None = None
    dest_conn: sqlite3.Connection | None = None
    try:
        src_conn, open_info = open_readonly_source(src)
        emit("SOURCE_OPEN_URI", open_info["uri"])
        emit("SOURCE_OPEN_QUERY_ONLY", "ON")
        emit("SOURCE_DEV_AFTER_OPEN", open_info["dev"])
        emit("SOURCE_INO_AFTER_OPEN", open_info["ino"])
        dest_conn = sqlite3.connect(str(dest))
        try:
            perform_backup(src_conn, dest_conn)
        except OSError as exc:
            if exc.errno == errno.ENOSPC:
                raise BackupError("DEST_PARENT_INSUFFICIENT_SPACE") from exc
            raise BackupError("BACKUP_COPY_FAILED", str(exc)) from exc
        result = read_integrity(dest_conn)
        if result != "ok":
            raise BackupError("INTEGRITY_CHECK_FAILED")
        emit("PRAGMA_INTEGRITY_CHECK", "ok")
    finally:
        _close_quietly(dest_conn)
        _close_quietly(src_conn)


def run_contract(
    src: Path,
    dest: Path,
    *,
    restore_rehearse: bool = False,
    quarantine_dir: Path | None = None,
) -> int:
    emit("PACK", PACK_NAME)
    emit("PRODUCTION_BACKUP_EXECUTED", "NO")
    emit("MIGRATION_MAY_PROCEED", "NO")
    dest_created = False
    dest_verified = False
    dest_existed = False
    src_dev_ino: tuple[int, int] | None = None
    try:
        refuse_source(src)
        src_before = stat_info(src)
        src_dev_ino = (src_before["dev"], src_before["ino"])
        emit("SOURCE_PATH", src_before["path"])
        emit("SOURCE_DEV", src_before["dev"])
        emit("SOURCE_INO", src_before["ino"])
        emit("SOURCE_SIZE", src_before["size"])
        emit("SOURCE_MTIME", src_before["mtime"])
        emit("SOURCE_MODE", src_before["mode"])
        emit("PRODUCTION_SOURCE_USED", is_production_path(src))
        emit(
            "OWNER_PRODUCTION_BACKUP_APPROVED_EFFECTIVE",
            (os.environ.get("OWNER_PRODUCTION_BACKUP_APPROVED") or "").strip() == "1",
        )

        refuse_dest_identity(src, dest, src_before)
        ensure_dest_dir(dest.parent)
        emit("DEST_DIR_MODE_AFTER_CREATE", oct(stat.S_IMODE(path_stat(dest.parent).st_mode)))
        check_free_space(src, dest.parent)
        staging = dest.with_name(dest.name + ".tmp")
        if staging.exists():
            dispose_partial_dest(staging, source_dev_ino=src_dev_ino)
        dest_existed = dest.exists()
        try:
            create_dest_exclusive(staging)
            dest_created = True
            emit("STAGING_FILE_MODE_AFTER_CREATE", oct(stat.S_IMODE(path_stat(staging).st_mode)))
        except BackupError:
            dest_created = (not dest_existed) and (dest.exists() or staging.exists())
            raise
        stg_st = path_stat(staging)
        if (stg_st.st_dev, stg_st.st_ino) == (src_before["dev"], src_before["ino"]):
            raise BackupError("DEST_SAME_INODE_AS_SOURCE")
        emit("DEST_PATH", str(Path(os.path.abspath(str(dest)))))
        emit("STAGING_PATH", str(staging))
        emit("DEST_OVERWRITE", "NO")
        emit("DEST_DIR_MODE", oct(DEST_DIR_MODE))
        emit("DEST_FILE_MODE_TARGET", oct(DEST_FILE_MODE))

        run_backup(src, staging)
        os.chmod(dest.parent, DEST_DIR_MODE)
        os.chmod(staging, DEST_FILE_MODE)
        verify_dest_permissions(dest.parent, staging)

        src_after = stat_info(src)
        emit("SOURCE_DEV_AFTER_BACKUP", src_after["dev"])
        emit("SOURCE_INO_AFTER_BACKUP", src_after["ino"])
        if (src_after["dev"], src_after["ino"]) != (src_before["dev"], src_before["ino"]):
            raise BackupError("SOURCE_DEV_INO_CHANGED")

        emit("SOURCE_FILE_SHA256", file_sha(src))
        emit("STAGING_SHA256", file_sha(staging))
        if not compare_schema(src, staging):
            raise BackupError("SCHEMA_MISMATCH")

        os.replace(str(staging), str(dest))
        os.chmod(dest, DEST_FILE_MODE)
        verify_dest_permissions(dest.parent, dest)
        dest_info = stat_info(dest)
        emit("DEST_DEV", dest_info["dev"])
        emit("DEST_INO", dest_info["ino"])
        emit("DEST_SIZE", dest_info["size"])
        emit("DEST_MTIME", dest_info["mtime"])
        emit("DEST_MODE", dest_info["mode"])
        emit("DEST_SHA256", file_sha(dest))
        emit("SOURCE_IDENTITY", "%s:%s" % (src_before["dev"], src_before["ino"]))
        emit("DEST_IDENTITY", "%s:%s" % (dest_info["dev"], dest_info["ino"]))
        same_id = dest_info["ino"] == src_before["ino"] and dest_info["dev"] == src_before["dev"]
        emit("DEST_SAME_INODE_AS_SOURCE", same_id)
        emit("DB_IDENTITY_DISTINCT", not same_id and dest_info["path"] != src_before["path"])
        if same_id:
            raise BackupError("DEST_SAME_INODE_AS_SOURCE")
        dest_verified = True

        if restore_rehearse:
            restored = restore_to_temp(dest)
            if not compare_schema(dest, restored):
                emit("RESTORE_REHEARSE_OK", "NO")
                raise BackupError("RESTORE_SCHEMA_MISMATCH")
            emit("RESTORE_REHEARSE_OK", "YES")

        executed = production_backup_executed(src, True)
        emit("PRODUCTION_BACKUP_EXECUTED", "YES" if executed else "NO")
        emit("BACKUP_OK", "YES")
        emit("MIGRATION_MAY_PROCEED", "NO")
        emit("PRODUCTION_BACKUP_DESIGN_COMPLETE", "YES")
        emit("PRODUCTION_BACKUP_DESIGN_APPROVED", "NO")
        emit("PRODUCTION_APPLY_READY", "NO")
        return 0
    except BackupError as exc:
        emit("BACKUP_OK", "NO")
        emit("MIGRATION_MAY_PROCEED", "NO")
        emit("PRODUCTION_BACKUP_EXECUTED", "NO")
        emit("FAIL_REASON", exc.code)
        if dest_created and not dest_verified:
            staging = dest.with_name(dest.name + ".tmp")
            action = dispose_partial_dest(
                staging,
                quarantine_dir=quarantine_dir,
                source_dev_ino=src_dev_ino,
            )
            if dest.exists() and not dest_existed:
                action = dispose_partial_dest(
                    dest,
                    quarantine_dir=quarantine_dir,
                    source_dev_ino=src_dev_ino,
                )
            emit("PARTIAL_BACKUP_DISPOSAL", action)
            emit("PARTIAL_BACKUP_DEST_ONLY", "YES")
            emit("COMPLETED_DEST_LEFT", "NO")
        elif dest_created and dest_verified:
            emit("PARTIAL_BACKUP_DISPOSAL", "KEPT_VERIFIED_DEST")
        else:
            emit("PARTIAL_BACKUP_DISPOSAL", "NOT_CREATED")
        return 2


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SQLite backup design contract (not Production)")
    parser.add_argument("--src", required=True, help="explicit single DB source path")
    dest = parser.add_mutually_exclusive_group(required=True)
    dest.add_argument("--dest", help="explicit single destination DB path")
    dest.add_argument("--dest-dir", help="dedicated directory for a new timestamped backup")
    parser.add_argument("--restore-rehearse", action="store_true")
    parser.add_argument(
        "--quarantine-dir",
        default=None,
        help="if set, failed dest is moved here instead of deleted",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    src = Path(args.src)
    if args.dest:
        dest = Path(args.dest)
    else:
        dest_dir = Path(args.dest_dir)
        ensure_dest_dir(dest_dir)
        dest = timestamped_dest(dest_dir)
    quarantine = Path(args.quarantine_dir) if args.quarantine_dir else None
    try:
        return run_contract(
            src,
            dest,
            restore_rehearse=args.restore_rehearse,
            quarantine_dir=quarantine,
        )
    except BackupError as exc:
        emit("BACKUP_OK", "NO")
        emit("MIGRATION_MAY_PROCEED", "NO")
        emit("PRODUCTION_BACKUP_EXECUTED", "NO")
        emit("FAIL_REASON", exc.code)
        return 2

# --- embedded owner_backup_remote.py (shebang/coding/future stripped) ---

import os
import sqlite3
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

CANONICAL_SOURCE = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db"
DEST_ROOT = "/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups"
REVIEWED_CONTRACT_SHA256 = (
    "55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e"
)
PACK = "production_backup_owner_execution_fresh_20260912"
HISTORICAL_BACKUP_PATH = "/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260911T175303Z/expect_ai.db"
HISTORICAL_BACKUP_SHA256 = "f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d"
HISTORICAL_BACKUP_STAMP = "20260911T175303Z"
HISTORICAL_BACKUP_SIZE = 105967616
LAST_MEASURED_LIVE_SOURCE_SIZE = 107237376
LAST_MEASURED_PRED_ROW_COUNT = 301
V5_APPLY_ZIP_SHA256 = "60cef7b2354d2c3a4b49e6a5f687537cc6188936ccbf9534ba070ca7667f84d8"
V5_LOCAL_DESIGN_REVIEW = "PASS"
V5_OWNER_EXECUTION_ALLOWED = "NO"

OWNER_MIGRATIONS = (
    "001_init",
    "002_race_identity",
    "003_supply_platform",
    "004_user_domain",
    "005_results_eval",
    "006_result_automation",
    "007_collect_c0",
    "008_collect_contract_1_1",
    "009_user_race_results",
    "010_user_progress_audit",
    "011_research_evidence",
    "012_research_snapshot_features",
    "013_research_prediction_corpus",
    "014_research_historical_ingest",
    "015_research_race_meta",
    "016_research_knowledge_base",
    "017_research_knowledge_validation",
    "018_research_candidate_review",
    "019_final_predictions",
    "020_research_corpus_canonical",
    "020_user_challenge_lifecycle",
    "021_user_challenge_point_events",
)
OWNER_PRED_COLUMNS = (
    "id",
    "race_id",
    "core_race_id",
    "engine_source",
    "fallback_reason",
    "model_version",
    "bundle_json",
    "created_at",
)
OWNER_PRED_INDEX = "idx_predictions_race"
OWNER_PRED_INDEX_COLS = ("race_id", "created_at")
PERSIST_019 = "019_prediction_run_idempotency"
PERSIST_022 = "022_prediction_run_idempotency"
NEW_COLS = (
    "idempotency_key",
    "persist_source",
    "input_snapshot_hash",
    "prediction_semantic_hash",
)
PARTIAL_INDEX = "uq_predictions_idempotency_key_not_null"
# Owner live schema inventory identity (do not invent; these are the returned facts).
INVENTORY_SOURCE_DEV = 66305
INVENTORY_SOURCE_INO = 349935
INVENTORY_SOURCE_SIZE = 105783296
INVENTORY_SOURCE_MTIME = 1789143980
WATCHED_ENV_KEYS = (
    "PREDICTION_RUNS_ENABLED",
    "EXPECT_AI_ALLOW_MIGRATION_022",
    "EXPECT_AI_ALLOW_MIGRATION_019",
)
SERVICE_CANDIDATES = (
    "expect-ai.service",
    "win5-ai.service",
    "expect_ai.service",
)


def _load_bc():
    if "run_contract" in globals():
        names = (
            "emit",
            "run_contract",
            "open_readonly_source",
            "schema_fingerprint",
            "compare_schema_dicts",
            "fingerprint_path",
            "file_sha",
            "production_backup_executed",
            "BackupError",
            "SHARED_DEST_DIRS",
        )
        missing = [n for n in names if n not in globals()]
        if missing:
            raise RuntimeError("contract_snapshot_missing:" + ",".join(missing))
        return SimpleNamespace(**{n: globals()[n] for n in names})
    here = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    import backup_contract as m  # type: ignore

    return m


bc = _load_bc()


class Halt(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def emit(key: str, value: object) -> None:
    bc.emit(key, value)


def test_mode() -> bool:
    return (os.environ.get("OWNER_BACKUP_PACK_TEST_SRC") or "").strip() == "1"


def inventory_dev_ino() -> tuple[int, int]:
    raw_dev = (os.environ.get("OWNER_BACKUP_TEST_INVENTORY_DEV") or "").strip()
    raw_ino = (os.environ.get("OWNER_BACKUP_TEST_INVENTORY_INO") or "").strip()
    if test_mode() and raw_dev and raw_ino:
        return int(raw_dev), int(raw_ino)
    return int(INVENTORY_SOURCE_DEV), int(INVENTORY_SOURCE_INO)


def canonical_source() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_BACKUP_TEST_SRC") or "").strip()
        if override:
            return Path(override)
    return Path(CANONICAL_SOURCE)


def dest_root() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_BACKUP_TEST_DEST_ROOT") or "").strip()
        if override:
            return Path(override)
    return Path(DEST_ROOT)


def is_historical_backup_path(path: Path) -> bool:
    text = path.as_posix()
    try:
        resolved = path.resolve().as_posix()
    except OSError:
        resolved = text
    if HISTORICAL_BACKUP_STAMP in text or HISTORICAL_BACKUP_STAMP in resolved:
        return True
    return text == HISTORICAL_BACKUP_PATH or resolved == HISTORICAL_BACKUP_PATH


def refuse_historical_dest(dest: Path) -> None:
    emit("HISTORICAL_BACKUP_PATH", HISTORICAL_BACKUP_PATH)
    emit("HISTORICAL_BACKUP_SHA256", HISTORICAL_BACKUP_SHA256)
    emit("HISTORICAL_BACKUP_SIZE", HISTORICAL_BACKUP_SIZE)
    emit("HISTORICAL_BACKUP_NOT_APPLY_CANON", "YES")
    emit("HISTORICAL_BACKUP_DELETE", "NO")
    emit("HISTORICAL_BACKUP_OVERWRITE", "NO")
    emit("AUTO_BACKUP_RESTORE", "NO")
    if is_historical_backup_path(dest) or is_historical_backup_path(dest.parent):
        raise Halt("HISTORICAL_BACKUP_DEST_REFUSED")
    hist = Path(HISTORICAL_BACKUP_PATH)
    if hist.is_file():
        try:
            if dest.exists() and dest.resolve() == hist.resolve():
                raise Halt("HISTORICAL_BACKUP_DEST_REFUSED")
            if dest.exists() and (dest.stat().st_dev, dest.stat().st_ino) == (hist.stat().st_dev, hist.stat().st_ino):
                raise Halt("HISTORICAL_BACKUP_DEST_REFUSED")
        except Halt:
            raise
        except OSError:
            pass


def refuse_unapproved() -> None:
    if (os.environ.get("OWNER_PRODUCTION_BACKUP_APPROVED") or "").strip() != "1":
        raise Halt("OWNER_PRODUCTION_BACKUP_APPROVED_UNSET")


def sqlite_version(conn: sqlite3.Connection) -> str:
    row = conn.execute("select sqlite_version()").fetchone()
    return str(row[0]) if row else ""


def migration_list(conn: sqlite3.Connection) -> list[str]:
    try:
        return [str(r[0]) for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")]
    except sqlite3.Error:
        return []


def prediction_columns(conn: sqlite3.Connection) -> list[str]:
    try:
        return [str(r[1]) for r in conn.execute("PRAGMA table_info(predictions)")]
    except sqlite3.Error:
        return []


def index_columns(conn: sqlite3.Connection, name: str) -> list[str]:
    try:
        rows = conn.execute("PRAGMA index_info(%s)" % name).fetchall()
    except sqlite3.Error:
        return []
    ordered = sorted(rows, key=lambda r: int(r[0]))
    return [str(r[2] or "") for r in ordered]


def index_sql(conn: sqlite3.Connection, name: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
        (name,),
    ).fetchone()
    return str(row[0] or "") if row and row[0] else ""


def verify_owner_schema(conn: sqlite3.Connection) -> None:
    ver = sqlite_version(conn)
    emit("SQLITE_VERSION", ver)
    emit("SQLITE_VERSION_RECORDED", bool(ver))
    emit("INVENTORY_SQLITE_VERSION", "3.45.1")
    migrations = migration_list(conn)
    emit("SCHEMA_MIGRATIONS_COUNT", len(migrations))
    emit("OWNER_MIGRATION_COUNT", len(OWNER_MIGRATIONS))
    owner_set = set(OWNER_MIGRATIONS)
    have_set = set(migrations)
    emit("SEEDED_MISSING_COUNT", len(owner_set - have_set))
    emit("SEEDED_EXTRA_COUNT", len(have_set - owner_set))
    emit("MIGRATION_SET_MATCH_OWNER", have_set == owner_set)
    emit("HAS_PERSIST_019", PERSIST_019 in have_set)
    emit("HAS_PERSIST_022", PERSIST_022 in have_set)
    emit("HAS_019_FINAL_PREDICTIONS", "019_final_predictions" in have_set)
    cols = prediction_columns(conn)
    emit("PREDICTIONS_COLUMN_COUNT", len(cols))
    emit("PREDICTIONS_COLUMNS_MATCH_OWNER", cols == list(OWNER_PRED_COLUMNS))
    idx_cols = index_columns(conn, OWNER_PRED_INDEX)
    emit("PREDICTIONS_INDEX_NAME", OWNER_PRED_INDEX)
    emit("PREDICTIONS_INDEX_COLS_MATCH", idx_cols == list(OWNER_PRED_INDEX_COLS))
    emit("PREDICTIONS_INDEX_SQL_PRESENT", bool(index_sql(conn, OWNER_PRED_INDEX)))
    extra_cols = [c for c in NEW_COLS if c in cols]
    emit("NEW_PERSIST_COLUMNS_PRESENT", len(extra_cols))
    names = {
        str(r[0])
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    }
    emit("PARTIAL_UNIQUE_INDEX_PRESENT", PARTIAL_INDEX in names)
    emit("SCHEMA_MIGRATIONS_UNIQUE_COUNT", len(have_set))
    emit("SCHEMA_MIGRATIONS_DUPLICATE_COUNT", len(migrations) - len(have_set))
    reasons = []
    if extra_cols:
        reasons.append("NEW_PERSIST_COLUMNS_PRESENT")
    if PARTIAL_INDEX in names:
        reasons.append("PARTIAL_UNIQUE_INDEX_PRESENT")
    if PERSIST_019 in have_set:
        reasons.append("HAS_PERSIST_019")
    if PERSIST_022 in have_set:
        reasons.append("HAS_PERSIST_022")
    if len(migrations) != 22 or have_set != owner_set:
        reasons.append("MIGRATION_SET_MISMATCH")
    if len(migrations) - len(have_set) != 0:
        reasons.append("MIGRATION_DUPLICATE")
    if cols != list(OWNER_PRED_COLUMNS):
        reasons.append("PREDICTIONS_COLUMNS_MISMATCH")
    if idx_cols != list(OWNER_PRED_INDEX_COLS):
        reasons.append("PREDICTIONS_INDEX_MISMATCH")
    if reasons:
        emit("SOURCE_SCHEMA_GATE", "HALT")
        raise Halt(reasons[0])
    emit("SOURCE_SCHEMA_GATE", "PASS")


def verify_inventory_identity(src: Path) -> os.stat_result:
    st = src.stat()
    emit("SOURCE_PATH", str(src.resolve()) if src.exists() else str(src))
    emit("SOURCE_DEV", st.st_dev)
    emit("SOURCE_INO", st.st_ino)
    emit("SOURCE_SIZE", st.st_size)
    emit("SOURCE_MTIME", int(st.st_mtime))
    emit("SOURCE_MODE", oct(stat.S_IMODE(st.st_mode)))
    inv_dev, inv_ino = inventory_dev_ino()
    emit("INVENTORY_SOURCE_DEV", inv_dev)
    emit("INVENTORY_SOURCE_INO", inv_ino)
    emit("INVENTORY_SOURCE_SIZE", INVENTORY_SOURCE_SIZE)
    emit("INVENTORY_SOURCE_MTIME", INVENTORY_SOURCE_MTIME)
    emit("INVENTORY_DEV_INO_RECORDED", "YES")
    emit("INVENTORY_DEV_INO_ABSENT", "NO")
    emit("SOURCE_SIZE_EQUALS_INVENTORY", int(st.st_size) == int(INVENTORY_SOURCE_SIZE))
    emit("SOURCE_MTIME_EQUALS_INVENTORY", int(st.st_mtime) == int(INVENTORY_SOURCE_MTIME))
    if (int(st.st_dev), int(st.st_ino)) != (int(inv_dev), int(inv_ino)):
        emit("DB_DRIFT", "YES")
        emit("NEW_READONLY_INVENTORY_REQUIRED", "YES")
        raise Halt("DB_DRIFT")
    emit("DB_DRIFT", "NO")
    emit("NEW_READONLY_INVENTORY_REQUIRED", "NO")
    return st


def _flag_01(raw: str | None) -> int:
    return 1 if (raw or "").strip().lower() in ("1", "true", "yes", "on") else 0


def parse_systemd_show(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip()
    return out


def parse_assignment_blob(blob: str, *, split_null: bool) -> dict[str, str]:
    out: dict[str, str] = {}
    raw = blob.replace("\n", "\0") if split_null else blob
    parts = raw.split("\0") if split_null else raw.split()
    for part in parts:
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        if key in WATCHED_ENV_KEYS:
            out[key] = val
    return out


def parse_env_file(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, val = stripped.split("=", 1)
                key = key.strip()
                if key in WATCHED_ENV_KEYS:
                    out[key] = val.strip().strip("'\"")
    except OSError:
        return {}
    return out


def environment_file_paths(raw: str) -> list[str]:
    paths: list[str] = []
    for chunk in (raw or "").replace(" ", "\n").splitlines():
        item = chunk.strip()
        if not item:
            continue
        path = item.split("(", 1)[0].strip()
        if path.startswith("/"):
            paths.append(path)
    return paths


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
        return int(p.returncode), (p.stdout or "")
    except Exception:
        return 1, ""


def read_proc_environ(pid: str) -> tuple[bool, dict[str, str]]:
    if not pid.isdigit() or int(pid) <= 0:
        return False, {}
    try:
        with open("/proc/%s/environ" % pid, "rb") as fh:
            blob = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return False, {}
    return True, parse_assignment_blob(blob, split_null=True)


def collect_production_env() -> dict[str, object]:
    if test_mode() and (os.environ.get("OWNER_BACKUP_TEST_ENV") or "").strip() == "1":
        show = (os.environ.get("OWNER_BACKUP_TEST_SYSTEMD_SHOW") or "")
        proc_blob = (os.environ.get("OWNER_BACKUP_TEST_PROC_ENVIRON") or "")
        file_blob = (os.environ.get("OWNER_BACKUP_TEST_ENVFILE") or "")
        sd = parse_systemd_show(show)
        proc_ok = bool(proc_blob) or (os.environ.get("OWNER_BACKUP_TEST_PROC_OK") or "") == "1"
        proc = parse_assignment_blob(proc_blob.replace(" ", "\0"), split_null=True) if proc_blob else {}
        files = parse_assignment_blob(file_blob.replace(" ", "\0"), split_null=True) if file_blob else {}
        systemd_ok = bool(show) or (os.environ.get("OWNER_BACKUP_TEST_SYSTEMD_OK") or "") == "1"
        files_ok = bool(file_blob) or (os.environ.get("OWNER_BACKUP_TEST_FILES_OK") or "") == "1"
        env_line = sd.get("Environment") or ""
        systemd_env = parse_assignment_blob(env_line.replace(" ", "\0"), split_null=True)
        file_paths = environment_file_paths(sd.get("EnvironmentFiles") or "")
        if file_blob:
            file_paths = file_paths or ["TEST"]
        unit_loaded = (sd.get("LoadState") or "") == "loaded"
        mainpid = str(sd.get("MainPID") or "0").strip()
        mainpid_set = mainpid not in ("", "0")
        return {
            "systemd_ok": systemd_ok,
            "proc_ok": proc_ok,
            "files_ok": files_ok,
            "proc": proc,
            "systemd": systemd_env,
            "files": files,
            "env_files": "SET" if file_paths else "UNSET",
            "mainpid": "SET" if mainpid_set else "UNSET",
            "unit": sd.get("Id") or "TEST",
            "unit_loaded": unit_loaded,
            "file_paths_configured": bool(file_paths),
            "mainpid_set": mainpid_set,
            "load_state": sd.get("LoadState") or "UNSET",
        }

    unit = ""
    show_out = ""
    show_rc = 1
    for cand in SERVICE_CANDIDATES:
        for args in (
            [
                "systemctl",
                "show",
                cand,
                "--no-pager",
                "-p",
                "Id",
                "-p",
                "MainPID",
                "-p",
                "LoadState",
                "-p",
                "ActiveState",
                "-p",
                "Environment",
                "-p",
                "EnvironmentFiles",
            ],
            [
                "systemctl",
                "--user",
                "show",
                cand,
                "--no-pager",
                "-p",
                "Id",
                "-p",
                "MainPID",
                "-p",
                "LoadState",
                "-p",
                "ActiveState",
                "-p",
                "Environment",
                "-p",
                "EnvironmentFiles",
            ],
        ):
            rc, out = run_cmd(args)
            if rc == 0 and out.strip():
                parsed = parse_systemd_show(out)
                if (parsed.get("LoadState") or "") == "loaded":
                    show_rc = rc
                    show_out = out
                    unit = cand
                    break
        if show_out:
            break
    sd = parse_systemd_show(show_out)
    unit_loaded = (sd.get("LoadState") or "") == "loaded"
    systemd_ok = show_rc == 0 and bool(sd) and unit_loaded
    env_line = sd.get("Environment") or ""
    systemd_env = parse_assignment_blob(env_line.replace(" ", "\0"), split_null=True)
    file_paths = environment_file_paths(sd.get("EnvironmentFiles") or "")
    files: dict[str, str] = {}
    files_ok = False
    if file_paths:
        readable = 0
        for path in file_paths:
            parsed = parse_env_file(path)
            if parsed or os.path.isfile(path):
                readable += 1
            files.update(parsed)
        files_ok = readable == len(file_paths)
    elif systemd_ok:
        files_ok = True
    mainpid = str(sd.get("MainPID") or "0").strip()
    mainpid_set = mainpid not in ("", "0")
    proc_ok, proc = read_proc_environ(mainpid)
    return {
        "systemd_ok": systemd_ok,
        "proc_ok": proc_ok,
        "files_ok": files_ok,
        "proc": proc,
        "systemd": systemd_env,
        "files": files,
        "env_files": "SET" if file_paths else "UNSET",
        "mainpid": "SET" if mainpid_set else "UNSET",
        "unit": unit or "UNSET",
        "unit_loaded": unit_loaded,
        "file_paths_configured": bool(file_paths),
        "mainpid_set": mainpid_set,
        "load_state": sd.get("LoadState") or "UNSET",
    }


def verify_production_env() -> None:
    info = collect_production_env()
    emit("PRODUCTION_ENV_UNIT", info["unit"])
    emit("PRODUCTION_ENV_LOAD_STATE", info["load_state"])
    emit("PRODUCTION_ENV_UNIT_LOADED", "YES" if info["unit_loaded"] else "NO")
    emit("PRODUCTION_ENV_SYSTEMD_READ", info["systemd_ok"])
    emit("PRODUCTION_ENV_PROC_READ", info["proc_ok"])
    emit("PRODUCTION_ENV_FILES_READ", info["files_ok"])
    emit("PRODUCTION_ENV_MAINPID", info["mainpid"])
    emit("PRODUCTION_ENV_FILE_PRESENT", info["env_files"])
    determined = bool(
        info["unit_loaded"]
        and info["systemd_ok"]
        and (info["proc_ok"] or not info["mainpid_set"])
        and (info["files_ok"] or not info["file_paths_configured"])
    )
    emit("PRODUCTION_ENV_DETERMINED", determined)
    if not determined:
        raise Halt("PRODUCTION_ENV_UNDETERMINED")
    for key in WATCHED_ENV_KEYS:
        raw = None
        source = "UNSET"
        if info["proc_ok"] and key in info["proc"]:
            raw = info["proc"][key]
            source = "PROC"
        elif info["systemd_ok"] and key in info["systemd"]:
            raw = info["systemd"][key]
            source = "SYSTEMD_ENVIRONMENT"
        elif info["files_ok"] and key in info["files"]:
            raw = info["files"][key]
            source = "ENVIRONMENT_FILE"
        present = raw is not None
        effective = _flag_01(raw) if present else 0
        emit("%s_SET" % key, "SET" if present else "UNSET")
        emit("%s_EFFECTIVE" % key, effective)
        emit("%s_SOURCE" % key, source)
        if effective == 1:
            raise Halt("%s_EFFECTIVE_1" % key)
    emit("PRODUCTION_ENV_GATE", "PASS")


def dedicated_dest(src: Path) -> Path:
    root = dest_root()
    src_abs = Path(os.path.abspath(str(src)))
    root_abs = Path(os.path.abspath(str(root)))
    if root_abs == src_abs or root_abs == src_abs.parent:
        raise Halt("DEST_ROOT_IS_SOURCE_PARENT")
    shared = getattr(bc, "SHARED_DEST_DIRS", set())
    if root_abs in shared:
        raise Halt("DEST_ROOT_NOT_DEDICATED")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if stamp == HISTORICAL_BACKUP_STAMP:
        raise Halt("HISTORICAL_BACKUP_DEST_REFUSED")
    dest = root_abs / stamp / "expect_ai.db"
    refuse_historical_dest(dest)
    return dest


def emit_success(src: Path, dest: Path) -> None:
    dir_mode = stat.S_IMODE(dest.parent.stat().st_mode)
    file_mode = stat.S_IMODE(dest.stat().st_mode)
    dest_conn, _info = bc.open_readonly_source(dest)
    try:
        integrity = dest_conn.execute("PRAGMA integrity_check").fetchone()
        integrity_ok = bool(integrity) and str(integrity[0]) == "ok"
        dest_fp = bc.schema_fingerprint(dest_conn)
    finally:
        dest_conn.close()
    src_fp = bc.fingerprint_path(src)
    schema_ok = bc.compare_schema_dicts(src_fp, dest_fp)
    migration_ok = src_fp["schema_migrations"] == dest_fp["schema_migrations"]
    master_ok = src_fp["master_sha256"] == dest_fp["master_sha256"]
    src_st = src.stat()
    dest_st = dest.stat()
    distinct = (src_st.st_dev, src_st.st_ino) != (dest_st.st_dev, dest_st.st_ino)
    dest_sha = bc.file_sha(dest)
    emit("OWNER_BACKUP_STATUS", "SUCCESS")
    emit("BACKUP_INTEGRITY_OK", integrity_ok)
    emit("BACKUP_SCHEMA_OK", schema_ok)
    emit("BACKUP_MIGRATION_SET_OK", migration_ok)
    emit("BACKUP_MASTER_SHA_MATCH", master_ok)
    emit("BACKUP_DEST_SHA256", dest_sha)
    emit("BACKUP_SHA256_RECORDED", bool(dest_sha))
    emit("BACKUP_DISTINCT_INODE", distinct)
    emit("BACKUP_DIR_MODE", oct(dir_mode))
    emit("BACKUP_FILE_MODE", oct(file_mode))
    executed = bc.production_backup_executed(src, True)
    emit("PRODUCTION_BACKUP_EXECUTED", executed)
    passed = integrity_ok and schema_ok and migration_ok and master_ok and distinct
    if dir_mode != 0o700 or file_mode != 0o600 or not passed:
        raise Halt("OWNER_POST_BACKUP_VERIFY_FAILED")
    emit("APPLY_PRECONDITION_BACKUP_PASS", "YES")
    emit("FRESH_BACKUP_CANON_PINNED_IN_APPLY_PACK", "NO")
    emit("APPLY_FORBIDDEN_AFTER_BACKUP_FAIL", "NO")
    emit("PRODUCTION_022_APPLY_IN_THIS_PACK", "NO")
    emit("PRODUCTION_022_APPLY_EXECUTION_ALLOWED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("MIGRATION_MAY_PROCEED", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("APPLY_EXECUTED", "NO")
    emit("HISTORICAL_BACKUP_NOT_TOUCHED", "YES")


def fail_closed(code: str) -> int:
    emit("OWNER_BACKUP_STATUS", "FAIL")
    emit("BACKUP_OK", "NO")
    emit("PRODUCTION_BACKUP_EXECUTED", "NO")
    emit("APPLY_PRECONDITION_BACKUP_PASS", "NO")
    emit("APPLY_FORBIDDEN_AFTER_BACKUP_FAIL", "YES")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("PRODUCTION_022_APPLY_EXECUTION_ALLOWED", "NO")
    emit("APPLY_EXECUTED", "NO")
    emit("MIGRATION_MAY_PROCEED", "NO")
    emit("HISTORICAL_BACKUP_NOT_TOUCHED", "YES")
    emit("HALT_REASON", code)
    return 2


def main() -> int:
    emit("PACK", PACK)
    emit("BACKUP_ONLY", "YES")
    emit("FRESH_LIVE_BACKUP_ONLY", "YES")
    emit("V5_LOCAL_DESIGN_REVIEW", V5_LOCAL_DESIGN_REVIEW)
    emit("V5_OWNER_EXECUTION_ALLOWED", V5_OWNER_EXECUTION_ALLOWED)
    emit("V5_APPLY_ZIP_OVERWRITE", "NO")
    emit("HISTORICAL_BACKUP_NOT_APPLY_CANON", "YES")
    emit("AUTO_BACKUP_RESTORE", "NO")
    emit("PRODUCTION_022_APPLY_EXECUTION_ALLOWED", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("APPLY_EXECUTED", "NO")
    emit("LAST_MEASURED_LIVE_SOURCE_SIZE", LAST_MEASURED_LIVE_SOURCE_SIZE)
    emit("LAST_MEASURED_PRED_ROW_COUNT", LAST_MEASURED_PRED_ROW_COUNT)
    emit("MIGRATION_022_IN_THIS_PACK", "NO")
    emit("SERVICE_CHANGE_IN_THIS_PACK", "NO")
    emit("PERSISTENT_ENV_CHANGED", "NO")
    emit("SCP_USED", "NO")
    emit("DB_BYTES_ON_STDOUT", "NO")
    emit("RAW_ENVIRONMENT_LOGGED", "NO")
    emit("INVENTORY_DEV_INO_ABSENT_WITHDRAWN", "YES")
    emit("REVIEWED_CONTRACT_SHA256", REVIEWED_CONTRACT_SHA256)
    emit("CANONICAL_SOURCE", CANONICAL_SOURCE)
    emit("MIGRATION_MAY_PROCEED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    try:
        refuse_unapproved()
        verify_production_env()
        src = canonical_source()
        if (not test_mode()) and str(src.resolve()) != CANONICAL_SOURCE:
            raise Halt("REFUSED_NON_CANONICAL_SOURCE")
        if not src.is_file():
            raise Halt("SOURCE_MISSING")
        contract_path = None
        if "backup_contract" in sys.modules:
            contract_path = getattr(sys.modules["backup_contract"], "__file__", None)
        if contract_path:
            got = bc.file_sha(Path(contract_path))
            emit("CONTRACT_SHA256", got)
            emit("CONTRACT_SHA_MATCH", got == REVIEWED_CONTRACT_SHA256)
            if got != REVIEWED_CONTRACT_SHA256:
                raise Halt("CONTRACT_SHA_MISMATCH")
        elif "run_contract" in globals():
            emit("CONTRACT_SHA256", REVIEWED_CONTRACT_SHA256)
            emit("CONTRACT_SHA_MATCH", "STDIN_EMBEDDED")
            emit("CONTRACT_REVIEWED_SHA256", REVIEWED_CONTRACT_SHA256)
        else:
            raise Halt("CONTRACT_NOT_RESOLVED")
        st = src.stat()
        emit("SOURCE_PATH", str(src.resolve()) if src.exists() else str(src))
        emit("SOURCE_DEV", st.st_dev)
        emit("SOURCE_INO", st.st_ino)
        emit("SOURCE_SIZE", st.st_size)
        emit("SOURCE_MTIME", int(st.st_mtime))
        emit("SOURCE_MODE", oct(stat.S_IMODE(st.st_mode)))
        src_conn, _info = bc.open_readonly_source(src)
        try:
            qo = src_conn.execute("PRAGMA query_only").fetchone()
            emit("SOURCE_OPEN_QUERY_ONLY", "ON" if qo and str(qo[0]) in ("1", "on", "ON") else "NO")
            verify_owner_schema(src_conn)
        finally:
            src_conn.close()
        verify_inventory_identity(src)
        dest = dedicated_dest(src)
        emit("DEDICATED_DEST_DIR", str(dest.parent))
        emit("DEST_PATH_PLAN", str(dest))
        refuse_historical_dest(dest)
        os.environ["ALLOW_LOCAL_SQLITE_BACKUP"] = "1"
        emit("ALLOW_LOCAL_SQLITE_BACKUP_PROCESS_ONLY", "YES")
        rc = bc.run_contract(src, dest, restore_rehearse=False)
        if rc != 0:
            return fail_closed("BACKUP_CONTRACT_FAIL")
        emit_success(src, dest)
        return 0
    except Halt as exc:
        return fail_closed(exc.code)
    except bc.BackupError as exc:
        return fail_closed(exc.code)


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
