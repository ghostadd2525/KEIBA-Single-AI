#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan-pack tests. Never open Production DB. Never apply 022."""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "02_code"
sys.path.insert(0, str(CODE))

import apply_plan_gates as gates  # noqa: E402


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    src = (CODE / "apply_plan_gates.py").read_text(encoding="utf-8")
    ast.parse(src)
    expect("conn.executescript" not in src and "def migrate" not in src, "gates_no_migrate_call", failures)
    expect("migrate(" in src and "REFUSED_EXECUTION_TOKEN" in src, "gates_refuses_migrate_token", failures)
    expect("systemctl" not in src or "REFUSED_EXECUTION_TOKEN" in src, "gates_refuses_systemctl", failures)
    expect("sqlite3" not in src, "gates_no_sqlite", failures)
    expect("expect_ai.db" not in src, "gates_no_live_db_path", failures)

    flags = (ROOT / "FLAGS.txt").read_text(encoding="utf-8")
    expect("NOT_AN_EXECUTION_PACK=YES" in flags, "not_execution_pack", failures)
    expect("PRODUCTION_022_APPLY_PLAN_COMPLETE=YES" in flags, "plan_complete", failures)
    expect("PRODUCTION_APPLY_READY=NO" in flags, "apply_ready_no", failures)
    expect("OWNER_APPLY_APPROVED=NO" in flags, "owner_apply_no", failures)
    expect("DEFAULT_PREDICTION_RUNS_ENABLED=0" in flags, "post_default_off", failures)
    expect("POST_REMAINS_DISABLED_AFTER_022=YES" in flags, "post_stays_off", failures)
    expect("COLUMN_DELETE_FORBIDDEN=YES" in flags, "no_drop_column", failures)
    expect("ROW_DELETE_FORBIDDEN=YES" in flags, "no_row_delete", failures)
    expect("BUNDLE_JSON_UPDATE_FORBIDDEN=YES" in flags, "no_bundle_update", failures)
    expect("POST_ENABLE_IS_SEPARATE_STEP=YES" in flags, "post_separate", failures)
    expect("APPLY_PRECONDITION=OWNER_BACKUP_SUCCESS" in flags, "backup_precondition", failures)
    expect("7981db7fff2d8a8d0a057bf66aeddca72a37c842cdf66c926dd5d3f9ac4c1037" in flags, "claimed_v1_recorded", failures)

    all_docs = ""
    for path in (ROOT / "01_docs").glob("*.txt"):
        all_docs += path.read_text(encoding="utf-8")
    expect("GET envelope" in all_docs, "doc_get_envelope", failures)
    expect("/api/health" in all_docs, "doc_api_health", failures)
    expect("Research Week" in all_docs, "doc_research_week", failures)
    expect("systemctl" in all_docs, "doc_systemd", failures)
    expect("journal" in all_docs.lower() or "journalctl" in all_docs, "doc_journal", failures)
    expect("Conversation" in all_docs and "Challenge" in all_docs, "doc_surfaces", failures)
    rollback = (ROOT / "01_docs" / "03_rollback.txt").read_text(encoding="utf-8")
    expect(rollback.find("PREDICTION_RUNS_ENABLED=0") < rollback.find("Unset EXPECT_AI_ALLOW_MIGRATION_022"), "rollback_step1_before_step2", failures)
    expect(rollback.find("Unset EXPECT_AI_ALLOW_MIGRATION_022") < rollback.find("DROP INDEX IF EXISTS uq_predictions_idempotency_key_not_null"), "rollback_step2_before_step3", failures)
    expect("DROP COLUMN" in (ROOT / "01_docs" / "08_forbidden.txt").read_text(encoding="utf-8"), "forbid_drop_column", failures)

    os.environ.pop("OWNER_APPLY_APPROVED", None)
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
    os.environ["PREDICTION_RUNS_ENABLED"] = "0"
    rc = gates.main(["--check"])
    expect(rc == 0, "gates_check_pass", failures)

    rc = gates.main(["--apply"])
    expect(rc == 2, "refuse_apply_token", failures)

    os.environ["OWNER_APPLY_APPROVED"] = "1"
    rc = gates.main(["--check"])
    expect(rc == 2, "refuse_owner_apply_flag", failures)
    os.environ.pop("OWNER_APPLY_APPROVED", None)

    os.environ["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    rc = gates.main(["--check"])
    expect(rc == 2, "refuse_022_flag_on_plan", failures)
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
