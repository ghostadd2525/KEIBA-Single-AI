#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local 022 APPLY v2 payload tests. Never open live Production DB."""
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
NEW_COLS = apply.NEW_COLS


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


def schema_snapshot(path: Path) -> tuple[list[str], list[str], int]:
    conn = sqlite3.connect(str(path))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(predictions)")]
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations")]
    rows = int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
    conn.close()
    return cols, versions, rows


def env_ok() -> dict[str, str]:
    return {
        "OWNER_APPLY_TEST_ENV": "1",
        "OWNER_APPLY_TEST_SYSTEMD_OK": "1",
        "OWNER_APPLY_TEST_PROC_OK": "1",
        "OWNER_APPLY_TEST_FILES_OK": "1",
        "OWNER_APPLY_TEST_HTTP": "1",
        "OWNER_APPLY_TEST_SYSTEMD_SHOW": (
            "Id=expect-ai.service\nLoadState=loaded\nMainPID=1\nEnvironment=\nEnvironmentFiles=\nActiveState=active\n"
        ),
        "OWNER_APPLY_TEST_PROC_ENVIRON": "",
        "OWNER_APPLY_TEST_ENVFILE": "",
        "OWNER_APPLY_TEST_HEALTH_JSON": '{"status":"ok","db":"test","fallback_reasons":[],"result_automation":{}}',
        "OWNER_APPLY_TEST_GET_JSON": '{"ok":true,"data":[],"meta":{"count":0}}',
    }


def capture_main(env: dict[str, str]) -> tuple[int, str]:
    full = os.environ.copy()
    for k in list(full):
        if k.startswith("OWNER_APPLY_") or k in (
            "OWNER_PRODUCTION_022_APPLY_APPROVED",
            "EXPECT_AI_ALLOW_MIGRATION_022",
            "EXPECT_AI_ALLOW_MIGRATION_019",
            "PREDICTION_RUNS_ENABLED",
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


def last_kv(out: str, key: str) -> str | None:
    found = None
    prefix = key + "="
    for line in out.splitlines():
        if line.startswith(prefix):
            found = line[len(prefix):]
    return found


def main() -> int:
    failures: list[str] = []
    expect(apply.INVENTORY_SOURCE_DEV == 66305 and apply.INVENTORY_SOURCE_INO == 349935, "inventory_embedded", failures)
    expect(apply.BACKUP_SHA256 == "f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d", "backup_sha_canon", failures)
    expect(len(OWNER_MIGRATIONS) == 22, "owner_22", failures)

    rc, out = capture_main({})
    expect(rc == 2, "refuse_unapproved", failures)
    expect("HALT_REASON=OWNER_PRODUCTION_022_APPLY_APPROVED_UNSET" in out, "halt_unapproved", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "NO", "unapproved_executed_no", failures)
    expect("AUDIT_CLOSED=YES" in out, "unapproved_audit_closed", failures)

    tmp = Path(tempfile.mkdtemp(prefix="apply022v2-"))
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
    expect(last_kv(out, "APPLY_EXECUTED") == "NO", "drift_not_executed", failures)

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

    inactive_pre = dict(base)
    inactive_pre["OWNER_APPLY_TEST_SYSTEMD_SHOW"] = (
        "Id=expect-ai.service\nLoadState=loaded\nMainPID=1\nEnvironment=\nEnvironmentFiles=\nActiveState=inactive\n"
    )
    rc, out = capture_main(inactive_pre)
    expect(rc == 2, "pre_inactive_halts", failures)
    expect("HALT_REASON=SERVICE_NOT_ACTIVE" in out, "halt_pre_inactive", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "NO", "pre_inactive_not_executed", failures)

    def reset_src() -> None:
        if src.exists():
            src.unlink()
        seed_owner_schema(src)
        st = src.stat()
        base["OWNER_APPLY_TEST_SOURCE_DEV"] = str(st.st_dev)
        base["OWNER_APPLY_TEST_SOURCE_INO"] = str(st.st_ino)

    reset_src()
    alter2 = dict(base)
    alter2["OWNER_APPLY_TEST_FAIL"] = "alter2"
    rc, out = capture_main(alter2)
    expect(rc == 2, "alter2_halts", failures)
    expect("HALT_REASON=INJECTED_ALTER2_FAIL" in out, "halt_alter2", failures)
    expect("EXPLICIT_ROLLBACK=YES" in out, "alter2_rollback", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "NO", "alter2_not_executed", failures)
    cols, versions, rows = schema_snapshot(src)
    expect(cols == list(OWNER_PRED_COLUMNS), "alter2_columns_unchanged", failures)
    expect(apply.PERSIST_022 not in versions, "alter2_no_migration_row", failures)
    expect(sum(1 for c in NEW_COLS if c in cols) == 0, "alter2_new_cols_0", failures)
    expect(rows == 1, "alter2_rows_unchanged", failures)

    reset_src()
    idxfail = dict(base)
    idxfail["OWNER_APPLY_TEST_FAIL"] = "index"
    rc, out = capture_main(idxfail)
    expect(rc == 2, "index_halts", failures)
    expect("HALT_REASON=INJECTED_INDEX_FAIL" in out, "halt_index", failures)
    expect("EXPLICIT_ROLLBACK=YES" in out, "index_rollback", failures)
    cols, versions, _ = schema_snapshot(src)
    expect(cols == list(OWNER_PRED_COLUMNS), "index_columns_unchanged", failures)
    expect(apply.PERSIST_022 not in versions, "index_no_migration_row", failures)

    reset_src()
    migfail = dict(base)
    migfail["OWNER_APPLY_TEST_FAIL"] = "migration_insert"
    rc, out = capture_main(migfail)
    expect(rc == 2, "migration_insert_halts", failures)
    expect("HALT_REASON=INJECTED_MIGRATION_INSERT_FAIL" in out, "halt_migration_insert", failures)
    expect("EXPLICIT_ROLLBACK=YES" in out, "migration_insert_rollback", failures)
    cols, versions, _ = schema_snapshot(src)
    expect(cols == list(OWNER_PRED_COLUMNS), "migration_insert_columns_unchanged", failures)
    expect(apply.PERSIST_022 not in versions, "migration_insert_no_row", failures)

    reset_src()
    toctou = dict(base)
    toctou["OWNER_APPLY_TEST_FAIL"] = "schema_before_tx"
    rc, out = capture_main(toctou)
    expect(rc == 2, "schema_before_tx_halts", failures)
    expect("HALT_REASON=PREDICTIONS_COLUMNS_MISMATCH" in out, "halt_tx_recheck", failures)
    expect("TX_SOURCE_SCHEMA_GATE=PASS" not in out, "tx_schema_not_passed", failures)
    expect("TEST_SCHEMA_MUTATED_BEFORE_TX=YES" in out, "mutated_before_tx", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "NO", "toctou_not_executed", failures)

    reset_src()
    health_after = dict(base)
    health_after["OWNER_APPLY_TEST_FAIL"] = "health_after"
    rc, out = capture_main(health_after)
    expect(rc == 2, "health_after_halts", failures)
    expect("HALT_REASON=HEALTH_FAIL" in out, "halt_health_after", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "YES", "health_after_executed_yes", failures)
    expect("POST_APPLY_REGRESSION_PASS=NO" in out, "health_after_regression_no", failures)
    expect("ROLLBACK_REVIEW_REQUIRED=YES" in out, "health_after_rollback_review", failures)
    expect("AUTO_DROP_COLUMNS=NO" in out, "health_after_no_auto_drop_cols", failures)
    expect("AUTO_BACKUP_RESTORE=NO" in out, "health_after_no_restore", failures)
    cols, versions, _ = schema_snapshot(src)
    expect(apply.PERSIST_022 in versions, "health_after_022_kept", failures)
    expect(all(c in cols for c in NEW_COLS), "health_after_cols_kept", failures)

    reset_src()
    get_after = dict(base)
    get_after["OWNER_APPLY_TEST_FAIL"] = "get_after"
    rc, out = capture_main(get_after)
    expect(rc == 2, "get_after_halts", failures)
    expect("HALT_REASON=GET_PREDICTIONS_FAIL" in out, "halt_get_after", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "YES", "get_after_executed_yes", failures)
    expect("ROLLBACK_REVIEW_REQUIRED=YES" in out, "get_after_rollback_review", failures)

    reset_src()
    row_delta = dict(base)
    row_delta["OWNER_APPLY_TEST_FAIL"] = "row_delta"
    rc, out = capture_main(row_delta)
    expect(rc == 2, "row_delta_halts", failures)
    expect("HALT_REASON=GET_PRED_ROW_DELTA_NONEZERO" in out, "halt_row_delta", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "YES", "row_delta_executed_yes", failures)
    expect("POST_APPLY_REGRESSION_PASS=NO" in out, "row_delta_regression_no", failures)

    reset_src()
    inactive_after = dict(base)
    inactive_after["OWNER_APPLY_TEST_FAIL"] = "inactive"
    rc, out = capture_main(inactive_after)
    expect(rc == 2, "inactive_after_halts", failures)
    expect("HALT_REASON=SERVICE_NOT_ACTIVE" in out, "halt_inactive_after", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "YES", "inactive_after_executed_yes", failures)

    reset_src()
    journal = dict(base)
    journal["OWNER_APPLY_TEST_FAIL"] = "journal_error"
    rc, out = capture_main(journal)
    expect(rc == 2, "journal_error_halts", failures)
    expect("HALT_REASON=JOURNAL_ERROR_AFTER_APPLY" in out, "halt_journal", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "YES", "journal_executed_yes", failures)

    reset_src()
    win = dict(base)
    win["PREDICTION_RUNS_ENABLED"] = "1"
    win["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    win["OWNER_APPLY_TEST_GET_JSON"] = '{"ok":true,"data":[{"race_id":"local-fixture-1"}],"meta":{"count":1}}'
    rc, out = capture_main(win)
    expect(rc == 0, "windows_env_ignored", failures)
    expect("OWNER_APPLY_STATUS=SUCCESS" in out, "windows_env_success", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "YES", "commit_marks_executed", failures)
    expect("LIVE_CANONICAL_APPLY=NO" in out, "local_not_live_canonical", failures)
    expect("POST_REMAINS_DISABLED=YES" in out, "post_still_disabled", failures)
    expect("PROCESS_022_WINDOW=CLOSED" in out, "process_window_closed", failures)
    expect("PREDICTION_RUNS_ENABLED_EFFECTIVE=0" in out, "post_effective_0", failures)
    expect("HAS_PERSIST_022=YES" in out or "TX_HAS_PERSIST_022=YES" in out, "persist_022_recorded", failures)
    expect("PRODUCTION_APPLY_READY=NO" in out, "apply_ready_stays_no", failures)
    expect("POST_PREDICTION_RUNS_CALLED=NO" in out, "post_not_called", failures)
    expect("HTTP_CALL=POST" not in out, "no_http_post_line", failures)
    expect("BEGIN_IMMEDIATE=YES" in out, "begin_immediate_emitted", failures)
    expect(last_kv(out, "APPLY_PHASE") == "COMMITTED", "phase_committed", failures)
    expect("PRE_GET_CHECKED=YES" in out and "POST_GET_CHECKED=YES" in out, "get_checked", failures)
    expect("PRE_HEALTH_CHECKED=YES" in out and "POST_HEALTH_CHECKED=YES" in out, "health_checked", failures)
    expect("GET_ENVELOPE_SHAPE_MATCH=YES" in out, "envelope_match", failures)
    expect("POST_DETAIL_GET=ATTEMPTED" in out, "detail_from_list", failures)
    expect("local-fixture-1" not in out, "race_id_not_logged", failures)
    expect("GET_UI_CONVERSATION_RA_CHALLENGE_CHANGED=NO" not in out, "success_no_false_changed_no", failures)
    expect("OWNER_IMMEDIATE_POST_APPLY_SMOKE_REQUIRED=YES" in out, "smoke_required", failures)
    expect("AUDIT_CLOSED=YES" in out, "success_audit_closed", failures)
    cols, versions, rows = schema_snapshot(src)
    conn = sqlite3.connect(str(src))
    nulls = conn.execute("SELECT COUNT(*) FROM predictions WHERE idempotency_key IS NULL").fetchone()[0]
    conn.close()
    expect(cols == list(OWNER_PRED_COLUMNS) + list(NEW_COLS), "columns_after", failures)
    expect(apply.PERSIST_022 in versions, "migration_row", failures)
    expect(len(set(versions)) == 23, "twenty_three_versions", failures)
    expect(rows == 1 and nulls == 1, "existing_row_null_new_cols", failures)
    expect(bak.read_bytes() != src.read_bytes(), "source_changed_backup_untouched_bytes", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
