#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local 022 APPLY payload tests. Never open live Production DB."""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS = ROOT / "02_powershell"
sys.path.insert(0, str(PS))
import owner_apply_stdin as apply  # noqa: E402

PAYLOAD = (PS / "owner_apply_stdin.py").read_bytes()
OWNER_MIGRATIONS = apply.OWNER_MIGRATIONS
OWNER_PRED_COLUMNS = apply.OWNER_PRED_COLUMNS


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def seed_owner_schema(path: Path, extra_col: str | None = None, persist_022: bool = False, rows: int = 1) -> None:
    conn = sqlite3.connect(str(path))
    cols = ", ".join("%s TEXT" % c if c != "id" else "id INTEGER PRIMARY KEY" for c in OWNER_PRED_COLUMNS)
    conn.execute("CREATE TABLE schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE predictions(%s)" % cols)
    conn.execute("CREATE INDEX idx_predictions_race ON predictions(race_id, created_at)")
    for ver in OWNER_MIGRATIONS:
        conn.execute("INSERT INTO schema_migrations VALUES (?, 't')", (ver,))
    if extra_col:
        conn.execute("ALTER TABLE predictions ADD COLUMN %s TEXT" % extra_col)
    if persist_022:
        conn.execute("INSERT INTO schema_migrations VALUES (?, 't')", (apply.PERSIST_022,))
    for i in range(rows):
        conn.execute("INSERT INTO predictions(race_id, created_at) VALUES (?, 't')", ("local-%d" % i,))
    conn.commit()
    conn.close()


def env_ok() -> dict[str, str]:
    return {
        "OWNER_APPLY_TEST_ENV": "1",
        "OWNER_APPLY_TEST_SYSTEMD_OK": "1",
        "OWNER_APPLY_TEST_PROC_OK": "1",
        "OWNER_APPLY_TEST_FILES_OK": "1",
        "OWNER_APPLY_TEST_SYSTEMD_SHOW": (
            "Id=expect-ai.service\nLoadState=loaded\nMainPID=1\nEnvironment=\nEnvironmentFiles=\nActiveState=active\n"
        ),
        "OWNER_APPLY_TEST_PROC_ENVIRON": "",
        "OWNER_APPLY_TEST_ENVFILE": "",
    }


def capture_main(env: dict[str, str]) -> tuple[int, str]:
    full = os.environ.copy()
    for k in (
        "OWNER_PRODUCTION_022_APPLY_APPROVED",
        "OWNER_APPLY_PACK_TEST",
        "OWNER_APPLY_TEST_SRC",
        "OWNER_APPLY_TEST_BACKUP",
        "OWNER_APPLY_TEST_SOURCE_DEV",
        "OWNER_APPLY_TEST_SOURCE_INO",
        "OWNER_APPLY_TEST_BACKUP_DEV",
        "OWNER_APPLY_TEST_BACKUP_INO",
        "OWNER_APPLY_TEST_BACKUP_SHA",
        "EXPECT_AI_ALLOW_MIGRATION_022",
        "EXPECT_AI_ALLOW_MIGRATION_019",
        "PREDICTION_RUNS_ENABLED",
        "OWNER_APPLY_TEST_ENV",
        "OWNER_APPLY_TEST_SYSTEMD_SHOW",
        "OWNER_APPLY_TEST_PROC_ENVIRON",
        "OWNER_APPLY_TEST_ENVFILE",
        "OWNER_APPLY_TEST_SYSTEMD_OK",
        "OWNER_APPLY_TEST_PROC_OK",
        "OWNER_APPLY_TEST_FILES_OK",
    ):
        full.pop(k, None)
    full.update(env)
    full["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run([sys.executable, "-"], input=PAYLOAD, capture_output=True, env=full)
    out = (p.stdout or b"").decode("utf-8", errors="replace")
    err = (p.stderr or b"").decode("utf-8", errors="replace")
    if "SyntaxError" in err:
        print("STDERR=" + err)
    return int(p.returncode), out


def main() -> int:
    failures: list[str] = []
    expect(apply.INVENTORY_SOURCE_DEV == 66305 and apply.INVENTORY_SOURCE_INO == 349935, "inventory_embedded", failures)
    expect(apply.BACKUP_SHA256 == "f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d", "backup_sha_canon", failures)
    expect(len(OWNER_MIGRATIONS) == 22, "owner_22", failures)

    rc, out = capture_main({})
    expect(rc == 2, "refuse_unapproved", failures)
    expect("HALT_REASON=OWNER_PRODUCTION_022_APPLY_APPROVED_UNSET" in out, "halt_unapproved", failures)

    tmp = Path(tempfile.mkdtemp(prefix="apply022-"))
    src = tmp / "src.db"
    bak = tmp / "bak.db"
    seed_owner_schema(src)
    shutil.copy2(src, bak)
    sst = src.stat()
    bst = bak.stat()
    bsha = apply.file_sha(bak)
    base = {
        "OWNER_PRODUCTION_022_APPLY_APPROVED": "1",
        "OWNER_APPLY_PACK_TEST": "1",
        "OWNER_APPLY_TEST_SRC": str(src),
        "OWNER_APPLY_TEST_BACKUP": str(bak),
        "OWNER_APPLY_TEST_SOURCE_DEV": str(sst.st_dev),
        "OWNER_APPLY_TEST_SOURCE_INO": str(sst.st_ino),
        "OWNER_APPLY_TEST_BACKUP_DEV": str(bst.st_dev),
        "OWNER_APPLY_TEST_BACKUP_INO": str(bst.st_ino),
        "OWNER_APPLY_TEST_BACKUP_SHA": bsha,
    }
    base.update(env_ok())

    drift = dict(base)
    drift.pop("OWNER_APPLY_TEST_SOURCE_DEV", None)
    drift.pop("OWNER_APPLY_TEST_SOURCE_INO", None)
    rc, out = capture_main(drift)
    expect(rc == 2, "drift_halts", failures)
    expect("HALT_REASON=DB_DRIFT" in out, "halt_db_drift", failures)

    post = dict(base)
    post["OWNER_APPLY_TEST_PROC_ENVIRON"] = "PREDICTION_RUNS_ENABLED=1"
    rc, out = capture_main(post)
    expect(rc == 2, "post_flag_halts", failures)
    expect("HALT_REASON=PREDICTION_RUNS_ENABLED_EFFECTIVE_1" in out, "halt_post", failures)

    flag022 = dict(base)
    flag022["OWNER_APPLY_TEST_PROC_ENVIRON"] = "EXPECT_AI_ALLOW_MIGRATION_022=1"
    rc, out = capture_main(flag022)
    expect(rc == 2, "prod_022_effective_halts", failures)
    expect("HALT_REASON=EXPECT_AI_ALLOW_MIGRATION_022_EFFECTIVE_1" in out, "halt_prod_022", failures)

    already = tmp / "already.db"
    seed_owner_schema(already, extra_col="idempotency_key")
    ast = already.stat()
    extra = dict(base)
    extra["OWNER_APPLY_TEST_SRC"] = str(already)
    extra["OWNER_APPLY_TEST_SOURCE_DEV"] = str(ast.st_dev)
    extra["OWNER_APPLY_TEST_SOURCE_INO"] = str(ast.st_ino)
    rc, out = capture_main(extra)
    expect(rc == 2, "already_applied_halts", failures)
    expect("HALT_REASON=ALREADY_APPLIED_OR_PARTIAL" in out, "halt_already", failures)

    badsha = dict(base)
    badsha["OWNER_APPLY_TEST_BACKUP_SHA"] = "0" * 64
    rc, out = capture_main(badsha)
    expect(rc == 2, "backup_sha_halts", failures)
    expect("HALT_REASON=BACKUP_SHA_MISMATCH" in out, "halt_backup_sha", failures)

    win = dict(base)
    win["PREDICTION_RUNS_ENABLED"] = "1"
    win["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    rc, out = capture_main(win)
    expect(rc == 0, "windows_env_ignored", failures)
    expect("OWNER_APPLY_STATUS=SUCCESS" in out, "windows_env_success", failures)
    expect("APPLY_EXECUTED=NO" in out, "local_not_prod_executed", failures)
    expect("POST_REMAINS_DISABLED=YES" in out, "post_still_disabled", failures)
    expect("PROCESS_022_WINDOW=CLOSED" in out, "process_window_closed", failures)
    expect("PREDICTION_RUNS_ENABLED_EFFECTIVE=0" in out, "post_effective_0", failures)
    expect("HAS_PERSIST_022=YES" in out, "persist_022_recorded", failures)
    expect("PRODUCTION_APPLY_READY=NO" in out, "apply_ready_stays_no", failures)
    conn = sqlite3.connect(str(src))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(predictions)")]
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations")]
    rows = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    nulls = conn.execute("SELECT COUNT(*) FROM predictions WHERE idempotency_key IS NULL").fetchone()[0]
    conn.close()
    expect(cols == list(OWNER_PRED_COLUMNS) + list(apply.NEW_COLS), "columns_after", failures)
    expect(apply.PERSIST_022 in versions, "migration_row", failures)
    expect(len(set(versions)) == 23, "twenty_three_versions", failures)
    expect(rows == 1 and nulls == 1, "existing_row_null_new_cols", failures)
    expect(bak.read_bytes() != src.read_bytes(), "source_changed_backup_untouched_bytes", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
