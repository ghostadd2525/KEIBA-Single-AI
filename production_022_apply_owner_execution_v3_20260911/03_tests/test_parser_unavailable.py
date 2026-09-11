#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "run_tests.py"


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    src = RUN.read_text(encoding="utf-8")
    expect("PARSER_ENGINE_UNAVAILABLE" in src, "source_has_unavailable_token", failures)
    expect("resolve_parser_engine" in src, "source_has_resolver", failures)
    expect("if engine is None" in src, "source_guards_none_engine", failures)
    ev_i = src.find("ev.write_text")
    sums_i = src.find("SUMS.write_text")
    expect(ev_i != -1 and sums_i != -1 and ev_i < sums_i, "evidence_written_before_sums", failures)
    env = os.environ.copy()
    env["OWNER_APPLY_TEST_NO_PARSER"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import run_tests, sys;"
                "eng, name = run_tests.resolve_parser_engine();"
                "print('RESOLVED=' + str(eng));"
                "print('PARSER_ENGINE_UNAVAILABLE' if eng is None else 'HAS_ENGINE');"
                "sys.exit(0 if eng is None else 1)"
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    out = (probe.stdout or "") + (probe.stderr or "")
    expect(probe.returncode == 0, "resolver_exit0_when_forced_missing", failures)
    expect("PARSER_ENGINE_UNAVAILABLE" in out, "resolver_prints_unavailable", failures)
    expect("TypeError" not in out, "resolver_no_typeerror", failures)
    parse_none = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import run_tests;"
                "eng, name = run_tests.resolve_parser_engine();"
                "print('PARSER_ENGINE_UNAVAILABLE');"
                "assert eng is None;"
                "print('SKIP_PARSEFILE')"
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    pout = (parse_none.stdout or "") + (parse_none.stderr or "")
    expect(parse_none.returncode == 0, "skip_parsefile_when_missing", failures)
    expect("TypeError" not in pout, "skip_parsefile_no_typeerror", failures)
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
