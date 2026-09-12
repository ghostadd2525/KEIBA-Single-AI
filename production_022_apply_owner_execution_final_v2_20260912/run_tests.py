#!/usr/bin/env python3
from __future__ import print_function

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
PS1 = ROOT / "02_powershell" / "OWNER_APPLY.ps1"
PATH_PS1 = ROOT / "02_powershell" / "test_wrapper_paths.ps1"
SUMS = ROOT / "SHA256SUMS.txt"
EXPECTED_STDIN_SHA = "9a506fa195ddc4b88eaabfe10a28967fa46c537e8443ada6ef629531e93e18cf"
OUTPUT_GLOB = "production_022_apply_owner_execution_final_v2_20260912_output_*.txt"
fail = 0
EVIDENCE = []


def expect(cond, name):
    global fail
    print(("PASS " if cond else "FAIL ") + name)
    EVIDENCE.append(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fail += 1


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def choose_engine():
    exe = shutil.which("powershell.exe")
    if exe:
        return exe, "powershell.exe"
    pwsh = shutil.which("pwsh")
    if pwsh:
        return pwsh, "pwsh"
    return None, None


def resolve_parser_engine():
    if os.environ.get("OWNER_APPLY_TEST_NO_PARSER") == "1":
        return None, None
    return choose_engine()


def finalize_evidence_and_sums():
    ev = ROOT / "03_tests" / "parser_and_paths_evidence.txt"
    ev.write_text("\n".join(EVIDENCE) + "\n", encoding="utf-8")
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt" and "__pycache__" not in path.parts:
            rows.append("%s  %s" % (file_sha(path), path.relative_to(ROOT).as_posix()))
    SUMS.write_text("\n".join(rows) + "\n", encoding="utf-8")
    expect(SUMS.is_file(), "sums")
    dest = Path(tempfile.mkdtemp(prefix="applyfinalv2-sums-")) / "production_022_apply_owner_execution_final_v2_20260912"
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    chk = subprocess.run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=str(dest), capture_output=True, text=True)
    print(chk.stdout)
    if chk.stderr:
        print(chk.stderr)
    expect(chk.returncode == 0 and "FAILED" not in (chk.stdout or ""), "independent_sha256sum_c")


def parse_file(engine, path):
    cmd = (
        "$e=$null; $t=$null; "
        "[void][System.Management.Automation.Language.Parser]::ParseFile("
        "'%s', [ref]$t, [ref]$e); "
        "Write-Output ('PS_VERSION=' + [string]$PSVersionTable.PSVersion); "
        "Write-Output ('PS_EDITION=' + [string]$PSVersionTable.PSEdition); "
        "Write-Output ('PARSE_ERROR_COUNT=' + $e.Count); "
        "if ($e.Count -ne 0) { foreach ($x in $e) { Write-Output ('ERR=' + $x.ToString()) } }; "
        "exit ([int]$e.Count)"
    ) % str(path).replace("'", "''")
    return subprocess.run([engine, "-NoProfile", "-Command", cmd], capture_output=True, text=True)


def print_pending_verify():
    print("LOCAL_VERIFY=PENDING_WINDOWS_PS51_PARSEFILE")
    print("WINDOWS_PS51_PARSEFILE=OWNER_CONFIRM_AFTER_INDEPENDENT_REVIEW")
    print("OFFICIAL_ALL_PASS=NO")


def run_owner_apply_with_payload(engine, env_base, payload_bytes):
    tmp = Path(tempfile.mkdtemp(prefix="applyfinalv2-sha-"))
    downloads = tmp / "Downloads"
    downloads.mkdir()
    work = tmp / "02_powershell"
    work.mkdir()
    shutil.copy2(PS1, work / "OWNER_APPLY.ps1")
    (work / "owner_apply_stdin.py").write_bytes(payload_bytes)
    run_env = env_base.copy()
    run_env["USERPROFILE"] = str(tmp)
    run_env["OWNER_PRODUCTION_022_APPLY_APPROVED"] = "1"
    run_env["PREDICTION_RUNS_ENABLED"] = "0"
    run_env.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
    proc = subprocess.run(
        [engine, "-NoProfile", "-File", str(work / "OWNER_APPLY.ps1")],
        capture_output=True,
        text=True,
        env=run_env,
    )
    logs = list(downloads.glob(OUTPUT_GLOB))
    body = logs[0].read_text(encoding="utf-8") if logs else ""
    combined = (proc.stdout or "") + "\n" + body
    return proc, logs, body, combined


def expect_sha_mismatch_halt(proc, logs, body, combined, name):
    expect(proc.returncode == 2, name + "_exit2")
    expect(len(logs) == 1, name + "_output_file")
    expect("STDIN_PAYLOAD_SHA256_MATCH=NO" in combined, name + "_match_no")
    expect("SSH_STARTED=NO" in combined, name + "_ssh_no")
    expect("SSH_STARTED=YES" not in combined, name + "_no_ssh_started_yes")
    expect("HALT_REASON=STDIN_PAYLOAD_SHA256_MISMATCH" in combined, name + "_halt_reason")
    expect("OWNER_APPLY_STATUS=FAIL" in combined, name + "_status_fail")
    expect("APPLY_EXECUTED=NO" in combined, name + "_apply_no")
    expect("PRODUCTION_APPLY_READY=NO" in combined, name + "_ready_no")
    expect("MIGRATION_MAY_PROCEED=NO" in combined, name + "_migrate_no")
    expect("REMOTE_STDOUT" not in body, name + "_no_remote_stdout")
    expect("SSH_TIMEOUT=" not in body, name + "_no_ssh_timeout")
    expect("SSH_EXIT_RAW=" not in body, name + "_no_ssh_exit_raw")
    expect("Invoke-TimedProcess" not in (proc.stdout or ""), name + "_no_invoke_in_stdout")


def main():
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("OWNER_PRODUCTION_022_APPLY_APPROVED", None)
    env.pop("OWNER_PRODUCTION_BACKUP_APPROVED", None)
    env["PREDICTION_RUNS_ENABLED"] = "0"

    r = subprocess.run([sys.executable, str(ROOT / "03_tests" / "test_pack_contract.py")], capture_output=True, text=True, env=env)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "pack_contract")

    r = subprocess.run([sys.executable, str(ROOT / "03_tests" / "test_stdin_payload.py")], capture_output=True, text=True, env=env)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "stdin_payload")

    r = subprocess.run([sys.executable, str(ROOT / "03_tests" / "test_apply_remote.py")], capture_output=True, text=True, env=env)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "apply_remote")

    r = subprocess.run([sys.executable, str(ROOT / "03_tests" / "test_parser_unavailable.py")], capture_output=True, text=True, env=env)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "parser_unavailable")

    engine, engine_name = resolve_parser_engine()
    if engine is None:
        print("PARSER_ENGINE_UNAVAILABLE")
        EVIDENCE.append("PARSER_ENGINE_UNAVAILABLE")
        expect(False, "parser_engine_available")
        finalize_evidence_and_sums()
        print_pending_verify()
        print("FAIL_COUNT=%d" % fail)
        return 1

    expect(True, "parser_engine_available")
    print("PARSER_ENGINE=" + str(engine_name))
    EVIDENCE.append("PARSER_ENGINE=" + str(engine_name))
    if engine_name == "pwsh":
        EVIDENCE.append("NOTE=Windows powershell.exe not on this Linux host; Language.Parser.ParseFile used via pwsh")
        EVIDENCE.append("WINDOWS_PS51_PARSEFILE=OWNER_CONFIRM_AFTER_INDEPENDENT_REVIEW")
        EVIDENCE.append("OFFICIAL_ALL_PASS=NO")
    elif engine_name == "powershell.exe":
        EVIDENCE.append("WINDOWS_PS51_PARSEFILE=LOCAL_PARSEFILE_RAN")
        EVIDENCE.append("OFFICIAL_ALL_PASS=NO")
        EVIDENCE.append("NOTE=Owner still confirms PARSE_ERROR_COUNT=0 on the review machine")

    parsed = parse_file(engine, PS1)
    print(parsed.stdout)
    if parsed.stderr:
        print(parsed.stderr)
    EVIDENCE.append(parsed.stdout or "")
    expect(parsed.returncode == 0, "parsefile_exit0")
    expect("PARSE_ERROR_COUNT=0" in (parsed.stdout or ""), "parsefile_count0")

    paths = subprocess.run([engine, "-NoProfile", "-File", str(PATH_PS1)], capture_output=True, text=True, env=env)
    print(paths.stdout)
    if paths.stderr:
        print(paths.stderr)
    EVIDENCE.append(paths.stdout or "")
    expect(paths.returncode == 0, "paths_exit0")
    expect("PARSE_ERROR_COUNT=0" in (paths.stdout or ""), "paths_parse0")
    expect("PATH_TEST_FAIL_COUNT=0" in (paths.stdout or ""), "paths_fail0")
    for name in (
        "path_success_wrapper",
        "path_nonzero_reason_ssh_exit",
        "path_timeout_reason",
        "path_timeout_after_commit_executed_yes",
        "path_timeout_after_commit_phase_committed",
        "path_timeout_after_commit_not_unknown",
        "path_startfail_code",
        "path_success_drain_started",
        "approval_unset_not_ready",
        "approval_ready_when_explicit",
        "windows_env_not_prod_evidence",
        "approval_check_before_ssh",
        "no_pscustomobject_contains",
        "ast_stdout_drain_before_wait",
        "reads_pregenerated_stdin",
        "stdin_readallbytes",
        "no_runtime_name_concat",
        "canon_unset_not_ready",
        "canon_historical_not_ready",
        "canon_mismatch_not_ready",
        "canon_ready_when_pinned",
        "canon_check_before_ssh",
        "stdin_bundled_sha_matches_expected",
        "stdin_sha_correct_ready",
        "stdin_sha_correct_reason",
        "stdin_sha_1byte_changes",
        "stdin_sha_1byte_not_ready",
        "stdin_sha_1byte_reason",
        "stdin_sha_empty_not_ready",
        "stdin_sha_empty_reason",
        "stdin_sha_other_python_not_ready",
        "stdin_sha_other_python_reason",
        "stdin_sha_blank_not_ready",
        "ps1_has_expected_stdin_sha",
        "stdin_sha_check_before_ssh",
        "stdin_sha_match_yes_before_ssh",
        "stdin_sha_mismatch_halt_before_ssh",
    ):
        expect(("PASS " + name) in (paths.stdout or ""), "paths_" + name)

    tmp = Path(tempfile.mkdtemp(prefix="applyfinalv2-halt-"))
    downloads = tmp / "Downloads"
    downloads.mkdir()
    halt_env = env.copy()
    halt_env["USERPROFILE"] = str(tmp)
    halt_env.pop("OWNER_PRODUCTION_022_APPLY_APPROVED", None)
    halt_env.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
    halt = subprocess.run(
        [engine, "-NoProfile", "-File", str(PS1)],
        capture_output=True,
        text=True,
        env=halt_env,
    )
    print(halt.stdout)
    if halt.stderr:
        print(halt.stderr)
    expect(halt.returncode == 2, "ps1_unapproved_exit2")
    expect("SSH_STARTED=NO" in (halt.stdout or ""), "ps1_unapproved_no_ssh")
    expect("OWNER_PRODUCTION_022_APPLY_APPROVED_UNSET" in (halt.stdout or ""), "ps1_unapproved_reason")
    logs = list(downloads.glob(OUTPUT_GLOB))
    expect(len(logs) == 1, "ps1_output_file_created")
    if logs:
        body = logs[0].read_text(encoding="utf-8")
        expect("SSH_STARTED=NO" in body, "ps1_log_ssh_no")
        expect("REMOTE_STDOUT" not in body, "ps1_no_remote_block")

    correct = (ROOT / "02_powershell" / "owner_apply_stdin.py").read_bytes()
    expect(hashlib.sha256(correct).hexdigest() == EXPECTED_STDIN_SHA, "correct_payload_sha_constant")
    # Correct payload + approval=1 would start Production SSH. Do not run that.
    # SHA-match + proceed-to-SSH is covered by function tests and source order.
    EVIDENCE.append("CORRECT_PAYLOAD_FULL_PS1_WITH_APPROVAL=NOT_RUN")
    EVIDENCE.append("CORRECT_PAYLOAD_SSH_PROCEED=FUNCTION_AND_SOURCE_ORDER_ONLY")

    mutated = bytearray(correct)
    mutated[0] = (mutated[0] + 1) % 256
    proc, logs, body, combined = run_owner_apply_with_payload(engine, env, bytes(mutated))
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    expect_sha_mismatch_halt(proc, logs, body, combined, "mutated_1byte")

    proc, logs, body, combined = run_owner_apply_with_payload(engine, env, b"")
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    expect_sha_mismatch_halt(proc, logs, body, combined, "empty_payload")

    other_py = b"#!/usr/bin/env python3\nprint('not-the-owner-apply-stdin')\n"
    proc, logs, body, combined = run_owner_apply_with_payload(engine, env, other_py)
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    expect_sha_mismatch_halt(proc, logs, body, combined, "other_python")

    finalize_evidence_and_sums()
    print_pending_verify()
    if fail == 0:
        print("LOCAL_TESTS_PASS_PENDING_WINDOWS_PS51_PARSEFILE")
    else:
        print("FAIL_COUNT=%d" % fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
