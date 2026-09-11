#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "02_powershell" / "baseline_disabled_post_dry_run.py"
PS1 = ROOT / "02_powershell" / "OWNER_READONLY.ps1"
FLAGS = ROOT / "FLAGS.txt"


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    src = PY.read_text(encoding="utf-8")
    ps = PS1.read_text(encoding="utf-8")
    flags = FLAGS.read_text(encoding="utf-8")
    ast.parse(src)
    expect(True, "python_ast_parse", failures)
    expect('method="POST"' not in src and "method='POST'" not in src, "no_post_method", failures)
    expect('method="GET"' in src, "get_only_request", failures)
    expect("/v1/predictions/" not in src, "no_detail_path", failures)
    expect("mode=ro" in src, "sqlite_ro", failures)
    expect("INSERT INTO" not in src, "no_sql_write", failures)
    expect("ALTER TABLE" not in src, "no_alter", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_019=1" not in src, "no_enable_019", failures)
    expect("PREDICTION_RUNS_ENABLED=1" not in src, "no_enable_post", failures)
    expect("try { if ($null -ne $stdoutTask) { [void]$stdoutTask.Wait(2000) } } catch { }" in ps, "fixed_stdout_brace", failures)
    expect("try { if ($null -ne $stderrTask) { [void]$stderrTask.Wait(2000) } } catch { }" in ps, "fixed_stderr_brace", failures)
    expect("try { if ($null -ne $stdoutTask) { [void]$stdoutTask.Wait(2000) } catch { }" not in ps, "no_broken_stdout_brace", failures)
    expect("try { if ($null -ne $stderrTask) { [void]$stderrTask.Wait(2000) } catch { }" not in ps, "no_broken_stderr_brace", failures)
    expect("v2_20260911_output_" in ps, "v2_output_name", failures)
    expect("OWNER_PACK_V1_PARSE_ERROR=YES" in flags, "flag_v1_parse", failures)
    expect("PRODUCTION_DRY_RUN_READY=NO" in flags, "flag_dry_run_no", failures)
    expect("PR24_UPDATED=NO" in flags, "flag_pr24", failures)

    sys.path.insert(0, str(PY.parent))
    import baseline_disabled_post_dry_run as audit  # type: ignore

    absent = audit.classify_019(
        columns={"id", "race_id"},
        index_names={"idx_predictions_race"},
        index_sql=None,
        migrations={"001_init"},
    )
    expect(absent["status"] == "absent", "019_absent_helper", failures)
    print("ALL_PASS" if not failures else "FAIL_COUNT=%d" % len(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
