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
V2_ZIP = "f3152cdd3f92418da9c7a1f5227410f8fdff94e161ca3dda09c1e33c76bee75c"
V3_APPLY_ZIP = "e1adb68671a18847a1eb162cbb0d16ff6fc950b783a234ec93f811ff62ec788e"
V4_APPLY_ZIP = "8bc2457cf8871b86b62421069e9d4972c636ff74c185d7df753832df0897ed8d"
V1_MEASURE_ZIP = "f78acd66ed1f33b5ee394f4e12397d4de333b2934df7e2737e4bcb53f5c41269"
V2_MEASURE_ZIP = "780b4e6638160bba279670b0e77d064c4196c7d32e3526c77099ee3af08e6bc4"
MEASURE_V2_OUT = "df96d93c11efb6e078b6756e6d9ab561cc68b70f6b6ee67d67d6b2a4f082de7e"
HISTORICAL_BACKUP_SHA = "f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d"


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
    expect("BUSY_TIMEOUT_MS = 8000" in stdin, "busy_timeout", failures)
    expect("Get-RemoteApplyState" in ps, "ps1_parses_remote_apply_state", failures)
    expect("COMMITTED_STATE_KNOWN_AFTER_TIMEOUT" in ps, "ps1_timeout_committed_state", failures)
    expect("HTTP_PUBLIC_TIMEOUT_S = 3" in stdin, "public_http_timeout_3", failures)
    expect("APPLY_PHASE" in stdin, "apply_phase_tracked", failures)
    expect("except sqlite3.Error" in stdin, "sqlite_error_caught", failures)
    expect("AUDIT_CLOSED" in stdin, "audit_closed_emitted", failures)
    expect("GET_UI_CONVERSATION_RA_CHALLENGE_CHANGED\", \"NO\"" not in stdin, "no_unchecked_changed_no", failures)
    expect("GET_UI_CONVERSATION_RA_CHALLENGE_CHANGED=NO" not in stdin, "no_literal_changed_no", failures)
    expect("/v1/prediction-runs" in stdin and "POST_PREDICTION_RUNS" in stdin, "refuses_post_prediction_runs", failures)
    expect("INVENTORY_SOURCE_DEV = 66305" in stdin, "dev_embedded", failures)
    expect("INVENTORY_SOURCE_INO = 349935" in stdin, "ino_embedded", failures)
    expect(HISTORICAL_BACKUP_SHA in stdin, "historical_backup_sha_embedded", failures)
    expect("STALE_BACKUP_NOT_APPLY_CANON" in stdin, "stale_backup_halt", failures)
    expect("APPLY_BACKUP_CANON_UNSET" in stdin, "unset_backup_halt", failures)
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
    expect(V2_ZIP in flags, "v2_zip_recorded", failures)
    expect(V3_APPLY_ZIP in flags, "v3_apply_zip_recorded", failures)
    expect(V4_APPLY_ZIP in flags, "v4_apply_zip_recorded", failures)
    expect(V1_MEASURE_ZIP in flags, "v1_measure_zip_recorded", failures)
    expect(V2_MEASURE_ZIP in flags, "v2_measure_zip_recorded", failures)
    expect(MEASURE_V2_OUT in flags, "measure_v2_output_recorded", failures)
    expect("V4_APPLY_ZIP_OVERWRITE=NO" in flags, "v4_apply_kept", failures)
    expect("V1_MEASURE_ZIP_OVERWRITE=NO" in flags, "v1_measure_kept", failures)
    expect("V2_MEASURE_ZIP_OVERWRITE=NO" in flags, "v2_measure_kept", failures)
    expect("HISTORICAL_BACKUP_NOT_APPLY_CANON=YES" in flags, "old_backup_not_canon", failures)
    expect("APPLY_BACKUP_CANON=PENDING_FRESH_PRODUCTION_BACKUP" in flags, "fresh_backup_pending", failures)
    expect("$TimeoutMs = 240000" in ps, "ps1_wrapper_timeout_240s", failures)
    expect("REMOTE_HARD_DEADLINE_S = 120" in stdin, "remote_deadline_120", failures)
    expect("WRAPPER_TIMEOUT_MS = 240000" in stdin, "stdin_wrapper_timeout", failures)
    expect("SITE_UI_VISUAL_CHECKED" in stdin, "visual_checked_flag", failures)
    expect("INSUFFICIENT_TIME_BEFORE_APPLY" in stdin, "pre_commit_deadline", failures)
    expect("INSUFFICIENT_TIME_AFTER_COMMIT" in stdin, "post_commit_deadline", failures)
    expect(240000 >= 120 * 1000 + 20000 + 8000 + 40000, "wrapper_longer_than_remote_plus_drain", failures)
    expect("HTTP_MAX_JSON_BYTES = 262144" not in stdin, "no_single_json_cap", failures)
    expect("HTTP_MAX_INTERNAL_LIST_BYTES = 2097152" in stdin, "list_cap_2mib", failures)
    expect("HTTP_MAX_INTERNAL_DETAIL_BYTES = 262144" in stdin, "detail_cap", failures)
    expect("HTTP_MAX_INTERNAL_HEALTH_BYTES = 65536" in stdin, "health_cap", failures)
    expect("HTTP_MAX_PUBLIC_JSON_BYTES = 262144" in stdin, "public_json_cap", failures)
    expect("HTTP_ENDPOINT_CLASS" in stdin, "endpoint_class", failures)
    expect("HTTP_BYTES_READ_AT_LEAST" in stdin, "bytes_at_least", failures)
    expect("HTTP_REDIRECT_UNEXPECTED" in stdin, "redirect_guard", failures)
    expect("https://expect-keiba.com" in stdin, "public_expect_origin", failures)
    expect("https://keiba-single-ai.pages.dev" in stdin, "public_pages_origin", failures)
    expect("PENDING_PUBLIC_SMOKE" in stdin, "pending_public_smoke_token", failures)
    expect("PARSER_ENGINE_UNAVAILABLE" in (ROOT / "run_tests.py").read_text(encoding="utf-8"), "parser_unavailable_token", failures)
    run_src = (ROOT / "run_tests.py").read_text(encoding="utf-8")
    expect(run_src.find("ev.write_text") < run_src.find("SUMS.write_text"), "sums_after_evidence", failures)
    expect("sha256sum" in run_src and "-c" in run_src, "independent_sha256sum_c_required", failures)
    expect("STDIN_PAYLOAD_SHA256=" + file_sha(STDIN) in flags, "flags_stdin_sha", failures)
    expect("WINDOWS_ENV_IS_NOT_PRODUCTION_EVIDENCE=YES" in ps, "ps1_windows_not_evidence", failures)
    expect("OWNER_PRODUCTION_022_APPLY_APPROVED=1" in ps, "ps1_forwards_owner_one_only", failures)
    expect("V1_APPLY_ZIP_OVERWRITE=NO" in ps, "ps1_keeps_v1_zip", failures)
    expect("V2_APPLY_ZIP_OVERWRITE=NO" in ps, "ps1_keeps_v2_zip", failures)
    expect("V3_APPLY_ZIP_OVERWRITE=NO" in ps, "ps1_keeps_v3_zip", failures)
    expect("V4_APPLY_ZIP_OVERWRITE=NO" in ps, "ps1_keeps_v4_zip", failures)
    expect("V1_MEASURE_ZIP_OVERWRITE=NO" in ps, "ps1_keeps_v1_measure", failures)
    expect("V2_MEASURE_ZIP_OVERWRITE=NO" in ps, "ps1_keeps_v2_measure", failures)
    expect("WINDOWS_PS51_PARSEFILE=OWNER_CONFIRM_AFTER_INDEPENDENT_REVIEW" in flags, "ps51_deferred", failures)
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
