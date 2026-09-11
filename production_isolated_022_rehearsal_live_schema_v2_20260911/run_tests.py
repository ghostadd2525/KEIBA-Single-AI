#!/usr/bin/env python3
from __future__ import print_function

import hashlib
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "03_tests" / "test_rehearsal.py"
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
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run(
        [sys.executable, str(CONTRACT)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "rehearsal")
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
