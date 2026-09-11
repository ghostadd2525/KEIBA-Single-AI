#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local tests for stdin remote backup payload. Never open live Production DB."""
from __future__ import annotations

import io
import os
import sqlite3
import stat
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS = ROOT / "02_powershell"
sys.path.insert(0, str(PS))

import owner_backup_remote as remote  # noqa: E402

OWNER_MIGRATIONS = remote.OWNER_MIGRATIONS
OWNER_PRED_COLUMNS = remote.OWNER_PRED_COLUMNS


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def seed_owner_schema(path: Path, extra_col: str | None = None, persist_022: bool = False) -> None:
    conn = sqlite3.connect(str(path))
    cols = ", ".join("%s TEXT" % c if c != "id" else "id INTEGER PRIMARY KEY" for c in OWNER_PRED_COLUMNS)
    conn.execute("CREATE TABLE schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE predictions(%s)" % cols)
    if extra_col:
        conn.execute("ALTER TABLE predictions ADD COLUMN %s TEXT" % extra_col)
    conn.execute(
        "CREATE INDEX idx_predictions_race ON predictions(race_id, created_at)"
    )
    for ver in OWNER_MIGRATIONS:
        conn.execute("INSERT INTO schema_migrations VALUES (?, 't')", (ver,))
    if persist_022:
        conn.execute("INSERT INTO schema_migrations VALUES (?, 't')", (remote.PERSIST_022,))
    conn.commit()
    conn.close()


CLEAR_KEYS = (
    "OWNER_PRODUCTION_BACKUP_APPROVED",
    "ALLOW_LOCAL_SQLITE_BACKUP",
    "OWNER_BACKUP_PACK_TEST_SRC",
    "OWNER_BACKUP_TEST_SRC",
    "OWNER_BACKUP_TEST_DEST_ROOT",
    "OWNER_BACKUP_TEST_INVENTORY_DEV",
    "OWNER_BACKUP_TEST_INVENTORY_INO",
    "EXPECT_AI_ALLOW_MIGRATION_022",
    "EXPECT_AI_ALLOW_MIGRATION_019",
    "PREDICTION_RUNS_ENABLED",
)


def capture_main(env: dict[str, str]) -> tuple[int, str]:
    old = {}
    merged = {k: None for k in CLEAR_KEYS}
    merged.update(env)
    for k, v in merged.items():
        old[k] = os.environ.get(k)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = remote.main()
    finally:
        for k, prev in old.items():
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev
    return rc, buf.getvalue()


def main() -> int:
    failures: list[str] = []
    expect(remote.REVIEWED_CONTRACT_SHA256 == "55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e", "contract_sha_constant", failures)
    expect(remote.INVENTORY_SOURCE_DEV is None and remote.INVENTORY_SOURCE_INO is None, "inventory_dev_ino_not_invented", failures)
    expect(len(OWNER_MIGRATIONS) == 22, "owner_22", failures)
    expect("019_prediction_run_idempotency" not in OWNER_MIGRATIONS, "no_persist_019_in_canon", failures)
    expect("022_prediction_run_idempotency" not in OWNER_MIGRATIONS, "no_persist_022_in_canon", failures)

    os.environ.pop("OWNER_PRODUCTION_BACKUP_APPROVED", None)
    os.environ.pop("OWNER_BACKUP_PACK_TEST_SRC", None)
    rc, out = capture_main({})
    expect(rc == 2, "refuse_unapproved", failures)
    expect("HALT_REASON=OWNER_PRODUCTION_BACKUP_APPROVED_UNSET" in out, "halt_unapproved", failures)
    expect("APPLY_PRECONDITION_BACKUP_PASS=NO" in out, "unapproved_no_apply_precondition", failures)

    tmp = Path(tempfile.mkdtemp(prefix="bakv2-remote-"))
    db = tmp / "src.db"
    seed_owner_schema(db)
    dest_root = tmp / "backups"
    st = db.stat()
    base = {
        "OWNER_PRODUCTION_BACKUP_APPROVED": "1",
        "ALLOW_LOCAL_SQLITE_BACKUP": "1",
        "OWNER_BACKUP_PACK_TEST_SRC": "1",
        "OWNER_BACKUP_TEST_SRC": str(db),
        "OWNER_BACKUP_TEST_DEST_ROOT": str(dest_root),
        "PREDICTION_RUNS_ENABLED": "0",
    }

    rc, out = capture_main(base)
    expect(rc == 2, "absent_inventory_identity_halts", failures)
    expect("HALT_REASON=INVENTORY_DEV_INO_ABSENT" in out, "halt_identity_absent", failures)
    expect("NEW_READONLY_INVENTORY_REQUIRED=YES" in out, "asks_new_inventory", failures)
    expect("SOURCE_SCHEMA_GATE=PASS" in out, "schema_checked_before_identity_halt", failures)
    expect(not dest_root.exists() or not any(dest_root.rglob("expect_ai.db")), "no_backup_when_identity_absent", failures)

    drift = dict(base)
    drift["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(st.st_dev)
    drift["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(st.st_ino + 99999)
    rc, out = capture_main(drift)
    expect(rc == 2, "drift_halts", failures)
    expect("HALT_REASON=DB_DRIFT" in out, "halt_db_drift", failures)
    expect("DB_DRIFT=YES" in out, "drift_flag", failures)

    bad_schema = tmp / "bad.db"
    seed_owner_schema(bad_schema, extra_col="idempotency_key")
    bst = bad_schema.stat()
    extra = dict(base)
    extra["OWNER_BACKUP_TEST_SRC"] = str(bad_schema)
    extra["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(bst.st_dev)
    extra["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(bst.st_ino)
    rc, out = capture_main(extra)
    expect(rc == 2, "extra_col_halts", failures)
    expect("HALT_REASON=NEW_PERSIST_COLUMNS_PRESENT" in out, "halt_new_cols", failures)

    persist = tmp / "p022.db"
    seed_owner_schema(persist, persist_022=True)
    pst = persist.stat()
    p022 = dict(base)
    p022["OWNER_BACKUP_TEST_SRC"] = str(persist)
    p022["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(pst.st_dev)
    p022["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(pst.st_ino)
    rc, out = capture_main(p022)
    expect(rc == 2, "persist_022_halts", failures)
    expect("HALT_REASON=HAS_PERSIST_022" in out, "halt_has_022", failures)

    flagged = dict(base)
    flagged["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    flagged["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(st.st_dev)
    flagged["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(st.st_ino)
    rc, out = capture_main(flagged)
    expect(rc == 2, "022_flag_halts", failures)
    expect("HALT_REASON=EXPECT_AI_ALLOW_MIGRATION_022_SET" in out, "halt_022_flag", failures)

    post = dict(base)
    post["PREDICTION_RUNS_ENABLED"] = "1"
    post["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(st.st_dev)
    post["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(st.st_ino)
    rc, out = capture_main(post)
    expect(rc == 2, "post_flag_halts", failures)
    expect("HALT_REASON=PREDICTION_RUNS_ENABLED" in out, "halt_post", failures)

    ok = dict(base)
    ok["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(st.st_dev)
    ok["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(st.st_ino)
    rc, out = capture_main(ok)
    expect(rc == 0, "local_backup_success", failures)
    expect("OWNER_BACKUP_STATUS=SUCCESS" in out, "success_status", failures)
    expect("BACKUP_INTEGRITY_OK=YES" in out, "success_integrity", failures)
    expect("BACKUP_SCHEMA_OK=YES" in out, "success_schema", failures)
    expect("BACKUP_MIGRATION_SET_OK=YES" in out, "success_migrations", failures)
    expect("BACKUP_MASTER_SHA_MATCH=YES" in out, "success_master", failures)
    expect("BACKUP_SHA256_RECORDED=YES" in out, "success_sha", failures)
    expect("BACKUP_DISTINCT_INODE=YES" in out, "success_inode", failures)
    expect("BACKUP_DIR_MODE=0o700" in out, "success_dir_mode", failures)
    expect("BACKUP_FILE_MODE=0o600" in out, "success_file_mode", failures)
    expect("APPLY_PRECONDITION_BACKUP_PASS=YES" in out, "success_precondition", failures)
    expect("PRODUCTION_APPLY_READY=NO" in out, "success_apply_ready_no", failures)
    expect("MIGRATION_MAY_PROCEED=NO" in out, "success_may_proceed_no", failures)
    expect("PRODUCTION_BACKUP_EXECUTED=NO" in out, "local_not_counted_as_prod_executed", failures)
    expect("migrate(" not in (PS / "owner_backup_remote.py").read_text(encoding="utf-8"), "remote_no_migrate", failures)
    stamps = list(dest_root.glob("*/expect_ai.db")) if dest_root.exists() else []
    expect(len(stamps) == 1, "one_dest", failures)
    if stamps:
        expect(stat.S_IMODE(stamps[0].parent.stat().st_mode) == 0o700, "dest_dir_0700", failures)
        expect(stat.S_IMODE(stamps[0].stat().st_mode) == 0o600, "dest_file_0600", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
