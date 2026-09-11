#!/usr/bin/env python3
from __future__ import print_function

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "03_tests" / "test_v5_rebase.py"
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


def main():
    r = subprocess.run([sys.executable, str(CONTRACT)], capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "contract")
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            rows.append("%s  %s" % (file_sha(path), path.relative_to(ROOT).as_posix()))
    SUMS.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("ALL_PASS" if fail == 0 else "FAIL_COUNT=%d" % fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
