#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Owner EC2 only — v2.1.1 correction.

Fix the v2.1 SCRIPT ANCHOR BUG. Production already has
is_race_day_fn(job["race_date"]) in retry paths; that must not STOP apply.

Replace exactly one bad pre-run gate call. Runner only.
"""
from __future__ import annotations

import argparse
import hashlib
import py_compile
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXPECTED_PRE_RUNNER = "71814f1e4698cb6a6d3c5f6a23ade6e24dd845526c8ddb858963288675acc318"
EXPECTED_PRE_PROVIDER = "3a9cf04cd8cc53ee2421a23cedf0cb0daf064c9130b10b7b8e0396a810ca05bb"

DEFAULT_WIN5 = Path("/home/ubuntu/KEIBA-Single-AI/services/win5-ai")
OPS = Path("app/ops")

OLD_GATE_RE = re.compile(
    r'_gate = _pre_run_catalog_gate\(\s*'
    r'job\["race_date"\],\s*'
    r'\(\(not _pre_run_days\) or \(job\["race_date"\] in _pre_run_days\)\)\s*'
    r'\)',
    re.M,
)
NEW_GATE = (
    '_gate = _pre_run_catalog_gate(job["race_date"], is_race_day_fn(job["race_date"]))'
)
NEW_GATE_RE = re.compile(
    r'_gate = _pre_run_catalog_gate\(\s*'
    r'job\["race_date"\],\s*'
    r'is_race_day_fn\(job\["race_date"\]\)\s*'
    r'\)',
    re.M,
)
IS_RACE_DAY_JOB_RE = re.compile(r'is_race_day_fn\(job\["race_date"\]\)')
DEAD_DAYS_RE = re.compile(r"^[ \t]*_pre_run_days = _load_race_days\(\)\s*\n", re.M)


class Stop(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def count_old_gate(text: str) -> int:
    return len(OLD_GATE_RE.findall(text))


def count_new_gate(text: str) -> int:
    return len(NEW_GATE_RE.findall(text))


def apply_v211_runner(text: str) -> str:
    old_n = count_old_gate(text)
    new_n = count_new_gate(text)
    print(f"OLD_GATE_CALL_BEFORE={old_n}")
    print(f"NEW_GATE_CALL_BEFORE={new_n}")
    if old_n != 1:
        raise Stop(f"STOP: expected OLD exact gate call once, found {old_n}")
    if new_n != 0:
        raise Stop(f"STOP: expected NEW exact gate call absent before, found {new_n}")

    out, nsub = OLD_GATE_RE.subn(NEW_GATE, text, count=1)
    if nsub != 1:
        raise Stop("STOP: failed to replace OLD exact gate call once")

    dead = list(DEAD_DAYS_RE.finditer(out))
    if len(dead) > 1:
        raise Stop("STOP: multiple standalone _pre_run_days assignments")
    if dead:
        out = out[: dead[0].start()] + out[dead[0].end() :]

    old_after = count_old_gate(out)
    new_after = count_new_gate(out)
    days_after = out.count("_pre_run_days")
    fn_after = len(IS_RACE_DAY_JOB_RE.findall(out))
    print(f"OLD_GATE_CALL_AFTER={old_after}")
    print(f"NEW_GATE_CALL_AFTER={new_after}")
    print(f"PRE_RUN_DAYS_AFTER={days_after}")
    print(f"IS_RACE_DAY_FN_JOB_TOTAL_AFTER={fn_after}")
    if old_after != 0:
        raise Stop("STOP: OLD exact gate call still present")
    if new_after != 1:
        raise Stop("STOP: expected NEW exact gate call once after")
    if days_after != 0:
        raise Stop("STOP: _pre_run_days still present")
    if fn_after != 3:
        raise Stop(
            f"STOP: expected is_race_day_fn(job[\"race_date\"]) total 3 after, found {fn_after}"
        )
    return out


def require_owner(win5: Path) -> tuple[Path, Path]:
    host = subprocess.check_output(["hostname"], text=True).strip()
    if host == "cursor":
        raise Stop(f"STOP: hostname={host!r} is the Cloud Agent, not Owner EC2.")
    runner = win5 / OPS / "result_automation_runner.py"
    provider = win5 / OPS / "result_providers.py"
    if not runner.is_file() or not provider.is_file():
        raise Stop("STOP: Production ops files missing")
    runner_sha = sha256_file(runner)
    provider_sha = sha256_file(provider)
    print(f"PRE_SHA result_automation_runner.py={runner_sha}")
    print(f"PRE_SHA result_providers.py={provider_sha}")
    if runner_sha != EXPECTED_PRE_RUNNER:
        raise Stop(
            f"STOP: runner PRE SHA mismatch\n"
            f"  expected {EXPECTED_PRE_RUNNER}\n"
            f"  actual   {runner_sha}"
        )
    if provider_sha != EXPECTED_PRE_PROVIDER:
        raise Stop(
            f"STOP: provider SHA drifted; v2.1.1 must not retouch provider\n"
            f"  expected {EXPECTED_PRE_PROVIDER}\n"
            f"  actual   {provider_sha}"
        )
    print("PRE_SHA_MATCH=YES")
    return runner, provider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="v2.1.1 exact pre-run gate correction")
    parser.add_argument("--win5-root", default=str(DEFAULT_WIN5))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if not args.dry_run and not args.apply:
        args.dry_run = True
    win5 = Path(args.win5_root).resolve()
    try:
        print("hostname=", subprocess.check_output(["hostname"], text=True).strip())
        runner, provider = require_owner(win5)
        src = runner.read_text(encoding="utf-8")
        new = apply_v211_runner(src)
        print("HUNK_1_READY=YES")
        print("HUNK_COUNT=1")
        print("MODE=", "APPLY" if args.apply and not args.dry_run else "DRY_RUN")
        if args.dry_run and not args.apply:
            print("DRY_RUN: no files written")
            print("FINAL_STATIC_GATE=PASS")
            return 0
        backup = win5 / "var" / "ra-no-meeting-hunk-v2-1-1-backup"
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(runner, backup / "result_automation_runner.py.pre")
        provider_before = sha256_file(provider)
        runner.write_text(new, encoding="utf-8")
        if sha256_file(provider) != provider_before:
            raise Stop("STOP: provider file changed; abort")
        py_compile.compile(str(runner), doraise=True)
        print("COMPILE_OK result_automation_runner.py")
        print("POST_SHA result_automation_runner.py=", sha256_file(runner))
        print("POST_SHA result_providers.py=", sha256_file(provider))
        print("SERVICE_RESTARTED=NO")
        print("DB_WRITE_PERFORMED=NO")
        print("FINAL_STATIC_GATE=PASS")
        return 0
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        print("FINAL_STATIC_GATE=FAIL")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
