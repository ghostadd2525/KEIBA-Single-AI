#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Owner EC2 only — v2.1 correction.

Replace the undefined _pre_run_days race-day argument with existing
is_race_day_fn(job["race_date"]). Runner only. No provider change.

Usage on Owner EC2:
  python3 /tmp/prod-ra-no-meeting-manual-apply-v2-1.py --dry-run
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

OLD = '((not _pre_run_days) or (job["race_date"] in _pre_run_days))'
NEW = 'is_race_day_fn(job["race_date"])'
DEAD_DAYS_RE = re.compile(r"^[ \t]*_pre_run_days = _load_race_days\(\)\n", re.M)


class Stop(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_v21_runner(text: str) -> str:
    n = text.count(OLD)
    if n != 1:
        raise Stop(f"STOP: expected exactly 1 OLD race-day expr, found {n}")
    if NEW in text:
        raise Stop("STOP: is_race_day_fn(job[\"race_date\"]) already present")
    out = text.replace(OLD, NEW, 1)
    # Remove the now-dead v2 local that caused NameError if left unused.
    dead = list(DEAD_DAYS_RE.finditer(out))
    if len(dead) > 1:
        raise Stop("STOP: multiple _pre_run_days = _load_race_days() lines")
    if dead:
        out = out[: dead[0].start()] + out[dead[0].end() :]
    if "_pre_run_days" in out:
        raise Stop("STOP: _pre_run_days still present after correction")
    if out.count(NEW) != 1:
        raise Stop("STOP: expected exactly 1 is_race_day_fn(job[\"race_date\"])")
    return out


def require_owner(win5: Path) -> None:
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
            f"STOP: provider SHA drifted; v2.1 must not retouch provider\n"
            f"  expected {EXPECTED_PRE_PROVIDER}\n"
            f"  actual   {provider_sha}"
        )
    print("EXPECTED_PRE_SHA_MATCH=YES")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="v2.1 is_race_day_fn correction")
    parser.add_argument("--win5-root", default=str(DEFAULT_WIN5))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if not args.dry_run and not args.apply:
        args.dry_run = True
    win5 = Path(args.win5_root).resolve()
    runner = win5 / OPS / "result_automation_runner.py"
    provider = win5 / OPS / "result_providers.py"
    try:
        print("hostname=", subprocess.check_output(["hostname"], text=True).strip())
        require_owner(win5)
        src = runner.read_text(encoding="utf-8")
        new = apply_v21_runner(src)
        print("HUNK_1_READY=YES")
        print("UNDEFINED_PRE_RUN_DAYS_OCCURRENCES_AFTER=", new.count("_pre_run_days"))
        print("EXISTING_IS_RACE_DAY_FN_REUSED=YES")
        print("MODE=", "APPLY" if args.apply and not args.dry_run else "DRY_RUN")
        if args.dry_run and not args.apply:
            print("DRY_RUN: no files written")
            print("V2_1_STATIC_GATE=PASS")
            return 0
        backup = win5 / "var" / "ra-no-meeting-hunk-v2-1-backup"
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
        print("V2_1_STATIC_GATE=PASS")
        return 0
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        print("V2_1_STATIC_GATE=FAIL")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
