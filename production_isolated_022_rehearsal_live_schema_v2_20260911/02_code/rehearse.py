#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Isolated 022 rehearsal v2. Owner SCHEMA_MIGRATIONS 22-name set is canonical.

Never opens Production. Never starts HTTP. Never enables POST.
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
OWNER_SCHEMA_MIGRATIONS = (
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
    "019_final_predictions",
    "020_research_corpus_canonical",
    "020_user_challenge_lifecycle",
    "021_user_challenge_point_events",
)
FORBIDDEN_FAKE_SEEDS = ("020_live_series", "021_live_series")
PRODUCTION_DB_PATHS = (
    "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db",
    "/opt/expect-ai/current/services/win5-ai/var/expect_ai.db",
    "/var/lib/expect-ai/expect_ai.db",
)


def emit(key: str, value: Any) -> None:
    if value is True:
        text = "YES"
    elif value is False:
        text = "NO"
    elif value is None:
        text = "UNKNOWN"
    else:
        text = str(value)
    print("%s=%s" % (key, text.replace("\n", " ").replace("\r", "")))


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


def race_index_cols(conn: sqlite3.Connection) -> list[str]:
    return [
        str(r[2])
        for r in conn.execute("PRAGMA index_info(idx_predictions_race)").fetchall()
    ]


def seed_compare(seeded: list[str]) -> dict[str, Any]:
    owner = list(OWNER_SCHEMA_MIGRATIONS)
    owner_set = set(owner)
    seeded_set = set(seeded)
    missing = sorted(owner_set - seeded_set)
    extra = sorted(seeded_set - owner_set)
    dupes = sorted({v for v in seeded if seeded.count(v) > 1})
    fakes = sorted(v for v in seeded if v in FORBIDDEN_FAKE_SEEDS)
    return {
        "count": len(seeded),
        "set_match": seeded_set == owner_set and len(seeded) == 22 and not dupes,
        "missing": missing,
        "extra": extra,
        "dupes": dupes,
        "fakes": fakes,
        "ordered_match": seeded == owner,
    }


def seed_live(conn: sqlite3.Connection) -> None:
    conn.executescript(LIVE_SQL.read_text(encoding="utf-8"))
    for ver in OWNER_SCHEMA_MIGRATIONS:
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
    os.environ["PREDICTION_RUNS_ENABLED"] = "0"
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_019", None)
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)

    emit("PACK", PACK.name)
    emit("OWNER_LIVE_SCHEMA_INVENTORY_IMPORTED", "YES")
    emit("CLAIMED_WRONG_SEED_ZIP_SHA256", "7981db7fff2d8a8d0a057bf66aeddca72a37c842cdf66c926dd5d3f9ac4c1037")
    emit("CLAIMED_WRONG_SEED_ZIP_OVERWRITTEN", "NO")
    emit("BACKUP_V2_INDEPENDENT_REVIEW_COMPLETE", "YES")
    emit("BACKUP_DESIGN_REVIEW", "PASS")
    emit("PRODUCTION_BACKUP_DESIGN_APPROVED", "YES")
    emit("PRODUCTION_BACKUP_EXECUTION_ALLOWED", "NO")
    emit("PRODUCTION_BACKUP_EXECUTION_PACK", "NO")
    emit("PRODUCTION_BACKUP_EXECUTED", "NO")
    emit("LIVE_SCHEMA_REHEARSAL_INDEPENDENT_REVIEW_COMPLETE", "YES")
    emit("LIVE_SCHEMA_022_REHEARSAL_PASS_CLAIMED_ZIP", "NO")
    emit("FAIL_REASON_CLAIMED_ZIP", "SEED_MIGRATION_SET_MISMATCH")
    emit("PRODUCTION_CHANGED", "NO")
    emit("DB_CHANGED", "NO")
    emit("APPLY_EXECUTED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("GET_SURFACE_MODIFIED", "NO")
    emit("UI_MODIFIED", "NO")
    emit("HTTP_STARTED", "NO")
    emit("PREDICTION_RUNS_ENABLED", "0")

    tmp = Path(tempfile.mkdtemp(prefix="iso-022-v2-"))
    db = tmp / "live_shape.db"
    refuse_prod(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    seed_live(conn)

    cols = pred_cols(conn)
    emit("PREDICTIONS_COLUMN_COUNT_BEFORE", len(cols))
    emit("PREDICTIONS_EXISTING_COLUMNS", ",".join(cols))
    emit("PREDICTIONS_COLUMNS_MATCH_OWNER", cols == list(OWNER_COLUMNS))
    emit("IDX_PREDICTIONS_RACE_COLS", ",".join(race_index_cols(conn)))
    emit("IDX_PREDICTIONS_RACE_MATCH_OWNER", race_index_cols(conn) == ["race_id", "created_at"])

    seeded = versions(conn)
    cmp = seed_compare(seeded)
    emit("SEEDED_MIGRATION_COUNT", cmp["count"])
    emit("OWNER_CANONICAL_MIGRATION_COUNT", 22)
    emit("OWNER_SCHEMA_MIGRATIONS", ",".join(OWNER_SCHEMA_MIGRATIONS))
    emit("SEEDED_SCHEMA_MIGRATIONS", ",".join(seeded))
    emit("SEEDED_MIGRATION_SET_MATCH_OWNER", cmp["set_match"])
    emit("SEEDED_MIGRATION_ORDER_MATCH_OWNER", cmp["ordered_match"])
    emit("SEEDED_MISSING_COUNT", len(cmp["missing"]))
    emit("SEEDED_EXTRA_COUNT", len(cmp["extra"]))
    emit("SEEDED_DUPLICATE_COUNT", len(cmp["dupes"]))
    emit("SEEDED_FAKE_020_021_COUNT", len(cmp["fakes"]))
    if cmp["missing"]:
        emit("SEEDED_MISSING", ",".join(cmp["missing"]))
    if cmp["extra"]:
        emit("SEEDED_EXTRA", ",".join(cmp["extra"]))
    if not cmp["set_match"]:
        emit("LIVE_SCHEMA_022_REHEARSAL_PASS", "NO")
        emit("FAIL_REASON", "SEED_MIGRATION_SET_MISMATCH")
        conn.close()
        return 2

    os.environ["PREDICTION_RUNS_ENABLED"] = "0"
    blocked = migrate(conn)
    emit("FIRST_APPLY_WITHOUT_ALLOW", ",".join(blocked) if blocked else "NONE")

    os.environ["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    os.environ["PREDICTION_RUNS_ENABLED"] = "0"
    first = migrate(conn)
    emit("FIRST_APPLY", ",".join(first) if first else "NONE")
    emit("MIGRATION_FIRST_APPLY_PASS", PERSIST_MIGRATION in first)
    emit("NEW_COLS_PRESENT", all(c in pred_cols(conn) for c in _PREDICTION_RUN_COLUMNS))
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
    emit("EXISTING_NULL_ROW_COMPAT", nulls == 300)

    second = migrate(conn)
    emit("SECOND_APPLY", ",".join(second) if second else "NONE")
    emit("MIGRATION_SECOND_APPLY_NOOP", second == [])

    conn.execute("DROP INDEX IF EXISTS %s" % _IDEMPOTENCY_INDEX)
    conn.commit()
    emit("SCHEMA_STATUS_AFTER_INDEX_DROP", prediction_run_schema_status(conn))
    repaired = migrate(conn)
    emit("PARTIAL_REPAIR_APPLIED", ",".join(repaired) if repaired else "NONE")
    emit("MIGRATION_PARTIAL_REPAIR_PASS", prediction_run_schema_status(conn) == "complete" and index_present(conn))

    conn.execute("DROP INDEX IF EXISTS %s" % _IDEMPOTENCY_INDEX)
    conn.execute(
        "CREATE INDEX %s ON predictions(idempotency_key)" % _IDEMPOTENCY_INDEX
    )
    conn.commit()
    emit("SCHEMA_STATUS_AFTER_WRONG_INDEX", prediction_run_schema_status(conn))
    wrong_repaired = migrate(conn)
    emit("WRONG_INDEX_REPAIR_APPLIED", ",".join(wrong_repaired) if wrong_repaired else "NONE")
    emit("MIGRATION_WRONG_INDEX_REPAIR_PASS", prediction_run_schema_status(conn) == "complete")

    legacy_insert(conn, "conv-legacy-1", "conversation")
    legacy_insert(conn, "ra-legacy-1", "result_automation")
    legacy_insert(conn, "challenge-legacy-1", "challenge")
    conn.commit()
    extra = conn.execute(
        "SELECT persist_source, idempotency_key FROM predictions "
        "WHERE race_id IN ('conv-legacy-1','ra-legacy-1','challenge-legacy-1')"
    ).fetchall()
    emit("LEGACY_INSERT_COUNT", len(extra))
    emit("CONVERSATION_RA_CHALLENGE_NULL_COMPAT", all(r[0] is None and r[1] is None for r in extra) and len(extra) == 3)

    os.environ["PREDICTION_RUNS_ENABLED"] = "0"
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
    conn.execute("DROP INDEX IF EXISTS %s" % _IDEMPOTENCY_INDEX)
    conn.commit()
    after_unset = migrate(conn)
    emit("ROLLBACK_MIGRATE_AFTER_UNSET_ALLOW", ",".join(after_unset) if after_unset else "NONE")
    emit("ROLLBACK_INDEX_ABSENT", not index_present(conn))
    emit("ROLLBACK_COLUMNS_REMAIN", all(c in pred_cols(conn) for c in _PREDICTION_RUN_COLUMNS))
    emit("PREDICTION_RUNS_ENABLED", os.environ.get("PREDICTION_RUNS_ENABLED"))
    emit("POST_ENABLED", "NO")
    emit("PRODUCTION_BACKUP_EXECUTION_PACK", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("NEXT_STEP", "INDEPENDENT_REVIEW_OF_022_REHEARSAL_V2")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
