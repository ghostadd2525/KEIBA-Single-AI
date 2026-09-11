#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REHEARSE = ROOT / "02_code" / "rehearse.py"
BACKUP = ROOT / "02_code" / "python_backup_design.py"
FLAGS = ROOT / "FLAGS.txt"
README = ROOT / "00_README.txt"
OWNER = ROOT / "00_OWNER_手順.txt"
CONSTRAINTS = ROOT / "04_constraints.txt"
COLLISION = ROOT / "01_docs" / "collision.txt"
ROLLBACK = ROOT / "01_docs" / "rollback_order.txt"
BACKUP_DOC = ROOT / "01_docs" / "backup_without_sqlite3_cli.txt"
AUDIT = ROOT / "01_docs" / "owner_audit_imported.txt"
STUB_019 = ROOT / "02_code" / "live_schema_stubs" / "019_final_predictions.sql"
STUB_020 = ROOT / "02_code" / "live_schema_stubs" / "020_live_schema_unknown.sql"
STUB_021 = ROOT / "02_code" / "live_schema_stubs" / "021_live_schema_unknown.sql"
PERSIST_019 = ROOT / "02_code" / "persist_019" / "019_prediction_run_idempotency.sql"
PERSIST_019_SHA = "d8fc71e316d7819a4dcfc0977bf6444308410144b62fd29a33ca764ea853370f"
PROTECTED_ZIPS = (
    (
        Path("/workspace/production_single_ai_prediction_run_local_review_20260910.zip"),
        "9ff00084c77cc0e2f539d2638abd6097eda8a54ab244faf85aadc0f9e5879e6f",
    ),
    (
        Path("/workspace/production_single_ai_prediction_run_local_review_v2_20260911.zip"),
        "b0d107cb6733bb72b2e23a95472a27836ba5c1fda213add4557387fc3d64fd89",
    ),
    (
        Path("/workspace/production_single_ai_prediction_run_local_review_v3_20260911.zip"),
        "bf99f3b4aa38f9fdd10ab9992f15ebcda9a260f070caf7eebe0f9156517f6118",
    ),
    (
        Path("/workspace/production_single_ai_prediction_run_local_review_v4_20260911.zip"),
        "4fd4dc88315f7dbab3f495dea249ad1fcb715b375a64de85762a779571aa2c80",
    ),
    (
        Path("/workspace/production_prediction_run_baseline_disabled_post_dry_run_readonly_20260911.zip"),
        "2930e43193ca8e17abbc4d0ec2eff79090070efc5bc44727e3e16e866e546663",
    ),
    (
        Path("/workspace/production_prediction_run_baseline_disabled_post_dry_run_readonly_v2_20260911.zip"),
        "405927d6ee55ccd7c8872feea9c9b000737bbac9c243099665961aabd15627b0",
    ),
)


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    src = REHEARSE.read_text(encoding="utf-8")
    ast.parse(src)
    expect(True, "rehearse_ast_parse", failures)
    ast.parse(BACKUP.read_text(encoding="utf-8"))
    expect(True, "backup_design_ast_parse", failures)
    expect("app.data.db import migrate" in src or "from app.data.db import migrate" in src, "uses_official_migrate", failures)
    expect("FIRST_APPLY_VIA" in src, "records_official_migrate", failures)
    expect("PRODUCTION_APPLY_READY" in src, "emits_apply_ready", failures)
    expect('emit("PRODUCTION_APPLY_READY", "NO")' in src, "apply_ready_hard_no", failures)
    expect("PRODUCTION_DB_PATHS" in src and "KEIBA-Single-AI" in src, "refuses_prod_db", failures)
    expect("PREDICTION_RUNS_ENABLED=0 then UNSET EXPECT_AI_ALLOW_MIGRATION_019 then DROP INDEX" in src, "rollback_order_in_code", failures)

    flags = FLAGS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    owner = OWNER.read_text(encoding="utf-8")
    constraints = CONSTRAINTS.read_text(encoding="utf-8")
    collision = COLLISION.read_text(encoding="utf-8")
    rollback = ROLLBACK.read_text(encoding="utf-8")
    backup_doc = BACKUP_DOC.read_text(encoding="utf-8")
    audit = AUDIT.read_text(encoding="utf-8")
    expect("PRODUCTION_APPLY_READY=NO" in flags, "flag_apply_no", failures)
    expect("OWNER_APPLY_APPROVED=NO" in flags, "flag_owner_apply_no", failures)
    expect("OWNER_AUDIT_IMPORTED=YES" in flags, "flag_imported", failures)
    expect("6f0901221eaa625c51976d5ce6aae110175732a1cd7dfd846c6d774a24f66862" in flags, "flag_owner_sha", failures)
    expect("PRODUCTION_BACKUP_READY=NO" in flags, "flag_backup_no", failures)
    expect("GITHUB_PR23_UPDATED=NO" in flags, "flag_pr23", failures)
    expect("GITHUB_PR24_UPDATED=NO" in flags, "flag_pr24", failures)
    expect("GITHUB_PR25_UPDATED=NO" in flags, "flag_pr25", failures)
    expect("THIS IS NOT APPLY" in readme, "readme_not_apply", failures)
    expect("PR #23 / #24 / #25" in readme, "readme_no_old_prs", failures)
    expect("PREDICTION_RUNS_ENABLED=0" in owner, "owner_rollback_enabled0", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_019" in owner, "owner_rollback_allow", failures)
    expect("Creating a Production backup" in constraints, "constraints_no_prod_backup", failures)
    expect("STUBS_ARE_LIVE_SQL=NO" in collision, "collision_stubs_not_live", failures)
    expect("022_prediction_run_idempotency" in collision, "collision_recommend_022", failures)
    expect("PREDICTION_RUNS_ENABLED=0" in rollback, "rollback_step1", failures)
    expect("unset EXPECT_AI_ALLOW_MIGRATION_019" in rollback, "rollback_step2", failures)
    expect("DROP INDEX IF EXISTS uq_predictions_idempotency_key_not_null" in rollback, "rollback_step3", failures)
    expect("PRODUCTION_BACKUP_READY=NO" in backup_doc, "backup_doc_not_ready", failures)
    expect("Connection.backup" in backup_doc, "backup_doc_api", failures)
    expect("OUTPUT_SHA256=6f0901221eaa625c51976d5ce6aae110175732a1cd7dfd846c6d774a24f66862" in audit, "audit_sha", failures)
    expect("NOT live Production SQL" in STUB_019.read_text(encoding="utf-8"), "stub019_not_live", failures)
    expect("NOT live Production SQL" in STUB_020.read_text(encoding="utf-8"), "stub020_not_live", failures)
    expect("NOT live Production SQL" in STUB_021.read_text(encoding="utf-8"), "stub021_not_live", failures)
    expect(file_sha(PERSIST_019) == PERSIST_019_SHA, "persist_019_sha", failures)
    expect("ALLOW_LOCAL_SQLITE_BACKUP" in BACKUP.read_text(encoding="utf-8"), "backup_gate", failures)

    for path, digest in PROTECTED_ZIPS:
        expect(path.is_file(), "protected_exists_" + path.name, failures)
        if path.is_file():
            expect(file_sha(path) == digest, "protected_sha_" + path.name, failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d" % len(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
