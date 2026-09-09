#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Owner EC2 only — Production manual hunk v2 (NO_CATALOG_EXPECTED pre-run gate).

Does not checkout/merge PR #9 or PR #10.
Does not replace whole files.
Does not restart services or write the DB.

Usage on Owner EC2:
  python3 /tmp/prod-ra-no-meeting-manual-apply-v2.py --dry-run
  # apply only after dry-run PASS and explicit approval
  python3 /tmp/prod-ra-no-meeting-manual-apply-v2.py --apply
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

EXPECTED_PRE = {
    "result_providers.py": "e5aef59b646d5f3d43954b3282b67745ee854922c90b3c548d4b51d53ee1ac0b",
    "result_automation_runner.py": "cc834b388df94b757b7be8be924cfee72900f5a016456e9d63fbe8664238bf5e",
}

DEFAULT_WIN5 = Path("/home/ubuntu/KEIBA-Single-AI/services/win5-ai")
OPS = Path("app/ops")
GATE_MARK = "PROD_RA_NO_MEETING_PRE_RUN_GATE_V2"

PROVIDER_RAISE_RE = re.compile(
    r"if not catalog:\n"
    r"(?P<indent>[ \t]*)raise NetkeibaResultError\(\s*"
    r"f\"PI catalog empty for \{race_date\}\"\s*"
    r"\)",
    re.M,
)

HELPER_SRC = f'''
def _pre_run_catalog_gate(race_date, is_race_day):
    """{GATE_MARK}: skip only PI success-empty + expected=0 + settled=0."""
    from app.ops.netkeiba_results import NetkeibaResultError, fetch_pi_race_catalog
    from app.ops.result_day_contract import NO_CATALOG_EXPECTED

    try:
        catalog = fetch_pi_race_catalog(race_date)
    except NetkeibaResultError:
        return {{"action": "run", "reason": "pi_catalog_failure"}}

    if catalog:
        return {{
            "action": "run",
            "reason": "catalog_present",
            "catalog_count": len(catalog),
        }}

    snap = ra_cadence.count_unsettled_races(
        race_date,
        is_race_day=is_race_day,
        catalog_races=[],
    )
    expected_n = int((snap or {{}}).get("EXPECTED_RACE_COUNT") or 0)
    settled_n = int((snap or {{}}).get("SETTLED_RACE_COUNT") or 0)
    if expected_n == 0 and settled_n == 0:
        return {{
            "action": "skip",
            "reason": NO_CATALOG_EXPECTED,
            "catalog_count": 0,
            "EXPECTED_RACE_COUNT": expected_n,
            "SETTLED_RACE_COUNT": settled_n,
        }}
    return {{
        "action": "run",
        "reason": "local_evidence",
        "catalog_count": 0,
        "EXPECTED_RACE_COUNT": expected_n,
        "SETTLED_RACE_COUNT": settled_n,
    }}
'''


class Stop(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_owner_layout(win5: Path) -> None:
    host = subprocess.check_output(["hostname"], text=True).strip()
    if host == "cursor":
        raise Stop(
            f"STOP: hostname={host!r} is the Cloud Agent, not Owner EC2."
        )
    if not win5.is_dir():
        raise Stop(f"STOP: win5-ai root not found: {win5}")
    for name in EXPECTED_PRE:
        path = win5 / OPS / name
        if not path.is_file():
            raise Stop(f"STOP: missing Production file {path}")


def verify_pre_sha(win5: Path) -> None:
    for name, expected in EXPECTED_PRE.items():
        digest = sha256_file(win5 / OPS / name)
        print(f"PRE_SHA {name}={digest}")
        if digest != expected:
            raise Stop(
                f"STOP: PRE SHA mismatch for {name}\n"
                f"  expected {expected}\n"
                f"  actual   {digest}"
            )
    print("PRE_SHA_MATCH=YES")


def apply_hunk1_provider(text: str) -> str:
    matches = list(PROVIDER_RAISE_RE.finditer(text))
    if len(matches) != 1:
        raise Stop(
            f"STOP: HUNK 1 expected exactly 1 empty-catalog raise, found {len(matches)}"
        )
    m = matches[0]
    indent = m.group("indent")
    repl = f"if not catalog:\n{indent}return []"
    out = text[: m.start()] + repl + text[m.end() :]
    if "PI catalog empty" in out:
        raise Stop("STOP: HUNK 1 left the empty-catalog raise in place")
    return out


def decide_pre_run_action(catalog, snap):
    """Pure skip rule used by tests and documented for the runner hunk."""
    if catalog == "FAILURE":
        return "run"
    if catalog:
        return "run"
    expected_n = int((snap or {}).get("EXPECTED_RACE_COUNT") or 0)
    settled_n = int((snap or {}).get("SETTLED_RACE_COUNT") or 0)
    if expected_n == 0 and settled_n == 0:
        return "skip"
    return "run"


def _ensure_imports(text: str) -> str:
    needed = [
        (
            "from app.ops.netkeiba_results import NetkeibaResultError, fetch_pi_race_catalog\n",
            "fetch_pi_race_catalog",
        ),
        (
            "from app.ops.result_day_contract import NO_CATALOG_EXPECTED\n",
            "NO_CATALOG_EXPECTED",
        ),
    ]
    out = text
    insert_at = None
    m = re.search(r"from app\.ops import ra_cadence\n", out)
    if m:
        insert_at = m.end()
    else:
        raise Stop("STOP: runner does not import ra_cadence; refusing to add settlement path")
    for line, token in needed:
        if token not in out:
            out = out[:insert_at] + line + out[insert_at:]
            insert_at += len(line)
    return out


def _insert_helper(text: str) -> str:
    if GATE_MARK in text:
        raise Stop("STOP: v2 gate already present")
    fn = re.search(r"\ndef run_auto\(", text)
    if not fn:
        raise Stop("STOP: run_auto() not found")
    helper = "\n" + HELPER_SRC.strip() + "\n\n"
    return text[: fn.start()] + helper + text[fn.start() :]


def _wrap_common_svc_run(text: str) -> str:
    sites = list(re.finditer(r"^([ \t]*)out = svc\.run\(", text, re.M))
    if len(sites) != 1:
        raise Stop(
            f"STOP: expected exactly 1 common 'out = svc.run(' site, found {len(sites)}"
        )
    m = sites[0]
    indent = m.group(1)
    if "for job in jobs:" not in text[: m.start()]:
        raise Stop("STOP: common svc.run is not under 'for job in jobs:'")

    race_day_call = None
    if re.search(r"def _is_race_day\(", text):
        race_day_call = "_is_race_day(job[\"race_date\"])"
    elif re.search(r"def is_race_day\(", text):
        race_day_call = "is_race_day(job[\"race_date\"])"
    elif "_load_race_days" in text:
        race_day_call = (
            "((not _pre_run_days) or (job[\"race_date\"] in _pre_run_days))"
        )
    else:
        raise Stop(
            "STOP: no existing race-day helper (_is_race_day / is_race_day / "
            "_load_race_days). Refusing to invent calendar logic."
        )

    days_init = ""
    if "_load_race_days" in race_day_call:
        days_init = f"{indent}_pre_run_days = _load_race_days()\n"

    block = (
        f"{days_init}"
        f"{indent}_gate = _pre_run_catalog_gate("
        f"job[\"race_date\"], {race_day_call})\n"
        f"{indent}if _gate.get(\"action\") == \"skip\":\n"
        f"{indent}    results.append({{\n"
        f"{indent}        \"status\": \"skipped\",\n"
        f"{indent}        \"run_status\": \"NOOP\",\n"
        f"{indent}        \"race_date\": job[\"race_date\"],\n"
        f"{indent}        \"reason\": _gate.get(\"reason\") or NO_CATALOG_EXPECTED,\n"
        f"{indent}        \"result_sync\": False,\n"
        f"{indent}        \"EXPECTED_RACE_COUNT\": _gate.get(\"EXPECTED_RACE_COUNT\", 0),\n"
        f"{indent}        \"SETTLED_RACE_COUNT\": _gate.get(\"SETTLED_RACE_COUNT\", 0),\n"
        f"{indent}    }})\n"
        f"{indent}    continue\n"
        f"{indent}out = svc.run("
    )
    return text[: m.start()] + block + text[m.end() :]


def apply_hunk2_runner(text: str) -> str:
    if "build_day_settlement" in HELPER_SRC:
        raise Stop("STOP: helper must not reference build_day_settlement")
    if "SELECT " in HELPER_SRC:
        raise Stop("STOP: helper must not embed SQL")
    out = _ensure_imports(text)
    out = _insert_helper(out)
    out = _wrap_common_svc_run(out)
    if out.count("out = svc.run(") != 1:
        raise Stop("STOP: common svc.run site lost or duplicated")
    if GATE_MARK not in out:
        raise Stop("STOP: gate marker missing")
    return out


def compile_check(path: Path) -> None:
    py_compile.compile(str(path), doraise=True)
    print(f"COMPILE_OK {path.name}")


def import_check(win5: Path) -> None:
    env = dict(**__import__("os").environ)
    env["PYTHONPATH"] = str(win5)
    code = (
        "import app.ops.result_automation_runner as r; "
        "assert hasattr(r, '_pre_run_catalog_gate'); "
        "print('IMPORT_OK', r.__name__)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(win5),
        env=env,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        raise Stop(f"STOP: import check failed\n{proc.stderr}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Production RA pre-run gate hunk v2")
    parser.add_argument("--win5-root", default=str(DEFAULT_WIN5))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if not args.dry_run and not args.apply:
        args.dry_run = True

    win5 = Path(args.win5_root).resolve()
    provider = win5 / OPS / "result_providers.py"
    runner = win5 / OPS / "result_automation_runner.py"

    try:
        print("hostname=", subprocess.check_output(["hostname"], text=True).strip())
        print("win5_root=", win5)
        require_owner_layout(win5)
        verify_pre_sha(win5)
        new_provider = apply_hunk1_provider(provider.read_text(encoding="utf-8"))
        new_runner = apply_hunk2_runner(runner.read_text(encoding="utf-8"))
        print("HUNK_1_READY=YES")
        print("HUNK_2_READY=YES")
        print("BUILD_DAY_SETTLEMENT_RUNNER_IMPORT=NO")
        print("SQL_DUPLICATION_IN_RUNNER=NO")
        print("MODE=", "APPLY" if args.apply and not args.dry_run else "DRY_RUN")
        if args.dry_run and not args.apply:
            print("DRY_RUN: no files written")
            print("FINAL_STATIC_APPLY_GATE=PASS")
            return 0

        backup = win5 / "var" / "ra-no-meeting-hunk-v2-backup"
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(provider, backup / "result_providers.py.pre")
        shutil.copy2(runner, backup / "result_automation_runner.py.pre")
        provider.write_text(new_provider, encoding="utf-8")
        runner.write_text(new_runner, encoding="utf-8")
        compile_check(provider)
        compile_check(runner)
        import_check(win5)
        print("POST_SHA result_providers.py=", sha256_file(provider))
        print("POST_SHA result_automation_runner.py=", sha256_file(runner))
        print("SERVICE_RESTARTED=NO")
        print("DB_WRITE_PERFORMED=NO")
        print("FINAL_STATIC_APPLY_GATE=PASS")
        return 0
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        print("FINAL_STATIC_APPLY_GATE=FAIL")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
