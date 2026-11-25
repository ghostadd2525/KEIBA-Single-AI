#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "02_powershell" / "OWNER_PROBE.ps1"
STDIN = ROOT / "02_powershell" / "owner_probe_stdin.py"
FLAGS = ROOT / "FLAGS.txt"
MAIN_CAND = "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c"
LIVE_MAIN = "7486a9ad7578e9ccdf883eaaac85f0b0de7ba329e286302b8d2f57db81d79235"


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
    expect("owner_probe_stdin.py" in ps, "ps1_single_stdin_file", failures)
    expect("ReadAllBytes" in ps, "ps1_byte_for_byte", failures)
    expect("Test-PackPayloadSha" in ps, "ps1_pack_sha_gate", failures)
    expect(ps.find("$shaGate = Test-PackPayloadSha") < ps.find("$gate = Test-OwnerApprovalReady"), "sha_before_approval", failures)
    expect(ps.find("Test-OwnerApprovalReady") < ps.find("Invoke-TimedProcess -FileName 'ssh'"), "approval_before_ssh_text", failures)
    expect("scp " not in ps.lower() and "scp " not in stdin.lower(), "no_scp", failures)
    expect("sudo " not in ps.lower(), "wrapper_no_sudo", failures)
    expect('SUDO_NL_ARGV = ("sudo", "-n", "-l")' in stdin, "stdin_sudo_nl_only", failures)
    expect("sudo -n systemctl" not in stdin, "stdin_no_sudo_systemctl", failures)
    expect('RESTART_ARGV' not in stdin, "no_restart_argv", failures)
    expect("SYSTEMCTL_MUTATE_REFUSED" in stdin, "mutate_refused_token", failures)
    expect("SetEnvironmentVariable" not in ps, "no_setenv", failures)
    expect(".Contains(" not in ps, "no_pscustomobject_contains", failures)
    expect("$env:OWNER_READONLY_STEP1_PROBE_APPROVED =" not in ps, "ps1_does_not_assign_approval", failures)
    expect("$env:OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED =" not in ps, "ps1_does_not_assign_deploy_approval", failures)
    expect("OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED=1" not in ps, "ps1_does_not_forward_deploy_approval", failures)
    expect("OWNER_READONLY_STEP1_PROBE_APPROVED=1" in ps, "ps1_forwards_probe_one_only", failures)
    expect("BEGIN IMMEDIATE" not in stdin, "no_begin_immediate", failures)
    expect("migrate(" not in stdin, "no_app_migrate", failures)
    expect("systemctl edit" not in stdin and "systemctl start" not in stdin, "no_systemd_mutate", failures)
    expect("DROP INDEX" not in stdin, "no_drop_index", failures)
    expect("DROP COLUMN" not in stdin, "no_drop_column", failures)
    expect("DELETE FROM predictions" not in stdin, "no_delete_rows", failures)
    expect("CANDIDATE_TAR_GZ_B64" not in stdin, "no_candidate_tar", failures)
    expect("OWNER_MIGRATIONS" in stdin and "022_prediction_run_idempotency" in stdin, "schema_includes_022", failures)
    expect("len(migrations) != 23" in stdin, "expects_23_versions", failures)
    expect("OWNER_PRED_COLUMNS" in stdin, "expects_12_columns", failures)
    expect("uq_predictions_idempotency_key_not_null" in stdin, "partial_unique", failures)
    expect(MAIN_CAND in stdin and MAIN_CAND in flags, "main_candidate_sha", failures)
    expect(LIVE_MAIN in stdin and LIVE_MAIN in flags, "live_main_sha", failures)
    expect("LIVE_OPS_DEPLOY" in stdin, "ops_not_deployed_token", failures)
    expect("PRODUCTION_CODE_DEPLOY_ALLOWED=NO" in flags, "flags_deploy_allowed_no", failures)
    expect("OWNER_DEPLOY_PS1_RERUN_ALLOWED=NO" in flags, "flags_no_rerun", failures)
    expect("POST_CODE_PRODUCTION_DEPLOYED=NO" in flags, "flags_not_deployed", failures)
    expect("CONTRACT_QA_FAILURE=PRE_EXISTING_BASELINE_FAILURE" in flags, "contract_qa_baseline", failures)
    expect("WRAPPER_SETS_OWNER_READONLY_STEP1_PROBE_APPROVED=NO" in flags, "wrapper_no_set_approval", failures)
    expect("WRAPPER_FORWARDS_OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED=NO" in flags, "wrapper_no_forward_deploy", failures)
    expect("THIS_IS_NOT_A_DEPLOY_PACK=YES" in flags, "flags_not_deploy_pack", failures)
    expect("CANDIDATE_TAR_EMBEDDED=NO" in flags, "flags_no_candidate_tar", failures)
    expect("$TimeoutMs = 300000" in ps, "ps1_wrapper_timeout_300s", failures)
    expect("REMOTE_HARD_DEADLINE_S = 180" in stdin, "remote_deadline_180", failures)
    expect(300000 >= 180 * 1000 + 20000 + 8000 + 40000, "wrapper_longer_than_remote_plus_drain", failures)
    expect("JOURNALCTL_TIMEOUT_S = 30" in stdin, "journalctl_timeout_30", failures)
    expect("journalctl -t python3" not in stdin, "no_python3_journal_identifier", failures)
    expect('localhost_ai("/health")' in stdin or "/health" in stdin, "internal_health_get", failures)
    expect("/v1/prediction-runs" not in stdin, "no_prediction_runs_path", failures)
    expect("method=\"POST\"" not in stdin and 'method="POST"' not in stdin, "no_post_method", failures)
    expect("WINDOWS_PS51_PARSEFILE=OWNER_CONFIRM_AFTER_INDEPENDENT_REVIEW" in flags, "ps51_deferred", failures)
    expect("STDIN_PAYLOAD_SHA256=" + file_sha(STDIN) in flags, "flags_stdin_sha", failures)
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
