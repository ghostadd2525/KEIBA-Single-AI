#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "02_powershell" / "OWNER_DEPLOY_V3.ps1"
STDIN = ROOT / "02_powershell" / "owner_deploy_stdin.py"
FLAGS = ROOT / "FLAGS.txt"
HUNK_V3 = "4d7cdcf6ba9e7d6cc94d903364a302ac7f63bf0ec0db590460b1745b8d9b37ab"
MAIN_CAND = "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c"


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
    expect("owner_deploy_stdin.py" in ps, "ps1_single_stdin_file", failures)
    expect("ReadAllBytes" in ps, "ps1_byte_for_byte", failures)
    expect("Test-PackPayloadSha" in ps, "ps1_pack_sha_gate", failures)
    expect(ps.find("$shaGate = Test-PackPayloadSha") < ps.find("$gate = Test-OwnerApprovalReady"), "sha_before_approval", failures)
    expect(ps.find("Test-OwnerApprovalReady") < ps.find("Invoke-TimedProcess -FileName 'ssh'"), "approval_before_ssh_text", failures)
    expect("scp " not in ps.lower() and "scp " not in stdin.lower(), "no_scp", failures)
    expect("sudo " not in ps.lower(), "wrapper_no_sudo", failures)
    expect('RESTART_ARGV = ("sudo", "-n", "systemctl", "restart", RESTART_UNIT)' in stdin, "restart_argv_sudo_n", failures)
    expect("sudo -n systemctl restart" in stdin, "restart_unit_in_command", failures)
    expect("SUDO_REFUSED" in stdin, "other_sudo_refused", failures)
    expect("SetEnvironmentVariable" not in ps, "no_setenv", failures)
    expect(".Contains(" not in ps, "no_pscustomobject_contains", failures)
    expect("$env:OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED =" not in ps, "ps1_does_not_assign_approval", failures)
    expect("$env:OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED =" not in ps, "ps1_does_not_assign_v2_approval", failures)
    expect("$env:OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED =" not in ps, "ps1_does_not_assign_v1_approval", failures)
    expect("BEGIN IMMEDIATE" not in stdin, "no_begin_immediate", failures)
    expect("migrate(" not in stdin, "no_app_migrate", failures)
    expect("systemctl edit" not in stdin and "systemctl start" not in stdin, "no_systemd_mutate", failures)
    expect('RESTART_UNIT = "expect-ai.service"' in stdin, "restart_unit", failures)
    expect("RESTART_TIMEOUT_S = 60" in stdin, "restart_timeout_60", failures)
    expect("SYSTEMCTL_RESTART_EXIT" in stdin, "records_restart_exit", failures)
    expect("SYSTEMCTL_RESTART_STDERR_REDACTED" in stdin, "records_restart_stderr", failures)
    expect("RESTART_OUTCOME" in stdin, "records_restart_outcome", failures)
    expect("OLD_EXECUTION_PACK_RERUN_REFUSED" in stdin, "refuses_v1_rerun", failures)
    expect("V2_RERUN_ALLOWED" in stdin, "records_v2_rerun_no", failures)
    expect("wait_until_ready" in stdin, "has_wait_until_ready", failures)
    expect("READINESS_POLL_TIMEOUT_S = 45" in stdin, "readiness_timeout_45", failures)
    expect("READINESS_POLL_INTERVAL_S = 1.0" in stdin, "readiness_interval_1", failures)
    expect("READINESS_HTTP_TIMEOUT_S = 2" in stdin, "readiness_http_timeout_2", failures)
    expect("READINESS_MAX_ATTEMPTS = 45" in stdin, "readiness_max_attempts_45", failures)
    expect("READINESS_TIMEOUT" in stdin, "readiness_timeout_halt", failures)
    expect("time.sleep(45" not in stdin and "time.sleep(60" not in stdin, "no_arbitrary_long_sleep", failures)
    expect("def wait_until_ready" in stdin, "wait_fn_defined", failures)
    expect("DROP INDEX" not in stdin, "no_drop_index", failures)
    expect("DROP COLUMN" not in stdin, "no_drop_column", failures)
    expect("DELETE FROM predictions" not in stdin, "no_delete_rows", failures)
    expect("schema rollback" not in stdin.lower() or "SCHEMA_ROLLBACK" in stdin, "schema_rollback_flag_present", failures)
    expect("SCHEMA_ROLLBACK" in stdin, "schema_rollback_token", failures)
    expect("/v1/prediction-runs" in stdin, "disabled_post_probe_path", failures)
    expect("POST_REFUSED" in stdin, "refuses_other_post", failures)
    expect("PREDICTION_RUNS_DISABLED" in stdin, "expects_disabled_code", failures)
    expect("OWNER_MIGRATIONS" in stdin and "022_prediction_run_idempotency" in stdin, "schema_includes_022", failures)
    expect('"rel": "app/data/migrations/022_prediction_run_idempotency.sql"' not in stdin, "022_sql_not_deploy_target", failures)
    expect('    "app/data/migrations/022_prediction_run_idempotency.sql",' in stdin, "022_sql_must_absent", failures)
    expect(not (ROOT / "payload" / "candidates" / "services" / "win5-ai" / "app" / "data" / "migrations" / "022_prediction_run_idempotency.sql").exists(), "022_sql_candidate_file_absent", failures)
    expect("DEPLOY_TARGET_COUNT=10" in flags, "flags_ten_targets", failures)
    expect("len(migrations) != 23" in stdin, "expects_23_versions", failures)
    expect("OWNER_PRED_COLUMNS" in stdin, "expects_12_columns", failures)
    expect("uq_predictions_idempotency_key_not_null" in stdin, "partial_unique", failures)
    expect(MAIN_CAND in stdin and MAIN_CAND in flags, "main_candidate_sha", failures)
    expect(HUNK_V3 in stdin and HUNK_V3 in flags, "hunk_v3_zip_recorded", failures)
    expect("LIVE_OPS_DEPLOY" in stdin, "ops_not_deployed_token", failures)
    expect("PRODUCTION_CODE_DEPLOY_ALLOWED=NO" in flags, "flags_deploy_allowed_no", failures)
    expect("OWNER_DEPLOY_APPROVED=NO" in flags, "flags_owner_no", failures)
    expect("POST_CODE_PRODUCTION_DEPLOYED=NO" in flags, "flags_not_deployed", failures)
    expect("CONTRACT_QA_FAILURE=PRE_EXISTING_BASELINE_FAILURE" in flags, "contract_qa_baseline", failures)
    expect("WRAPPER_SETS_OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED=NO" in flags, "wrapper_no_set_approval", failures)
    expect("V2_RERUN_ALLOWED=NO" in flags, "flags_v2_rerun_no", failures)
    expect("$TimeoutMs = 400000" in ps, "ps1_wrapper_timeout_400s", failures)
    expect("REMOTE_HARD_DEADLINE_S = 300" in stdin, "remote_deadline_300", failures)
    expect(400000 >= 300 * 1000 + 20000 + 8000 + 40000, "wrapper_longer_than_remote_plus_drain", failures)
    expect("HTTP_MAX_INTERNAL_LIST_BYTES = 2097152" in stdin, "list_cap_2mib", failures)
    expect("https://expect-keiba.com" in stdin, "public_expect_origin", failures)
    expect("https://keiba-single-ai.pages.dev" in stdin, "public_pages_origin", failures)
    expect("PENDING_PUBLIC_SMOKE" in stdin, "pending_public_smoke_token", failures)
    expect("WINDOWS_PS51_PARSEFILE=OWNER_CONFIRM_AFTER_INDEPENDENT_REVIEW" in flags, "ps51_deferred", failures)
    expect("STDIN_PAYLOAD_SHA256=" + file_sha(STDIN) in flags, "flags_stdin_sha", failures)
    expect("CANDIDATE_TAR_GZ_B64 = (" in stdin, "candidates_embedded", failures)
    expect('CANDIDATE_TAR_GZ_B64 = "EMBED_CANDIDATE_TAR_GZ_B64"' not in stdin, "candidates_not_placeholder", failures)
    expect("OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED=1" in ps, "ps1_forwards_owner_one_only", failures)
    expect("OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED=1" not in ps, "ps1_does_not_forward_v1_approval", failures)
    expect("OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED=1" not in ps, "ps1_does_not_forward_v2_approval", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_022=1" not in ps, "ps1_does_not_forward_022", failures)
    expect("PREDICTION_RUNS_ENABLED=1" not in ps, "ps1_does_not_forward_post_flag", failures)
    run_src = (ROOT / "run_tests.py").read_text(encoding="utf-8")
    expect("PARSER_ENGINE_UNAVAILABLE" in run_src, "parser_unavailable_token", failures)
    expect(run_src.find("ev.write_text") < run_src.find("SUMS.write_text"), "sums_after_evidence", failures)
    expect("sha256sum" in run_src and "-c" in run_src, "independent_sha256sum_c_required", failures)
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
