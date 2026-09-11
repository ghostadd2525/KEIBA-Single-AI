#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "02_powershell" / "OWNER_APPLY.ps1"
STDIN = ROOT / "02_powershell" / "owner_apply_stdin.py"
FLAGS = ROOT / "FLAGS.txt"
APPLY_ZIP = "82d632dcac8169ea15181f80d4a3bc78213850a722cb56b877e2ff4e23aa453d"
V4_ZIP = "67553d9227331b84ffe95e4c6a5fb5d69810509b729e3dc1b02b48d9cf06f69d"
V1_ZIP = "a34855f3dc7967f7801b05cdfad80099b6b5b261b1c2970019fca22cb53335ab"
BACKUP_SHA = "f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d"


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    failures: list[str] = []
    ast.parse(STDIN.read_text(encoding="utf-8"))
    ps = PS1.read_text(encoding="utf-8")
    stdin = STDIN.read_text(encoding="utf-8")
    flags = FLAGS.read_text(encoding="utf-8")
    expect("python3 -" in ps, "stdin_python", failures)
    expect("owner_apply_stdin.py" in ps, "ps1_single_stdin_file", failures)
    expect("ReadAllBytes" in ps, "ps1_byte_for_byte", failures)
    expect('__name__ = "backup_contract"' not in ps, "no_runtime_concat", failures)
    expect("scp " not in ps.lower() and "scp " not in stdin.lower(), "no_scp", failures)
    expect("sudo " not in ps.lower() and "sudo " not in stdin.lower(), "no_sudo", failures)
    expect("SetEnvironmentVariable" not in ps, "no_setenv", failures)
    expect(".Contains(" not in ps, "no_pscustomobject_contains", failures)
    expect("$env:OWNER_PRODUCTION_022_APPLY_APPROVED =" not in ps, "ps1_does_not_assign_approval", failures)
    expect(ps.find("Test-OwnerApprovalReady") < ps.find("Invoke-TimedProcess -FileName 'ssh'"), "approval_before_ssh_text", failures)
    expect("migrate(" not in stdin, "no_app_migrate", failures)
    expect("systemctl start" not in stdin and "systemctl restart" not in stdin and "systemctl edit" not in stdin, "no_systemd_mutate", failures)
    expect("DROP COLUMN" not in stdin, "no_drop_column", failures)
    expect("DELETE FROM predictions" not in stdin, "no_delete_rows", failures)
    expect("UPDATE predictions" not in stdin, "no_update_rows", failures)
    expect("BEGIN IMMEDIATE" in stdin, "begin_immediate", failures)
    expect("busy_timeout=30000" in stdin, "busy_timeout", failures)
    expect("APPLY_PHASE" in stdin, "apply_phase_tracked", failures)
    expect("except sqlite3.Error" in stdin, "sqlite_error_caught", failures)
    expect("AUDIT_CLOSED" in stdin, "audit_closed_emitted", failures)
    expect("GET_UI_CONVERSATION_RA_CHALLENGE_CHANGED\", \"NO\"" not in stdin, "no_unchecked_changed_no", failures)
    expect("GET_UI_CONVERSATION_RA_CHALLENGE_CHANGED=NO" not in stdin, "no_literal_changed_no", failures)
    expect("/v1/prediction-runs" in stdin and "POST_PREDICTION_RUNS" in stdin, "refuses_post_prediction_runs", failures)
    expect("INVENTORY_SOURCE_DEV = 66305" in stdin, "dev_embedded", failures)
    expect("INVENTORY_SOURCE_INO = 349935" in stdin, "ino_embedded", failures)
    expect(BACKUP_SHA in stdin, "backup_sha_embedded", failures)
    expect("022_prediction_run_idempotency" in stdin, "persist_022_name", failures)
    expect("PREDICTION_RUNS_ENABLED" in stdin, "watches_post", failures)
    expect("PRODUCTION_APPLY_READY=NO" in flags, "flags_apply_ready_no", failures)
    expect("OWNER_APPLY_APPROVED=NO" in flags, "flags_owner_apply_no", failures)
    expect("APPLY_EXECUTED=NO" in flags, "flags_apply_executed_no", failures)
    expect("POST_REMAINS_DISABLED_AFTER_022=YES" in flags, "flags_post_disabled", failures)
    expect("PRODUCTION_022_APPLY_EXECUTION_ALLOWED=NO" in flags, "flags_exec_not_allowed", failures)
    expect(APPLY_ZIP in flags, "apply_plan_zip_recorded", failures)
    expect(V4_ZIP in flags, "v4_zip_recorded", failures)
    expect(V1_ZIP in flags, "v1_zip_recorded", failures)
    expect("STDIN_PAYLOAD_SHA256=" + file_sha(STDIN) in flags, "flags_stdin_sha", failures)
    expect("WINDOWS_ENV_IS_NOT_PRODUCTION_EVIDENCE=YES" in ps, "ps1_windows_not_evidence", failures)
    expect("OWNER_PRODUCTION_022_APPLY_APPROVED=1" in ps, "ps1_forwards_owner_one_only", failures)
    expect("V1_APPLY_ZIP_OVERWRITE=NO" in ps, "ps1_keeps_v1_zip", failures)
    expect("WINDOWS_PS51_PARSEFILE=OWNER_CONFIRM_AFTER_INDEPENDENT_REVIEW" in flags, "ps51_deferred", failures)
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
