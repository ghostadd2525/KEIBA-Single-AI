#!/usr/bin/env python3
from __future__ import print_function

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ROOT = Path(__file__).resolve().parent
PS1 = ROOT / "02_powershell" / "OWNER_READONLY.ps1"
PY = ROOT / "02_powershell" / "baseline_disabled_post_dry_run.py"
PATH_PS1 = ROOT / "02_powershell" / "test_wrapper_paths.ps1"
CONTRACT = ROOT / "03_tests" / "test_pack_contract.py"
SUMS = ROOT / "SHA256SUMS.txt"
V1_ZIP = Path("/workspace/production_prediction_run_baseline_disabled_post_dry_run_readonly_20260911.zip")
V1_ZIP_SHA = "2930e43193ca8e17abbc4d0ec2eff79090070efc5bc44727e3e16e866e546663"
V1_PY_IN_ZIP = (
    "production_prediction_run_baseline_disabled_post_dry_run_readonly_20260911/"
    "02_powershell/baseline_disabled_post_dry_run.py"
)
V1_PS1_IN_ZIP = (
    "production_prediction_run_baseline_disabled_post_dry_run_readonly_20260911/"
    "02_powershell/OWNER_READONLY.ps1"
)
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
    r = subprocess.run(
        [engine, "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
    )
    return r


def main():
    expect(V1_ZIP.is_file(), "v1_zip_exists")
    expect(file_sha(V1_ZIP) == V1_ZIP_SHA, "v1_zip_unmodified")
    z = zipfile.ZipFile(str(V1_ZIP))
    v1_py = z.read(V1_PY_IN_ZIP)
    v1_ps1 = z.read(V1_PS1_IN_ZIP)
    expect(PY.read_bytes() == v1_py, "remote_python_byte_identical_v1_zip")
    expect(hashlib.sha256(PY.read_bytes()).hexdigest() == hashlib.sha256(v1_py).hexdigest(), "remote_python_sha_match")
    expect(PS1.read_bytes() != v1_ps1, "wrapper_ps1_not_identical_to_broken_v1")

    engine, engine_name = choose_engine()
    expect(engine is not None, "parser_engine_available")
    print("PARSER_ENGINE=" + str(engine_name))
    print("PARSER_ENGINE_PATH=" + str(engine))
    EVIDENCE.append("PARSER_ENGINE=" + str(engine_name))
    EVIDENCE.append("PARSER_ENGINE_PATH=" + str(engine))
    expect(engine_name in ("powershell.exe", "pwsh"), "parser_engine_named")
    if engine_name == "pwsh":
        print("POWERSHELL_EXE_AVAILABLE=NO")
        EVIDENCE.append("POWERSHELL_EXE_AVAILABLE=NO")
        EVIDENCE.append("NOTE=Windows powershell.exe not on this Linux host; Language.Parser.ParseFile used via pwsh")
    else:
        print("POWERSHELL_EXE_AVAILABLE=YES")
        EVIDENCE.append("POWERSHELL_EXE_AVAILABLE=YES")

    tmp = Path(tempfile.mkdtemp(prefix="dryrun-v2-parse-"))
    v1_ps1_path = tmp / "OWNER_READONLY_v1.ps1"
    v1_ps1_path.write_bytes(v1_ps1)
    v1_parse = parse_file(engine, v1_ps1_path)
    print(v1_parse.stdout)
    if v1_parse.stderr:
        print(v1_parse.stderr)
    EVIDENCE.append("----- V1_PARSEFILE -----")
    EVIDENCE.append(v1_parse.stdout or "")
    expect("PARSE_ERROR_COUNT=4" in (v1_parse.stdout or ""), "v1_parse_error_count_4")
    expect("missing its Catch or Finally" in (v1_parse.stdout or ""), "v1_missing_catch_or_finally")
    expect("Missing closing '}'" in (v1_parse.stdout or ""), "v1_missing_closing_brace")
    expect(v1_parse.returncode != 0, "v1_parsefile_nonzero")

    v2_parse = parse_file(engine, PS1)
    print(v2_parse.stdout)
    if v2_parse.stderr:
        print(v2_parse.stderr)
    EVIDENCE.append("----- V2_PARSEFILE -----")
    EVIDENCE.append(v2_parse.stdout or "")
    expect(v2_parse.returncode == 0, "v2_parsefile_exit0")
    expect("PARSE_ERROR_COUNT=0" in (v2_parse.stdout or ""), "v2_parsefile_count0")

    file_args = [engine, "-NoProfile", "-File", str(PATH_PS1)]
    paths = subprocess.run(file_args, capture_output=True, text=True)
    print("PATHS_ENGINE_INVOCATION=" + " ".join(file_args))
    print(paths.stdout)
    if paths.stderr:
        print(paths.stderr)
    EVIDENCE.append("----- PATHS_FILE -----")
    EVIDENCE.append("INVOCATION=" + " ".join(file_args))
    EVIDENCE.append(paths.stdout or "")
    expect(paths.returncode == 0, "paths_exit0")
    expect("PARSE_ERROR_COUNT=0" in (paths.stdout or ""), "paths_parse0")
    expect("PATH_TEST_FAIL_COUNT=0" in (paths.stdout or ""), "paths_fail0")
    for name in (
        "path_success_wrapper",
        "path_success_stdout",
        "path_success_stderr",
        "path_success_drain_started",
        "path_nonzero_reason_ssh_exit",
        "path_nonzero_stdout",
        "path_nonzero_stderr",
        "path_timeout_reason",
        "path_timeout_drain_started",
        "path_startfail_code",
        "ast_stdout_drain_before_wait",
        "ast_stderr_drain_before_wait",
    ):
        expect(("PASS " + name) in (paths.stdout or ""), "paths_" + name)

    r = subprocess.run([sys.executable, str(CONTRACT)], capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "contract_all_pass")

    expect(SUMS.is_file(), "sha256sums_exists")
    if SUMS.is_file():
        lines = [ln.strip() for ln in SUMS.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
        expect(len(lines) > 5, "sha256sums_nonempty")
        for ln in lines:
            parts = ln.split()
            if len(parts) < 2:
                expect(False, "sha256sums_row")
                continue
            digest, rel = parts[0], parts[-1]
            path = ROOT / rel
            expect(path.is_file(), "sha256sums_file_" + rel.replace("/", "_"))
            if path.is_file():
                expect(file_sha(path) == digest, "sha256sums_match_" + rel.replace("/", "_"))

    ev = ROOT / "03_tests" / "parser_and_paths_evidence.txt"
    # evidence file is written by the caller after first pass; if present, keep
    print("ALL_PASS" if fail == 0 else "FAIL_COUNT=%d" % fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
