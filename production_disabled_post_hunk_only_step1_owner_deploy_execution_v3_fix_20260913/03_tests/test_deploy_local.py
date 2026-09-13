#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local 工程1 deploy payload tests. Never open live Production."""
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
PAYLOAD = (PS / "owner_deploy_stdin.py").read_bytes()
LIVE = ROOT / "payload" / "live_preconditions"
sys.path.insert(0, str(PS))
import owner_deploy_stdin as deploy  # noqa: E402


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def last_kv(out: str, key: str) -> str | None:
    found = None
    prefix = key + "="
    for line in out.splitlines():
        if line.startswith(prefix):
            found = line[len(prefix):]
    return found


def seed_schema(path: Path, rows: int = 2, versions: tuple[str, ...] | None = None, cols: tuple[str, ...] | None = None, partial: bool = True) -> None:
    conn = sqlite3.connect(str(path))
    use_cols = cols or deploy.OWNER_PRED_COLUMNS
    colsql = ", ".join("id INTEGER PRIMARY KEY" if c == "id" else "%s TEXT" % c for c in use_cols)
    conn.execute("CREATE TABLE schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE predictions(%s)" % colsql)
    conn.execute("CREATE INDEX idx_predictions_race ON predictions(race_id, created_at)")
    if partial and "idempotency_key" in use_cols:
        conn.execute(
            "CREATE UNIQUE INDEX uq_predictions_idempotency_key_not_null "
            "ON predictions(idempotency_key) WHERE idempotency_key IS NOT NULL"
        )
    for ver in versions or deploy.OWNER_MIGRATIONS:
        conn.execute("INSERT INTO schema_migrations VALUES (?, 't')", (ver,))
    for i in range(rows):
        conn.execute("INSERT INTO predictions(race_id, created_at) VALUES (?, 't')", ("local-%d" % i,))
    conn.commit()
    conn.close()


def copy_live(tree: Path) -> Path:
    win5 = tree / "services" / "win5-ai"
    shutil.copytree(LIVE, win5)
    (win5 / "var").mkdir(parents=True, exist_ok=True)
    return win5


def env_ok() -> dict[str, str]:
    return {
        "OWNER_DEPLOY_TEST_ENV": "1",
        "OWNER_DEPLOY_TEST_SYSTEMD_OK": "1",
        "OWNER_DEPLOY_TEST_PROC_OK": "1",
        "OWNER_DEPLOY_TEST_FILES_OK": "1",
        "OWNER_DEPLOY_TEST_HTTP": "1",
        "OWNER_DEPLOY_TEST_SYSTEMD_SHOW": (
            "Id=expect-ai.service\nLoadState=loaded\nMainPID=1\nEnvironment=\nEnvironmentFiles=\nActiveState=active\nSubState=running\nExecMainStartTimestamp=Fri 2026-09-11 06:34:42 JST\n"
        ),
        "OWNER_DEPLOY_TEST_SYSTEMD_SHOW_AFTER": (
            "Id=expect-ai.service\nLoadState=loaded\nMainPID=2\nEnvironment=\nEnvironmentFiles=\nActiveState=active\nSubState=running\nExecMainStartTimestamp=Sun 2026-09-13 16:20:00 JST\n"
        ),
        "OWNER_DEPLOY_TEST_PROC_ENVIRON": "",
        "OWNER_DEPLOY_TEST_ENVFILE": "",
    }


def capture_main(env: dict[str, str]) -> tuple[int, str]:
    full = os.environ.copy()
    for k in list(full):
        if k.startswith("OWNER_DEPLOY_") or k in (
            "OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED",
            "OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED",
            "OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED",
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


def restart_lines(log: Path) -> list[str]:
    if not log.is_file():
        return []
    return [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]


def base_env(tree: Path, db: Path, backup: Path, restart_log: Path) -> dict[str, str]:
    env = {
        "OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED": "1",
        "OWNER_DEPLOY_PACK_TEST": "1",
        "OWNER_DEPLOY_TEST_ROOT": str(tree),
        "OWNER_DEPLOY_TEST_SRC": str(db),
        "OWNER_DEPLOY_TEST_BACKUP_DIR": str(backup),
        "OWNER_DEPLOY_TEST_RESTART_LOG": str(restart_log),
    }
    env.update(env_ok())
    return env


def main() -> int:
    failures: list[str] = []
    expect(len(deploy.DEPLOY_TARGETS) == 10, "ten_targets", failures)
    expect(all("022_prediction_run_idempotency.sql" != t["rel"] for t in deploy.DEPLOY_TARGETS), "022_sql_not_deploy_target", failures)
    expect("app/data/migrations/022_prediction_run_idempotency.sql" in deploy.MUST_ABSENT, "022_sql_must_absent", failures)
    expect(len(deploy.OWNER_MIGRATIONS) == 23, "twenty_three_versions", failures)
    expect(len(deploy.OWNER_PRED_COLUMNS) == 12, "twelve_columns", failures)
    expect(deploy.MAIN_PY_CANDIDATE_SHA256 == "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c", "main_cand_sha", failures)
    expect(deploy.RESTART_ARGV == ("sudo", "-n", "systemctl", "restart", "expect-ai.service"), "restart_argv", failures)

    rc, out = capture_main({})
    expect(rc == 2, "refuse_unapproved", failures)
    expect("HALT_REASON=OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED_UNSET" in out, "halt_unapproved", failures)
    expect(last_kv(out, "DEPLOY_EXECUTED") == "NO", "unapproved_executed_no", failures)
    expect(last_kv(out, "RESTART_EXECUTED") == "NO", "unapproved_restart_no", failures)

    tmp = Path(tempfile.mkdtemp(prefix="step1deploy-"))
    tree = tmp / "repo"
    win5 = copy_live(tree)
    db = win5 / "var" / "expect_ai.db"
    seed_schema(db)
    backup = tmp / "backup"
    restart_log = tmp / "restart.log"
    base = base_env(tree, db, backup, restart_log)

    rc, out = capture_main(base)
    expect(rc == 0, "happy_exit0", failures)
    expect(last_kv(out, "FILES_REPLACED") == "YES", "happy_replaced", failures)
    expect(last_kv(out, "RESTART_EXECUTED") == "YES", "happy_restart", failures)
    expect(last_kv(out, "DEPLOY_RESTART_COUNT") == "1", "happy_restart_count1", failures)
    expect(last_kv(out, "RECOVERY_RESTART_COUNT") == "0", "happy_no_recovery", failures)
    expect(last_kv(out, "OPS_DEPLOYED") == "NO", "happy_ops_not_deployed", failures)
    expect(last_kv(out, "POST_PREDICTION_RUNS_ERROR_CODE") == "PREDICTION_RUNS_DISABLED", "happy_post_disabled", failures)
    expect(last_kv(out, "HEALTH_OK") == "YES", "happy_health_ok", failures)
    expect(last_kv(out, "HEALTH_STATUS") == "200", "happy_health_200", failures)
    expect(last_kv(out, "READINESS_OK") == "YES", "happy_readiness_ok", failures)
    expect(last_kv(out, "READINESS_OUTCOME") == "PASS", "happy_readiness_pass", failures)
    expect(last_kv(out, "SYSTEMCTL_RESTART_EXIT") == "0", "happy_restart_exit0", failures)
    expect(last_kv(out, "RESTART_OUTCOME") == "SUCCESS", "happy_restart_outcome", failures)
    expect(last_kv(out, "SUDO_N_FLAG") == "YES", "happy_sudo_n", failures)
    expect(last_kv(out, "PRED_ROW_DELTA_TOTAL") == "0", "happy_row_delta0", failures)
    expect(last_kv(out, "SCHEMA_ROLLBACK") == "NO", "happy_no_schema_rollback", failures)
    expect(last_kv(out, "MIGRATE") == "NO", "happy_no_migrate", failures)
    lines = restart_lines(restart_log)
    expect(lines == ["sudo -n systemctl restart expect-ai.service"], "happy_restart_log_single", failures)
    main_got = deploy.file_sha_nofollow(win5 / "app" / "main.py")
    expect(main_got == deploy.MAIN_PY_CANDIDATE_SHA256, "happy_main_candidate_bytes", failures)
    ops1 = deploy.file_sha_nofollow(win5 / "app" / "ops" / "prediction_capacity.py")
    expect(ops1 == "c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e", "happy_ops_capacity_unchanged", failures)

    tmp2 = Path(tempfile.mkdtemp(prefix="step1mismatch-"))
    tree2 = tmp2 / "repo"
    win5b = copy_live(tree2)
    (win5b / "app" / "main.py").write_bytes(b"not-the-live-main")
    db2 = win5b / "var" / "expect_ai.db"
    seed_schema(db2)
    log2 = tmp2 / "restart.log"
    env2 = base_env(tree2, db2, tmp2 / "backup", log2)
    rc, out = capture_main(env2)
    expect(rc == 2, "mismatch_exit2", failures)
    expect("HALT_REASON=PRECONDITION_LIVE_SHA_MISMATCH" in out, "halt_live_sha", failures)
    expect(restart_lines(log2) == [], "mismatch_no_restart", failures)
    expect((win5b / "app" / "predictions" / "runs.py").exists() is False, "mismatch_no_write", failures)

    tmp3 = Path(tempfile.mkdtemp(prefix="step1absent-"))
    tree3 = tmp3 / "repo"
    win5c = copy_live(tree3)
    (win5c / "app" / "predictions").mkdir(parents=True, exist_ok=True)
    (win5c / "app" / "predictions" / "runs.py").write_text("present\n", encoding="utf-8")
    db3 = win5c / "var" / "expect_ai.db"
    seed_schema(db3)
    log3 = tmp3 / "restart.log"
    rc, out = capture_main(base_env(tree3, db3, tmp3 / "backup", log3))
    expect(rc == 2, "absent_mismatch_exit2", failures)
    expect("HALT_REASON=PRECONDITION_ABSENT_MISMATCH" in out, "halt_absent", failures)
    expect(restart_lines(log3) == [], "absent_no_restart", failures)

    tmp4 = Path(tempfile.mkdtemp(prefix="step1flag-"))
    tree4 = tmp4 / "repo"
    win5d = copy_live(tree4)
    db4 = win5d / "var" / "expect_ai.db"
    seed_schema(db4)
    log4 = tmp4 / "restart.log"
    flagged = base_env(tree4, db4, tmp4 / "backup", log4)
    flagged["OWNER_DEPLOY_TEST_PROC_ENVIRON"] = "PREDICTION_RUNS_ENABLED=1"
    rc, out = capture_main(flagged)
    expect(rc == 2, "post_flag_halts", failures)
    expect("HALT_REASON=PREDICTION_RUNS_ENABLED_EFFECTIVE_1" in out, "halt_post_flag", failures)
    expect(restart_lines(log4) == [], "post_flag_no_restart", failures)

    tmp5 = Path(tempfile.mkdtemp(prefix="step1mig-"))
    tree5 = tmp5 / "repo"
    win5e = copy_live(tree5)
    db5 = win5e / "var" / "expect_ai.db"
    seed_schema(db5)
    log5 = tmp5 / "restart.log"
    flagged022 = base_env(tree5, db5, tmp5 / "backup", log5)
    flagged022["OWNER_DEPLOY_TEST_PROC_ENVIRON"] = "EXPECT_AI_ALLOW_MIGRATION_022=1"
    rc, out = capture_main(flagged022)
    expect(rc == 2, "flag022_halts", failures)
    expect("HALT_REASON=EXPECT_AI_ALLOW_MIGRATION_022_EFFECTIVE_1" in out, "halt_022_flag", failures)

    tmp6 = Path(tempfile.mkdtemp(prefix="step1schema-"))
    tree6 = tmp6 / "repo"
    win5f = copy_live(tree6)
    db6 = win5f / "var" / "expect_ai.db"
    seed_schema(db6, versions=deploy.OWNER_MIGRATIONS[:-1])
    log6 = tmp6 / "restart.log"
    rc, out = capture_main(base_env(tree6, db6, tmp6 / "backup", log6))
    expect(rc == 2, "schema_mismatch_halts", failures)
    expect("HALT_REASON=SCHEMA_MIGRATIONS_MISMATCH" in out, "halt_schema", failures)
    expect(restart_lines(log6) == [], "schema_no_restart", failures)

    tmp7 = Path(tempfile.mkdtemp(prefix="step1after-"))
    tree7 = tmp7 / "repo"
    win5g = copy_live(tree7)
    db7 = win5g / "var" / "expect_ai.db"
    seed_schema(db7)
    live_main = (win5g / "app" / "main.py").read_bytes()
    log7 = tmp7 / "restart.log"
    inj = base_env(tree7, db7, tmp7 / "backup", log7)
    inj["OWNER_DEPLOY_TEST_FAIL"] = "after_replace"
    rc, out = capture_main(inj)
    expect(rc == 2, "after_replace_exit2", failures)
    expect("HALT_REASON=INJECTED_AFTER_REPLACE" in out, "halt_after_replace", failures)
    expect(last_kv(out, "CODE_RESTORED") == "YES", "after_replace_restored", failures)
    expect(last_kv(out, "RESTART_EXECUTED") == "NO", "after_replace_no_deploy_restart", failures)
    expect(last_kv(out, "RECOVERY_RESTART_COUNT") == "0", "after_replace_no_recovery", failures)
    expect(restart_lines(log7) == [], "after_replace_restart_log_empty", failures)
    expect((win5g / "app" / "main.py").read_bytes() == live_main, "after_replace_main_restored", failures)
    expect((win5g / "app" / "predictions" / "runs.py").exists() is False, "after_replace_absent_removed", failures)

    tmp8 = Path(tempfile.mkdtemp(prefix="step1restartfail-"))
    tree8 = tmp8 / "repo"
    win5h = copy_live(tree8)
    db8 = win5h / "var" / "expect_ai.db"
    seed_schema(db8)
    live_main8 = (win5h / "app" / "main.py").read_bytes()
    log8 = tmp8 / "restart.log"
    inj2 = base_env(tree8, db8, tmp8 / "backup", log8)
    inj2["OWNER_DEPLOY_TEST_FAIL"] = "after_restart"
    rc, out = capture_main(inj2)
    expect(rc == 2, "after_restart_exit2", failures)
    expect("HALT_REASON=INJECTED_AFTER_RESTART" in out, "halt_after_restart", failures)
    expect(last_kv(out, "CODE_RESTORED") == "YES", "after_restart_restored", failures)
    expect(last_kv(out, "RESTART_EXECUTED") == "YES", "after_restart_had_deploy_restart", failures)
    expect(last_kv(out, "RECOVERY_RESTART_EXECUTED") == "YES", "after_restart_recovery", failures)
    expect(restart_lines(log8) == ["sudo -n systemctl restart expect-ai.service", "sudo -n systemctl restart expect-ai.service"], "after_restart_two_restarts", failures)
    expect((win5h / "app" / "main.py").read_bytes() == live_main8, "after_restart_main_restored", failures)
    expect(last_kv(out, "SCHEMA_ROLLBACK") == "NO", "after_restart_no_schema_rollback", failures)

    tmp9 = Path(tempfile.mkdtemp(prefix="step1must-"))
    tree9 = tmp9 / "repo"
    win5i = copy_live(tree9)
    (win5i / "app" / "predictions").mkdir(parents=True, exist_ok=True)
    (win5i / "app" / "predictions" / "corpus.py").write_text("nope\n", encoding="utf-8")
    db9 = win5i / "var" / "expect_ai.db"
    seed_schema(db9)
    log9 = tmp9 / "restart.log"
    rc, out = capture_main(base_env(tree9, db9, tmp9 / "backup", log9))
    expect(rc == 2, "must_absent_halts", failures)
    expect("HALT_REASON=MUST_ABSENT_PRESENT" in out, "halt_must_absent", failures)

    tmp9b = Path(tempfile.mkdtemp(prefix="step1022sql-"))
    tree9b = tmp9b / "repo"
    win5sql = copy_live(tree9b)
    mig = win5sql / "app" / "data" / "migrations"
    mig.mkdir(parents=True, exist_ok=True)
    (mig / "022_prediction_run_idempotency.sql").write_text("-- should stay absent\n", encoding="utf-8")
    db9b = win5sql / "var" / "expect_ai.db"
    seed_schema(db9b)
    log9b = tmp9b / "restart.log"
    rc, out = capture_main(base_env(tree9b, db9b, tmp9b / "backup", log9b))
    expect(rc == 2, "022_sql_present_halts", failures)
    expect("HALT_REASON=MUST_ABSENT_PRESENT" in out, "halt_022_sql_must_absent", failures)
    expect(restart_lines(log9b) == [], "022_sql_present_no_restart", failures)

    tmp10 = Path(tempfile.mkdtemp(prefix="step1posten-"))
    tree10 = tmp10 / "repo"
    win5j = copy_live(tree10)
    db10 = win5j / "var" / "expect_ai.db"
    seed_schema(db10)
    log10 = tmp10 / "restart.log"
    post_en = base_env(tree10, db10, tmp10 / "backup", log10)
    post_en["OWNER_DEPLOY_TEST_FAIL"] = "post_enabled"
    rc, out = capture_main(post_en)
    expect(rc == 2, "post_enabled_halts", failures)
    expect("HALT_REASON=POST_NOT_DISABLED" in out, "halt_post_not_disabled", failures)
    expect(last_kv(out, "CODE_RESTORED") == "YES", "post_enabled_restored", failures)
    expect(last_kv(out, "RECOVERY_RESTART_EXECUTED") == "YES", "post_enabled_recovery_restart", failures)

    tmp11 = Path(tempfile.mkdtemp(prefix="step1v1rerun-"))
    tree11 = tmp11 / "repo"
    copy_live(tree11)
    db11 = tree11 / "services" / "win5-ai" / "var" / "expect_ai.db"
    seed_schema(db11)
    log11 = tmp11 / "restart.log"
    v1only = base_env(tree11, db11, tmp11 / "backup", log11)
    v1only.pop("OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED", None)
    v1only["OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED"] = "1"
    rc, out = capture_main(v1only)
    expect(rc == 2, "v1_approval_refused_exit2", failures)
    expect("HALT_REASON=OLD_EXECUTION_PACK_RERUN_REFUSED" in out, "halt_v1_rerun", failures)
    expect(restart_lines(log11) == [], "v1_rerun_no_restart", failures)

    tmp12 = Path(tempfile.mkdtemp(prefix="step1timeoutok-"))
    tree12 = tmp12 / "repo"
    win5k = copy_live(tree12)
    db12 = win5k / "var" / "expect_ai.db"
    seed_schema(db12)
    log12 = tmp12 / "restart.log"
    to_ok = base_env(tree12, db12, tmp12 / "backup", log12)
    to_ok["OWNER_DEPLOY_TEST_RESTART_TIMEOUT"] = "1"
    rc, out = capture_main(to_ok)
    expect(rc == 0, "timeout_changed_pid_success_exit0", failures)
    expect(last_kv(out, "SYSTEMCTL_RESTART_TIMEOUT") == "YES", "timeout_flag_yes", failures)
    expect(last_kv(out, "RESTART_OUTCOME") == "SUCCESS", "timeout_classified_success", failures)
    expect(last_kv(out, "RESTART_EXECUTED") == "YES", "timeout_success_restart_executed", failures)
    expect(last_kv(out, "SYSTEMCTL_RESTART_STDERR_REDACTED") == "TIMEOUT", "timeout_stderr_recorded", failures)

    tmp13 = Path(tempfile.mkdtemp(prefix="step1restartfail-"))
    tree13 = tmp13 / "repo"
    win5m = copy_live(tree13)
    db13 = win5m / "var" / "expect_ai.db"
    seed_schema(db13)
    live_main13 = (win5m / "app" / "main.py").read_bytes()
    log13 = tmp13 / "restart.log"
    rf = base_env(tree13, db13, tmp13 / "backup", log13)
    rf["OWNER_DEPLOY_TEST_RESTART_FAIL"] = "1"
    rf["OWNER_DEPLOY_TEST_RESTART_STDERR"] = "Failed to restart expect-ai.service: Access denied"
    rc, out = capture_main(rf)
    expect(rc == 2, "restart_fail_exit2", failures)
    expect("HALT_REASON=RESTART_FAIL" in out, "halt_restart_fail", failures)
    expect(last_kv(out, "SYSTEMCTL_RESTART_EXIT") is not None, "restart_fail_exit_recorded", failures)
    expect("Access denied" in (last_kv(out, "SYSTEMCTL_RESTART_STDERR_REDACTED") or ""), "restart_fail_stderr_recorded", failures)
    expect(last_kv(out, "CODE_RESTORED") == "YES", "restart_fail_restored", failures)
    expect(last_kv(out, "RESTART_EXECUTED") == "NO", "restart_fail_not_executed", failures)
    expect(last_kv(out, "RECOVERY_RESTART_COUNT") == "0", "restart_fail_no_recovery", failures)
    expect((win5m / "app" / "main.py").read_bytes() == live_main13, "restart_fail_main_restored", failures)
    expect(restart_lines(log13) == ["sudo -n systemctl restart expect-ai.service"], "restart_fail_one_attempt", failures)

    tmp14 = Path(tempfile.mkdtemp(prefix="step1v2rerun-"))
    tree14 = tmp14 / "repo"
    copy_live(tree14)
    db14 = tree14 / "services" / "win5-ai" / "var" / "expect_ai.db"
    seed_schema(db14)
    log14 = tmp14 / "restart.log"
    v2only = base_env(tree14, db14, tmp14 / "backup", log14)
    v2only.pop("OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED", None)
    v2only["OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED"] = "1"
    rc, out = capture_main(v2only)
    expect(rc == 2, "v2_approval_refused_exit2", failures)
    expect("HALT_REASON=OLD_EXECUTION_PACK_RERUN_REFUSED" in out, "halt_v2_rerun", failures)
    expect(restart_lines(log14) == [], "v2_rerun_no_restart", failures)

    tmp15 = Path(tempfile.mkdtemp(prefix="step1ready-delay-"))
    tree15 = tmp15 / "repo"
    win5n = copy_live(tree15)
    db15 = win5n / "var" / "expect_ai.db"
    seed_schema(db15)
    log15 = tmp15 / "restart.log"
    delayed = base_env(tree15, db15, tmp15 / "backup", log15)
    delayed["OWNER_DEPLOY_TEST_READINESS_FAIL_COUNT"] = "2"
    delayed["OWNER_DEPLOY_TEST_READINESS_TIMEOUT_S"] = "2"
    delayed["OWNER_DEPLOY_TEST_READINESS_INTERVAL_S"] = "0.05"
    rc, out = capture_main(delayed)
    expect(rc == 0, "readiness_delay_exit0", failures)
    expect(last_kv(out, "READINESS_OK") == "YES", "readiness_delay_ok", failures)
    expect(last_kv(out, "READINESS_OUTCOME") == "PASS", "readiness_delay_pass", failures)
    attempts = last_kv(out, "READINESS_ATTEMPT")
    expect(attempts is not None and int(attempts) >= 3, "readiness_delay_polled", failures)
    expect(last_kv(out, "CODE_RESTORED") != "YES", "readiness_delay_not_restored", failures)
    expect(restart_lines(log15) == ["sudo -n systemctl restart expect-ai.service"], "readiness_delay_one_restart", failures)

    tmp16 = Path(tempfile.mkdtemp(prefix="step1ready-to-"))
    tree16 = tmp16 / "repo"
    win5o = copy_live(tree16)
    db16 = win5o / "var" / "expect_ai.db"
    seed_schema(db16)
    live_main16 = (win5o / "app" / "main.py").read_bytes()
    log16 = tmp16 / "restart.log"
    never = base_env(tree16, db16, tmp16 / "backup", log16)
    never["OWNER_DEPLOY_TEST_READINESS_NEVER"] = "1"
    never["OWNER_DEPLOY_TEST_READINESS_TIMEOUT_S"] = "0.25"
    never["OWNER_DEPLOY_TEST_READINESS_INTERVAL_S"] = "0.05"
    never["OWNER_DEPLOY_TEST_READINESS_MAX_ATTEMPTS"] = "8"
    rc, out = capture_main(never)
    expect(rc == 2, "readiness_timeout_exit2", failures)
    expect("HALT_REASON=READINESS_TIMEOUT" in out, "halt_readiness_timeout", failures)
    expect(last_kv(out, "READINESS_OUTCOME") == "TIMEOUT", "readiness_timeout_outcome", failures)
    expect(last_kv(out, "CODE_RESTORED") == "YES", "readiness_timeout_restored", failures)
    expect(last_kv(out, "RESTART_EXECUTED") == "YES", "readiness_timeout_had_deploy_restart", failures)
    expect(last_kv(out, "RECOVERY_RESTART_EXECUTED") == "YES", "readiness_timeout_recovery", failures)
    expect((win5o / "app" / "main.py").read_bytes() == live_main16, "readiness_timeout_main_restored", failures)
    expect(restart_lines(log16) == ["sudo -n systemctl restart expect-ai.service", "sudo -n systemctl restart expect-ai.service"], "readiness_timeout_two_restarts", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
