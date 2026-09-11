#!/usr/bin/env python3
from __future__ import print_function

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ROOT = Path(__file__).resolve().parent
PS1 = ROOT / "02_powershell" / "OWNER_READONLY.ps1"
PY = ROOT / "02_powershell" / "baseline_disabled_post_dry_run.py"
CONTRACT = ROOT / "03_tests" / "test_pack_contract.py"
SUMS = ROOT / "SHA256SUMS.txt"
fail = 0


def expect(cond, name):
    global fail
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fail += 1


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_ps():
    ps = PS1.read_text(encoding="utf-8")
    expect("??" not in ps, "ps51_no_null_coalesce")
    expect(re.search(r"\?\.\w", ps) is None, "ps51_no_null_conditional")
    expect(" && " not in ps, "ps51_no_andand")
    expect(" || " not in ps, "ps51_no_oror")
    start_i = ps.find("[void]$proc.Start()")
    out_i = ps.find("$stdoutTask = $proc.StandardOutput.ReadToEndAsync()")
    err_i = ps.find("$stderrTask = $proc.StandardError.ReadToEndAsync()")
    wait_i = ps.find("$proc.WaitForExit($TimeoutMs)")
    expect(start_i != -1 and out_i > start_i and out_i < wait_i, "stdout_drain_before_wait")
    expect(start_i != -1 and err_i > start_i and err_i < wait_i, "stderr_drain_before_wait")
    expect("python3 -" in ps, "stdin")
    expect("scp " not in ps.lower(), "no_scp")
    expect("POST_ENDPOINT_CALLED=NO" in ps, "no_post_flag")
    expect("baseline_disabled_post_dry_run_readonly_20260911" in ps, "pack_output_name")


def test_compile():
    r = subprocess.run([sys.executable, "-m", "py_compile", str(PY), str(CONTRACT)], capture_output=True, text=True)
    expect(r.returncode == 0, "python_compile")
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)


def test_sums():
    expect(SUMS.is_file(), "sha256sums_exists")
    if not SUMS.is_file():
        return
    lines = [ln.strip() for ln in SUMS.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    expect(len(lines) > 5, "sha256sums_nonempty")
    for ln in lines:
        parts = ln.split()
        expect(len(parts) >= 2, "sha256sums_row")
        if len(parts) < 2:
            continue
        digest, rel = parts[0], parts[-1]
        path = ROOT / rel
        expect(path.is_file(), "sha256sums_file_" + rel.replace("/", "_"))
        if path.is_file():
            expect(sha256_file(path) == digest, "sha256sums_match_" + rel.replace("/", "_"))


def main():
    test_ps()
    test_compile()
    test_sums()
    r = subprocess.run([sys.executable, str(CONTRACT)], capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "contract_all_pass")
    print("ALL_PASS" if fail == 0 else "FAIL_COUNT=%d" % fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
