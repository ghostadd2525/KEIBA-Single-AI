#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local tests for stdin remote backup payload. Never open live Production DB."""
from __future__ import annotations

import os
import sqlite3
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS = ROOT / "02_powershell"
sys.path.insert(0, str(PS))

import owner_backup_remote as remote  # noqa: E402
PAYLOAD = (PS / "owner_backup_stdin.py").read_bytes()

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
    "OWNER_BACKUP_TEST_ENV",
    "OWNER_BACKUP_TEST_SYSTEMD_SHOW",
    "OWNER_BACKUP_TEST_PROC_ENVIRON",
    "OWNER_BACKUP_TEST_ENVFILE",
    "OWNER_BACKUP_TEST_SYSTEMD_OK",
    "OWNER_BACKUP_TEST_PROC_OK",
    "OWNER_BACKUP_TEST_FILES_OK",
)


def env_determined_off() -> dict[str, str]:
    return {
        "OWNER_BACKUP_TEST_ENV": "1",
        "OWNER_BACKUP_TEST_SYSTEMD_OK": "1",
        "OWNER_BACKUP_TEST_PROC_OK": "1",
        "OWNER_BACKUP_TEST_FILES_OK": "1",
        "OWNER_BACKUP_TEST_SYSTEMD_SHOW": (
            "Id=expect-ai.service\nLoadState=loaded\nMainPID=1\nEnvironment=\nEnvironmentFiles=\nActiveState=active\n"
        ),
        "OWNER_BACKUP_TEST_PROC_ENVIRON": "",
        "OWNER_BACKUP_TEST_ENVFILE": "",
    }


def capture_main(env: dict[str, str]) -> tuple[int, str]:
    full = os.environ.copy()
    for k in CLEAR_KEYS:
        full.pop(k, None)
    for k, v in env.items():
        if v is None:
            full.pop(k, None)
        else:
            full[k] = v
    full["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run([sys.executable, "-"], input=PAYLOAD, capture_output=True, env=full)
    out = (p.stdout or b"").decode("utf-8", errors="replace")
    err = (p.stderr or b"").decode("utf-8", errors="replace")
    if "SyntaxError" in err:
        print("STDERR=" + err)
    return int(p.returncode), out


def main() -> int:
    failures: list[str] = []
    expect(remote.REVIEWED_CONTRACT_SHA256 == "55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e", "contract_sha_constant", failures)
    expect(remote.INVENTORY_SOURCE_DEV == 66305 and remote.INVENTORY_SOURCE_INO == 349935, "inventory_dev_ino_embedded", failures)
    remote_src = (PS / "owner_backup_remote.py").read_text(encoding="utf-8")
    expect("INVENTORY_DEV_INO_ABSENT_WITHDRAWN" in remote_src, "withdraw_absent_constant", failures)
    expect("def flag_on(" not in remote_src, "no_login_shell_flag_helper", failures)
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
    }
    base.update(env_determined_off())

    rc, out = capture_main(base)
    expect(rc == 2, "canon_identity_mismatches_temp_db", failures)
    expect("HALT_REASON=DB_DRIFT" in out, "embedded_identity_drift_on_temp", failures)
    expect("INVENTORY_SOURCE_DEV=66305" in out, "emits_embedded_dev", failures)
    expect("INVENTORY_SOURCE_INO=349935" in out, "emits_embedded_ino", failures)
    expect("INVENTORY_DEV_INO_ABSENT=NO" in out, "absent_withdrawn", failures)
    expect("SOURCE_SCHEMA_GATE=PASS" in out, "schema_checked_before_identity_halt", failures)
    expect(not dest_root.exists() or not any(dest_root.rglob("expect_ai.db")), "no_backup_on_drift", failures)

    undetermined = dict(base)
    undetermined["OWNER_BACKUP_TEST_SYSTEMD_OK"] = "0"
    undetermined["OWNER_BACKUP_TEST_PROC_OK"] = "0"
    undetermined["OWNER_BACKUP_TEST_FILES_OK"] = "0"
    undetermined["OWNER_BACKUP_TEST_SYSTEMD_SHOW"] = ""
    rc, out = capture_main(undetermined)
    expect(rc == 2, "undetermined_env_halts", failures)
    expect("HALT_REASON=PRODUCTION_ENV_UNDETERMINED" in out, "halt_env_undetermined", failures)

    notfound = dict(base)
    notfound["OWNER_BACKUP_TEST_SYSTEMD_SHOW"] = (
        "Id=expect-ai.service\nLoadState=not-found\nMainPID=0\nEnvironment=\nEnvironmentFiles=\nActiveState=inactive\n"
    )
    rc, out = capture_main(notfound)
    expect(rc == 2, "notfound_unit_halts", failures)
    expect("HALT_REASON=PRODUCTION_ENV_UNDETERMINED" in out, "halt_unit_not_loaded", failures)

    unread_proc = dict(base)
    unread_proc["OWNER_BACKUP_TEST_PROC_OK"] = "0"
    rc, out = capture_main(unread_proc)
    expect(rc == 2, "unread_proc_halts", failures)
    expect("HALT_REASON=PRODUCTION_ENV_UNDETERMINED" in out, "halt_proc_unread", failures)

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
    flagged["OWNER_BACKUP_TEST_PROC_ENVIRON"] = "EXPECT_AI_ALLOW_MIGRATION_022=1"
    flagged["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(st.st_dev)
    flagged["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(st.st_ino)
    rc, out = capture_main(flagged)
    expect(rc == 2, "022_flag_halts", failures)
    expect("HALT_REASON=EXPECT_AI_ALLOW_MIGRATION_022_EFFECTIVE_1" in out, "halt_022_flag", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_022_EFFECTIVE=1" in out, "022_effective_1", failures)
    expect("Environment=" not in out.split("HALT_REASON")[0] or "RAW_ENVIRONMENT_LOGGED=NO" in out, "no_raw_environment", failures)

    post = dict(base)
    post["OWNER_BACKUP_TEST_PROC_ENVIRON"] = "PREDICTION_RUNS_ENABLED=1"
    post["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(st.st_dev)
    post["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(st.st_ino)
    rc, out = capture_main(post)
    expect(rc == 2, "post_flag_halts", failures)
    expect("HALT_REASON=PREDICTION_RUNS_ENABLED_EFFECTIVE_1" in out, "halt_post", failures)

    mig019 = dict(base)
    mig019["OWNER_BACKUP_TEST_PROC_ENVIRON"] = "EXPECT_AI_ALLOW_MIGRATION_019=1"
    mig019["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(st.st_dev)
    mig019["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(st.st_ino)
    rc, out = capture_main(mig019)
    expect(rc == 2, "019_flag_halts", failures)
    expect("HALT_REASON=EXPECT_AI_ALLOW_MIGRATION_019_EFFECTIVE_1" in out, "halt_019_flag", failures)

    sd022 = dict(base)
    sd022["OWNER_BACKUP_TEST_SYSTEMD_SHOW"] = (
        "Id=expect-ai.service\nLoadState=loaded\nMainPID=1\n"
        "Environment=EXPECT_AI_ALLOW_MIGRATION_022=1\nEnvironmentFiles=\nActiveState=active\n"
    )
    sd022["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(st.st_dev)
    sd022["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(st.st_ino)
    rc, out = capture_main(sd022)
    expect(rc == 2, "systemd_022_halts", failures)
    expect("HALT_REASON=EXPECT_AI_ALLOW_MIGRATION_022_EFFECTIVE_1" in out, "halt_systemd_022", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_022_SOURCE=SYSTEMD_ENVIRONMENT" in out, "022_source_systemd", failures)
    expect("Environment=EXPECT_AI_ALLOW_MIGRATION_022=1" not in out, "no_raw_systemd_environment_line", failures)

    file022 = dict(base)
    file022["OWNER_BACKUP_TEST_ENVFILE"] = "EXPECT_AI_ALLOW_MIGRATION_022=1"
    file022["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(st.st_dev)
    file022["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(st.st_ino)
    rc, out = capture_main(file022)
    expect(rc == 2, "envfile_022_halts", failures)
    expect("HALT_REASON=EXPECT_AI_ALLOW_MIGRATION_022_EFFECTIVE_1" in out, "halt_envfile_022", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_022_SOURCE=ENVIRONMENT_FILE" in out, "022_source_envfile", failures)

    win = dict(base)
    win["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    win["EXPECT_AI_ALLOW_MIGRATION_019"] = "1"
    win["PREDICTION_RUNS_ENABLED"] = "1"
    win["OWNER_BACKUP_TEST_DEST_ROOT"] = str(tmp / "backups-windows-ignored")
    win["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(st.st_dev)
    win["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(st.st_ino)
    rc, out = capture_main(win)
    expect(rc == 0, "windows_login_env_ignored", failures)
    expect("PREDICTION_RUNS_ENABLED_SET=UNSET" in out, "windows_post_not_prod", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_022_SET=UNSET" in out, "windows_022_not_prod", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_019_SET=UNSET" in out, "windows_019_not_prod", failures)
    expect("OWNER_BACKUP_STATUS=SUCCESS" in out, "windows_env_still_success", failures)

    ok = dict(base)
    ok["OWNER_BACKUP_TEST_INVENTORY_DEV"] = str(st.st_dev)
    ok["OWNER_BACKUP_TEST_INVENTORY_INO"] = str(st.st_ino)
    rc, out = capture_main(ok)
    expect(rc == 0, "local_backup_success", failures)
    expect("OWNER_BACKUP_STATUS=SUCCESS" in out, "success_status", failures)
    expect("CONTRACT_SHA_MATCH=STDIN_EMBEDDED" in out, "success_contract_embedded", failures)
    expect("PACK=production_backup_owner_execution_v4_20260911" in out, "success_pack_v4", failures)
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
