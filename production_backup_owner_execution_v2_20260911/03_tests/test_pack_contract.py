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
    expect("systemctl" not in remote and "systemctl" not in ps, "no_systemctl", failures)
    expect("INVENTORY_SOURCE_DEV = None" in remote, "dev_not_invented", failures)
    expect("INVENTORY_SOURCE_INO = None" in remote, "ino_not_invented", failures)
    expect("INVENTORY_DEV_INO_ABSENT" in remote, "absent_identity_halt", failures)
    expect("DB_DRIFT" in remote, "drift_halt", failures)
    expect("022_prediction_run_idempotency" in remote and "HAS_PERSIST_022" in remote, "persist_022_gate", failures)
    expect("PRODUCTION_APPLY_READY=NO" in flags, "flags_apply_ready_no", failures)
    expect("PRODUCTION_BACKUP_EXECUTION_ALLOWED=NO" in flags, "flags_exec_allowed_no", failures)
    expect(V1_ZIP in flags, "v1_zip_recorded", failures)
    expect(APPLY_ZIP in flags, "apply_plan_zip_recorded", failures)
    expect("OWNER_PRODUCTION_BACKUP_APPROVED=NO" in flags, "flags_owner_approved_no", failures)
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
