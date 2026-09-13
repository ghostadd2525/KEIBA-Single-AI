#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local read-only probe payload tests. Never open live Production."""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS = ROOT / "02_powershell"
PAYLOAD = (PS / "owner_probe_stdin.py").read_bytes()
LIVE = ROOT / "payload" / "live_preconditions"
sys.path.insert(0, str(PS))
import owner_probe_stdin as probe  # noqa: E402


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
    use_cols = cols or probe.OWNER_PRED_COLUMNS
    colsql = ", ".join("id INTEGER PRIMARY KEY" if c == "id" else "%s TEXT" % c for c in use_cols)
    conn.execute("CREATE TABLE schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE predictions(%s)" % colsql)
    conn.execute("CREATE INDEX idx_predictions_race ON predictions(race_id, created_at)")
    if partial and "idempotency_key" in use_cols:
        conn.execute(
            "CREATE UNIQUE INDEX uq_predictions_idempotency_key_not_null "
            "ON predictions(idempotency_key) WHERE idempotency_key IS NOT NULL"
        )
    for ver in versions or probe.OWNER_MIGRATIONS:
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


def tree_fingerprint(win5: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(win5.rglob("*")):
        if path.is_file():
            rel = path.relative_to(win5).as_posix()
            out[rel] = probe.file_sha_bytes(path.read_bytes())
    return out


def pre_window_usec() -> str:
    ts = datetime(2026, 9, 13, 5, 0, 0, tzinfo=timezone.utc).timestamp()
    return str(int(ts * 1_000_000))


def in_window_usec() -> str:
    ts = datetime(2026, 9, 13, 6, 18, 30, tzinfo=timezone.utc).timestamp()
    return str(int(ts * 1_000_000))


def env_ok() -> dict[str, str]:
    return {
        "OWNER_PROBE_TEST_HTTP": "1",
        "OWNER_PROBE_TEST_FILES_OK": "1",
        "OWNER_PROBE_TEST_PROC_OK": "1",
        "OWNER_PROBE_TEST_SYSTEMD_SHOW": (
            "Id=expect-ai.service\nLoadState=loaded\nActiveState=active\nSubState=running\n"
            "MainPID=4242\nFragmentPath=/lib/systemd/system/expect-ai.service\nUser=ubuntu\nGroup=ubuntu\n"
            "ActiveEnterTimestamp=Sun 2026-09-13 05:00:00 UTC\nActiveEnterTimestampUSec=%s\n"
            "InactiveEnterTimestamp=\nNRestarts=0\nResult=success\nExecMainStartTimestamp=Sun 2026-09-13 05:00:00 UTC\n"
            "Environment=\nEnvironmentFiles=\n" % pre_window_usec()
        ),
        "OWNER_PROBE_TEST_PROC_ENVIRON": "",
        "OWNER_PROBE_TEST_ENVFILE": "",
        "OWNER_PROBE_TEST_SUDO_NL_RC": "0",
        "OWNER_PROBE_TEST_SUDO_NL": (
            "User ubuntu may run the following commands on this host:\n"
            "    (ALL) NOPASSWD: /usr/bin/systemctl restart expect-ai.service\n"
        ),
        "OWNER_PROBE_TEST_JOURNAL": "2026-09-13T06:18:30+00:00 expect-ai.service: Access denied\n",
        "OWNER_PROBE_TEST_ID": "uid=1000(ubuntu) gid=1000(ubuntu) groups=1000(ubuntu)\n",
        "OWNER_PROBE_TEST_SYSTEMCTL_VERSION": "systemd 249 (249.11-0ubuntu3.12)\n",
        "OWNER_PROBE_TEST_PROC_COMM": "python3",
    }


def capture_main(env: dict[str, str]) -> tuple[int, str]:
    full = os.environ.copy()
    for k in list(full):
        if k.startswith("OWNER_PROBE_") or k in (
            "OWNER_READONLY_STEP1_PROBE_APPROVED",
            "OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED",
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


def cmd_lines(log: Path) -> list[str]:
    if not log.is_file():
        return []
    return [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]


def base_env(tree: Path, db: Path, backup: Path, cmd_log: Path) -> dict[str, str]:
    env = {
        "OWNER_READONLY_STEP1_PROBE_APPROVED": "1",
        "OWNER_PROBE_PACK_TEST": "1",
        "OWNER_PROBE_TEST_ROOT": str(tree),
        "OWNER_PROBE_TEST_SRC": str(db),
        "OWNER_PROBE_TEST_BACKUP_DIR": str(backup),
        "OWNER_PROBE_TEST_CMD_LOG": str(cmd_log),
    }
    env.update(env_ok())
    return env


def main() -> int:
    failures: list[str] = []
    expect(len(probe.DEPLOY_TARGETS) == 11, "eleven_targets", failures)
    expect(len(probe.OWNER_MIGRATIONS) == 23, "twenty_three_versions", failures)
    expect(len(probe.OWNER_PRED_COLUMNS) == 12, "twelve_columns", failures)
    expect(probe.LIVE_MAIN_PY_SHA256 == "7486a9ad7578e9ccdf883eaaac85f0b0de7ba329e286302b8d2f57db81d79235", "live_main_sha", failures)
    expect(probe.MAIN_PY_CANDIDATE_SHA256 == "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c", "cand_main_sha", failures)
    expect(probe.classify_main_py(probe.LIVE_MAIN_PY_SHA256) == "LIVE", "classify_live", failures)
    expect(probe.classify_main_py(probe.MAIN_PY_CANDIDATE_SHA256) == "CANDIDATE", "classify_candidate", failures)
    expect(probe.classify_main_py("abc") == "OTHER", "classify_other", failures)

    rc, out = capture_main({})
    expect(rc == 2, "refuse_unapproved", failures)
    expect("HALT_REASON=OWNER_READONLY_STEP1_PROBE_APPROVED_UNSET" in out, "halt_unapproved", failures)
    expect(last_kv(out, "PROBE_EXECUTED") == "NO", "unapproved_executed_no", failures)
    expect(last_kv(out, "SYSTEMCTL_MUTATE_ISSUED") == "NO", "unapproved_no_mutate", failures)

    tmp = Path(tempfile.mkdtemp(prefix="step1probe-"))
    tree = tmp / "repo"
    win5 = copy_live(tree)
    db = win5 / "var" / "expect_ai.db"
    seed_schema(db, rows=2)
    backup = tmp / "backup"
    backup.mkdir()
    (backup / "app_main.py.bak").write_text("x\n", encoding="utf-8")
    cmd_log = tmp / "cmd.log"
    before = tree_fingerprint(win5)
    rc, out = capture_main(base_env(tree, db, backup, cmd_log))
    after = tree_fingerprint(win5)
    expect(rc == 0, "happy_exit0", failures)
    expect(last_kv(out, "PROBE_EXECUTED") == "YES", "happy_executed", failures)
    expect(last_kv(out, "PROBE_PHASE") == "COMPLETE", "happy_phase", failures)
    expect(last_kv(out, "RESTORE_DISK_MATCH") == "YES", "happy_restore", failures)
    expect(last_kv(out, "MAIN_PY_STILL_CANDIDATE") == "NO", "happy_main_not_candidate", failures)
    expect(last_kv(out, "MAIN_PY_CLASS") == "LIVE", "happy_main_live", failures)
    expect(last_kv(out, "OPS_UNCHANGED") == "YES", "happy_ops", failures)
    expect(last_kv(out, "FLAGS_UNSET_OR_0") == "YES", "happy_flags", failures)
    expect(last_kv(out, "SCHEMA_READONLY_PASS") == "YES", "happy_schema", failures)
    expect(last_kv(out, "HEALTH_OK") == "YES", "happy_health", failures)
    expect(last_kv(out, "PRED_ROW_DELTA_TOTAL") == "0", "happy_row_delta0", failures)
    expect(last_kv(out, "SYSTEMCTL_MUTATE_ISSUED") == "NO", "happy_no_mutate", failures)
    expect(last_kv(out, "SUDO_N_L_HAS_SYSTEMCTL_RESTART_EXPECT_AI") == "YES", "happy_sudo_restart_listed", failures)
    expect(last_kv(out, "UBUNTU_RESTART_NOPASSWD") == "YES", "happy_restart_nopasswd", failures)
    expect(last_kv(out, "JOURNAL_HAS_ACCESS_DENIED") == "YES", "happy_journal_access_denied", failures)
    expect(last_kv(out, "SYSTEMCTL_SHOW_AS_UBUNTU") == "YES", "happy_show_ok", failures)
    expect(last_kv(out, "UNIT_LOADSTATE") == "loaded", "happy_loadstate", failures)
    expect(last_kv(out, "UNIT_ACTIVESTATE") == "active", "happy_activestate", failures)
    expect(last_kv(out, "UNIT_MAINPID") == "4242", "happy_mainpid", failures)
    expect(last_kv(out, "RUNNING_PROCESS_LIKELY_PREDEPLOY_BYTES") == "YES", "happy_predeploy_process", failures)
    expect(last_kv(out, "CANDIDATE_TAR_EMBEDDED") == "NO", "happy_no_tar", failures)
    expect(last_kv(out, "MIGRATE") == "NO", "happy_no_migrate", failures)
    expect(last_kv(out, "POST") == "NO", "happy_no_post", failures)
    expect(before == after, "happy_no_tree_writes", failures)
    lines = cmd_lines(cmd_log)
    expect(any(ln.startswith("sudo -n -l") for ln in lines), "happy_sudo_nl_logged", failures)
    expect(not any(" restart " in (" " + ln + " ") or ln.endswith(" restart") for ln in lines), "happy_no_restart_cmd", failures)
    expect(not any(" reload" in ln for ln in lines), "happy_no_reload_cmd", failures)
    expect(all("systemctl restart" not in ln for ln in lines), "happy_no_systemctl_restart", failures)

    tmp2 = Path(tempfile.mkdtemp(prefix="step1probe-mismatch-"))
    tree2 = tmp2 / "repo"
    win5b = copy_live(tree2)
    (win5b / "app" / "main.py").write_bytes(b"not-the-live-main")
    db2 = win5b / "var" / "expect_ai.db"
    seed_schema(db2)
    backup2 = tmp2 / "backup"
    backup2.mkdir()
    log2 = tmp2 / "cmd.log"
    fp_before = tree_fingerprint(win5b)
    rc, out = capture_main(base_env(tree2, db2, backup2, log2))
    fp_after = tree_fingerprint(win5b)
    expect(rc == 2, "mismatch_exit2", failures)
    expect(last_kv(out, "RESTORE_DISK_MATCH") == "NO", "mismatch_restore_no", failures)
    expect(last_kv(out, "MAIN_PY_STILL_CANDIDATE") == "NO", "mismatch_not_candidate_bytes", failures)
    expect(last_kv(out, "PROBE_EXECUTED") == "YES", "mismatch_still_completed", failures)
    expect(last_kv(out, "SCHEMA_READONLY_PASS") == "YES", "mismatch_still_schema", failures)
    expect(fp_before == fp_after, "mismatch_no_writes", failures)
    expect(all("systemctl restart" not in ln for ln in cmd_lines(log2)), "mismatch_no_restart", failures)

    tmp3 = Path(tempfile.mkdtemp(prefix="step1probe-absent-"))
    tree3 = tmp3 / "repo"
    win5c = copy_live(tree3)
    (win5c / "app" / "predictions").mkdir(parents=True, exist_ok=True)
    (win5c / "app" / "predictions" / "runs.py").write_text("present\n", encoding="utf-8")
    db3 = win5c / "var" / "expect_ai.db"
    seed_schema(db3)
    log3 = tmp3 / "cmd.log"
    (tmp3 / "backup").mkdir()
    rc, out = capture_main(base_env(tree3, db3, tmp3 / "backup", log3))
    expect(rc == 2, "absent_mismatch_exit2", failures)
    expect(last_kv(out, "RESTORE_DISK_MATCH") == "NO", "absent_restore_no", failures)
    expect(last_kv(out, "PROBE_EXECUTED") == "YES", "absent_still_completed", failures)

    tmp4 = Path(tempfile.mkdtemp(prefix="step1probe-flag-"))
    tree4 = tmp4 / "repo"
    win5d = copy_live(tree4)
    db4 = win5d / "var" / "expect_ai.db"
    seed_schema(db4)
    log4 = tmp4 / "cmd.log"
    (tmp4 / "backup").mkdir()
    flagged = base_env(tree4, db4, tmp4 / "backup", log4)
    flagged["OWNER_PROBE_TEST_PROC_ENVIRON"] = "PREDICTION_RUNS_ENABLED=1"
    rc, out = capture_main(flagged)
    expect(rc == 2, "post_flag_fails", failures)
    expect(last_kv(out, "FLAGS_UNSET_OR_0") == "NO", "post_flag_recorded", failures)
    expect("PREDICTION_RUNS_ENABLED_EFFECTIVE_1" in out, "post_flag_finding", failures)
    expect(last_kv(out, "RESTORE_DISK_MATCH") == "YES", "post_flag_still_restore", failures)
    expect(all("systemctl restart" not in ln for ln in cmd_lines(log4)), "post_flag_no_restart", failures)

    tmp5 = Path(tempfile.mkdtemp(prefix="step1probe-022-"))
    tree5 = tmp5 / "repo"
    win5e = copy_live(tree5)
    db5 = win5e / "var" / "expect_ai.db"
    seed_schema(db5)
    log5 = tmp5 / "cmd.log"
    (tmp5 / "backup").mkdir()
    flagged022 = base_env(tree5, db5, tmp5 / "backup", log5)
    flagged022["OWNER_PROBE_TEST_PROC_ENVIRON"] = "EXPECT_AI_ALLOW_MIGRATION_022=1"
    rc, out = capture_main(flagged022)
    expect(rc == 2, "flag022_fails", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_022_EFFECTIVE_1" in out, "flag022_finding", failures)

    tmp6 = Path(tempfile.mkdtemp(prefix="step1probe-schema-"))
    tree6 = tmp6 / "repo"
    win5f = copy_live(tree6)
    db6 = win5f / "var" / "expect_ai.db"
    seed_schema(db6, versions=probe.OWNER_MIGRATIONS[:-1])
    log6 = tmp6 / "cmd.log"
    (tmp6 / "backup").mkdir()
    rc, out = capture_main(base_env(tree6, db6, tmp6 / "backup", log6))
    expect(rc == 2, "schema_mismatch_fails", failures)
    expect(last_kv(out, "SCHEMA_READONLY_PASS") == "NO", "schema_pass_no", failures)
    expect(last_kv(out, "RESTORE_DISK_MATCH") == "YES", "schema_still_restore", failures)
    expect(all("systemctl restart" not in ln for ln in cmd_lines(log6)), "schema_no_restart", failures)

    tmp7 = Path(tempfile.mkdtemp(prefix="step1probe-sudo-"))
    tree7 = tmp7 / "repo"
    win5g = copy_live(tree7)
    db7 = win5g / "var" / "expect_ai.db"
    seed_schema(db7)
    log7 = tmp7 / "cmd.log"
    (tmp7 / "backup").mkdir()
    sudo_fail = base_env(tree7, db7, tmp7 / "backup", log7)
    sudo_fail["OWNER_PROBE_TEST_SUDO_NL_RC"] = "1"
    sudo_fail["OWNER_PROBE_TEST_SUDO_NL"] = ""
    rc, out = capture_main(sudo_fail)
    expect(last_kv(out, "SUDO_N_L_STATUS") == "FAIL", "sudo_fail_recorded", failures)
    expect(last_kv(out, "UBUNTU_RESTART_NOPASSWD") == "UNKNOWN", "sudo_fail_unknown_priv", failures)
    expect(last_kv(out, "PROBE_EXECUTED") == "YES", "sudo_fail_still_completed", failures)
    expect(last_kv(out, "RESTORE_DISK_MATCH") == "YES", "sudo_fail_restore_ok", failures)
    expect(rc == 2, "sudo_fail_exit2_finding", failures)

    tmp8 = Path(tempfile.mkdtemp(prefix="step1probe-window-"))
    tree8 = tmp8 / "repo"
    win5h = copy_live(tree8)
    db8 = win5h / "var" / "expect_ai.db"
    seed_schema(db8)
    log8 = tmp8 / "cmd.log"
    (tmp8 / "backup").mkdir()
    windowed = base_env(tree8, db8, tmp8 / "backup", log8)
    show = windowed["OWNER_PROBE_TEST_SYSTEMD_SHOW"]
    show = show.replace(pre_window_usec(), in_window_usec())
    show = show.replace("Sun 2026-09-13 05:00:00 UTC", "Sun 2026-09-13 06:18:30 UTC")
    windowed["OWNER_PROBE_TEST_SYSTEMD_SHOW"] = show
    rc, out = capture_main(windowed)
    expect(rc == 0, "window_exit0", failures)
    expect(last_kv(out, "RUNNING_PROCESS_MAY_HAVE_CANDIDATE_BYTES") == "YES", "window_maybe_candidate_bytes", failures)
    expect(last_kv(out, "RESTORE_DISK_MATCH") == "YES", "window_disk_restored", failures)

    tmp9 = Path(tempfile.mkdtemp(prefix="step1probe-must-"))
    tree9 = tmp9 / "repo"
    win5i = copy_live(tree9)
    (win5i / "app" / "predictions").mkdir(parents=True, exist_ok=True)
    (win5i / "app" / "predictions" / "corpus.py").write_text("nope\n", encoding="utf-8")
    db9 = win5i / "var" / "expect_ai.db"
    seed_schema(db9)
    log9 = tmp9 / "cmd.log"
    (tmp9 / "backup").mkdir()
    rc, out = capture_main(base_env(tree9, db9, tmp9 / "backup", log9))
    expect(rc == 2, "must_absent_fails", failures)
    expect("MUST_ABSENT_PRESENT" in out, "must_absent_finding", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
