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
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "03_tests" / "test_inventory.py"
PS1 = ROOT / "02_powershell" / "OWNER_READONLY.ps1"
PATH_PS1 = ROOT / "02_powershell" / "test_wrapper_paths.ps1"
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


def parse_file(engine, path):
    cmd = (
        "$e=$null; $t=$null; "
        "[void][System.Management.Automation.Language.Parser]::ParseFile("
        "'%s', [ref]$t, [ref]$e); "
        "Write-Output ('PARSE_ERROR_COUNT=' + $e.Count); "
        "if ($e.Count -ne 0) { foreach ($x in $e) { Write-Output ('ERR=' + $x.ToString()) } }; "
        "exit ([int]$e.Count)"
    ) % str(path).replace("'", "''")
    return subprocess.run([engine, "-NoProfile", "-Command", cmd], capture_output=True, text=True)


def write_sums():
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS.txt":
            continue
        rel = path.relative_to(ROOT).as_posix()
        rows.append("%s  %s" % (file_sha(path), rel))
    SUMS.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main():
    r = subprocess.run([sys.executable, str(CONTRACT)], capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "contract")

    engine = shutil.which("powershell.exe") or shutil.which("pwsh")
    expect(engine is not None, "parser_engine")
    if engine:
        parsed = parse_file(engine, PS1)
        print(parsed.stdout)
        expect(parsed.returncode == 0 and "PARSE_ERROR_COUNT=0" in (parsed.stdout or ""), "parse0")
        paths = subprocess.run([engine, "-NoProfile", "-File", str(PATH_PS1)], capture_output=True, text=True)
        print(paths.stdout)
        expect(paths.returncode == 0 and "PARSE_ERROR_COUNT=0" in (paths.stdout or ""), "paths0")

    write_sums()
    expect(SUMS.is_file(), "sums")
    print("ALL_PASS" if fail == 0 else "FAIL_COUNT=%d" % fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
