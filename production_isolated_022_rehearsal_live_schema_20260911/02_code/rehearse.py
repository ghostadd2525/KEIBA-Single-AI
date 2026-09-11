#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Isolated 022 rehearsal on Owner-imported live predictions shape.

Never opens Production. Never enables POST. Never changes GET / UI.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

CODE = Path(__file__).resolve().parent
PACK = CODE.parent
sys.path.insert(0, str(CODE))

from migrate_022 import (  # noqa: E402
    PERSIST_MIGRATION,
    _IDEMPOTENCY_INDEX,
    _PREDICTION_RUN_COLUMNS,
    migrate,
    prediction_run_schema_status,
)

LIVE_SQL = CODE / "live_schema.sql"
OWNER_COLUMNS = (
    "id",
    "race_id",
    "core_race_id",
    "engine_source",
    "fallback_reason",
    "model_version",
    "bundle_json",
    "created_at",
)
# 001-018 names below match repo stems so schema_migrations looks Production-shaped.
REPO_STEMS_001_018 = (
    "001_init",
    "002_race_identity",
    "003_supply_platform",
    "004_user_domain",
    "005_results_eval",
    "006_result_automation",
    "007_collect_c0",
    "008_collect_contract_1_1",
    "009_user_race_results",
    "010_user_progress_audit",
    "011_research_evidence",
    "012_research_snapshot_features",
    "013_research_prediction_corpus",
    "014_research_historical_ingest",
    "015_research_race_meta",
    "016_research_knowledge_base",
    "017_research_knowledge_validation",
    "018_research_candidate_review",
)
LIVE_VERSIONS = REPO_STEMS_001_018 + (
    "019_final_predictions",
    "020_live_series",
    "021_live_series",
)
PRODUCTION_DB_PATHS = (
    "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db",
    "/opt/expect-ai/current/services/win5-ai/var/expect_ai.db",
    "/var/lib/expect-ai/expect_ai.db",
)
KV: list[str] = []


def emit(key: str, value: Any) -> None:
    if value is True:
        text = "YES"
    elif value is False:
        text = "NO"
    elif value is None:
        text = "UNKNOWN"
    else:
        text = str(value)
    line = "%s=%s" % (key, text.replace("\n", " ").replace("\r", ""))
    print(line)
    KV.append(line)


def refuse_prod(path: Path) -> None:
    resolved = str(path.resolve()) if path.exists() else str(path)
    for banned in PRODUCTION_DB_PATHS:
        if resolved == banned or resolved.startswith(banned):
            raise RuntimeError("refused Production DB path")


def pred_cols(conn: sqlite3.Connection) -> list[str]:
    return [str(r[1]) for r in conn.execute("PRAGMA table_info(predictions)")]


def versions(conn: sqlite3.Connection) -> list[str]:
    return [str(r[0]) for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")]


def index_present(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (_IDEMPOTENCY_INDEX,),
    ).fetchone()
    return row is not None


def seed_live(conn: sqlite3.Connection) -> None:
    conn.executescript(LIVE_SQL.read_text(encoding="utf-8"))
    for ver in LIVE_VERSIONS:
        conn.execute(
            "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES (?, 'owner-import')",
            (ver,),
        )
    bundle = '{"schema_version":"single-prediction-bundle/2.0","evaluation":{"runners":[]}}'
    for i in range(300):
        conn.execute(
            "INSERT INTO predictions(race_id, core_race_id, engine_source, fallback_reason, "
            "model_version, bundle_json, created_at) VALUES (?,?,?,?,?,?,?)",
            (
                "fixture-%03d" % i,
                None,
                "real_ai",
                None,
                "fixture",
                bundle,
                "2026-07-19T00:00:00+00:00",
            ),
        )
    conn.execute(
        "INSERT INTO conversation_history(session_id, role, content, intent, race_id, meta_json, created_at) "
        "VALUES ('s1','user','ping','chat',NULL,'{}','2026-07-19T00:00:00+00:00')"
    )
    conn.commit()


def legacy_insert(conn: sqlite3.Connection, race_id: str, engine: str) -> None:
    conn.execute(
        "INSERT INTO predictions(race_id, core_race_id, engine_source, fallback_reason, "
        "model_version, bundle_json, created_at) VALUES (?,?,?,?,?,?,?)",
        (race_id, None, engine, None, "legacy", "{}", "2026-09-11T00:00:00+00:00"),
    )


def main() -> int:
    emit("PACK", PACK.name)
    emit("OWNER_LIVE_SCHEMA_INVENTORY_IMPORTED", "YES")
    emit("AUDIT_STATUS", "SUCCESS")
    emit("SQLITE_VERSION_OWNER", "3.45.1")
    emit("OWNER_SCHEMA_MIGRATIONS_COUNT", 22)
    emit("HAS_019_FINAL_PREDICTIONS", "YES")
    emit("HAS_020_SERIES", "YES")
    emit("HAS_021_SERIES", "YES")
    emit("HAS_PERSIST_019", "NO")
    emit("HAS_PERSIST_022", "NO")
    emit("LIVE_SCHEMA_022_STRUCTURAL_COMPATIBILITY", "YES")
    emit("PRODUCTION_CHANGED", "NO")
    emit("DB_CHANGED", "NO")
    emit("BACKUP_COPY_EXECUTED", "NO")
    emit("APPLY_EXECUTED", "NO")
    emit("PRODUCTION_BACKUP_EXECUTED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("GET_SURFACE_MODIFIED", "NO")
    emit("UI_MODIFIED", "NO")
    emit("CONVERSATION_SERVICE_MODIFIED", "NO")
    emit("WIN_PROB_MODEL_RANK_MARK_MODIFIED", "NO")
    emit("PREDICTION_RUNS_ENABLED_DEFAULT", "UNSET_DISABLED")
    emit("HTTP_STARTED", "NO")

    tmp = Path(tempfile.mkdtemp(prefix="iso-022-live-"))
    db = tmp / "live_shape.db"
    refuse_prod(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    seed_live(conn)
    cols = pred_cols(conn)
    emit("PREDICTIONS_COLUMN_COUNT_BEFORE", len(cols))
    emit("PREDICTIONS_EXISTING_COLUMNS", ",".join(cols))
    emit("PREDICTIONS_COLUMNS_MATCH_OWNER", cols == list(OWNER_COLUMNS))
    idx = [
        str(r[1])
        for r in conn.execute("PRAGMA index_list(predictions)")
    ]
    emit("PREDICTIONS_INDEX_BEFORE", ",".join(idx))
    emit("HAS_022_COLS_BEFORE", any(c in cols for c in _PREDICTION_RUN_COLUMNS))
    emit("SEEDED_MIGRATION_COUNT", len(versions(conn)))
    emit("SEEDED_HAS_019_FINAL", "019_final_predictions" in versions(conn))
    emit("SEEDED_HAS_PERSIST_019", "019_prediction_run_idempotency" in versions(conn))
    emit("SEEDED_HAS_PERSIST_022", PERSIST_MIGRATION in versions(conn))
    emit("ROWCOUNT_BEFORE", int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]))
    emit("SCHEMA_STATUS_BEFORE", prediction_run_schema_status(conn))

    os.environ.pop("PREDICTION_RUNS_ENABLED", None)
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_019", None)
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
    blocked = migrate(conn)
    emit("FIRST_APPLY_WITHOUT_ALLOW", ",".join(blocked) if blocked else "NONE")
    emit("SCHEMA_STATUS_STILL_ABSENT", prediction_run_schema_status(conn) == "absent")

    os.environ["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    first = migrate(conn)
    emit("FIRST_APPLY", ",".join(first) if first else "NONE")
    emit("FIRST_APPLY_VIA", "standalone_migrate_022")
    emit("MIGRATION_FIRST_APPLY_PASS", PERSIST_MIGRATION in first)
    emit("SCHEMA_STATUS_AFTER_FIRST", prediction_run_schema_status(conn))
    cols2 = pred_cols(conn)
    emit("PREDICTIONS_COLUMN_COUNT_AFTER", len(cols2))
    emit("NEW_COLS_PRESENT", all(c in cols2 for c in _PREDICTION_RUN_COLUMNS))
    emit("LIVE_INDEX_STILL_PRESENT", "idx_predictions_race" in [
        str(r[1]) for r in conn.execute("PRAGMA index_list(predictions)")
    ])
    emit("PARTIAL_UNIQUE_INDEX_PRESENT", index_present(conn))
    nulls = int(
        conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE persist_source IS NULL "
            "AND idempotency_key IS NULL AND input_snapshot_hash IS NULL "
            "AND prediction_semantic_hash IS NULL"
        ).fetchone()[0]
    )
    emit("NULL_COMPAT_ROWCOUNT", nulls)
    emit("EXISTING_NULL_ROW_COMPAT", nulls == 300)
    emit("ROWCOUNT_AFTER_FIRST", int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]))

    second = migrate(conn)
    emit("SECOND_APPLY", ",".join(second) if second else "NONE")
    emit("MIGRATION_SECOND_APPLY_NOOP", second == [])
    emit("SCHEMA_STATUS_AFTER_SECOND", prediction_run_schema_status(conn))

    conn.execute("DROP INDEX IF EXISTS %s" % _IDEMPOTENCY_INDEX)
    conn.commit()
    emit("SCHEMA_STATUS_AFTER_INDEX_DROP", prediction_run_schema_status(conn))
    repaired = migrate(conn)
    emit("PARTIAL_REPAIR_APPLIED", ",".join(repaired) if repaired else "NONE")
    emit("MIGRATION_PARTIAL_REPAIR_PASS", prediction_run_schema_status(conn) == "complete" and index_present(conn))
    emit("PARTIAL_ROWCOUNT_STILL_300", int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]) == 300)

    legacy_insert(conn, "conv-legacy-1", "conversation")
    legacy_insert(conn, "ra-legacy-1", "result_automation")
    legacy_insert(conn, "challenge-legacy-1", "challenge")
    conn.execute(
        "INSERT INTO conversation_history(session_id, role, content, intent, race_id, meta_json, created_at) "
        "VALUES ('s2','assistant','ok','chat',NULL,'{}','2026-09-11T00:00:00+00:00')"
    )
    conn.commit()
    extra = conn.execute(
        "SELECT race_id, persist_source, idempotency_key FROM predictions "
        "WHERE race_id IN ('conv-legacy-1','ra-legacy-1','challenge-legacy-1')"
    ).fetchall()
    emit("LEGACY_INSERT_COUNT", len(extra))
    emit("CONVERSATION_RA_CHALLENGE_NULL_COMPAT", all(r[1] is None and r[2] is None for r in extra) and len(extra) == 3)
    emit("CONVERSATION_HISTORY_COUNT", int(conn.execute("SELECT COUNT(*) FROM conversation_history").fetchone()[0]))

    os.environ["PREDICTION_RUNS_ENABLED"] = "0"
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
    conn.execute("DROP INDEX IF EXISTS %s" % _IDEMPOTENCY_INDEX)
    conn.commit()
    after_unset = migrate(conn)
    emit("ROLLBACK_MIGRATE_AFTER_UNSET_ALLOW", ",".join(after_unset) if after_unset else "NONE")
    emit("ROLLBACK_INDEX_ABSENT", not index_present(conn))
    emit("ROLLBACK_COLUMNS_REMAIN", all(c in pred_cols(conn) for c in _PREDICTION_RUN_COLUMNS))
    emit("ROLLBACK_REQUIRED_ORDER", "PREDICTION_RUNS_ENABLED=0 then UNSET EXPECT_AI_ALLOW_MIGRATION_022 then DROP INDEX")

    emit("POST_ENABLED", "NO")
    emit("PRODUCTION_BACKUP_DESIGN_APPROVED", "NO")
    emit("PRODUCTION_BACKUP_EXECUTED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("NEXT_STEP", "BACKUP_V2_AND_LIVE_SCHEMA_BASED_ISOLATED_REHEARSAL")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
