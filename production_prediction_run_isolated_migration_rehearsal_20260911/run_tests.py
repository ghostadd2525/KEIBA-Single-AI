#!/usr/bin/env python3
from __future__ import print_function

import hashlib
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "03_tests" / "test_rehearsal.py"
REHEARSE = ROOT / "02_code" / "rehearse.py"
SUMS = ROOT / "SHA256SUMS.txt"
EVIDENCE = ROOT / "evidence"
fail = 0
REQUIRED_KV = (
    "OWNER_AUDIT_IMPORTED=YES",
    "OWNER_OUTPUT_SHA256=6f0901221eaa625c51976d5ce6aae110175732a1cd7dfd846c6d774a24f66862",
    "PRODUCTION_DB_OPENED=NO",
    "PRODUCTION_CHANGED=NO",
    "PRODUCTION_APPLY_READY=NO",
    "OWNER_APPLY_APPROVED=NO",
    "PRODUCTION_BACKUP_READY=NO",
    "PRODUCTION_BACKUP_EXECUTED=NO",
    "MIGRATION_FIRST_APPLY_PASS=YES",
    "MIGRATION_SECOND_APPLY_NOOP=YES",
    "MIGRATION_PARTIAL_REPAIR_PASS=YES",
    "NULL_COMPAT_300=YES",
    "GET_ENVELOPE_SCHEMA_OK_BEFORE=YES",
    "GET_ENVELOPE_SCHEMA_OK_AFTER=YES",
    "GET_RESPONSE_SCHEMA_UNCHANGED=YES",
    "GET_ROWCOUNT_UNCHANGED_ACROSS_019=YES",
    "GET_DB_WRITE_COUNT_BEFORE_019=0",
    "GET_DB_WRITE_COUNT_AFTER_019=0",
    "CONVERSATION_HISTORY_COUNT_UNCHANGED=YES",
    "POST_DISABLED_BEFORE=YES",
    "POST_DISABLED_AFTER_019=YES",
    "POST_DISABLED_AFTER_ROLLBACK=YES",
    "CONVERSATION_LEGACY_SAVE_OK=YES",
    "CHALLENGE_LEGACY_INSERT_OK=YES",
    "RA_LEGACY_INSERT_OK=YES",
    "LEGACY_PERSIST_SOURCE_ALL_NULL=YES",
    "ROLLBACK_IF_ALLOW_REMAINS_INDEX_REGENERATED=YES",
    "ROLLBACK_AFTER_UNSET_ALLOW_INDEX_ABSENT=YES",
    "PYTHON_CONNECTION_BACKUP_LOCAL_PASS=YES",
    "PYTHON_BACKUP_USED_ON_PRODUCTION=NO",
    "COLLISION_TWO_019_STEMS=YES",
    "STUBS_ARE_LIVE_SQL=NO",
    "PRODUCTION_SCHEMA_COPIED=NO",
    "MIGRATION_REHEARSAL_COMPLETE=YES",
    "ACTIVE_WRITE_PATH_REGRESSION_COMPLETE=YES_ISOLATED_ONLY",
    "FIRST_APPLY_VIA=app.data.db.migrate",
)


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


def write_sums():
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel == "SHA256SUMS.txt":
            continue
        if rel.startswith("evidence/") and rel not in (
            "evidence/rehearsal_kv.txt",
            "evidence/rehearsal_summary.json",
            "evidence/get_before.json",
            "evidence/get_after.json",
            "evidence/run_tests.txt",
            "evidence/local_impl_hashes.txt",
        ):
            continue
        rows.append("%s  %s" % (file_sha(path), rel))
    SUMS.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main():
    r = subprocess.run([sys.executable, str(CONTRACT)], capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    expect(r.returncode == 0 and "ALL_PASS" in (r.stdout or ""), "contract_all_pass")

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    reh = subprocess.run([sys.executable, str(REHEARSE)], capture_output=True, text=True)
    print(reh.stdout)
    if reh.stderr:
        print(reh.stderr)
    (EVIDENCE / "run_tests.txt").write_text(
        (reh.stdout or "") + "\n----- STDERR -----\n" + (reh.stderr or ""),
        encoding="utf-8",
    )
    expect(reh.returncode == 0, "rehearse_exit0")
    out = reh.stdout or ""
    kv = EVIDENCE / "rehearsal_kv.txt"
    expect(kv.is_file(), "rehearsal_kv_exists")
    kv_text = kv.read_text(encoding="utf-8") if kv.is_file() else ""
    combined = out + "\n" + kv_text
    for item in REQUIRED_KV:
        expect(item in combined, "kv_" + item.split("=", 1)[0].lower())

    write_sums()
    expect(SUMS.is_file(), "sha256sums_exists")
    if SUMS.is_file():
        lines = [ln.strip() for ln in SUMS.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
        expect(len(lines) > 10, "sha256sums_nonempty")
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

    print("ALL_PASS" if fail == 0 else "FAIL_COUNT=%d" % fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
