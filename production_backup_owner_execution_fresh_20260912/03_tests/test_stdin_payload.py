#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compile and SHA tests for the single SSH stdin payload. No Production."""
from __future__ import annotations

import hashlib
import os
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS = ROOT / "02_powershell"
STDIN = PS / "owner_backup_stdin.py"
CONTRACT = PS / "backup_contract.py"
REMOTE = PS / "owner_backup_remote.py"
PS1 = PS / "OWNER_BACKUP.ps1"
REVIEWED = "55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e"

sys.path.insert(0, str(PS))
import build_stdin_payload as builder  # noqa: E402


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def v3_concat_text() -> str:
    return (
        '__name__ = "backup_contract"\n'
        + CONTRACT.read_text(encoding="utf-8")
        + '\n__name__ = "__main__"\n'
        + REMOTE.read_text(encoding="utf-8")
    )


def main() -> int:
    failures: list[str] = []
    payload = STDIN.read_bytes()
    saved = Path(tempfile.mkdtemp(prefix="bakv4-payload-")) / "sent_stdin_payload.py"
    saved.write_bytes(payload)
    expect(sha256(payload) == sha256(saved.read_bytes()), "saved_payload_sha_matches_file", failures)
    expect(sha256(CONTRACT.read_bytes()) == REVIEWED, "contract_byte_identical", failures)
    rebuilt = builder.build()
    expect(sha256(rebuilt) == sha256(payload), "rebuild_matches_committed_stdin", failures)
    expect(payload == rebuilt, "rebuild_bytes_identical", failures)

    ps = PS1.read_text(encoding="utf-8")
    expect("owner_backup_stdin.py" in ps, "ps1_reads_stdin_file", failures)
    expect("ReadAllBytes" in ps, "ps1_readallbytes", failures)
    expect('__name__ = "backup_contract"' not in ps, "ps1_no_name_concat", failures)
    expect("Get-Content -LiteralPath $ContractPy" not in ps, "ps1_no_contract_gettext", failures)
    expect("$ContractText" not in ps and "$RemoteText" not in ps, "ps1_no_runtime_concat_vars", failures)
    expect(sha256(payload) == sha256(STDIN.read_bytes()), "test_payload_is_ps1_file_payload", failures)

    future_lines = [ln for ln in payload.decode("utf-8").splitlines() if ln.startswith("from __future__ import")]
    expect(len(future_lines) == 1, "one_future_import", failures)
    expect(not payload.startswith(b"\xef\xbb\xbf"), "no_bom", failures)

    py_compile.compile(str(STDIN), doraise=True)
    expect(True, "py_compile_stdin", failures)
    compile(payload, str(STDIN), "exec")
    expect(True, "builtin_compile_stdin", failures)

    v3 = v3_concat_text()
    v3_failed = False
    v3_msg = ""
    try:
        compile(v3, "<v3-concat>", "exec")
    except SyntaxError as exc:
        v3_failed = True
        v3_msg = str(exc)
    expect(v3_failed, "v3_concat_compile_fails", failures)
    expect("future" in v3_msg.lower(), "v3_future_import_syntaxerror", failures)

    v3_path = saved.parent / "v3_concat_counterexample.py"
    v3_path.write_text(v3, encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "py_compile", str(v3_path)], capture_output=True, text=True)
    expect(r.returncode != 0, "v3_py_compile_nonzero", failures)
    expect("future" in ((r.stderr or "") + (r.stdout or "")).lower(), "v3_py_compile_future_msg", failures)

    env = os.environ.copy()
    env.pop("OWNER_PRODUCTION_BACKUP_APPROVED", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = subprocess.run([sys.executable, "-"], input=payload, capture_output=True, env=env)
    out = (started.stdout or b"").decode("utf-8", errors="replace")
    err = (started.stderr or b"").decode("utf-8", errors="replace")
    expect("SyntaxError" not in err, "python3_dash_no_syntaxerror", failures)
    expect(started.returncode == 2, "python3_dash_unapproved_exit2", failures)
    expect("HALT_REASON=OWNER_PRODUCTION_BACKUP_APPROVED_UNSET" in out, "python3_dash_unapproved_reason", failures)
    expect("PACK=production_backup_owner_execution_fresh_20260912" in out, "python3_dash_pack_name", failures)
    expect("CONTRACT_SHA_MATCH=STDIN_EMBEDDED" in out or "REVIEWED_CONTRACT_SHA256=" + REVIEWED in out, "python3_dash_namespace", failures)

    print("STDIN_PAYLOAD_SHA256=" + sha256(payload))
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
