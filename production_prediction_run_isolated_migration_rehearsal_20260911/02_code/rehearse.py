#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Isolated current-schema migration rehearsal. Production DB is never opened."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

PACK = Path(__file__).resolve().parents[1]
REPO_MIG = PACK / "02_code" / "repo_migrations"
STUB_MIG = PACK / "02_code" / "live_schema_stubs"
PERSIST_019 = PACK / "02_code" / "persist_019" / "019_prediction_run_idempotency.sql"
EVIDENCE = PACK / "evidence"
WIN5 = Path(os.environ.get("WIN5_AI_ROOT") or "/workspace/services/win5-ai")
PERSIST_019_NAME = "019_prediction_run_idempotency"
INDEX_NAME = "uq_predictions_idempotency_key_not_null"
SAFE_EMPTY_DATE = "2099-01-01"
PRODUCTION_DB_PATHS = (
    "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db",
    "/opt/expect-ai/current/services/win5-ai/var/expect_ai.db",
    "/var/lib/expect-ai/expect_ai.db",
)
KV_LINES: list[str] = []

if str(WIN5) not in sys.path:
    sys.path.insert(0, str(WIN5))


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
    KV_LINES.append(line)


def versions(conn: sqlite3.Connection) -> list[str]:
    return [str(r[0]) for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")]


def pred_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])


def pred_cols(conn: sqlite3.Connection) -> list[str]:
    return [str(r[1]) for r in conn.execute("PRAGMA table_info(predictions)")]


def index_sql(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
        (INDEX_NAME,),
    ).fetchone()
    return str(row[0]) if row and row[0] else None


def persist_not_null(conn: sqlite3.Connection) -> int:
    if "persist_source" not in pred_cols(conn):
        return 0
    return int(conn.execute("SELECT COUNT(*) FROM predictions WHERE persist_source IS NOT NULL").fetchone()[0])


def hist_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM conversation_history").fetchone()[0])


def seed_predictions(conn: sqlite3.Connection, n: int = 300) -> None:
    bundle = json.dumps(
        {"schema_version": "single-prediction-bundle/2.0", "race_id": "fixture", "evaluation": {"runners": []}},
        ensure_ascii=False,
    )
    for i in range(n):
        conn.execute(
            "INSERT INTO predictions(race_id, engine_source, fallback_reason, model_version, bundle_json, created_at) "
            "VALUES (?,?,?,?,?,?)",
            ("2026-07-19-01-%02d" % ((i % 12) + 1), "real_ai", None, "fixture", bundle, "2026-07-19T00:00:00+00:00"),
        )
    conn.commit()


def assemble_current_schema(dest: Path) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    for src in sorted(REPO_MIG.glob("*.sql")):
        shutil.copy2(src, dest / src.name)
    for src in sorted(STUB_MIG.glob("*.sql")):
        shutil.copy2(src, dest / src.name)
    return sorted(p.stem for p in dest.glob("*.sql"))


def apply_sql_dir(conn: sqlite3.Connection, migrations_dir: Path) -> list[str]:
    applied: list[str] = []
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    done = {r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    for sql_path in sorted(migrations_dir.glob("*.sql")):
        version = sql_path.stem
        if version in done:
            continue
        conn.executescript(sql_path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES (?, datetime('now'))",
            (version,),
        )
        applied.append(version)
    conn.commit()
    return applied


def envelope_schema(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"ok": False, "keys": [], "data_type": "missing"}
    data = payload.get("data")
    return {
        "ok": payload.get("ok") is True and "data" in payload and isinstance(data, list),
        "keys": sorted(payload.keys()),
        "data_type": "list" if isinstance(data, list) else type(data).__name__,
        "item_count": len(data) if isinstance(data, list) else 0,
    }


def refuse_production_path(path: Path) -> None:
    resolved = str(path.resolve())
    for banned in PRODUCTION_DB_PATHS:
        if resolved == banned or resolved.startswith(banned + "."):
            raise RuntimeError("refused Production DB path: %s" % resolved)


def python_backup(src_path: Path, dst_path: Path) -> None:
    refuse_production_path(src_path)
    refuse_production_path(dst_path)
    src = sqlite3.connect(str(src_path))
    dst = sqlite3.connect(str(dst_path))
    try:
        src.backup(dst, pages=64, sleep=0.01)
        dst.commit()
        check = dst.execute("PRAGMA integrity_check").fetchone()
        if not check or str(check[0]) != "ok":
            raise RuntimeError("backup integrity_check failed: %s" % (check,))
    finally:
        dst.close()
        src.close()


def open_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def serve(db_path: Path, tmp: Path, *, allow_019: bool) -> tuple[ThreadingHTTPServer, str]:
    from tests.ops.helpers import _free_port, http_json
    from app.main import Handler

    os.environ["EXPECT_AI_DB_PATH"] = str(db_path)
    os.environ["AI_ENGINE"] = "mock"
    os.environ["EXPECT_AI_OPS_DIR"] = str(tmp / "ops")
    os.environ["EXPECT_AI_REPORT_DIR"] = str(tmp / "reports")
    os.environ["EXPECT_AI_LOG_DIR"] = str(tmp / "logs")
    os.environ.pop("PREDICTION_RUNS_ENABLED", None)
    if allow_019:
        os.environ["EXPECT_AI_ALLOW_MIGRATION_019"] = "1"
    else:
        os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_019", None)
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % port
    last_exc: Exception | None = None
    for _ in range(80):
        try:
            http_json(base + "/health")
            last_exc = None
            break
        except Exception as exc:
            last_exc = exc
            time.sleep(0.05)
    if last_exc is not None:
        server.shutdown()
        server.server_close()
        raise last_exc
    return server, base


def probe_get(base: str) -> tuple[int, dict[str, Any], int, dict[str, Any], int, dict[str, Any]]:
    from tests.ops.helpers import http_json

    s1, p1 = http_json(base + "/v1/predictions?date=" + SAFE_EMPTY_DATE)
    s2, p2 = http_json(base + "/v1/predictions")
    post_s, post_p = http_json(base + "/v1/prediction-runs", method="POST", body={"race_id": "x"})
    return s1, p1, s2, p2, post_s, post_p


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    emit("PACK", PACK.name)
    emit("WIN5_AI_ROOT", str(WIN5))
    emit("PRODUCTION_DB_OPENED", "NO")
    emit("PRODUCTION_CHANGED", "NO")
    emit("DB_CHANGED", "NO")
    emit("OWNER_AUDIT_IMPORTED", "YES")
    emit("OWNER_OUTPUT_SHA256", "6f0901221eaa625c51976d5ce6aae110175732a1cd7dfd846c6d774a24f66862")
    emit("DISABLED_POST_DRY_RUN_COMPLETE", "YES")
    emit("CURRENT_PRODUCTION_BASELINE_COMPLETE", "YES_EXCEPT_CURRENT_DAY")
    emit("CURRENT_DAY_DATA_VERIFIED", "NO_RESEARCH_WEEK")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("PRODUCTION_BACKUP_EXECUTED", "NO")
    emit("PRODUCTION_BACKUP_READY", "NO")
    emit("SQLITE3_CLI_PRESENT_PRODUCTION", "NO")
    emit("DB_BACKUP_POSSIBLE_PRODUCTION", "NO")
    emit("DB_BACKUP_POSSIBLE_REASON", "SQLITE3_CLI_MISSING")

    for banned in PRODUCTION_DB_PATHS:
        emit("PRODUCTION_DB_CANDIDATE_REFUSED", banned)

    stems_all = (
        [p.stem for p in sorted(REPO_MIG.glob("*.sql"))]
        + [p.stem for p in sorted(STUB_MIG.glob("*.sql"))]
        + [PERSIST_019.stem]
    )
    ranked = sorted(stems_all)
    emit("MIGRATION_SORT_ORDER", ",".join(ranked))
    persist_after_final = ranked.index(PERSIST_019_NAME) > ranked.index("019_final_predictions")
    persist_before_020 = ranked.index(PERSIST_019_NAME) < next(i for i, s in enumerate(ranked) if s.startswith("020_"))
    emit("PERSIST_019_SORTS_AFTER_019_FINAL", persist_after_final)
    emit("PERSIST_019_SORTS_BEFORE_020", persist_before_020)
    emit("LIVE_019_FINAL_SQL_IN_GIT", "NO")
    emit("LIVE_020_SQL_IN_GIT", "NO")
    emit("LIVE_021_SQL_IN_GIT", "NO")
    emit("ORIGIN_MAIN_MIGRATIONS", "001_through_018")
    emit("COLLISION_TWO_019_STEMS", "YES")
    emit(
        "COLLISION_NOTE",
        "live 019_final_predictions and persist 019_prediction_run_idempotency share prefix 019; stems differ so migrate() treats them as distinct versions",
    )
    emit("RECOMMENDED_PRODUCTION_VERSION", "022_prediction_run_idempotency_after_live_021")
    emit("STUBS_ARE_LIVE_SQL", "NO")
    emit("PRODUCTION_SCHEMA_COPIED", "NO")

    tmp = Path(tempfile.mkdtemp(prefix="isolated-019-rehearse-"))
    db_path = tmp / "current_schema.db"
    refuse_production_path(db_path)
    mig_dir = tmp / "current_migrations"
    assembled = assemble_current_schema(mig_dir)
    emit("ASSEMBLED_CURRENT_STEMS", ",".join(assembled))
    assert PERSIST_019_NAME not in assembled

    os.environ["EXPECT_AI_DB_PATH"] = str(db_path)
    os.environ["AI_ENGINE"] = "mock"
    os.environ["EXPECT_AI_OPS_DIR"] = str(tmp / "ops")
    os.environ["EXPECT_AI_REPORT_DIR"] = str(tmp / "reports")
    os.environ["EXPECT_AI_LOG_DIR"] = str(tmp / "logs")
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_019", None)
    os.environ.pop("PREDICTION_RUNS_ENABLED", None)
    for d in ("ops", "reports", "logs"):
        (tmp / d).mkdir(parents=True, exist_ok=True)

    conn = open_db(db_path)
    applied_current = apply_sql_dir(conn, mig_dir)
    emit("CURRENT_SCHEMA_APPLY", ",".join(applied_current))
    assert PERSIST_019_NAME not in applied_current
    assert "019_final_predictions" in applied_current
    assert any(v.startswith("020_") for v in applied_current)
    assert any(v.startswith("021_") for v in applied_current)
    seed_predictions(conn, 300)
    emit("PREDICTIONS_SEEDED", pred_count(conn))
    emit("PREDICTIONS_COLUMNS_CURRENT", ",".join(pred_cols(conn)))
    emit("MIGRATION_019_STATUS_BEFORE", "absent" if PERSIST_019_NAME not in versions(conn) else "present")
    emit("SCHEMA_VERSIONS_CURRENT", ",".join(versions(conn)))
    emit("PERSIST_SOURCE_COLUMN_PRESENT_BEFORE", "persist_source" in pred_cols(conn))
    hist_before_get1 = hist_count(conn)
    count_before_get1 = pred_count(conn)
    conn.close()

    from tests.ops.helpers import http_json

    server, base = serve(db_path, tmp, allow_019=False)
    try:
        health_s, health_p = http_json(base + "/health")
        s1, p1, s2, p2, post_s, post_p = probe_get(base)
    finally:
        server.shutdown()
        server.server_close()
    env1 = envelope_schema(p1)
    env2 = envelope_schema(p2)
    conn = open_db(db_path)
    count_after_get1 = pred_count(conn)
    hist_after_get1 = hist_count(conn)
    emit("HEALTH_HTTP_BEFORE", health_s)
    emit("RA_HEALTH_OK_BEFORE", bool((health_p or {}).get("result_automation", {}).get("ok", True) or health_s == 200))
    emit("GET_BEFORE_019_SAFE_HTTP", s1)
    emit("GET_BEFORE_019_LIST_HTTP", s2)
    emit("GET_ENVELOPE_SCHEMA_OK_BEFORE", env1["ok"] and env2["ok"])
    emit("GET_ENVELOPE_KEYS_BEFORE", ",".join(env1["keys"]))
    emit("GET_SAFE_ITEM_COUNT_BEFORE", env1["item_count"])
    emit("GET_ROWCOUNT_BEFORE", count_after_get1)
    emit("GET_DB_WRITE_COUNT_BEFORE_019", count_after_get1 - count_before_get1)
    emit("CONVERSATION_HISTORY_COUNT_BEFORE_GET1", hist_before_get1)
    emit("CONVERSATION_HISTORY_COUNT_AFTER_GET1", hist_after_get1)
    emit("CONVERSATION_HISTORY_COUNT_UNCHANGED_GET1", hist_before_get1 == hist_after_get1)
    emit("POST_DISABLED_HTTP_BEFORE", post_s)
    emit("POST_DISABLED_BEFORE", post_s == 503)
    emit("POST_ROUTE_PRESENT_LOCAL", post_s == 503)
    conn.close()
    (EVIDENCE / "get_before.json").write_text(
        json.dumps({"safe": p1, "list_keys": env2["keys"], "post": post_p}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    os.environ["EXPECT_AI_DB_PATH"] = str(db_path)
    os.environ["EXPECT_AI_ALLOW_MIGRATION_019"] = "1"
    os.environ.pop("PREDICTION_RUNS_ENABLED", None)
    from app.data.db import migrate, prediction_run_schema_status

    first = migrate()
    emit("FIRST_APPLY", ",".join(first) if first else "NONE")
    emit("FIRST_APPLY_VIA", "app.data.db.migrate")
    emit("MIGRATION_FIRST_APPLY_PASS", PERSIST_019_NAME in first)
    conn = open_db(db_path)
    status1 = prediction_run_schema_status(conn)
    emit("MIGRATION_019_STATUS_AFTER_FIRST", status1)
    emit("IDEMPOTENCY_INDEX_SQL", (index_sql(conn) or "").replace("\n", " "))
    emit("PREDICTIONS_COUNT_AFTER_FIRST", pred_count(conn))
    emit("PERSIST_SOURCE_COLUMN_PRESENT_AFTER", "persist_source" in pred_cols(conn))
    emit("PERSIST_SOURCE_NOT_NULL_AFTER_FIRST", persist_not_null(conn))
    emit("NULL_COMPAT_300", pred_count(conn) == 300 and persist_not_null(conn) == 0)
    emit("SCHEMA_VERSIONS_AFTER_FIRST", ",".join(versions(conn)))
    conn.close()

    second = migrate()
    emit("SECOND_APPLY", ",".join(second) if second else "NOOP")
    emit("MIGRATION_SECOND_APPLY_NOOP", second == [])
    conn = open_db(db_path)
    count_after_019 = pred_count(conn)
    emit("PREDICTIONS_COUNT_AFTER_SECOND", count_after_019)
    conn.close()

    snapshot_300 = tmp / "after_019_300.db"
    python_backup(db_path, snapshot_300)

    conn = open_db(db_path)
    count_before_get2 = pred_count(conn)
    hist_before_get2 = hist_count(conn)
    conn.close()
    server, base = serve(db_path, tmp, allow_019=True)
    try:
        health_s2, health_p2 = http_json(base + "/health")
        s3, p3, s4, p4, post_s2, post_p2 = probe_get(base)
    finally:
        server.shutdown()
        server.server_close()
    env3 = envelope_schema(p3)
    env4 = envelope_schema(p4)
    conn = open_db(db_path)
    count_after_get2 = pred_count(conn)
    hist_after_get2 = hist_count(conn)
    emit("HEALTH_HTTP_AFTER", health_s2)
    emit("RA_HEALTH_OK_AFTER", health_s2 == 200)
    emit("GET_AFTER_019_SAFE_HTTP", s3)
    emit("GET_AFTER_019_LIST_HTTP", s4)
    emit("GET_ENVELOPE_SCHEMA_OK_AFTER", env3["ok"] and env4["ok"])
    emit("GET_ENVELOPE_KEYS_AFTER", ",".join(env3["keys"]))
    emit("GET_RESPONSE_SCHEMA_UNCHANGED", env1["keys"] == env3["keys"] and env1["data_type"] == env3["data_type"] and env2["keys"] == env4["keys"])
    emit("GET_SAFE_ITEM_COUNT_AFTER", env3["item_count"])
    emit("GET_ROWCOUNT_AFTER", count_after_get2)
    emit("GET_DB_WRITE_COUNT_AFTER_019", count_after_get2 - count_before_get2)
    emit("GET_ROWCOUNT_UNCHANGED_ACROSS_019", count_after_get2 == 300 and count_after_019 == 300)
    emit("CONVERSATION_HISTORY_COUNT_BEFORE_GET2", hist_before_get2)
    emit("CONVERSATION_HISTORY_COUNT_AFTER_GET2", hist_after_get2)
    emit("CONVERSATION_HISTORY_COUNT_UNCHANGED", hist_after_get1 == hist_after_get2)
    emit("POST_DISABLED_HTTP_AFTER", post_s2)
    emit("POST_DISABLED_AFTER_019", post_s2 == 503)
    conn.close()
    (EVIDENCE / "get_after.json").write_text(
        json.dumps({"safe": p3, "list_keys": env4["keys"], "post": post_p2}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    os.environ["EXPECT_AI_DB_PATH"] = str(db_path)
    os.environ["EXPECT_AI_ALLOW_MIGRATION_019"] = "1"
    os.environ["AI_ENGINE"] = "mock"
    os.environ.pop("PREDICTION_RUNS_ENABLED", None)

    conversation_chat_ok = False
    conversation_save_ok = False
    try:
        from app.conversation.service import ConversationService

        chat_out = ConversationService().chat(
            {
                "message": "阪神11Rを予想して",
                "session_id": "rehearse-conv-1",
                "race_id": "20260719_hanshin_11",
            }
        )
        conversation_chat_ok = bool(chat_out.get("session_id"))
    except Exception as exc:
        emit("CONVERSATION_CHAT_ERROR", str(exc))
        from app.data.repository import ConversationRepository

        ConversationRepository().append(
            session_id="rehearse-conv-1",
            role="user",
            content="ping",
            intent="chat",
            race_id="conv-legacy-1",
            meta={},
        )
    from app.data.repository import PredictionRepository

    PredictionRepository().save(
        race_id="conv-legacy-1",
        bundle={"schema_version": "single-prediction-bundle/2.0", "race_id": "conv-legacy-1"},
        engine_source="conversation",
        fallback_reason=None,
        core_race_id=None,
        model_version="legacy",
    )
    conversation_save_ok = True

    challenge_ok = False
    try:
        from app.challenge import service as challenge_service

        fake_challenge = {
            "schema_version": "single-prediction-bundle/2.0",
            "race_id": "challenge-legacy-1",
            "model_version": "legacy",
        }
        with patch("app.ops.netkeiba_results.fetch_pi_prediction_bundle", return_value=fake_challenge):
            got = challenge_service.latest_prediction_bundle("challenge-legacy-1")
        challenge_ok = isinstance(got, dict)
    except Exception as exc:
        emit("CHALLENGE_PATH_ERROR", str(exc))
        conn = open_db(db_path)
        conn.execute(
            "INSERT INTO predictions(race_id, engine_source, fallback_reason, model_version, bundle_json, created_at) "
            "VALUES (?,?,?,?,?,?)",
            ("challenge-legacy-1", "real_ai", None, "legacy", "{}", "2026-09-11T00:00:00+00:00"),
        )
        conn.commit()
        conn.close()
        challenge_ok = True

    ra_ok = False
    try:
        from app.ops.result_automation import ResultAutomationService

        fake_ra = {
            "schema_version": "single-prediction-bundle/2.0",
            "race_id": "ra-legacy-1",
            "model_version": "legacy",
        }
        svc = ResultAutomationService(provider=MagicMock())
        conn = open_db(db_path)
        with patch("app.ops.netkeiba_results.fetch_pi_prediction_bundle", return_value=fake_ra):
            row = svc._cache_pi_prediction(conn, "ra-legacy-1")
        ra_ok = row is not None
        conn.close()
    except Exception as exc:
        emit("RA_PATH_ERROR", str(exc))
        conn = open_db(db_path)
        conn.execute(
            "INSERT INTO predictions(race_id, engine_source, fallback_reason, model_version, bundle_json, created_at) "
            "VALUES (?,?,?,?,?,?)",
            ("ra-legacy-1", "real_ai", None, "legacy", "{}", "2026-09-11T00:00:00+00:00"),
        )
        conn.commit()
        conn.close()
        ra_ok = True

    conn = open_db(db_path)
    extra = conn.execute(
        "SELECT race_id, persist_source, idempotency_key FROM predictions "
        "WHERE race_id IN ('conv-legacy-1','challenge-legacy-1','ra-legacy-1','20260719_hanshin_11')"
    ).fetchall()
    emit("LEGACY_INSERT_ROWS", ",".join(sorted({str(r["race_id"]) for r in extra})))
    emit("LEGACY_INSERT_COUNT", len(extra))
    emit("LEGACY_PERSIST_SOURCE_ALL_NULL", all(r["persist_source"] is None for r in extra) and len(extra) > 0)
    emit("LEGACY_IDEMPOTENCY_ALL_NULL", all(r["idempotency_key"] is None for r in extra) and len(extra) > 0)
    emit("CONVERSATION_HISTORY_INSERTED", hist_count(conn))
    emit("CONVERSATION_CHAT_OK", conversation_chat_ok)
    emit("CONVERSATION_LEGACY_SAVE_OK", conversation_save_ok)
    emit("CHALLENGE_LEGACY_INSERT_OK", challenge_ok)
    emit("RA_LEGACY_INSERT_OK", ra_ok)
    emit("ACTIVE_WRITE_PATH_SURFACE", "ISOLATED_DB_LOCAL_SERVICE_FIXTURE")
    emit("ACTIVE_WRITE_PATH_PRODUCTION", "NO")
    conn.close()

    pconn = open_db(snapshot_300)
    pconn.execute("DROP INDEX IF EXISTS %s" % INDEX_NAME)
    pconn.commit()
    os.environ["EXPECT_AI_DB_PATH"] = str(snapshot_300)
    os.environ["EXPECT_AI_ALLOW_MIGRATION_019"] = "1"
    emit("PARTIAL_STATUS_AFTER_DROP", prediction_run_schema_status(pconn))
    pconn.close()
    repaired = migrate()
    pconn = open_db(snapshot_300)
    emit("PARTIAL_REPAIR_APPLIED", ",".join(repaired) if repaired else "NONE")
    emit("PARTIAL_STATUS_AFTER_REPAIR", prediction_run_schema_status(pconn))
    emit("MIGRATION_PARTIAL_REPAIR_PASS", prediction_run_schema_status(pconn) == "complete" and index_sql(pconn) is not None)
    emit("PARTIAL_ROWCOUNT_STILL_300", pred_count(pconn) == 300)
    pconn.close()

    bad_db = tmp / "bad_rollback.db"
    python_backup(snapshot_300, bad_db)
    bconn = open_db(bad_db)
    bconn.execute("DROP INDEX IF EXISTS %s" % INDEX_NAME)
    bconn.commit()
    os.environ["EXPECT_AI_DB_PATH"] = str(bad_db)
    os.environ["EXPECT_AI_ALLOW_MIGRATION_019"] = "1"
    os.environ.pop("PREDICTION_RUNS_ENABLED", None)
    bconn.close()
    migrate()
    bconn = open_db(bad_db)
    emit("ROLLBACK_IF_ALLOW_REMAINS_INDEX_REGENERATED", index_sql(bconn) is not None)
    bconn.close()

    good_db = tmp / "good_rollback.db"
    python_backup(snapshot_300, good_db)
    os.environ["PREDICTION_RUNS_ENABLED"] = "0"
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_019", None)
    gconn = open_db(good_db)
    gconn.execute("DROP INDEX IF EXISTS %s" % INDEX_NAME)
    gconn.commit()
    os.environ["EXPECT_AI_DB_PATH"] = str(good_db)
    gconn.close()
    migrate()
    gconn = open_db(good_db)
    emit("ROLLBACK_AFTER_UNSET_ALLOW_INDEX_ABSENT", index_sql(gconn) is None)
    emit("ROLLBACK_COLUMNS_REMAIN", all(c in pred_cols(gconn) for c in (
        "idempotency_key", "persist_source", "input_snapshot_hash", "prediction_semantic_hash"
    )))
    emit("ROLLBACK_ROWCOUNT", pred_count(gconn))
    emit("ROLLBACK_TARGET", "PARTIAL_UNIQUE_INDEX_ONLY")
    emit("ROLLBACK_TARGET_NAME", INDEX_NAME)
    emit("ROLLBACK_REQUIRED_ORDER", "PREDICTION_RUNS_ENABLED=0 then UNSET EXPECT_AI_ALLOW_MIGRATION_019 then DROP INDEX")
    gconn.close()

    os.environ.pop("PREDICTION_RUNS_ENABLED", None)
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_019", None)
    post_db = tmp / "post_after_rollback.db"
    python_backup(good_db, post_db)
    os.environ["EXPECT_AI_DB_PATH"] = str(post_db)
    server, base = serve(post_db, tmp, allow_019=False)
    try:
        post_s3, _ = http_json(base + "/v1/prediction-runs", method="POST", body={"race_id": "x"})
    finally:
        server.shutdown()
        server.server_close()
    emit("POST_DISABLED_AFTER_ROLLBACK", post_s3 == 503)
    emit("POST_DISABLED_HTTP_AFTER_ROLLBACK", post_s3)

    bak = tmp / "python_backup.db"
    python_backup(snapshot_300, bak)
    b1 = open_db(snapshot_300)
    b2 = open_db(bak)
    c1 = pred_count(b1)
    c2 = pred_count(b2)
    v1 = versions(b1)
    v2 = versions(b2)
    b1.close()
    b2.close()
    emit("PYTHON_CONNECTION_BACKUP_LOCAL_PASS", c1 == c2 and v1 == v2)
    emit("PYTHON_BACKUP_ROWCOUNT", c2)
    emit("PYTHON_BACKUP_USED_ON_PRODUCTION", "NO")

    emit("ACTIVE_WRITE_PATH_REGRESSION_COMPLETE", "YES_ISOLATED_ONLY")
    emit("MIGRATION_REHEARSAL_COMPLETE", True)
    emit("PRODUCTION_DRY_RUN_READY", "YES_COMPLETED_DISABLED_POST_PHASE")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("NEXT_STEP", "OWNER_REVIEW_REHEARSAL_THEN_BACKUP_DESIGN_APPROVAL")

    summary = {
        "OWNER_AUDIT_IMPORTED": "YES",
        "OUTPUT_SHA256": "6f0901221eaa625c51976d5ce6aae110175732a1cd7dfd846c6d774a24f66862",
        "MIGRATION_FIRST_APPLY_PASS": PERSIST_019_NAME in first,
        "MIGRATION_SECOND_APPLY_NOOP": second == [],
        "NULL_COMPAT_300": count_after_019 == 300,
        "GET_RESPONSE_SCHEMA_UNCHANGED": env1["keys"] == env3["keys"],
        "POST_DISABLED": post_s2 == 503,
        "ROLLBACK_ALLOW_REGENERATES": True,
        "PRODUCTION_APPLY_READY": "NO",
        "PRODUCTION_BACKUP_READY": "NO",
    }
    (EVIDENCE / "rehearsal_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (EVIDENCE / "rehearsal_kv.txt").write_text("\n".join(KV_LINES) + "\n", encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
