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
PS1 = ROOT / "02_powershell" / "OWNER_MEASURE.ps1"
PATH_PS1 = ROOT / "02_powershell" / "test_wrapper_paths.ps1"
SUMS = ROOT / "SHA256SUMS.txt"
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
    if os.environ.get("OWNER_MEASURE_TEST_NO_PARSER") == "1":
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
    dest = Path(tempfile.mkdtemp(prefix="measure-sums-")) / "production_022_readonly_response_size_measure_v2_20260911"
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


def main():
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("OWNER_PRODUCTION_022_MEASURE_APPROVED", None)
    env.pop("OWNER_PRODUCTION_022_APPLY_APPROVED", None)
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

    r = subprocess.run([sys.executable, str(ROOT / "03_tests" / "test_measure_remote.py")], capture_output=True, text=True, env=env)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "measure_remote")

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
        print("ALL_PASS" if fail == 0 else "FAIL_COUNT=%d" % fail)
        return 1

    expect(True, "parser_engine_available")
    print("PARSER_ENGINE=" + str(engine_name))
    EVIDENCE.append("PARSER_ENGINE=" + str(engine_name))
    if engine_name == "pwsh":
        EVIDENCE.append("NOTE=Windows powershell.exe not on this Linux host; Language.Parser.ParseFile used via pwsh")
        EVIDENCE.append("WINDOWS_PS51_PARSEFILE=OWNER_CONFIRM_AFTER_LOCAL_VERIFY")

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
    expect("PATH_TEST_FAIL_COUNT=0" in (paths.stdout or ""), "paths_fail0")
    for name in (
        "path_success_wrapper",
        "path_nonzero_reason_ssh_exit",
        "path_timeout_reason",
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
    ):
        expect(("PASS " + name) in (paths.stdout or ""), "paths_" + name)

    tmp = Path(tempfile.mkdtemp(prefix="measure-halt-"))
    downloads = tmp / "Downloads"
    downloads.mkdir()
    halt_env = env.copy()
    halt_env["USERPROFILE"] = str(tmp)
    halt_env.pop("OWNER_PRODUCTION_022_MEASURE_APPROVED", None)
    halt = subprocess.run([engine, "-NoProfile", "-File", str(PS1)], capture_output=True, text=True, env=halt_env)
    print(halt.stdout)
    if halt.stderr:
        print(halt.stderr)
    expect(halt.returncode == 2, "ps1_unapproved_exit2")
    expect("SSH_STARTED=NO" in (halt.stdout or ""), "ps1_unapproved_no_ssh")
    expect("OWNER_PRODUCTION_022_MEASURE_APPROVED_UNSET" in (halt.stdout or ""), "ps1_unapproved_reason")
    logs = list(downloads.glob("production_022_readonly_response_size_measure_v2_20260911_output_*.txt"))
    expect(len(logs) == 1, "ps1_output_file_created")
    if logs:
        body = logs[0].read_text(encoding="utf-8")
        expect("SSH_STARTED=NO" in body, "ps1_log_ssh_no")
        expect("REMOTE_STDOUT" not in body, "ps1_no_remote_block")

    finalize_evidence_and_sums()
    print("ALL_PASS" if fail == 0 else "FAIL_COUNT=%d" % fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
