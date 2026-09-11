#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "files" / "services" / "win5-ai"
WIN5 = Path("/workspace/services/win5-ai")
ARCH_019 = FILES / "app/data/migrations_not_apply/019_prediction_run_idempotency.sql"
SQL_022 = FILES / "app/data/migrations/022_prediction_run_idempotency.sql"
OLD_SHA = "d8fc71e316d7819a4dcfc0977bf6444308410144b62fd29a33ca764ea853370f"
PROTECTED = (
    (
        Path("/workspace/production_single_ai_prediction_run_local_review_v4_20260911.zip"),
        "4fd4dc88315f7dbab3f495dea249ad1fcb715b375a64de85762a779571aa2c80",
    ),
    (
        Path("/workspace/production_prediction_run_baseline_disabled_post_dry_run_readonly_v2_20260911.zip"),
        "405927d6ee55ccd7c8872feea9c9b000737bbac9c243099665961aabd15627b0",
    ),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    expect(sha(ARCH_019) == OLD_SHA, "019_archive_unmodified", failures)
    expect("022_prediction_run_idempotency" in SQL_022.read_text(encoding="utf-8"), "022_header", failures)
    db_src = (FILES / "app/data/db.py").read_text(encoding="utf-8")
    expect("PERSIST_MIGRATION = \"022_prediction_run_idempotency\"" in db_src, "const_022", failures)
    expect("SUPERSEDED_019" in db_src, "skip_019", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_022" in db_src, "gate_022", failures)
    expect("019_prediction_run_idempotency" not in list((WIN5 / "app/data/migrations").glob("*.sql")).__repr__() or not (WIN5 / "app/data/migrations/019_prediction_run_idempotency.sql").exists(), "019_not_active", failures)
    expect(not (WIN5 / "app/data/migrations/019_prediction_run_idempotency.sql").exists(), "019_removed_from_active", failures)
    rollback = (ROOT / "rollback.md").read_text(encoding="utf-8")
    expect("PREDICTION_RUNS_ENABLED=0" in rollback, "rb_step1", failures)
    expect("EXPECT_AI_ALLOW_MIGRATION_022" in rollback, "rb_step2", failures)
    expect("DROP INDEX IF EXISTS uq_predictions_idempotency_key_not_null" in rollback, "rb_step3", failures)
    for path, digest in PROTECTED:
        expect(path.is_file() and sha(path) == digest, "protected_" + path.name, failures)

    sys.path.insert(0, str(WIN5))
    os.environ["EXPECT_AI_DB_PATH"] = str(Path(tempfile.mkdtemp(prefix="v5-022-")) / "t.db")
    os.environ["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_019", None)
    from app.data.db import PERSIST_MIGRATION, migrate

    applied = migrate()
    expect(PERSIST_MIGRATION in applied, "first_apply_022", failures)
    second = migrate()
    expect(second == [] or PERSIST_MIGRATION not in second, "second_noop", failures)
    conn = sqlite3.connect(os.environ["EXPECT_AI_DB_PATH"])
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations")]
    expect("022_prediction_run_idempotency" in versions, "version_row", failures)
    expect("019_prediction_run_idempotency" not in versions, "no_019_version", failures)
    conn.close()

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d" % len(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
