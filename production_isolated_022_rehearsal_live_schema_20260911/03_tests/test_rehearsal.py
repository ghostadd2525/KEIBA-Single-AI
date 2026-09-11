#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-contained isolated 022 rehearsal tests. No workspace migration tree."""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REHEARSE = ROOT / "02_code" / "rehearse.py"
FLAGS = ROOT / "FLAGS.txt"
LIVE = ROOT / "02_code" / "live_schema.sql"
SQL022 = ROOT / "02_code" / "022_prediction_run_idempotency.sql"


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    ast.parse(REHEARSE.read_text(encoding="utf-8"))
    ast.parse((ROOT / "02_code" / "migrate_022.py").read_text(encoding="utf-8"))
    expect(True, "ast_parse", failures)
    banned = os.sep + os.path.join("workspace", "services", "win5-ai")
    expect(banned not in REHEARSE.read_text(encoding="utf-8"), "rehearse_self_contained", failures)
    expect("idx_predictions_race" in LIVE.read_text(encoding="utf-8"), "live_index", failures)
    expect("core_race_id" in LIVE.read_text(encoding="utf-8"), "live_core_race_id", failures)
    expect("idempotency_key" in SQL022.read_text(encoding="utf-8"), "022_cols", failures)
    flags = FLAGS.read_text(encoding="utf-8")
    expect("LIVE_SCHEMA_022_STRUCTURAL_COMPATIBILITY=YES" in flags, "compat_yes", failures)
    expect("PRODUCTION_APPLY_READY=NO" in flags, "apply_no", failures)
    expect("PRODUCTION_BACKUP_EXECUTED=NO" in flags, "backup_no", failures)

    env = os.environ.copy()
    env.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
    env.pop("PREDICTION_RUNS_ENABLED", None)
    r = subprocess.run([sys.executable, str(REHEARSE)], capture_output=True, text=True, env=env, cwd=str(ROOT))
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    out = r.stdout or ""
    expect(r.returncode == 0, "rehearse_exit0", failures)
    expect("MIGRATION_FIRST_APPLY_PASS=YES" in out, "first_apply", failures)
    expect("MIGRATION_SECOND_APPLY_NOOP=YES" in out, "second_noop", failures)
    expect("MIGRATION_PARTIAL_REPAIR_PASS=YES" in out, "partial_repair", failures)
    expect("EXISTING_NULL_ROW_COMPAT=YES" in out, "null_300", failures)
    expect("CONVERSATION_RA_CHALLENGE_NULL_COMPAT=YES" in out, "legacy_null", failures)
    expect("ROLLBACK_INDEX_ABSENT=YES" in out, "rollback_drop", failures)
    expect("ROLLBACK_COLUMNS_REMAIN=YES" in out, "rollback_cols", failures)
    expect("PREDICTIONS_COLUMNS_MATCH_OWNER=YES" in out, "owner_cols", failures)
    expect("LIVE_SCHEMA_022_STRUCTURAL_COMPATIBILITY=YES" in out, "compat_emit", failures)
    expect("PRODUCTION_APPLY_READY=NO" in out, "apply_emit", failures)
    expect("HTTP_STARTED=NO" in out, "no_http", failures)
    expect("GET_SURFACE_MODIFIED=NO" in out, "get_untouched", failures)
    expect("HIDE" not in out, "no_hidden_payload", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d" % len(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
