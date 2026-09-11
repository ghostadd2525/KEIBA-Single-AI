#!/usr/bin/env python3
from __future__ import print_function

import hashlib
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SUMS = ROOT / "SHA256SUMS.txt"
fail = 0


def expect(cond, name):
    global fail
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fail += 1


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_py(rel):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run(
        [sys.executable, str(ROOT / rel)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    return r.returncode


def main():
    expect(run_py("03_tests/test_backup_contract.py") == 0, "reviewed_v2_contract_tests")
    expect(run_py("03_tests/test_owner_backup.py") == 0, "owner_wrapper_tests")
    contract = ROOT / "02_code" / "backup_contract.py"
    expect(
        file_sha(contract) == "55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e",
        "contract_byte_identical_reviewed_v2",
    )
    flags = (ROOT / "FLAGS.txt").read_text(encoding="utf-8")
    expect("PRODUCTION_BACKUP_EXECUTION_ALLOWED=NO" in flags, "flags_exec_allowed_no")
    expect("PRODUCTION_BACKUP_EXECUTED=NO" in flags, "flags_executed_no")
    expect("OWNER_PRODUCTION_BACKUP_APPROVED=NO" in flags, "flags_owner_approved_no")
    expect("PRODUCTION_BACKUP_EXECUTION_PACK_CREATED=YES" in flags, "flags_pack_created")
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt" and "__pycache__" not in path.parts:
            rows.append("%s  %s" % (file_sha(path), path.relative_to(ROOT).as_posix()))
    SUMS.write_text("\n".join(rows) + "\n", encoding="utf-8")
    expect(SUMS.is_file(), "sums")
    print("ALL_PASS" if fail == 0 else "FAIL_COUNT=%d" % fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
