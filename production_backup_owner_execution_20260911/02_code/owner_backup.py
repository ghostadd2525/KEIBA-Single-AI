#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Owner Production backup wrapper. Backup only. No 022 apply. No service change.

Do not run until Owner sets OWNER_PRODUCTION_BACKUP_APPROVED=1.
This pack never sets that flag.
"""
from __future__ import annotations

import argparse
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))

import backup_contract as bc  # noqa: E402

PACK = "production_backup_owner_execution_20260911"
CANONICAL_SOURCE = Path(
    "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db"
)
REVIEWED_CONTRACT_SHA256 = (
    "55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e"
)
REVIEWED_BACKUP_V2_ZIP_SHA256 = (
    "9653f26224679d750ea1c3f578a0b8dda0e2178dab5b8ad464ee8cf9a42b9a5a"
)


def contract_sha() -> str:
    return bc.file_sha(CODE / "backup_contract.py")


def refuse_if_unapproved() -> None:
    if (os.environ.get("OWNER_PRODUCTION_BACKUP_APPROVED") or "").strip() != "1":
        raise bc.BackupError("REFUSED_OWNER_PRODUCTION_BACKUP_APPROVED_UNSET")
    if (os.environ.get("ALLOW_LOCAL_SQLITE_BACKUP") or "").strip() != "1":
        raise bc.BackupError("REFUSED_ALLOW_LOCAL_SQLITE_BACKUP_UNSET")


def refuse_side_effects() -> None:
    if (os.environ.get("EXPECT_AI_ALLOW_MIGRATION_022") or "").strip() in ("1", "true", "yes"):
        raise bc.BackupError("REFUSED_MIGRATION_022_FLAG_SET_DURING_BACKUP")
    if (os.environ.get("PREDICTION_RUNS_ENABLED") or "").strip() in ("1", "true", "yes"):
        raise bc.BackupError("REFUSED_PREDICTION_RUNS_ENABLED_DURING_BACKUP")


def dedicated_timestamp_dir(dest_root: Path, source: Path) -> Path:
    dest_root = Path(os.path.abspath(str(dest_root)))
    src_abs = Path(os.path.abspath(str(source)))
    src_parent = src_abs.parent
    dest_cmp = dest_root.resolve() if dest_root.exists() else dest_root
    if dest_cmp in bc.SHARED_DEST_DIRS or dest_root in bc.SHARED_DEST_DIRS:
        raise bc.BackupError("DEST_ROOT_NOT_DEDICATED")
    if dest_root == src_parent or dest_root == src_abs or dest_cmp == src_parent or dest_cmp == src_abs:
        raise bc.BackupError("DEST_ROOT_IS_SOURCE_PARENT")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dedicated = dest_root / stamp
    return dedicated


def dest_file(dedicated_dir: Path) -> Path:
    return dedicated_dir / "expect_ai.db"


def emit_owner_success_gates(src: Path, dest: Path) -> None:
    """Owner-pack gates after the reviewed v2 contract returns 0.

    File-byte SHA equality is not required (sqlite backup may rewrite pages).
    Canonical sqlite_master SHA + migration set + integrity + distinct inode are.
    v2 contract itself always emits MIGRATION_MAY_PROCEED=NO; this wrapper
    records APPLY_PRECONDITION_BACKUP_PASS without authorizing 022 APPLY.
    """
    dir_mode = stat.S_IMODE(dest.parent.stat().st_mode)
    file_mode = stat.S_IMODE(dest.stat().st_mode)
    if dir_mode != 0o700:
        raise bc.BackupError("PERMISSION_MISMATCH_DEST_DIR", oct(dir_mode))
    if file_mode != 0o600:
        raise bc.BackupError("PERMISSION_MISMATCH_DEST_FILE", oct(file_mode))
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
    bc.emit("OWNER_BACKUP_STATUS", "SUCCESS" if integrity_ok and schema_ok and distinct else "FAIL")
    bc.emit("BACKUP_INTEGRITY_OK", integrity_ok)
    bc.emit("BACKUP_SCHEMA_OK", schema_ok)
    bc.emit("BACKUP_MIGRATION_SET_OK", migration_ok)
    bc.emit("BACKUP_MASTER_SHA_MATCH", master_ok)
    bc.emit("BACKUP_DEST_SHA256", dest_sha)
    bc.emit("BACKUP_SHA256_RECORDED", bool(dest_sha))
    bc.emit("BACKUP_DISTINCT_INODE", distinct)
    bc.emit("BACKUP_DIR_MODE", oct(dir_mode))
    bc.emit("BACKUP_FILE_MODE", oct(file_mode))
    passed = integrity_ok and schema_ok and migration_ok and master_ok and distinct
    if not passed:
        raise bc.BackupError("OWNER_POST_BACKUP_VERIFY_FAILED")
    bc.emit("APPLY_PRECONDITION_BACKUP_PASS", "YES")
    bc.emit("APPLY_FORBIDDEN_AFTER_BACKUP_FAIL", "NO")
    bc.emit("PRODUCTION_022_APPLY_IN_THIS_PACK", "NO")
    bc.emit("PRODUCTION_APPLY_READY", "NO")
    bc.emit("OWNER_APPLY_APPROVED", "NO")
    bc.emit("MIGRATION_MAY_PROCEED", "NO")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Owner Production backup (backup only)")
    parser.add_argument("--dest-root", required=True, help="parent for a new 0700 timestamp directory")
    parser.add_argument(
        "--src",
        default=str(CANONICAL_SOURCE),
        help="must remain the Owner-inventory Production path unless local test override",
    )
    args = parser.parse_args(argv)
    bc.emit("PACK", PACK)
    bc.emit("REVIEWED_BACKUP_V2_ZIP_SHA256", REVIEWED_BACKUP_V2_ZIP_SHA256)
    bc.emit("REVIEWED_CONTRACT_SHA256", REVIEWED_CONTRACT_SHA256)
    bc.emit("CONTRACT_SHA256", contract_sha())
    bc.emit("CONTRACT_SHA_MATCH", contract_sha() == REVIEWED_CONTRACT_SHA256)
    bc.emit("BACKUP_ONLY", "YES")
    bc.emit("MIGRATION_022_IN_THIS_PACK", "NO")
    bc.emit("SERVICE_CHANGE_IN_THIS_PACK", "NO")
    bc.emit("MIGRATION_MAY_PROCEED", "NO")
    try:
        if contract_sha() != REVIEWED_CONTRACT_SHA256:
            raise bc.BackupError("CONTRACT_SHA_MISMATCH")
        refuse_if_unapproved()
        refuse_side_effects()
        src = Path(args.src)
        if src.resolve() != CANONICAL_SOURCE and not (
            (os.environ.get("OWNER_BACKUP_PACK_TEST_SRC") or "").strip() == "1"
        ):
            if str(src.resolve()) != str(CANONICAL_SOURCE):
                raise bc.BackupError("REFUSED_NON_CANONICAL_SOURCE")
        dedicated = dedicated_timestamp_dir(Path(args.dest_root), src)
        dest = dest_file(dedicated)
        bc.emit("CANONICAL_SOURCE", str(CANONICAL_SOURCE))
        bc.emit("DEDICATED_DEST_DIR", str(dedicated))
        bc.emit("DEST_PATH_PLAN", str(dest))
        rc = bc.run_contract(src, dest, restore_rehearse=False)
        if rc != 0:
            bc.emit("OWNER_BACKUP_STATUS", "FAIL")
            bc.emit("APPLY_PRECONDITION_BACKUP_PASS", "NO")
            bc.emit("MIGRATION_MAY_PROCEED", "NO")
            bc.emit("APPLY_FORBIDDEN_AFTER_BACKUP_FAIL", "YES")
            bc.emit("PRODUCTION_APPLY_READY", "NO")
            return rc
        emit_owner_success_gates(src, dest)
        return 0
    except bc.BackupError as exc:
        bc.emit("BACKUP_OK", "NO")
        bc.emit("OWNER_BACKUP_STATUS", "FAIL")
        bc.emit("MIGRATION_MAY_PROCEED", "NO")
        bc.emit("PRODUCTION_BACKUP_EXECUTED", "NO")
        bc.emit("APPLY_PRECONDITION_BACKUP_PASS", "NO")
        bc.emit("APPLY_FORBIDDEN_AFTER_BACKUP_FAIL", "YES")
        bc.emit("PRODUCTION_APPLY_READY", "NO")
        bc.emit("FAIL_REASON", exc.code)
        return 2


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
