#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "02_powershell" / "OWNER_BACKUP.ps1"
REMOTE = ROOT / "02_powershell" / "owner_backup_remote.py"
CONTRACT = ROOT / "02_powershell" / "backup_contract.py"
FLAGS = ROOT / "FLAGS.txt"
REVIEWED = "55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e"
V1_ZIP = "35ef43ad03c0da93f76d85b3513ae8dcb32506468c22012e4bcd098ee6b33e19"
V2_ZIP = "5675a8a3f4171e466620dc51c6e626667417a8f57e2df769730129da6da0409a"
APPLY_ZIP = "82d632dcac8169ea15181f80d4a3bc78213850a722cb56b877e2ff4e23aa453d"


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    failures: list[str] = []
    ast.parse(REMOTE.read_text(encoding="utf-8"))
    ps = PS1.read_text(encoding="utf-8")
    remote = REMOTE.read_text(encoding="utf-8")
    flags = FLAGS.read_text(encoding="utf-8")
    expect(file_sha(CONTRACT) == REVIEWED, "contract_byte_identical_v2", failures)
    expect("python3 -" in ps, "stdin_python", failures)
    expect("scp " not in ps.lower() and "scp " not in remote.lower(), "no_scp", failures)
    expect("sudo " not in ps.lower(), "no_sudo", failures)
    expect("SetEnvironmentVariable" not in ps, "no_setenv", failures)
    expect(".Contains(" not in ps, "no_pscustomobject_contains", failures)
    expect("$env:OWNER_PRODUCTION_BACKUP_APPROVED =" not in ps, "ps1_does_not_assign_approval", failures)
    expect("Test-OwnerApprovalReady" in ps, "approval_fn", failures)
    expect("Invoke-TimedProcess -FileName 'ssh'" in ps, "ssh_via_timed_process", failures)
    expect(ps.find("Test-OwnerApprovalReady") < ps.find("Invoke-TimedProcess -FileName 'ssh'"), "approval_before_ssh_text", failures)
    expect("migrate(" not in remote, "remote_no_migrate", failures)
    expect("systemctl start" not in remote and "systemctl restart" not in remote, "no_systemd_mutate", failures)
    expect("sudo " not in remote, "remote_no_sudo", failures)
    expect("INVENTORY_SOURCE_DEV = 66305" in remote, "dev_embedded", failures)
    expect("INVENTORY_SOURCE_INO = 349935" in remote, "ino_embedded", failures)
    expect("INVENTORY_DEV_INO_ABSENT_WITHDRAWN" in remote, "absent_withdrawn", failures)
    expect("DB_DRIFT" in remote, "drift_halt", failures)
    expect("PRODUCTION_ENV_UNDETERMINED" in remote, "env_undetermined_halt", failures)
    expect("RAW_ENVIRONMENT_LOGGED" in remote, "no_raw_env_flag", failures)
    expect("systemctl" in remote and "-p" in remote and "Environment" in remote, "reads_systemd_show", failures)
    expect("LoadState" in remote and "EnvironmentFiles" in remote, "reads_loadstate_and_envfiles", failures)
    expect("/proc/" in remote and "environ" in remote, "reads_proc_environ", failures)
    expect("systemctl start" not in remote and "systemctl restart" not in remote and "systemctl stop" not in remote, "no_systemd_mutate_verbs", failures)
    expect("022_prediction_run_idempotency" in remote and "HAS_PERSIST_022" in remote, "persist_022_gate", failures)
    expect("PRODUCTION_APPLY_READY=NO" in flags, "flags_apply_ready_no", failures)
    expect("PRODUCTION_BACKUP_EXECUTION_ALLOWED=NO" in flags, "flags_exec_allowed_no", failures)
    expect(V1_ZIP in flags, "v1_zip_recorded", failures)
    expect(V2_ZIP in flags, "v2_zip_recorded", failures)
    expect(APPLY_ZIP in flags, "apply_plan_zip_recorded", failures)
    expect("OWNER_PRODUCTION_BACKUP_APPROVED=NO" in flags, "flags_owner_approved_no", failures)
    expect("WINDOWS_ENV_IS_NOT_PRODUCTION_EVIDENCE=YES" in ps, "ps1_windows_not_evidence", failures)
    expect("OWNER_PRODUCTION_BACKUP_APPROVED=1" in ps, "ps1_forwards_owner_one_only", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_022=" not in ps.split("OWNER_PRODUCTION_BACKUP_APPROVED=1")[-1], "ps1_does_not_forward_022", failures)
    expect("INVENTORY_SOURCE_DEV=66305" in flags, "flags_dev", failures)
    expect("INVENTORY_DEV_INO_ABSENT_WITHDRAWN=YES" in flags, "flags_absent_withdrawn", failures)
    expect("PRODUCTION_022_APPLY_PLAN_REVIEW=PASS" in flags, "flags_apply_plan_pass", failures)
    expect("BACKUP_OWNER_V2_REVIEW=CHANGES_REQUIRED" in flags, "flags_v2_changes_required", failures)
    absent = (ROOT / "01_docs" / "inventory_identity_absent.txt").read_text(encoding="utf-8")
    expect("WITHDRAWN" in absent and "66305" in absent, "absent_doc_withdrawn", failures)
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
