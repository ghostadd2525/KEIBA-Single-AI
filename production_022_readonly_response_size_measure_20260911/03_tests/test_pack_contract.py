#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "02_powershell" / "OWNER_MEASURE.ps1"
STDIN = ROOT / "02_powershell" / "owner_measure_stdin.py"
FLAGS = ROOT / "FLAGS.txt"
V4_ZIP = "8bc2457cf8871b86b62421069e9d4972c636ff74c185d7df753832df0897ed8d"
V4_OUT = "307fe722bbd75f650e4019a1d9eb600a0d39d3a15dd18245fd379536d14fa462"
BACKUP_SHA = "f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d"


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    failures: list[str] = []
    ast.parse(STDIN.read_text(encoding="utf-8"))
    ps = PS1.read_text(encoding="utf-8")
    stdin = STDIN.read_text(encoding="utf-8")
    flags = FLAGS.read_text(encoding="utf-8")
    expect("python3 -" in ps, "stdin_python", failures)
    expect("owner_measure_stdin.py" in ps, "ps1_single_stdin_file", failures)
    expect("ReadAllBytes" in ps, "ps1_byte_for_byte", failures)
    expect("scp " not in ps.lower() and "scp " not in stdin.lower(), "no_scp", failures)
    expect("sudo " not in ps.lower() and "sudo " not in stdin.lower(), "no_sudo", failures)
    expect(".Contains(" not in ps, "no_pscustomobject_contains", failures)
    expect("$env:OWNER_PRODUCTION_022_MEASURE_APPROVED =" not in ps, "ps1_does_not_assign_approval", failures)
    expect("ALTER TABLE" not in stdin, "no_alter", failures)
    expect("BEGIN IMMEDIATE" not in stdin, "no_write_tx", failures)
    expect("DROP " not in stdin, "no_drop", failures)
    expect("DELETE FROM" not in stdin, "no_delete", failures)
    expect("mode=ro" in stdin, "sqlite_readonly", failures)
    expect("query_only=ON" in stdin, "query_only", failures)
    expect("MEASURE_INTERNAL_LIST_MAX_BYTES = 8388608" in stdin, "list_cap_8mib", failures)
    expect("MEASURE_PUBLIC_JSON_MAX_BYTES = 262144" in stdin, "public_cap_separate", failures)
    expect("HTTP_ENDPOINT_CLASS" in stdin, "endpoint_class", failures)
    expect("HTTP_BYTES_READ_AT_LEAST" in stdin, "bytes_at_least", failures)
    expect("HTTP_LIMIT_BYTES" in stdin, "limit_bytes", failures)
    expect("/v1/prediction-runs" in stdin, "refuses_post_prediction_runs", failures)
    expect(V4_ZIP in flags, "v4_zip_recorded", failures)
    expect(V4_OUT in flags, "v4_output_recorded", failures)
    expect(BACKUP_SHA in flags, "backup_sha_recorded", failures)
    expect("V4_RERUN=NO" in flags, "v4_no_rerun", failures)
    expect("PRODUCTION_022_APPLY_EXECUTION_ALLOWED=NO" in flags, "apply_not_allowed", failures)
    expect("OWNER_APPLY_APPROVED=NO" in flags, "owner_apply_no", failures)
    expect("$TimeoutMs = 180000" in ps, "ps1_timeout_180s", failures)
    expect("REMOTE_HARD_DEADLINE_S = 90" in stdin, "remote_deadline_90", failures)
    expect(180000 >= 90 * 1000 + 20000 + 8000 + 40000, "wrapper_longer_than_remote", failures)
    expect("STDIN_PAYLOAD_SHA256=" + file_sha(STDIN) in flags, "flags_stdin_sha", failures)
    expect("PARSER_ENGINE_UNAVAILABLE" in (ROOT / "run_tests.py").read_text(encoding="utf-8"), "parser_unavailable_token", failures)
    run_src = (ROOT / "run_tests.py").read_text(encoding="utf-8")
    expect(run_src.find("ev.write_text") < run_src.find("SUMS.write_text"), "sums_after_evidence", failures)
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
