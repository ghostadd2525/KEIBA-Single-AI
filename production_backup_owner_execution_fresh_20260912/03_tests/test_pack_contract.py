#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "02_powershell" / "OWNER_BACKUP.ps1"
REMOTE = ROOT / "02_powershell" / "owner_backup_remote.py"
STDIN = ROOT / "02_powershell" / "owner_backup_stdin.py"
CONTRACT = ROOT / "02_powershell" / "backup_contract.py"
FLAGS = ROOT / "FLAGS.txt"
REVIEWED = "55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e"
V1_ZIP = "35ef43ad03c0da93f76d85b3513ae8dcb32506468c22012e4bcd098ee6b33e19"
V2_ZIP = "5675a8a3f4171e466620dc51c6e626667417a8f57e2df769730129da6da0409a"
V3_ZIP = "6a36403eb758fb2a176480bd8fb05fc001a1d878888513e49588ca18cc6327f8"
V4_BACKUP_ZIP = "67553d9227331b84ffe95e4c6a5fb5d69810509b729e3dc1b02b48d9cf06f69d"
APPLY_ZIP = "82d632dcac8169ea15181f80d4a3bc78213850a722cb56b877e2ff4e23aa453d"
V5_APPLY_ZIP = "60cef7b2354d2c3a4b49e6a5f687537cc6188936ccbf9534ba070ca7667f84d8"
MEASURE_V1_ZIP = "f78acd66ed1f33b5ee394f4e12397d4de333b2934df7e2737e4bcb53f5c41269"
MEASURE_V2_ZIP = "780b4e6638160bba279670b0e77d064c4196c7d32e3526c77099ee3af08e6bc4"
HISTORICAL_SHA = "f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d"


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
    ast.parse(STDIN.read_text(encoding="utf-8"))
    ps = PS1.read_text(encoding="utf-8")
    remote = REMOTE.read_text(encoding="utf-8")
    stdin = STDIN.read_text(encoding="utf-8")
    flags = FLAGS.read_text(encoding="utf-8")
    expect(file_sha(CONTRACT) == REVIEWED, "contract_byte_identical_v2", failures)
    expect("python3 -" in ps, "stdin_python", failures)
    expect("owner_backup_stdin.py" in ps, "ps1_single_stdin_file", failures)
    expect("ReadAllBytes" in ps, "ps1_byte_for_byte", failures)
    expect('__name__ = "backup_contract"' not in ps, "no_runtime_concat", failures)
    expect("scp " not in ps.lower() and "scp " not in remote.lower(), "no_scp", failures)
    expect("sudo " not in ps.lower(), "no_sudo", failures)
    expect("SetEnvironmentVariable" not in ps, "no_setenv", failures)
    expect(".Contains(" not in ps, "no_pscustomobject_contains", failures)
    expect("$env:OWNER_PRODUCTION_BACKUP_APPROVED =" not in ps, "ps1_does_not_assign_approval", failures)
    expect("Test-OwnerApprovalReady" in ps, "approval_fn", failures)
    expect("Invoke-TimedProcess -FileName 'ssh'" in ps, "ssh_via_timed_process", failures)
    expect(ps.find("Test-OwnerApprovalReady") < ps.find("Invoke-TimedProcess -FileName 'ssh'"), "approval_before_ssh_text", failures)
    expect("migrate(" not in remote and "migrate(" not in stdin, "remote_no_migrate", failures)
    expect("systemctl start" not in remote and "systemctl restart" not in remote, "no_systemd_mutate", failures)
    expect("sudo " not in remote, "remote_no_sudo", failures)
    expect("INVENTORY_SOURCE_DEV = 66305" in remote and "INVENTORY_SOURCE_DEV = 66305" in stdin, "dev_embedded", failures)
    expect("INVENTORY_SOURCE_INO = 349935" in remote and "INVENTORY_SOURCE_INO = 349935" in stdin, "ino_embedded", failures)
    expect("INVENTORY_DEV_INO_ABSENT_WITHDRAWN" in remote, "absent_withdrawn", failures)
    expect("DB_DRIFT" in remote, "drift_halt", failures)
    expect("PRODUCTION_ENV_UNDETERMINED" in remote, "env_undetermined_halt", failures)
    expect("RAW_ENVIRONMENT_LOGGED" in remote, "no_raw_env_flag", failures)
    expect("systemctl" in remote and "-p" in remote and "Environment" in remote, "reads_systemd_show", failures)
    expect("LoadState" in remote and "EnvironmentFiles" in remote, "reads_loadstate_and_envfiles", failures)
    expect("/proc/" in remote and "environ" in remote, "reads_proc_environ", failures)
    expect("systemctl start" not in remote and "systemctl restart" not in remote and "systemctl stop" not in remote, "no_systemd_mutate_verbs", failures)
    expect("022_prediction_run_idempotency" in remote and "HAS_PERSIST_022" in remote, "persist_022_gate", failures)
    expect(sum(1 for ln in stdin.splitlines() if ln.startswith("from __future__ import")) == 1, "stdin_one_future", failures)
    expect("PRODUCTION_APPLY_READY=NO" in flags, "flags_apply_ready_no", failures)
    expect("PRODUCTION_BACKUP_EXECUTION_ALLOWED=NO" in flags, "flags_exec_allowed_no", failures)
    expect(V1_ZIP in flags, "v1_zip_recorded", failures)
    expect(V2_ZIP in flags, "v2_zip_recorded", failures)
    expect(V3_ZIP in flags, "v3_zip_recorded", failures)
    expect(APPLY_ZIP in flags, "apply_plan_zip_recorded", failures)
    expect("OWNER_PRODUCTION_BACKUP_APPROVED=NO" in flags, "flags_owner_approved_no", failures)
    expect("BACKUP_OWNER_V3_REVIEW=FAILED_RUNTIME_PAYLOAD_SYNTAX" in flags, "flags_v3_failed_syntax", failures)
    expect("STDIN_PAYLOAD_SHA256=" + file_sha(STDIN) in flags, "flags_stdin_sha", failures)
    expect("WINDOWS_ENV_IS_NOT_PRODUCTION_EVIDENCE=YES" in ps, "ps1_windows_not_evidence", failures)
    expect("OWNER_PRODUCTION_BACKUP_APPROVED=1" in ps, "ps1_forwards_owner_one_only", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_022=" not in ps.split("OWNER_PRODUCTION_BACKUP_APPROVED=1")[-1], "ps1_does_not_forward_022", failures)
    expect("INVENTORY_SOURCE_DEV=66305" in flags, "flags_dev", failures)
    expect("INVENTORY_DEV_INO_ABSENT_WITHDRAWN=YES" in flags, "flags_absent_withdrawn", failures)
    expect("PRODUCTION_022_APPLY_PLAN_REVIEW=PASS" in flags, "flags_apply_plan_pass", failures)
    expect("BACKUP_OWNER_V2_REVIEW=CHANGES_REQUIRED" in flags, "flags_v2_changes_required", failures)
    expect(V4_BACKUP_ZIP in flags, "v4_backup_zip_recorded", failures)
    expect(V5_APPLY_ZIP in flags, "v5_apply_zip_recorded", failures)
    expect(MEASURE_V1_ZIP in flags, "measure_v1_zip_recorded", failures)
    expect(MEASURE_V2_ZIP in flags, "measure_v2_zip_recorded", failures)
    expect(HISTORICAL_SHA in flags and HISTORICAL_SHA in remote, "historical_sha_recorded", failures)
    expect("PACK=production_backup_owner_execution_fresh_20260912" in flags, "flags_fresh_pack", failures)
    expect("FRESH_LIVE_BACKUP_ONLY=YES" in flags, "flags_fresh_live_only", failures)
    expect("HISTORICAL_BACKUP_DEST_REFUSED" in remote, "remote_historical_dest_token", failures)
    expect("HISTORICAL_BACKUP_NOT_APPLY_CANON=YES" in flags, "flags_historical_not_canon", failures)
    expect("HISTORICAL_BACKUP_DELETE=NO" in flags, "flags_historical_delete_no", failures)
    expect("HISTORICAL_BACKUP_OVERWRITE=NO" in flags, "flags_historical_overwrite_no", failures)
    expect("AUTO_BACKUP_RESTORE=NO" in flags, "flags_no_auto_restore", failures)
    expect("restore_rehearse=False" in remote, "remote_restore_rehearse_false", failures)
    expect("V5_OWNER_EXECUTION_ALLOWED=NO" in flags, "flags_v5_exec_no", failures)
    expect("V5_APPLY_PACK_OVERWRITE=NO" in flags, "flags_v5_overwrite_no", failures)
    expect("MEASURE_V1_OVERWRITE=NO" in flags, "flags_measure_v1_overwrite_no", failures)
    expect("MEASURE_V2_OVERWRITE=NO" in flags, "flags_measure_v2_overwrite_no", failures)
    expect("APPLY_OWNER_V1_OVERWRITE=NO" in flags, "flags_apply_v1_overwrite_no", failures)
    expect("APPLY_OWNER_V4_OVERWRITE=NO" in flags, "flags_apply_v4_overwrite_no", failures)
    expect("PRODUCTION_022_APPLY_EXECUTION_ALLOWED=NO" in flags, "flags_apply_exec_no", failures)
    expect("APPLY_EXECUTED=NO" in flags, "flags_apply_executed_no", failures)
    expect("FRESH_BACKUP_CANON_PINNED_IN_APPLY_PACK=NO" in flags, "flags_canon_not_pinned", failures)
    expect("APPLY_APPROVAL_NOT_ALLOWED_IN_BACKUP_PACK" in ps, "ps1_apply_approval_halt_token", failures)
    expect(
        ps.find("APPLY_APPROVAL_NOT_ALLOWED_IN_BACKUP_PACK") < ps.find("Invoke-TimedProcess -FileName 'ssh'"),
        "ps1_apply_approval_halt_before_ssh",
        failures,
    )
    expect(not (ROOT / "02_powershell" / "OWNER_APPLY.ps1").exists(), "no_owner_apply_ps1", failures)
    absent = (ROOT / "01_docs" / "inventory_identity_absent.txt").read_text(encoding="utf-8")
    expect("WITHDRAWN" in absent and "66305" in absent, "absent_doc_withdrawn", failures)
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
