#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
STDIN = PS / "owner_deploy_stdin.py"
PS1 = PS / "OWNER_DEPLOY.ps1"


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    failures: list[str] = []
    payload = STDIN.read_bytes()
    saved = Path(tempfile.mkdtemp(prefix="step1-payload-")) / "sent_stdin_payload.py"
    saved.write_bytes(payload)
    expect(sha256(payload) == sha256(saved.read_bytes()), "saved_payload_sha_matches_file", failures)
    ps = PS1.read_text(encoding="utf-8")
    expect("owner_deploy_stdin.py" in ps, "ps1_reads_stdin_file", failures)
    expect("ReadAllBytes" in ps, "ps1_readallbytes", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_022=1" not in ps, "ps1_does_not_forward_022", failures)
    expect(sum(1 for ln in payload.decode("utf-8").splitlines() if ln.startswith("from __future__ import")) == 1, "one_future_import", failures)
    py_compile.compile(str(STDIN), doraise=True)
    expect(True, "py_compile_stdin", failures)
    compile(payload, str(STDIN), "exec")
    expect(True, "builtin_compile_stdin", failures)
    env = os.environ.copy()
    env.pop("OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = subprocess.run([sys.executable, "-"], input=payload, capture_output=True, env=env)
    out = (started.stdout or b"").decode("utf-8", errors="replace")
    err = (started.stderr or b"").decode("utf-8", errors="replace")
    expect("SyntaxError" not in err, "python3_dash_no_syntaxerror", failures)
    expect(started.returncode == 2, "python3_dash_unapproved_exit2", failures)
    expect("HALT_REASON=OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED_UNSET" in out, "python3_dash_unapproved_reason", failures)
    expect("DEPLOY_EXECUTED=NO" in out, "unapproved_not_executed", failures)
    expect("RESTART_EXECUTED=NO" in out, "unapproved_no_restart", failures)
    expect("SSH_STARTED=" not in out, "payload_does_not_ssh", failures)
    expect("AUDIT_CLOSED=YES" in out, "unapproved_audit_closed", failures)
    print("STDIN_PAYLOAD_SHA256=" + sha256(payload))
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
