#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Owner backup pack tests. Never open the live Production DB."""
from __future__ import annotations

import ast
import os
import sqlite3
import stat
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "02_code"
sys.path.insert(0, str(CODE))

import backup_contract as bc  # noqa: E402
import owner_backup as ob  # noqa: E402

CANONICAL = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db"


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def seed(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(
        "CREATE TABLE schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL);"
        "CREATE TABLE predictions(id INTEGER PRIMARY KEY, race_id TEXT, created_at TEXT);"
        "INSERT INTO schema_migrations VALUES ('001_init','t');"
    )
    conn.commit()
    conn.close()


def main() -> int:
    failures: list[str] = []
    ast.parse((CODE / "owner_backup.py").read_text(encoding="utf-8"))
    ast.parse((CODE / "backup_contract.py").read_text(encoding="utf-8"))
    expect(ob.contract_sha() == ob.REVIEWED_CONTRACT_SHA256, "contract_sha_matches_reviewed_v2", failures)
    expect(ob.CANONICAL_SOURCE.as_posix() == CANONICAL, "canonical_source", failures)
    src = (CODE / "owner_backup.py").read_text(encoding="utf-8")
    expect("EXPECT_AI_ALLOW_MIGRATION_022" in src and "REFUSED_MIGRATION_022" in src, "refuses_022_flag", failures)
    expect("migrate(" not in src, "no_migrate_call", failures)
    expect("systemctl" not in src, "no_systemd", failures)
    flags = (ROOT / "FLAGS.txt").read_text(encoding="utf-8")
    expect("PRODUCTION_BACKUP_EXECUTION_ALLOWED=NO" in flags, "exec_allowed_no", failures)
    expect("PRODUCTION_BACKUP_EXECUTED=NO" in flags, "executed_no", failures)
    expect("PRODUCTION_BACKUP_EXECUTION_PACK_CREATED=YES" in flags, "pack_created", failures)
    expect("OWNER_PRODUCTION_BACKUP_APPROVED=NO" in flags, "pack_does_not_grant_approval", failures)
    expect("MIGRATION_MAY_PROCEED=NO" in flags, "pack_migration_may_proceed_no", failures)

    os.environ.pop("OWNER_PRODUCTION_BACKUP_APPROVED", None)
    os.environ.pop("ALLOW_LOCAL_SQLITE_BACKUP", None)
    rc = ob.main(["--dest-root", "/tmp/should-not-use"])
    expect(rc == 2, "refuse_without_approval", failures)

    tmp = Path(tempfile.mkdtemp(prefix="owner-bak-pack-"))
    db = tmp / "src.db"
    seed(db)
    dest_root = tmp / "backups"
    os.environ["OWNER_PRODUCTION_BACKUP_APPROVED"] = "1"
    os.environ["ALLOW_LOCAL_SQLITE_BACKUP"] = "1"
    os.environ["OWNER_BACKUP_PACK_TEST_SRC"] = "1"
    os.environ["PREDICTION_RUNS_ENABLED"] = "0"
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
    rc = ob.main(["--src", str(db), "--dest-root", str(dest_root)])
    expect(rc == 0, "local_wrapper_backup", failures)
    stamps = [p for p in dest_root.iterdir() if p.is_dir()]
    expect(len(stamps) == 1, "one_timestamp_dir", failures)
    dest = None
    if stamps:
        expect(stat.S_IMODE(stamps[0].stat().st_mode) == 0o700, "dir_0700", failures)
        dest = stamps[0] / "expect_ai.db"
        expect(dest.is_file(), "dest_file", failures)
        expect(stat.S_IMODE(dest.stat().st_mode) == 0o600, "file_0600", failures)
        if dest.is_file():
            src_st = db.stat()
            dest_st = dest.stat()
            expect((src_st.st_dev, src_st.st_ino) != (dest_st.st_dev, dest_st.st_ino), "distinct_inode", failures)

    os.environ["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    rc = ob.main(["--src", str(db), "--dest-root", str(tmp / "nope")])
    expect(rc == 2, "refuse_when_022_flag_on", failures)
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)

    os.environ["PREDICTION_RUNS_ENABLED"] = "1"
    rc = ob.main(["--src", str(db), "--dest-root", str(tmp / "nope2")])
    expect(rc == 2, "refuse_when_post_enabled", failures)
    os.environ["PREDICTION_RUNS_ENABLED"] = "0"

    os.environ.pop("OWNER_BACKUP_PACK_TEST_SRC", None)
    rc = ob.main(["--src", str(db), "--dest-root", str(tmp / "nope3")])
    expect(rc == 2, "refuse_non_canonical_without_test_override", failures)
    os.environ["OWNER_BACKUP_PACK_TEST_SRC"] = "1"

    try:
        ob.dedicated_timestamp_dir(db.parent, db)
        expect(False, "refuse_source_parent_as_dest_root", failures)
    except bc.BackupError as exc:
        expect(exc.code == "DEST_ROOT_IS_SOURCE_PARENT", "refuse_source_parent_as_dest_root", failures)

    try:
        ob.dedicated_timestamp_dir(Path("/tmp"), db)
        expect(False, "refuse_shared_dest_root", failures)
    except bc.BackupError as exc:
        expect(exc.code == "DEST_ROOT_NOT_DEDICATED", "refuse_shared_dest_root", failures)

    expect("migrate(" not in (CODE / "backup_contract.py").read_text(encoding="utf-8"), "contract_no_migrate", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
