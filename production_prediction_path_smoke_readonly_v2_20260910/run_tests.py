#!/usr/bin/env python3
from __future__ import print_function

import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ROOT = Path(__file__).resolve().parent
PS1 = ROOT / "02_powershell" / "OWNER_READONLY.ps1"
CONTRACT = ROOT / "03_tests" / "test_pack_contract.py"
fail = 0


def expect(cond, name):
    global fail
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fail += 1


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
    expect("V1_DO_NOT_RUN=YES" in ps, "v1_ban")
    expect("POST_ENDPOINT_CALLED=NO" in ps, "no_post_flag")
    expect("v2_20260910" in ps, "v2_output_name")


def main():
    test_ps()
    r = subprocess.run([sys.executable, str(CONTRACT)], capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "contract_all_pass")
    print("ALL_PASS" if fail == 0 else "FAIL_COUNT=%d" % fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
