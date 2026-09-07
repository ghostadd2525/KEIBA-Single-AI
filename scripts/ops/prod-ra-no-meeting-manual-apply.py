#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Owner EC2 only — Production baseline manual hunk apply for 9/7 NO_CATALOG_EXPECTED.

Does NOT checkout/merge PR #9.
Does NOT replace whole files.
Does NOT restart services.
Does NOT write the DB.

Usage on Owner EC2:
  cd /home/ubuntu/KEIBA-Single-AI
  python3 scripts/ops/prod-ra-no-meeting-manual-apply.py --dry-run
  python3 scripts/ops/prod-ra-no-meeting-manual-apply.py --apply

STOP if either PRE SHA does not match.
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

PROVIDER_RAISE_RE = re.compile(
    r"if not catalog:\n"
    r"(?P<indent>[ \t]*)raise NetkeibaResultError\(\s*"
    r"f\"PI catalog empty for \{race_date\}\"\s*"
    r"\)",
    re.M,
)

GATE_MARK = "PROD_RA_NO_MEETING_PRE_RUN_GATE_V1"

HELPER_SRC = f'''
def _prod_expected_count(settlement):
    if not isinstance(settlement, dict):
        return 0
    ids = settlement.get("expected_race_ids")
    if isinstance(ids, (list, tuple, set)):
        return len(ids)
    expected = settlement.get("expected")
    if isinstance(expected, (list, tuple, set)):
        return len(expected)
    for key in ("expected_count", "expected_n", "expected"):
        if key in settlement and settlement.get(key) is not None:
            try:
                return int(settlement.get(key) or 0)
            except (TypeError, ValueError):
                continue
    return 0


def _prod_count_race_results(race_date):
    conn = app_db.connect()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM race_results WHERE race_date=?",
            (race_date,),
        ).fetchone()
        return int((row["n"] if row else 0) or 0)
    finally:
        conn.close()


def _pre_run_catalog_gate(race_date):
    """{GATE_MARK}: skip svc.run only for PI-success empty catalog + no local evidence."""
    from app.ops.netkeiba_results import NetkeibaResultError, fetch_pi_race_catalog
    from app.ops.result_day_contract import NO_CATALOG_EXPECTED

    try:
        catalog = fetch_pi_race_catalog(race_date)
    except NetkeibaResultError:
        return {{"action": "run", "reason": "pi_catalog_failure"}}
    except Exception:
        return {{"action": "run", "reason": "pi_catalog_failure"}}

    if catalog:
        return {{
            "action": "run",
            "reason": "catalog_present",
            "catalog_count": len(catalog),
        }}

    try:
        settlement = build_day_settlement(race_date)
    except TypeError:
        settlement = build_day_settlement(race_date=race_date)
    expected_n = _prod_expected_count(settlement)
    results_n = _prod_count_race_results(race_date)
    if expected_n == 0 and results_n == 0:
        return {{
            "action": "skip",
            "reason": NO_CATALOG_EXPECTED,
            "catalog_count": 0,
            "expected": expected_n,
            "results": results_n,
        }}
    return {{
        "action": "run",
        "reason": "local_evidence",
        "catalog_count": 0,
        "expected": expected_n,
        "results": results_n,
    }}


def _gated_svc_run(svc, results, race_date, **kwargs):
    gate = _pre_run_catalog_gate(race_date)
    if gate.get("action") == "skip":
        results.append(
            {{
                "status": "skipped",
                "run_status": "NOOP",
                "race_date": race_date,
                "reason": gate.get("reason") or "NO_CATALOG_EXPECTED",
                "result_sync": False,
                "catalog_count": gate.get("catalog_count", 0),
                "expected": gate.get("expected", 0),
                "results": gate.get("results", 0),
            }}
        )
        return None
    return svc.run(race_date, **kwargs)
'''


class Stop(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_owner_layout(win5: Path) -> None:
    host = subprocess.check_output(["hostname"], text=True).strip()
    if host == "cursor":
        raise Stop(
            f"STOP: hostname={host!r} is the Cloud Agent, not Owner EC2. "
            "Copy this script to Owner EC2 and run it there."
        )
    if not win5.is_dir():
        raise Stop(f"STOP: win5-ai root not found: {win5}")
    for name in EXPECTED_PRE:
        path = win5 / OPS / name
        if not path.is_file():
            raise Stop(f"STOP: missing Production file {path}")


def verify_pre_sha(win5: Path) -> dict[str, str]:
    got = {}
    for name, expected in EXPECTED_PRE.items():
        path = win5 / OPS / name
        digest = sha256_file(path)
        got[name] = digest
        print(f"PRE_SHA {name}={digest}")
        if digest != expected:
            raise Stop(
                f"STOP: PRE SHA mismatch for {name}\n"
                f"  expected {expected}\n"
                f"  actual   {digest}\n"
                "Production baseline drifted; do not apply hunks."
            )
    print("PRE_SHA_MATCH=YES")
    return got


def apply_hunk1_provider(text: str) -> str:
    matches = list(PROVIDER_RAISE_RE.finditer(text))
    if len(matches) != 1:
        raise Stop(
            f"STOP: HUNK 1 expected exactly 1 empty-catalog raise, found {len(matches)}"
        )
    m = matches[0]
    indent = m.group("indent")
    repl = f"if not catalog:\n{indent}return []"
    start = m.start()
    # include the leading 'if not catalog:\\n' already in pattern
    return text[:start] + repl + text[m.end():]


def _find_helper_insert_index(text: str) -> int:
    fn = re.search(r"\ndef run_auto\(", text)
    if not fn:
        raise Stop("STOP: run_auto() not found in Production runner")
    return fn.start()


def apply_hunk23_runner(text: str) -> str:
    if GATE_MARK in text or "_gated_svc_run(" in text:
        raise Stop("STOP: pre-run gate already present; refusing double apply")
    if "build_day_settlement" not in text:
        raise Stop(
            "STOP: Production runner does not reference build_day_settlement; "
            "refusing to invent a new settlement path"
        )
    if "NO_CATALOG_EXPECTED" not in text and "result_day_contract" not in text:
        print(
            "NOTE: runner text does not mention NO_CATALOG_EXPECTED; "
            "helper will import it from result_day_contract"
        )

    sites = text.count("svc.run(")
    if sites < 1:
        raise Stop("STOP: no svc.run( call sites found to wrap")
    # Wrap first, then insert helper so the helper's own svc.run( is left intact.
    wrapped = text.replace("svc.run(", "_gated_svc_run(svc, results, ")
    if wrapped.count("_gated_svc_run(svc, results, ") != sites:
        raise Stop("STOP: svc.run wrap count mismatch")
    if "svc.run(" in wrapped:
        raise Stop("STOP: leftover svc.run( after wrap (before helper insert)")

    insert_at = _find_helper_insert_index(wrapped)
    helper = "\n" + HELPER_SRC.strip() + "\n\n"
    out = wrapped[:insert_at] + helper + wrapped[insert_at:]
    if GATE_MARK not in out:
        raise Stop("STOP: helper marker missing after insert")
    leftover = out.count("svc.run(")
    if leftover != 1:
        raise Stop(
            f"STOP: expected exactly 1 remaining svc.run( inside helper, found {leftover}"
        )
    print(f"HUNK_3 wrapped_svc_run_sites={sites}")
    return out


def compile_check(path: Path) -> None:
    py_compile.compile(str(path), doraise=True)
    print(f"COMPILE_OK {path.name}")


def import_check(win5: Path) -> None:
    env = dict(**__import__("os").environ)
    env["PYTHONPATH"] = str(win5)
    code = (
        "import app.ops.result_providers as p, app.ops.result_automation_runner as r; "
        "assert hasattr(r, '_pre_run_catalog_gate'); "
        "assert hasattr(r, '_gated_svc_run'); "
        "print('IMPORT_OK', p.__name__, r.__name__)"
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


def git_diff(win5: Path, rels: list[str]) -> None:
    repo = win5.parents[1] if win5.name == "win5-ai" else win5
    proc = subprocess.run(
        ["git", "diff", "--stat", "--"] + rels,
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    print("DIFF_STAT:")
    print(proc.stdout or "(no git diff; files may be outside git index)")
    if proc.returncode != 0:
        print(proc.stderr)
    proc = subprocess.run(
        ["git", "diff", "--"] + rels,
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    print("DIFF:")
    print(proc.stdout)


def forbidden_touch(win5: Path, before: dict[str, str]) -> None:
    forbidden = [
        OPS / "result_automation.py",
        OPS / "netkeiba_results.py",
        OPS / "ra_cadence.py",
        OPS / "result_day_contract.py",
    ]
    for rel in forbidden:
        path = win5 / rel
        if not path.is_file():
            continue
        now = sha256_file(path)
        if rel.name in before and before[rel.name] != now:
            raise Stop(f"STOP: forbidden file changed: {rel}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Production RA NO_CATALOG_EXPECTED manual hunk apply")
    parser.add_argument(
        "--win5-root",
        default=str(DEFAULT_WIN5),
        help="Production win5-ai root (default: /home/ubuntu/KEIBA-Single-AI/services/win5-ai)",
    )
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
        print("pwd=", Path.cwd())
        print("win5_root=", win5)
        require_owner_layout(win5)
        verify_pre_sha(win5)

        provider_src = provider.read_text(encoding="utf-8")
        runner_src = runner.read_text(encoding="utf-8")
        new_provider = apply_hunk1_provider(provider_src)
        new_runner = apply_hunk23_runner(runner_src)

        if new_provider == provider_src:
            raise Stop("STOP: HUNK 1 produced no change")
        if "raise NetkeibaResultError" in new_provider and "PI catalog empty" in new_provider:
            raise Stop("STOP: HUNK 1 left the empty-catalog raise in place")
        if "return []" not in new_provider:
            raise Stop("STOP: HUNK 1 missing return []")

        print("HUNK_1_READY=YES")
        print("HUNK_2_READY=YES")
        print("HUNK_3_READY=YES")
        print(
            "MODE=",
            "APPLY" if args.apply and not args.dry_run else "DRY_RUN",
        )

        if args.dry_run and not args.apply:
            print("DRY_RUN: no files written")
            return 0

        backup_dir = win5 / "var" / "ra-no-meeting-hunk-backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(provider, backup_dir / "result_providers.py.pre")
        shutil.copy2(runner, backup_dir / "result_automation_runner.py.pre")
        provider.write_text(new_provider, encoding="utf-8")
        runner.write_text(new_runner, encoding="utf-8")
        print("WROTE", provider)
        print("WROTE", runner)
        print("BACKUP", backup_dir)

        compile_check(provider)
        compile_check(runner)
        import_check(win5)
        print("POST_SHA result_providers.py=", sha256_file(provider))
        print("POST_SHA result_automation_runner.py=", sha256_file(runner))
        git_diff(
            win5,
            [
                "services/win5-ai/app/ops/result_providers.py",
                "services/win5-ai/app/ops/result_automation_runner.py",
                str(provider),
                str(runner),
            ],
        )
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
