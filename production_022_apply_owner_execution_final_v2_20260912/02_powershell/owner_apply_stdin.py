#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single SSH stdin payload for 022 schema APPLY final. Pregenerated. Do not concatenate."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

PACK = "production_022_apply_owner_execution_final_20260912"
CANONICAL_SOURCE = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db"
HISTORICAL_BACKUP_PATH = "/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260911T175303Z/expect_ai.db"
HISTORICAL_BACKUP_SHA256 = "f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d"
HISTORICAL_BACKUP_SIZE = 105967616
HISTORICAL_BACKUP_STAMP = "20260911T175303Z"
HISTORICAL_BACKUP_IDENTITY = "66305:287106"
INVENTORY_SOURCE_DEV = 66305
INVENTORY_SOURCE_INO = 349935
MEASURED_LIVE_SOURCE_SIZE = 107237376
MEASURED_PRED_ROW_COUNT = 301
MEASURE_V2_OUTPUT_SHA256 = "df96d93c11efb6e078b6756e6d9ab561cc68b70f6b6ee67d67d6b2a4f082de7e"
FRESH_BACKUP_OWNER_LOG_SHA256 = "f3525b6fea85526083224b38a7d48271ae6a356c3af4bf67908efa07c852495d"
APPLY_BACKUP_CANON = "PINNED_FRESH_PRODUCTION_BACKUP"
APPLY_BACKUP_PATH = "/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260912T013332Z/expect_ai.db"
APPLY_BACKUP_SHA256 = "32dfe70339a7237442d08a032d019ec03abbb8b85d0c90fa39d385e54da07e6a"
APPLY_BACKUP_DEV = 66305
APPLY_BACKUP_INO = 287343
APPLY_BACKUP_SIZE = 107413504
APPLY_BACKUP_IDENTITY = "66305:287343"
APPLY_BACKUP_STAMP = "20260912T013332Z"
PERSIST_022 = "022_prediction_run_idempotency"
PERSIST_019 = "019_prediction_run_idempotency"
PARTIAL_INDEX = "uq_predictions_idempotency_key_not_null"
RACE_INDEX = "idx_predictions_race"
NEW_COLS = (
    "idempotency_key",
    "persist_source",
    "input_snapshot_hash",
    "prediction_semantic_hash",
)
OWNER_MIGRATIONS = (
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
OWNER_PRED_COLUMNS = (
    "id",
    "race_id",
    "core_race_id",
    "engine_source",
    "fallback_reason",
    "model_version",
    "bundle_json",
    "created_at",
)
INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_predictions_idempotency_key_not_null "
    "ON predictions(idempotency_key) WHERE idempotency_key IS NOT NULL"
)
ALTER_SQL = tuple("ALTER TABLE predictions ADD COLUMN %s TEXT" % c for c in NEW_COLS)
WATCHED_ENV_KEYS = (
    "PREDICTION_RUNS_ENABLED",
    "EXPECT_AI_ALLOW_MIGRATION_022",
    "EXPECT_AI_ALLOW_MIGRATION_019",
)
SERVICE_CANDIDATES = (
    "expect-ai.service",
    "win5-ai.service",
    "expect_ai.service",
)
APPROVAL = "OWNER_PRODUCTION_022_APPLY_APPROVED"
PHASE_NOT_STARTED = "NOT_STARTED"
PHASE_TRANSACTION_OPEN = "TRANSACTION_OPEN"
PHASE_COMMITTED = "COMMITTED"
PUBLIC_ORIGINS = (
    "https://expect-keiba.com",
    "https://keiba-single-ai.pages.dev",
)
PUBLIC_STATIC_PATHS = (
    "/",
    "/race.html",
    "/races.html",
)
PUBLIC_API_PATHS = (
    "/api/health",
    "/api/predictions",
)
REMOTE_HARD_DEADLINE_S = 120
WRAPPER_TIMEOUT_MS = 240000
DRAIN_WAIT_MS = 20000
KILL_DRAIN_WAIT_MS = 8000
SAFETY_BUFFER_MS = 40000
HTTP_LOCAL_TIMEOUT_S = 3
HTTP_PUBLIC_TIMEOUT_S = 3
SUBPROCESS_TIMEOUT_S = 3
BUSY_TIMEOUT_MS = 8000
# Measured v2 Owner limits. Do not collapse back to one HTTP_MAX_JSON_BYTES.
HTTP_MAX_INTERNAL_HEALTH_BYTES = 65536
HTTP_MAX_INTERNAL_LIST_BYTES = 2097152
HTTP_MAX_INTERNAL_DETAIL_BYTES = 262144
HTTP_MAX_PUBLIC_JSON_BYTES = 262144
HTTP_MAX_PUBLIC_HTML_BYTES = 524288
CLASS_INTERNAL_HEALTH = "INTERNAL_HEALTH"
CLASS_INTERNAL_LIST = "INTERNAL_LIST"
CLASS_INTERNAL_DETAIL = "INTERNAL_DETAIL"
CLASS_PUBLIC_JSON = "PUBLIC_JSON"
CLASS_PUBLIC_HTML = "PUBLIC_HTML"
COMMIT_BUDGET_S = 15
POST_COMMIT_BUDGET_S = 55
PRE_APPLY_MIN_REMAINING_S = COMMIT_BUDGET_S + POST_COMMIT_BUDGET_S
POST_AFTER_COMMIT_MIN_S = 25
SITE_IDENTIFIERS = ("Expect", "KEIBA")
ALLOWED_PUBLIC_HOSTS = ("expect-keiba.com", "keiba-single-ai.pages.dev")
DEFAULT_BFF_HEALTH_JSON = (
    '{"ok":true,"meta":{"service":"BffHealth","cache":"no-store"},'
    '"data":{"status":"ok","service":"bff","runtime":"cloudflare-pages-functions",'
    '"ai_proxy_configured":true}}'
)
DEFAULT_BFF_PREDICTIONS_OK_JSON = (
    '{"ok":true,"data":[],"meta":{"service":"PredictionService"}}'
)
DEFAULT_BFF_PREDICTIONS_CLOSED_JSON = (
    '{"ok":false,"error":{"code":"OPS_CLOSED","message":"closed","details":null}}'
)
DEFAULT_STATIC_HTML = (
    "<!DOCTYPE html><html><head><title>Expect ~ KEIBA AI ~</title></head>"
    "<body><p class=\"brand-name\">Expect</p></body></html>"
)


class Halt(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class Deadline:
    def __init__(self, hard_s: float) -> None:
        self.started = time.monotonic()
        self.hard_s = float(hard_s)

    def remaining(self) -> float:
        return self.hard_s - (time.monotonic() - self.started)

    def require(self, seconds: float, code: str) -> None:
        left = self.remaining()
        emit("DEADLINE_REMAINING_S", "%.1f" % max(0.0, left))
        if left < seconds:
            raise Halt(code)


class State:
    apply_phase = PHASE_NOT_STARTED
    apply_executed = False
    audit_closed = False
    http_calls: list[tuple[str, str]] = []
    ai_key = ""
    ai_port = 8000
    apply_started = ""
    unit = ""
    deadline: Deadline | None = None


STATE = State()


def emit(key: str, value: object) -> None:
    if value is True:
        text = "YES"
    elif value is False:
        text = "NO"
    else:
        text = str(value)
    print("%s=%s" % (key, text.replace("\n", " ")))
    sys.stdout.flush()


def test_mode() -> bool:
    return (os.environ.get("OWNER_APPLY_PACK_TEST") or "").strip() == "1"


def test_fail_mode() -> str:
    return (os.environ.get("OWNER_APPLY_TEST_FAIL") or "").strip()


def public_smoke_urls() -> list[str]:
    urls: list[str] = []
    for origin in PUBLIC_ORIGINS:
        for path in PUBLIC_STATIC_PATHS:
            urls.append(origin + path)
        for path in PUBLIC_API_PATHS:
            urls.append(origin + path)
    return urls


def can_run_public_smoke() -> bool:
    if test_mode():
        return (os.environ.get("OWNER_APPLY_TEST_PUBLIC_SMOKE") or "").strip() == "1"
    return True


def remote_hard_deadline_s() -> float:
    if test_mode():
        raw = (os.environ.get("OWNER_APPLY_TEST_DEADLINE_S") or "").strip()
        if raw:
            return float(raw)
    return float(REMOTE_HARD_DEADLINE_S)


def deadline() -> Deadline:
    if STATE.deadline is None:
        STATE.deadline = Deadline(remote_hard_deadline_s())
    return STATE.deadline


def wrapper_budget_ok() -> bool:
    remote_ms = int(REMOTE_HARD_DEADLINE_S * 1000)
    need = remote_ms + DRAIN_WAIT_MS + KILL_DRAIN_WAIT_MS + SAFETY_BUFFER_MS
    return WRAPPER_TIMEOUT_MS >= need


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_source() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_APPLY_TEST_SRC") or "").strip()
        if override:
            return Path(override)
    return Path(CANONICAL_SOURCE)


def is_historical_backup_path(path: Path) -> bool:
    text = path.as_posix()
    try:
        resolved = path.resolve().as_posix()
    except OSError:
        resolved = text
    if text == HISTORICAL_BACKUP_PATH or resolved == HISTORICAL_BACKUP_PATH:
        return True
    return HISTORICAL_BACKUP_STAMP in text or HISTORICAL_BACKUP_STAMP in resolved


def refuse_stale_or_unset_canon(path: Path | None = None, sha: str | None = None) -> None:
    if APPLY_BACKUP_CANON != "PINNED_FRESH_PRODUCTION_BACKUP":
        raise Halt("APPLY_BACKUP_CANON_UNSET")
    if not APPLY_BACKUP_PATH or APPLY_BACKUP_PATH == "PENDING_FRESH_PRODUCTION_BACKUP":
        raise Halt("APPLY_BACKUP_CANON_UNSET")
    if HISTORICAL_BACKUP_STAMP in APPLY_BACKUP_PATH or APPLY_BACKUP_PATH == HISTORICAL_BACKUP_PATH:
        raise Halt("STALE_BACKUP_NOT_APPLY_CANON")
    if APPLY_BACKUP_SHA256 == HISTORICAL_BACKUP_SHA256:
        raise Halt("STALE_BACKUP_NOT_APPLY_CANON")
    if path is not None and is_historical_backup_path(path):
        raise Halt("STALE_BACKUP_NOT_APPLY_CANON")
    if sha == HISTORICAL_BACKUP_SHA256:
        raise Halt("STALE_BACKUP_NOT_APPLY_CANON")


def backup_path() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_APPLY_TEST_BACKUP") or "").strip()
        if override:
            path = Path(override)
            refuse_stale_or_unset_canon(path=path)
            return path
        raise Halt("APPLY_BACKUP_CANON_UNSET")
    refuse_stale_or_unset_canon()
    return Path(APPLY_BACKUP_PATH)


def expected_source_dev_ino() -> tuple[int, int]:
    if test_mode():
        d = (os.environ.get("OWNER_APPLY_TEST_SOURCE_DEV") or "").strip()
        i = (os.environ.get("OWNER_APPLY_TEST_SOURCE_INO") or "").strip()
        if d and i:
            return int(d), int(i)
    return INVENTORY_SOURCE_DEV, INVENTORY_SOURCE_INO


def expected_backup_dev_ino() -> tuple[int, int]:
    if test_mode():
        d = (os.environ.get("OWNER_APPLY_TEST_BACKUP_DEV") or "").strip()
        i = (os.environ.get("OWNER_APPLY_TEST_BACKUP_INO") or "").strip()
        if d and i:
            return int(d), int(i)
        raise Halt("APPLY_BACKUP_CANON_UNSET")
    refuse_stale_or_unset_canon()
    return int(APPLY_BACKUP_DEV), int(APPLY_BACKUP_INO)


def expected_backup_sha() -> str:
    if test_mode():
        override = (os.environ.get("OWNER_APPLY_TEST_BACKUP_SHA") or "").strip()
        if override == HISTORICAL_BACKUP_SHA256:
            raise Halt("STALE_BACKUP_NOT_APPLY_CANON")
        if override:
            return override
        raise Halt("APPLY_BACKUP_CANON_UNSET")
    refuse_stale_or_unset_canon()
    return APPLY_BACKUP_SHA256


def expected_backup_size() -> int:
    if test_mode():
        raw = (os.environ.get("OWNER_APPLY_TEST_BACKUP_SIZE") or "").strip()
        if raw:
            return int(raw)
        raise Halt("APPLY_BACKUP_CANON_UNSET")
    refuse_stale_or_unset_canon()
    return int(APPLY_BACKUP_SIZE)


def refuse_unapproved() -> None:
    if (os.environ.get(APPROVAL) or "").strip() != "1":
        raise Halt("OWNER_PRODUCTION_022_APPLY_APPROVED_UNSET")


def migration_list(conn: sqlite3.Connection) -> list[str]:
    try:
        return [str(r[0]) for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")]
    except sqlite3.Error:
        return []


def prediction_columns(conn: sqlite3.Connection) -> list[str]:
    try:
        return [str(r[1]) for r in conn.execute("PRAGMA table_info(predictions)")]
    except sqlite3.Error:
        return []


def column_notnull(conn: sqlite3.Connection, name: str) -> int:
    for row in conn.execute("PRAGMA table_info(predictions)"):
        if str(row[1]) == name:
            return int(row[3] or 0)
    return -1


def pred_row_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()
    return int(row[0] if row else 0)


def pred_row_count_ro(path: Path) -> int:
    conn = sqlite3.connect("file:%s?mode=ro" % path.resolve().as_posix(), uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        return pred_row_count(conn)
    finally:
        conn.close()


def normalize_sql(sql: str) -> str:
    return " ".join((sql or "").split()).lower()


def inspect_index(conn: sqlite3.Connection) -> str:
    listed = {
        str(r[1]): int(r[2] or 0)
        for r in conn.execute("PRAGMA index_list(predictions)").fetchall()
    }
    master = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
        (PARTIAL_INDEX,),
    ).fetchone()
    if PARTIAL_INDEX not in listed and master is None:
        return "missing"
    unique = listed.get(PARTIAL_INDEX, 0) == 1
    cols = [
        str(r[2] or "")
        for r in conn.execute("PRAGMA index_info(%s)" % PARTIAL_INDEX).fetchall()
    ]
    sql = normalize_sql(master[0] if master and master[0] else "")
    compact = sql.replace(" ", "")
    has_unique = unique and ("createuniqueindex" in compact or " unique " in " %s " % sql)
    single_key = cols == ["idempotency_key"]
    has_predicate = "whereidempotency_keyisnotnull" in compact
    on_predictions = "onpredictions(idempotency_key)" in compact
    if has_unique and single_key and has_predicate and on_predictions:
        return "ok"
    return "mismatch"


def inspect_race_index(conn: sqlite3.Connection) -> str:
    names = {str(r[1]) for r in conn.execute("PRAGMA index_list(predictions)").fetchall()}
    if RACE_INDEX not in names:
        return "missing"
    rows = conn.execute("PRAGMA index_info(%s)" % RACE_INDEX).fetchall()
    cols = [str(r[2] or "") for r in sorted(rows, key=lambda r: int(r[0]))]
    if cols == ["race_id", "created_at"]:
        return "ok"
    return "mismatch"


def verify_pre_schema(conn: sqlite3.Connection, *, prefix: str = "") -> int:
    migrations = migration_list(conn)
    cols = prediction_columns(conn)
    have = set(migrations)
    owner = set(OWNER_MIGRATIONS)
    missing = sorted(owner - have)
    extra = sorted(have - owner)
    dup_count = len(migrations) - len(have)
    emit("%sSCHEMA_MIGRATIONS_COUNT" % prefix, len(migrations))
    emit("%sSCHEMA_MIGRATIONS_UNIQUE_COUNT" % prefix, len(have))
    emit("%sSCHEMA_MIGRATIONS_MISSING_COUNT" % prefix, len(missing))
    emit("%sSCHEMA_MIGRATIONS_EXTRA_COUNT" % prefix, len(extra))
    emit("%sSCHEMA_MIGRATIONS_DUPLICATE_COUNT" % prefix, dup_count)
    emit("%sPREDICTIONS_COLUMN_COUNT" % prefix, len(cols))
    emit("%sHAS_PERSIST_022" % prefix, PERSIST_022 in have)
    emit("%sHAS_PERSIST_019" % prefix, PERSIST_019 in have)
    emit("%sNEW_PERSIST_COLUMNS_PRESENT" % prefix, sum(1 for c in NEW_COLS if c in cols))
    emit("%sPARTIAL_UNIQUE_INDEX_STATE" % prefix, inspect_index(conn))
    emit("%sEXISTING_RACE_INDEX" % prefix, inspect_race_index(conn))
    rows = pred_row_count(conn)
    emit("%sPRED_ROW_COUNT_BEFORE" % prefix, rows)
    if dup_count != 0:
        raise Halt("MIGRATION_DUPLICATE")
    if PERSIST_019 in have:
        raise Halt("HAS_PERSIST_019")
    if PERSIST_022 in have or inspect_index(conn) != "missing" or any(c in cols for c in NEW_COLS):
        raise Halt("ALREADY_APPLIED_OR_PARTIAL")
    if len(migrations) != 22 or have != owner or missing or extra:
        raise Halt("MIGRATION_SET_MISMATCH")
    if cols != list(OWNER_PRED_COLUMNS):
        raise Halt("PREDICTIONS_COLUMNS_MISMATCH")
    if inspect_race_index(conn) != "ok":
        raise Halt("EXISTING_INDEX_MISSING_OR_MISMATCH")
    emit("%sSOURCE_SCHEMA_GATE" % prefix, "PASS")
    return rows


def verify_post_schema(conn: sqlite3.Connection, rows_before: int, *, prefix: str = "") -> None:
    migrations = migration_list(conn)
    cols = prediction_columns(conn)
    have = set(migrations)
    emit("%sSCHEMA_MIGRATIONS_COUNT_AFTER" % prefix, len(migrations))
    emit("%sPREDICTIONS_COLUMN_COUNT_AFTER" % prefix, len(cols))
    emit("%sHAS_PERSIST_022" % prefix, PERSIST_022 in have)
    emit("%sPARTIAL_UNIQUE_INDEX_STATE" % prefix, inspect_index(conn))
    rows = pred_row_count(conn)
    emit("%sPRED_ROW_COUNT_AFTER" % prefix, rows)
    if have != set(OWNER_MIGRATIONS) | {PERSIST_022}:
        raise Halt("POST_APPLY_MIGRATION_SET_MISMATCH")
    if PERSIST_019 in have:
        raise Halt("HAS_PERSIST_019")
    want_cols = list(OWNER_PRED_COLUMNS) + list(NEW_COLS)
    if cols != want_cols:
        raise Halt("POST_APPLY_COLUMNS_MISMATCH")
    for col in NEW_COLS:
        if column_notnull(conn, col) != 0:
            raise Halt("NEW_COLUMN_NOT_NULLABLE")
        nulls = conn.execute("SELECT COUNT(*) FROM predictions WHERE %s IS NULL" % col).fetchone()
        if int(nulls[0] if nulls else -1) != rows:
            raise Halt("NEW_COLUMN_NULL_COMPAT_FAIL")
    if inspect_index(conn) != "ok":
        raise Halt("APPLY_INDEX_MISMATCH")
    if inspect_race_index(conn) != "ok":
        raise Halt("EXISTING_INDEX_MISSING_OR_MISMATCH")
    if rows != rows_before:
        raise Halt("PRED_ROW_COUNT_CHANGED")
    emit("%sSOURCE_SCHEMA_AFTER" % prefix, "PASS")
    emit("%sNEW_COLUMN_NULL_COMPAT" % prefix, "PASS")


def verify_identity(path: Path, exp_dev: int, exp_ino: int, kind: str) -> os.stat_result:
    st = path.stat()
    emit("%s_DEV" % kind, st.st_dev)
    emit("%s_INO" % kind, st.st_ino)
    emit("%s_SIZE" % kind, st.st_size)
    emit("%s_MTIME" % kind, int(st.st_mtime))
    emit("%s_MODE" % kind, oct(stat.S_IMODE(st.st_mode)))
    if (int(st.st_dev), int(st.st_ino)) != (int(exp_dev), int(exp_ino)):
        emit("DB_DRIFT", "YES")
        raise Halt("DB_DRIFT" if kind == "SOURCE" else "BACKUP_DRIFT")
    emit("DB_DRIFT", "NO")
    return st


def verify_backup(path: Path) -> None:
    refuse_stale_or_unset_canon(path=path)
    if not path.is_file():
        raise Halt("BACKUP_MISSING")
    if not test_mode():
        resolved = path.resolve().as_posix()
        if resolved != APPLY_BACKUP_PATH and path.as_posix() != APPLY_BACKUP_PATH:
            raise Halt("BACKUP_PATH_MISMATCH")
    got = file_sha(path)
    emit("BACKUP_PATH", path.as_posix())
    emit("BACKUP_SHA256", got)
    if got == HISTORICAL_BACKUP_SHA256:
        raise Halt("STALE_BACKUP_NOT_APPLY_CANON")
    expected = expected_backup_sha()
    emit("BACKUP_SHA256_EXPECTED", expected)
    emit("BACKUP_SHA256_MATCH", got == expected)
    if got != expected:
        raise Halt("BACKUP_SHA_MISMATCH")
    st = verify_identity(path, *expected_backup_dev_ino(), "BACKUP")
    want_size = expected_backup_size()
    emit("BACKUP_SIZE_EXPECTED", want_size)
    emit("BACKUP_SIZE_MATCH", int(st.st_size) == int(want_size))
    if int(st.st_size) != int(want_size):
        raise Halt("BACKUP_SIZE_MISMATCH")
    emit("BACKUP_IDENTITY", "%s:%s" % (st.st_dev, st.st_ino))
    conn = sqlite3.connect("file:%s?mode=ro" % path.resolve().as_posix(), uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        ok = bool(integrity) and str(integrity[0]) == "ok"
        emit("BACKUP_INTEGRITY_OK", ok)
        if not ok:
            raise Halt("BACKUP_INTEGRITY_FAIL")
    finally:
        conn.close()
    emit("APPLY_PRECONDITION_BACKUP_PASS", "YES")


def _flag_01(raw: str | None) -> int:
    return 1 if (raw or "").strip().lower() in ("1", "true", "yes", "on") else 0


def parse_systemd_show(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip()
    return out


def parse_assignment_blob(blob: str, *, split_null: bool, extra_keys: tuple[str, ...] = ()) -> dict[str, str]:
    out: dict[str, str] = {}
    raw = blob.replace("\n", "\0") if split_null else blob
    parts = raw.split("\0") if split_null else raw.split()
    wanted = set(WATCHED_ENV_KEYS) | set(extra_keys)
    for part in parts:
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        if key in wanted:
            out[key] = val
    return out


def parse_env_file(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, val = stripped.split("=", 1)
                key = key.strip()
                if key in WATCHED_ENV_KEYS:
                    out[key] = val.strip().strip("'\"")
    except OSError:
        return {}
    return out


def environment_file_paths(raw: str) -> list[str]:
    paths: list[str] = []
    for chunk in (raw or "").replace(" ", "\n").splitlines():
        item = chunk.strip()
        if not item:
            continue
        path = item.split("(", 1)[0].strip()
        if path.startswith("/"):
            paths.append(path)
    return paths


def run_cmd(args: list[str]) -> tuple[int, str]:
    try:
        timeout_s = min(float(SUBPROCESS_TIMEOUT_S), max(1.0, deadline().remaining() - 1.0))
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        return int(p.returncode), (p.stdout or "")
    except Exception:
        return 1, ""


def read_proc_environ(pid: str) -> tuple[bool, dict[str, str]]:
    if not pid.isdigit() or int(pid) <= 0:
        return False, {}
    try:
        with open("/proc/%s/environ" % pid, "rb") as fh:
            blob = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return False, {}
    return True, parse_assignment_blob(
        blob,
        split_null=True,
        extra_keys=("AI_PORT", "AI_API_KEY", "AI_HOST"),
    )


def collect_production_env(*, after: bool = False) -> dict[str, object]:
    if test_mode() and (os.environ.get("OWNER_APPLY_TEST_ENV") or "").strip() == "1":
        show = os.environ.get("OWNER_APPLY_TEST_SYSTEMD_SHOW") or ""
        proc_blob = os.environ.get("OWNER_APPLY_TEST_PROC_ENVIRON") or ""
        file_blob = os.environ.get("OWNER_APPLY_TEST_ENVFILE") or ""
        sd = parse_systemd_show(show)
        proc_ok = bool(proc_blob) or (os.environ.get("OWNER_APPLY_TEST_PROC_OK") or "") == "1"
        proc = parse_assignment_blob(
            proc_blob.replace(" ", "\0"),
            split_null=True,
            extra_keys=("AI_PORT", "AI_API_KEY", "AI_HOST"),
        ) if proc_blob else {}
        files = parse_assignment_blob(file_blob.replace(" ", "\0"), split_null=True) if file_blob else {}
        systemd_ok = bool(show) or (os.environ.get("OWNER_APPLY_TEST_SYSTEMD_OK") or "") == "1"
        files_ok = bool(file_blob) or (os.environ.get("OWNER_APPLY_TEST_FILES_OK") or "") == "1"
        env_line = sd.get("Environment") or ""
        systemd_env = parse_assignment_blob(env_line.replace(" ", "\0"), split_null=True)
        file_paths = environment_file_paths(sd.get("EnvironmentFiles") or "")
        if file_blob:
            file_paths = file_paths or ["TEST"]
        unit_loaded = (sd.get("LoadState") or "") == "loaded"
        mainpid = str(sd.get("MainPID") or "0").strip()
        mainpid_set = mainpid not in ("", "0")
        active_state = sd.get("ActiveState") or "UNSET"
        if after and test_fail_mode() == "inactive":
            active_state = "inactive"
        return {
            "systemd_ok": systemd_ok,
            "proc_ok": proc_ok,
            "files_ok": files_ok,
            "proc": proc,
            "systemd": systemd_env,
            "files": files,
            "env_files": "SET" if file_paths else "UNSET",
            "mainpid": "SET" if mainpid_set else "UNSET",
            "unit": sd.get("Id") or "TEST",
            "unit_loaded": unit_loaded,
            "file_paths_configured": bool(file_paths),
            "mainpid_set": mainpid_set,
            "load_state": sd.get("LoadState") or "UNSET",
            "active_state": active_state,
            "ai_port": int((os.environ.get("OWNER_APPLY_TEST_AI_PORT") or proc.get("AI_PORT") or "8000").strip() or "8000"),
            "ai_key": (os.environ.get("OWNER_APPLY_TEST_AI_KEY") or proc.get("AI_API_KEY") or ""),
        }

    unit = ""
    show_out = ""
    show_rc = 1
    for cand in SERVICE_CANDIDATES:
        for args in (
            ["systemctl", "show", cand, "--no-pager", "-p", "Id", "-p", "MainPID", "-p", "LoadState", "-p", "ActiveState", "-p", "Environment", "-p", "EnvironmentFiles"],
            ["systemctl", "--user", "show", cand, "--no-pager", "-p", "Id", "-p", "MainPID", "-p", "LoadState", "-p", "ActiveState", "-p", "Environment", "-p", "EnvironmentFiles"],
        ):
            rc, out = run_cmd(args)
            if rc == 0 and out.strip():
                parsed = parse_systemd_show(out)
                if (parsed.get("LoadState") or "") == "loaded":
                    show_rc = rc
                    show_out = out
                    unit = cand
                    break
        if show_out:
            break
    sd = parse_systemd_show(show_out)
    unit_loaded = (sd.get("LoadState") or "") == "loaded"
    systemd_ok = show_rc == 0 and bool(sd) and unit_loaded
    env_line = sd.get("Environment") or ""
    systemd_env = parse_assignment_blob(env_line.replace(" ", "\0"), split_null=True)
    file_paths = environment_file_paths(sd.get("EnvironmentFiles") or "")
    files: dict[str, str] = {}
    files_ok = False
    if file_paths:
        readable = 0
        for path in file_paths:
            parsed = parse_env_file(path)
            if parsed or os.path.isfile(path):
                readable += 1
            files.update(parsed)
        files_ok = readable == len(file_paths)
    elif systemd_ok:
        files_ok = True
    mainpid = str(sd.get("MainPID") or "0").strip()
    mainpid_set = mainpid not in ("", "0")
    proc_ok, proc = read_proc_environ(mainpid)
    ai_port = 8000
    raw_port = proc.get("AI_PORT") if proc_ok else None
    if raw_port and str(raw_port).strip().isdigit():
        ai_port = int(str(raw_port).strip())
    return {
        "systemd_ok": systemd_ok,
        "proc_ok": proc_ok,
        "files_ok": files_ok,
        "proc": proc,
        "systemd": systemd_env,
        "files": files,
        "env_files": "SET" if file_paths else "UNSET",
        "mainpid": "SET" if mainpid_set else "UNSET",
        "unit": unit or "UNSET",
        "unit_loaded": unit_loaded,
        "file_paths_configured": bool(file_paths),
        "mainpid_set": mainpid_set,
        "load_state": sd.get("LoadState") or "UNSET",
        "active_state": sd.get("ActiveState") or "UNSET",
        "ai_port": ai_port,
        "ai_key": (proc.get("AI_API_KEY") or "") if proc_ok else "",
    }


def effective_env(info: dict[str, object]) -> dict[str, tuple[str, int]]:
    out: dict[str, tuple[str, int]] = {}
    for key in WATCHED_ENV_KEYS:
        raw = None
        source = "UNSET"
        if info["proc_ok"] and key in info["proc"]:
            raw = info["proc"][key]
            source = "PROC"
        elif info["systemd_ok"] and key in info["systemd"]:
            raw = info["systemd"][key]
            source = "SYSTEMD_ENVIRONMENT"
        elif info["files_ok"] and key in info["files"]:
            raw = info["files"][key]
            source = "ENVIRONMENT_FILE"
        present = raw is not None
        effective = _flag_01(raw) if present else 0
        out[key] = (source if present else "UNSET", effective)
        emit("%s_SET" % key, "SET" if present else "UNSET")
        emit("%s_EFFECTIVE" % key, effective)
        emit("%s_SOURCE" % key, source)
    return out


def verify_production_env(*, after: bool = False) -> dict[str, tuple[str, int]]:
    info = collect_production_env(after=after)
    STATE.unit = str(info["unit"] or "")
    STATE.ai_port = int(info["ai_port"] or 8000)
    if not STATE.ai_key:
        STATE.ai_key = str(info.get("ai_key") or "")
    emit("PRODUCTION_ENV_UNIT", info["unit"])
    emit("PRODUCTION_ENV_LOAD_STATE", info["load_state"])
    emit("PRODUCTION_ENV_ACTIVE_STATE", info["active_state"])
    emit("PRODUCTION_ENV_UNIT_LOADED", "YES" if info["unit_loaded"] else "NO")
    emit("PRODUCTION_ENV_SYSTEMD_READ", info["systemd_ok"])
    emit("PRODUCTION_ENV_PROC_READ", info["proc_ok"])
    emit("PRODUCTION_ENV_FILES_READ", info["files_ok"])
    emit("AI_PORT_USED", STATE.ai_port)
    emit("AI_API_KEY_SET", "SET" if STATE.ai_key else "UNSET")
    determined = bool(
        info["unit_loaded"]
        and info["systemd_ok"]
        and (info["proc_ok"] or not info["mainpid_set"])
        and (info["files_ok"] or not info["file_paths_configured"])
    )
    emit("PRODUCTION_ENV_DETERMINED", determined)
    if not determined:
        raise Halt("PRODUCTION_ENV_UNDETERMINED")
    if str(info["active_state"]) != "active":
        raise Halt("SERVICE_NOT_ACTIVE")
    eff = effective_env(info)
    if eff["PREDICTION_RUNS_ENABLED"][1] == 1:
        raise Halt("PREDICTION_RUNS_ENABLED_EFFECTIVE_1")
    if eff["EXPECT_AI_ALLOW_MIGRATION_019"][1] == 1:
        raise Halt("EXPECT_AI_ALLOW_MIGRATION_019_EFFECTIVE_1")
    if eff["EXPECT_AI_ALLOW_MIGRATION_022"][1] == 1:
        raise Halt("EXPECT_AI_ALLOW_MIGRATION_022_EFFECTIVE_1")
    emit("PRODUCTION_ENV_GATE", "PASS_AFTER" if after else "PASS")
    emit("SERVICE_ACTIVE_CHECKED", "YES")
    return eff


def envelope_shape(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {"type": type(payload).__name__}
    keys = sorted(str(k) for k in payload.keys())
    types = {str(k): type(payload[k]).__name__ for k in payload.keys()}
    shape: dict[str, object] = {"keys": keys, "types": types}
    meta = payload.get("meta")
    if isinstance(meta, dict):
        shape["meta_keys"] = sorted(str(k) for k in meta.keys())
    err = payload.get("error")
    if isinstance(err, dict):
        shape["error_keys"] = sorted(str(k) for k in err.keys())
    return shape


def shape_text(shape: dict[str, object]) -> str:
    return json.dumps(shape, sort_keys=True, separators=(",", ":"))


def redact_path(path: str) -> str:
    if path.startswith("/v1/predictions/") and path != "/v1/predictions":
        return "/v1/predictions/{id}"
    return path


def _parse_json_or_halt(raw: bytes) -> object:
    if not raw:
        raise Halt("HTTP_JSON_MALFORMED")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise Halt("HTTP_JSON_MALFORMED")


def path_equiv(requested: str, final: str) -> bool:
    if requested == final:
        return True
    if requested.rstrip("/") == final.rstrip("/"):
        return True
    if requested == "/" and final in ("/", "/index.html"):
        return True
    return False


class GuardedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts: tuple[str, ...], requested_path: str) -> None:
        urllib.request.HTTPRedirectHandler.__init__(self)
        self.allowed_hosts = set(allowed_hosts)
        self.requested_path = requested_path

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        parsed = urlparse(newurl)
        host = parsed.netloc.split(":")[0]
        path = parsed.path or "/"
        emit("HTTP_REDIRECT", "%s://%s%s" % (parsed.scheme or "https", host, redact_path(path)))
        if host not in self.allowed_hosts:
            raise Halt("HTTP_REDIRECT_UNEXPECTED")
        if not path_equiv(self.requested_path, path):
            raise Halt("HTTP_REDIRECT_UNEXPECTED")
        return urllib.request.HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, headers, newurl)


def class_for_path(path: str, public: bool) -> str:
    if public:
        if path in PUBLIC_STATIC_PATHS:
            return CLASS_PUBLIC_HTML
        return CLASS_PUBLIC_JSON
    if path == "/health":
        return CLASS_INTERNAL_HEALTH
    if path == "/v1/predictions":
        return CLASS_INTERNAL_LIST
    if path.startswith("/v1/predictions/"):
        return CLASS_INTERNAL_DETAIL
    return CLASS_INTERNAL_LIST


def cap_for_class(endpoint_class: str) -> int:
    if endpoint_class == CLASS_INTERNAL_HEALTH:
        return HTTP_MAX_INTERNAL_HEALTH_BYTES
    if endpoint_class == CLASS_INTERNAL_LIST:
        return HTTP_MAX_INTERNAL_LIST_BYTES
    if endpoint_class == CLASS_INTERNAL_DETAIL:
        return HTTP_MAX_INTERNAL_DETAIL_BYTES
    if endpoint_class == CLASS_PUBLIC_HTML:
        return HTTP_MAX_PUBLIC_HTML_BYTES
    return HTTP_MAX_PUBLIC_JSON_BYTES


def emit_oversized(endpoint_class: str, bytes_at_least: int, limit_bytes: int) -> None:
    emit("HTTP_BODY_OVERSIZED", "YES")
    emit("HTTP_ENDPOINT_CLASS", endpoint_class)
    emit("HTTP_BYTES_READ_AT_LEAST", bytes_at_least)
    emit("HTTP_LIMIT_BYTES", limit_bytes)


def read_limited(fp: object, max_bytes: int, endpoint_class: str) -> bytes:
    raw = fp.read(max_bytes + 1)  # type: ignore[attr-defined]
    if raw is None:
        return b""
    data = bytes(raw)
    if len(data) > max_bytes:
        emit_oversized(endpoint_class, len(data), max_bytes)
        raise Halt("HTTP_BODY_OVERSIZED")
    return data


def _http_fixture(url: str) -> tuple[int, object, str, str]:
    parsed = urlparse(url)
    path = redact_path(parsed.path or "/")
    host = parsed.netloc
    public = host in ALLOWED_PUBLIC_HOSTS
    fail = test_fail_mode()
    after = STATE.apply_executed
    final = url
    if public and after and fail == "public_smoke":
        raise Halt("PUBLIC_SMOKE_FAIL")
    if public and after and fail == "bad_redirect":
        emit("HTTP_REDIRECT", "https://evil.example/")
        raise Halt("HTTP_REDIRECT_UNEXPECTED")
    if public and after and fail == "oversized_body":
        emit_oversized(CLASS_PUBLIC_HTML, HTTP_MAX_PUBLIC_HTML_BYTES + 1, HTTP_MAX_PUBLIC_HTML_BYTES)
        raise Halt("HTTP_BODY_OVERSIZED")
    if public and after and fail == "malformed_json" and path in ("/api/health", "/api/predictions"):
        raise Halt("HTTP_JSON_MALFORMED")
    if public and after and fail == "wrong_content_type":
        raise Halt("HTTP_CONTENT_TYPE_MISMATCH")
    if path == "/health" and not public:
        if after and fail == "health_after":
            return 500, {"status": "fail"}, "application/json", final
        raw = os.environ.get("OWNER_APPLY_TEST_HEALTH_JSON") or ""
        payload = json.loads(raw) if raw else {"status": "ok", "db": "test", "fallback_reasons": [], "result_automation": {}}
        status = int((os.environ.get("OWNER_APPLY_TEST_HEALTH_STATUS") or "200").strip() or "200")
        return status, payload, "application/json", final
    if path == "/v1/predictions":
        if after and fail == "get_after":
            raise Halt("GET_PREDICTIONS_FAIL")
        if after and fail == "row_delta":
            src = canonical_source()
            conn = sqlite3.connect(str(src))
            try:
                conn.execute("INSERT INTO predictions(race_id, created_at) VALUES (?, 't')", ("local-delta",))
                conn.commit()
            finally:
                conn.close()
        raw = os.environ.get("OWNER_APPLY_TEST_GET_JSON") or ""
        payload = json.loads(raw) if raw else {"ok": True, "data": [], "meta": {"count": 0}}
        status = int((os.environ.get("OWNER_APPLY_TEST_GET_STATUS") or "200").strip() or "200")
        return status, payload, "application/json", final
    if path == "/v1/predictions/{id}":
        raw = os.environ.get("OWNER_APPLY_TEST_DETAIL_JSON") or ""
        payload = json.loads(raw) if raw else {"ok": True, "data": {}, "meta": {}}
        status = int((os.environ.get("OWNER_APPLY_TEST_DETAIL_STATUS") or "200").strip() or "200")
        return status, payload, "application/json", final
    if path == "/api/health":
        status = int((os.environ.get("OWNER_APPLY_TEST_API_HEALTH_STATUS") or "200").strip() or "200")
        raw = os.environ.get("OWNER_APPLY_TEST_API_HEALTH_JSON") or DEFAULT_BFF_HEALTH_JSON
        return status, json.loads(raw), "application/json", final
    if path in ("/", "/race.html", "/races.html"):
        status = int((os.environ.get("OWNER_APPLY_TEST_STATIC_STATUS") or "200").strip() or "200")
        html = os.environ.get("OWNER_APPLY_TEST_STATIC_HTML") or DEFAULT_STATIC_HTML
        return status, html.encode("utf-8"), "text/html; charset=utf-8", final
    if path == "/api/predictions":
        if after and fail == "ops_closed_wrong_code":
            return 503, {"ok": False, "error": {"code": "OTHER", "message": "x", "details": None}}, "application/json", final
        status = int((os.environ.get("OWNER_APPLY_TEST_PUBLIC_PREDICTIONS_STATUS") or "503").strip() or "503")
        raw = os.environ.get("OWNER_APPLY_TEST_PUBLIC_PREDICTIONS_JSON") or DEFAULT_BFF_PREDICTIONS_CLOSED_JSON
        return status, json.loads(raw), "application/json", final
    raise Halt("HTTP_FIXTURE_UNKNOWN_PATH")


def http_call_label(url: str) -> str:
    parsed = urlparse(url)
    path = redact_path(parsed.path or "/")
    if parsed.netloc:
        return "GET %s://%s%s" % (parsed.scheme or "https", parsed.netloc, path)
    return "GET %s" % path


def http_timeout_s(public: bool) -> float:
    base = float(HTTP_PUBLIC_TIMEOUT_S if public else HTTP_LOCAL_TIMEOUT_S)
    return min(base, max(1.0, deadline().remaining() - 1.0))


def http_get(url: str, *, headers: dict[str, str] | None = None, allow_auth_header: bool = False) -> tuple[int, object, str, str]:
    method = "GET"
    parsed = urlparse(url)
    path = parsed.path or "/"
    host = parsed.netloc.split(":")[0] if parsed.netloc else "127.0.0.1"
    public = host in ALLOWED_PUBLIC_HOSTS
    if method != "GET":
        raise Halt("HTTP_NON_GET_REFUSED")
    if path == "/v1/prediction-runs" or path.startswith("/v1/prediction-runs"):
        raise Halt("POST_PREDICTION_RUNS_REFUSED")
    deadline().require(1.0, "INSUFFICIENT_TIME_HTTP")
    hdrs = dict(headers or {})
    if not allow_auth_header:
        hdrs.pop("Authorization", None)
        hdrs.pop("authorization", None)
    label = http_call_label(url)
    STATE.http_calls.append((method, label))
    emit("HTTP_CALL", label)
    endpoint_class = class_for_path(path, public)
    max_bytes = cap_for_class(endpoint_class)
    emit("HTTP_ENDPOINT_CLASS", endpoint_class)
    emit("HTTP_LIMIT_BYTES", max_bytes)
    if test_mode() and (os.environ.get("OWNER_APPLY_TEST_HTTP") or "").strip() == "1":
        return _http_fixture(url)
    allowed = ALLOWED_PUBLIC_HOSTS if public else ("127.0.0.1", "localhost")
    opener = urllib.request.build_opener(GuardedRedirect(allowed, path or "/"))
    req = urllib.request.Request(url, method="GET", headers=hdrs)
    try:
        with opener.open(req, timeout=http_timeout_s(public)) as resp:
            raw = read_limited(resp, max_bytes, endpoint_class)
            ctype = str(resp.headers.get("Content-Type") or "")
            final = str(resp.geturl() or url)
            status = int(resp.getcode() or 0)
    except Halt:
        raise
    except urllib.error.HTTPError as exc:
        raw = read_limited(exc, max_bytes, endpoint_class) if exc.fp else b""
        ctype = str(exc.headers.get("Content-Type") if exc.headers else "")
        final = str(exc.geturl() if hasattr(exc, "geturl") else url)
        status = int(exc.code or 0)
    except Exception:
        raise Halt("HTTP_GET_FAIL")
    final_parsed = urlparse(final)
    final_host = final_parsed.netloc.split(":")[0]
    if public and final_host not in ALLOWED_PUBLIC_HOSTS:
        raise Halt("HTTP_REDIRECT_UNEXPECTED")
    if public and not path_equiv(path or "/", final_parsed.path or "/"):
        raise Halt("HTTP_REDIRECT_UNEXPECTED")
    emit("HTTP_FINAL", "%s://%s%s" % (final_parsed.scheme or parsed.scheme or "https", final_host, redact_path(final_parsed.path or "/")))
    wants_json = path.startswith("/api/") or path.startswith("/v1/") or path == "/health"
    if wants_json:
        if public and "json" not in ctype.lower():
            raise Halt("HTTP_CONTENT_TYPE_MISMATCH")
        if (not public) and ctype and "json" not in ctype.lower():
            raise Halt("HTTP_CONTENT_TYPE_MISMATCH")
        payload = _parse_json_or_halt(raw)
        return status, payload, ctype or "application/json", final
    if path in PUBLIC_STATIC_PATHS:
        if "html" not in ctype.lower():
            raise Halt("HTTP_CONTENT_TYPE_MISMATCH")
        return status, raw, ctype, final
    payload = raw
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        payload = raw
    return status, payload, ctype, final


def first_list_race_id(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        return None
    first = data[0]
    if not isinstance(first, dict):
        return None
    rid = first.get("race_id") or first.get("id")
    if rid is None or str(rid) == "":
        return None
    return str(rid)


def ops_closed(status: int, payload: object) -> bool:
    if status != 503:
        return False
    if not isinstance(payload, dict):
        return False
    err = payload.get("error")
    return isinstance(err, dict) and str(err.get("code") or "") == "OPS_CLOSED"


def localhost_ai(path: str) -> str:
    return "http://127.0.0.1:%d%s" % (int(STATE.ai_port or 8000), path)


def ai_headers() -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if STATE.ai_key:
        headers["X-AI-Key"] = STATE.ai_key
    return headers


def check_health(*, label: str) -> dict[str, object]:
    status, payload, _ctype, _final = http_get(localhost_ai("/health"), headers={"Accept": "application/json"})
    emit("%s_HEALTH_STATUS" % label, status)
    emit("%s_HEALTH_CHECKED" % label, "YES")
    keys = sorted(str(k) for k in payload.keys()) if isinstance(payload, dict) else []
    emit("%s_HEALTH_KEYS" % label, ",".join(keys))
    ok = status == 200 and isinstance(payload, dict) and str(payload.get("status") or "") == "ok"
    emit("%s_HEALTH_PASS" % label, ok)
    if not ok:
        raise Halt("HEALTH_FAIL")
    return envelope_shape(payload)


def check_get_predictions(src: Path, *, label: str) -> tuple[dict[str, object], object]:
    before = pred_row_count_ro(src)
    emit("%s_GET_PRED_ROW_BEFORE" % label, before)
    status, payload, _ctype, _final = http_get(localhost_ai("/v1/predictions"), headers=ai_headers())
    after = pred_row_count_ro(src)
    emit("%s_GET_STATUS" % label, status)
    emit("%s_GET_CHECKED" % label, "YES")
    emit("%s_GET_PRED_ROW_AFTER" % label, after)
    delta = after - before
    emit("%s_GET_PRED_ROW_DELTA" % label, delta)
    shape = envelope_shape(payload)
    emit("%s_GET_ENVELOPE_KEYS" % label, ",".join(str(k) for k in (shape.get("keys") or [])))
    ok = status == 200 and isinstance(payload, dict) and payload.get("ok") is True and "data" in payload
    emit("%s_GET_PASS" % label, ok)
    if not ok:
        raise Halt("GET_PREDICTIONS_FAIL")
    if delta != 0:
        raise Halt("GET_PRED_ROW_DELTA_NONEZERO")
    return shape, payload


def maybe_detail_get(payload: object, *, label: str) -> None:
    rid = first_list_race_id(payload)
    if not rid:
        emit("%s_DETAIL_GET" % label, "SKIPPED_EMPTY_LIST")
        emit("%s_DETAIL_GET_CHECKED" % label, "NO")
        return
    url = localhost_ai("/v1/predictions/%s" % rid)
    status, detail, _ctype, _final = http_get(url, headers=ai_headers(), allow_auth_header=False)
    emit("%s_DETAIL_GET" % label, "ATTEMPTED")
    emit("%s_DETAIL_GET_CHECKED" % label, "YES")
    emit("%s_DETAIL_GET_STATUS" % label, status)
    emit("%s_DETAIL_GET_AUTHORIZATION_SENT" % label, "NO")
    ok = status == 200 and isinstance(detail, dict) and detail.get("ok") is True
    emit("%s_DETAIL_GET_PASS" % label, ok)
    if not ok:
        raise Halt("DETAIL_GET_FAIL")


def validate_bff_health(status: int, payload: object, content_type: str) -> None:
    if status != 200:
        raise Halt("PUBLIC_SMOKE_FAIL")
    if "json" not in (content_type or "application/json").lower():
        raise Halt("HTTP_CONTENT_TYPE_MISMATCH")
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise Halt("PUBLIC_HEALTH_CONTRACT_FAIL")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise Halt("PUBLIC_HEALTH_CONTRACT_FAIL")
    if str(data.get("status") or "") not in ("ok", "degraded"):
        raise Halt("PUBLIC_HEALTH_CONTRACT_FAIL")
    if str(data.get("service") or "") != "bff":
        raise Halt("PUBLIC_HEALTH_CONTRACT_FAIL")


def validate_bff_predictions(status: int, payload: object, content_type: str) -> None:
    if "json" not in (content_type or "application/json").lower():
        raise Halt("HTTP_CONTENT_TYPE_MISMATCH")
    if not isinstance(payload, dict):
        raise Halt("PUBLIC_PREDICTIONS_CONTRACT_FAIL")
    if status == 200:
        if payload.get("ok") is not True or "data" not in payload:
            raise Halt("PUBLIC_PREDICTIONS_CONTRACT_FAIL")
        emit("PUBLIC_PREDICTIONS_OPS_CLOSED", "NO")
        return
    if status == 503:
        if not ops_closed(status, payload):
            raise Halt("PUBLIC_PREDICTIONS_CONTRACT_FAIL")
        emit("PUBLIC_PREDICTIONS_OPS_CLOSED", "YES")
        return
    raise Halt("PUBLIC_SMOKE_FAIL")


def validate_static_html(status: int, payload: object, content_type: str) -> None:
    if status != 200:
        raise Halt("PUBLIC_SMOKE_FAIL")
    if "html" not in (content_type or "").lower():
        raise Halt("HTTP_CONTENT_TYPE_MISMATCH")
    if isinstance(payload, bytes):
        text = payload.decode("utf-8", errors="replace")
    else:
        text = str(payload)
    if not all(token in text for token in SITE_IDENTIFIERS):
        raise Halt("PUBLIC_STATIC_IDENTITY_FAIL")


def run_public_smoke() -> None:
    urls = public_smoke_urls()
    emit("PUBLIC_SMOKE_REQUIRED_COUNT", len(urls))
    emit("SITE_UI_VISUAL_CHECKED", "NO")
    checked = 0
    for url in urls:
        deadline().require(HTTP_PUBLIC_TIMEOUT_S, "INSUFFICIENT_TIME_AFTER_COMMIT")
        parsed = urlparse(url)
        path = parsed.path or "/"
        status, payload, ctype, final = http_get(
            url,
            headers={"Accept": "text/html,application/json"},
            allow_auth_header=False,
        )
        emit("PUBLIC_SMOKE_STATUS", "%s://%s%s:%s" % (parsed.scheme, parsed.netloc, path, status))
        checked += 1
        if path == "/api/predictions":
            validate_bff_predictions(status, payload, ctype)
            continue
        if path == "/api/health":
            validate_bff_health(status, payload, ctype)
            continue
        validate_static_html(status, payload, ctype)
    emit("PUBLIC_SMOKE_CHECKED_COUNT", checked)
    emit("PUBLIC_UI_CHECKED", "YES")
    emit("PUBLIC_API_HEALTH_CHECKED", "YES")
    emit("PUBLIC_PREDICTIONS_CHECKED", "YES")
    emit("OWNER_IMMEDIATE_POST_APPLY_SMOKE_DONE", "YES")
    emit("SITE_UI_VISUAL_CHECKED", "NO")
    if checked != len(urls):
        raise Halt("PUBLIC_SMOKE_FAIL")


def journal_error_count() -> int:
    if test_mode():
        text = os.environ.get("OWNER_APPLY_TEST_JOURNAL") or ""
        if test_fail_mode() == "journal_error":
            text = "error: injected journal line"
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return len(lines)
    unit = STATE.unit if STATE.unit and STATE.unit != "UNSET" else "expect-ai.service"
    since = STATE.apply_started or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    rc, out = run_cmd(
        ["journalctl", "-u", unit, "--since", since, "-p", "err", "--no-pager", "-o", "cat"]
    )
    if rc != 0:
        raise Halt("JOURNAL_READ_FAIL")
    return len([ln for ln in (out or "").splitlines() if ln.strip()])


def assert_no_write_calls() -> None:
    methods = sorted({m for m, _ in STATE.http_calls})
    labels = [p for _, p in STATE.http_calls]
    emit("HTTP_METHODS", ",".join(methods) if methods else "NONE")
    post_called = any(m != "GET" for m, _ in STATE.http_calls) or any("prediction-runs" in p for p in labels)
    emit("POST_PREDICTION_RUNS_CALLED", post_called)
    emit("CONVERSATION_WRITE_CALLED", any("/v1/conversation/chat" in p or p.endswith("/v1/conversation") for p in labels))
    emit("RA_WRITE_CALLED", "NO")
    emit("CHALLENGE_WRITE_CALLED", "NO")
    if post_called:
        raise Halt("POST_PREDICTION_RUNS_CALLED")
    if any(m != "GET" for m, _ in STATE.http_calls):
        raise Halt("NON_GET_HTTP_CALLED")


def capture_runtime(src: Path, *, label: str) -> dict[str, object]:
    health_shape = check_health(label=label)
    get_shape, payload = check_get_predictions(src, label=label)
    maybe_detail_get(payload, label=label)
    assert_no_write_calls()
    return {"health": health_shape, "get": get_shape}


def compare_runtime(before: dict[str, object], after: dict[str, object]) -> None:
    emit("GET_ENVELOPE_COMPARE_CHECKED", "YES")
    same = shape_text(before["get"]) == shape_text(after["get"])
    emit("GET_ENVELOPE_SHAPE_MATCH", same)
    if not same:
        raise Halt("GET_ENVELOPE_SHAPE_MISMATCH")
    emit("HEALTH_ENVELOPE_COMPARE_CHECKED", "YES")
    hsame = shape_text(before["health"]) == shape_text(after["health"])
    emit("HEALTH_ENVELOPE_SHAPE_MATCH", hsame)
    if not hsame:
        raise Halt("HEALTH_ENVELOPE_SHAPE_MISMATCH")


def inject_schema_before_tx(src: Path) -> None:
    if test_fail_mode() != "schema_before_tx":
        return
    conn = sqlite3.connect(str(src))
    try:
        conn.execute("ALTER TABLE predictions ADD COLUMN injected_before_tx TEXT")
        conn.commit()
    finally:
        conn.close()
    emit("TEST_SCHEMA_MUTATED_BEFORE_TX", "YES")


def _rollback(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("ROLLBACK")
        emit("EXPLICIT_ROLLBACK", "YES")
    except sqlite3.Error:
        emit("EXPLICIT_ROLLBACK", "NO")


def apply_022(src: Path, src_st: os.stat_result) -> None:
    if (os.environ.get("EXPECT_AI_ALLOW_MIGRATION_022") or "").strip() != "1":
        raise Halt("APPLY_WINDOW_022_UNSET")
    conn = sqlite3.connect(str(src))
    conn.isolation_level = None
    committed = False
    try:
        deadline().require(COMMIT_BUDGET_S, "INSUFFICIENT_TIME_BEFORE_APPLY")
        conn.execute("PRAGMA busy_timeout=%d" % int(BUSY_TIMEOUT_MS))
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN IMMEDIATE")
        STATE.apply_phase = PHASE_TRANSACTION_OPEN
        emit("APPLY_PHASE", PHASE_TRANSACTION_OPEN)
        emit("BEGIN_IMMEDIATE", "YES")
        emit("BUSY_TIMEOUT_MS", BUSY_TIMEOUT_MS)
        now = src.stat()
        emit("TX_SOURCE_DEV", now.st_dev)
        emit("TX_SOURCE_INO", now.st_ino)
        if (int(now.st_dev), int(now.st_ino)) != (int(src_st.st_dev), int(src_st.st_ino)):
            raise Halt("SOURCE_IDENTITY_CHANGED")
        exp_dev, exp_ino = expected_source_dev_ino()
        if (int(now.st_dev), int(now.st_ino)) != (int(exp_dev), int(exp_ino)):
            emit("DB_DRIFT", "YES")
            raise Halt("DB_DRIFT")
        rows_before = verify_pre_schema(conn, prefix="TX_")
        fail = test_fail_mode()
        for idx, stmt in enumerate(ALTER_SQL):
            if fail == "alter2" and idx == 1:
                raise Halt("INJECTED_ALTER2_FAIL")
            conn.execute(stmt)
        if fail == "index":
            raise Halt("INJECTED_INDEX_FAIL")
        conn.execute(INDEX_SQL)
        if fail == "migration_insert":
            raise Halt("INJECTED_MIGRATION_INSERT_FAIL")
        conn.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, datetime('now'))",
            (PERSIST_022,),
        )
        verify_post_schema(conn, rows_before, prefix="TX_")
        conn.execute("COMMIT")
        committed = True
        STATE.apply_phase = PHASE_COMMITTED
        STATE.apply_executed = True
        emit("APPLY_PHASE", PHASE_COMMITTED)
        emit("APPLY_EXECUTED", "YES")
        sys.stdout.flush()
    except Halt:
        if not committed:
            _rollback(conn)
        raise
    except sqlite3.Error:
        if not committed:
            _rollback(conn)
            raise Halt("SQLITE_ERROR")
        raise Halt("SQLITE_ERROR_AFTER_COMMIT")
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def emit_rollback_review_holds() -> None:
    emit("AUTO_DROP_COLUMNS", "NO")
    emit("AUTO_DROP_INDEX", "NO")
    emit("AUTO_DELETE_ROWS", "NO")
    emit("AUTO_DELETE_SCHEMA_MIGRATIONS", "NO")
    emit("AUTO_REWRITE_BUNDLE_JSON", "NO")
    emit("AUTO_BACKUP_RESTORE", "NO")
    emit("INDEX_DROP_OWNER_DECISION_REQUIRED", "YES")
    emit("PREDICTION_RUNS_ENABLED_MUST_STAY", "0")


def fail_closed(code: str) -> int:
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
    try:
        assert_no_write_calls()
    except Halt:
        pass
    if STATE.apply_executed or STATE.apply_phase == PHASE_COMMITTED:
        emit("APPLY_EXECUTED", "YES")
        emit("APPLY_PHASE", PHASE_COMMITTED)
        emit("POST_APPLY_REGRESSION_PASS", "NO")
        emit("PRODUCTION_IMPACT_VERIFIED", "NO")
        emit("ROLLBACK_REVIEW_REQUIRED", "YES")
        emit_rollback_review_holds()
    else:
        emit("APPLY_EXECUTED", "NO")
        emit("APPLY_PHASE", STATE.apply_phase)
        emit("POST_APPLY_REGRESSION_PASS", "NO")
        emit("ROLLBACK_REVIEW_REQUIRED", "NO")
    emit("OWNER_APPLY_STATUS", "FAIL")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("MIGRATION_MAY_PROCEED", "NO")
    emit("POST_REMAINS_DISABLED", "YES")
    emit("HALT_REASON", code)
    emit("SITE_UI_VISUAL_CHECKED", "NO")
    emit("AUDIT_CLOSED", "YES")
    STATE.audit_closed = True
    return 2


def run() -> int:
    STATE.deadline = Deadline(remote_hard_deadline_s())
    emit("PACK", PACK)
    emit("APPLY_ONLY", "YES")
    emit("REMOTE_HARD_DEADLINE_S", int(deadline().hard_s) if not test_mode() else deadline().hard_s)
    emit("WRAPPER_TIMEOUT_MS", WRAPPER_TIMEOUT_MS)
    emit("DRAIN_WAIT_MS", DRAIN_WAIT_MS)
    emit("KILL_DRAIN_WAIT_MS", KILL_DRAIN_WAIT_MS)
    emit("SAFETY_BUFFER_MS", SAFETY_BUFFER_MS)
    emit("PRE_APPLY_MIN_REMAINING_S", PRE_APPLY_MIN_REMAINING_S)
    emit("POST_AFTER_COMMIT_MIN_S", POST_AFTER_COMMIT_MIN_S)
    emit("HTTP_LOCAL_TIMEOUT_S", HTTP_LOCAL_TIMEOUT_S)
    emit("HTTP_PUBLIC_TIMEOUT_S", HTTP_PUBLIC_TIMEOUT_S)
    emit("BUSY_TIMEOUT_MS", BUSY_TIMEOUT_MS)
    emit("HTTP_MAX_INTERNAL_HEALTH_BYTES", HTTP_MAX_INTERNAL_HEALTH_BYTES)
    emit("HTTP_MAX_INTERNAL_LIST_BYTES", HTTP_MAX_INTERNAL_LIST_BYTES)
    emit("HTTP_MAX_INTERNAL_DETAIL_BYTES", HTTP_MAX_INTERNAL_DETAIL_BYTES)
    emit("HTTP_MAX_PUBLIC_JSON_BYTES", HTTP_MAX_PUBLIC_JSON_BYTES)
    emit("HTTP_MAX_PUBLIC_HTML_BYTES", HTTP_MAX_PUBLIC_HTML_BYTES)
    emit("HTTP_MAX_JSON_BYTES_REMOVED", "YES")
    emit("MEASURE_V2_OUTPUT_SHA256", MEASURE_V2_OUTPUT_SHA256)
    emit("MEASURED_INTERNAL_LIST_BYTES", 583853)
    emit("MEASURED_INTERNAL_DETAIL_BYTES", 18563)
    emit("MEASURED_LIVE_SOURCE_SIZE", MEASURED_LIVE_SOURCE_SIZE)
    emit("MEASURED_PRED_ROW_COUNT", MEASURED_PRED_ROW_COUNT)
    emit("WRAPPER_BUDGET_OK", wrapper_budget_ok())
    emit("SITE_UI_VISUAL_CHECKED", "NO")
    if not wrapper_budget_ok():
        raise Halt("WRAPPER_TIMEOUT_SHORTER_THAN_REMOTE")
    emit("POST_ENABLE_IN_THIS_PACK", "NO")
    emit("SITE_SWITCH_IN_THIS_PACK", "NO")
    emit("SERVICE_CHANGE_IN_THIS_PACK", "NO")
    emit("PERSISTENT_ENV_CHANGED", "NO")
    emit("SCP_USED", "NO")
    emit("SUDO_USED", "NO")
    emit("RAW_ENVIRONMENT_LOGGED", "NO")
    emit("CANONICAL_SOURCE", CANONICAL_SOURCE)
    emit("APPLY_BACKUP_CANON", APPLY_BACKUP_CANON)
    emit("APPLY_BACKUP_PATH", APPLY_BACKUP_PATH)
    emit("APPLY_BACKUP_SHA256", APPLY_BACKUP_SHA256)
    emit("APPLY_BACKUP_IDENTITY", APPLY_BACKUP_IDENTITY)
    emit("APPLY_BACKUP_SIZE", APPLY_BACKUP_SIZE)
    emit("FRESH_BACKUP_OWNER_LOG_SHA256", FRESH_BACKUP_OWNER_LOG_SHA256)
    emit("HISTORICAL_BACKUP_PATH", HISTORICAL_BACKUP_PATH)
    emit("HISTORICAL_BACKUP_SHA256", HISTORICAL_BACKUP_SHA256)
    emit("HISTORICAL_BACKUP_SIZE", HISTORICAL_BACKUP_SIZE)
    emit("HISTORICAL_BACKUP_IDENTITY", HISTORICAL_BACKUP_IDENTITY)
    emit("HISTORICAL_BACKUP_NOT_APPLY_CANON", "YES")
    emit("AUTO_BACKUP_RESTORE", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("APPLY_PHASE", PHASE_NOT_STARTED)
    emit("GET_UI_CONVERSATION_RA_CHALLENGE_CHANGED", "UNCHECKED")
    refuse_unapproved()
    verify_production_env(after=False)
    bak = backup_path()
    verify_backup(bak)
    src = canonical_source()
    if (not test_mode()) and str(src.resolve()) != CANONICAL_SOURCE:
        raise Halt("REFUSED_NON_CANONICAL_SOURCE")
    if not src.is_file():
        raise Halt("SOURCE_MISSING")
    src_st = verify_identity(src, *expected_source_dev_ino(), "SOURCE")
    src_ro = sqlite3.connect("file:%s?mode=ro" % src.resolve().as_posix(), uri=True)
    try:
        src_ro.execute("PRAGMA query_only=ON")
        verify_pre_schema(src_ro, prefix="RO_")
    finally:
        src_ro.close()
    pre_runtime = capture_runtime(src, label="PRE")
    inject_schema_before_tx(src)
    emit("DEADLINE_REMAINING_BEFORE_APPLY_S", "%.1f" % max(0.0, deadline().remaining()))
    if test_fail_mode() == "deadline_before" or deadline().remaining() < PRE_APPLY_MIN_REMAINING_S:
        raise Halt("INSUFFICIENT_TIME_BEFORE_APPLY")
    STATE.apply_started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    emit("APPLY_STARTED_UTC", STATE.apply_started)
    os.environ["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    emit("PROCESS_022_WINDOW", "OPEN")
    emit("PROCESS_ONLY_022", "YES")
    try:
        apply_022(src, src_st)
    finally:
        os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
        emit("PROCESS_022_WINDOW", "CLOSED")
    emit("DEADLINE_REMAINING_AFTER_COMMIT_S", "%.1f" % max(0.0, deadline().remaining()))
    if test_fail_mode() == "deadline_after_commit" or deadline().remaining() < POST_AFTER_COMMIT_MIN_S:
        raise Halt("INSUFFICIENT_TIME_AFTER_COMMIT")
    after_st = src.stat()
    if (int(after_st.st_dev), int(after_st.st_ino)) != (int(src_st.st_dev), int(src_st.st_ino)):
        raise Halt("SOURCE_IDENTITY_CHANGED")
    src_after = sqlite3.connect("file:%s?mode=ro" % src.resolve().as_posix(), uri=True)
    try:
        src_after.execute("PRAGMA query_only=ON")
        verify_post_schema(src_after, pred_row_count(src_after), prefix="POST_")
    finally:
        src_after.close()
    verify_production_env(after=True)
    post_runtime = capture_runtime(src, label="POST")
    compare_runtime(pre_runtime, post_runtime)
    errors = journal_error_count()
    emit("JOURNAL_ERROR_CHECKED", "YES")
    emit("JOURNAL_ERROR_COUNT_AFTER_APPLY", errors)
    if errors != 0:
        raise Halt("JOURNAL_ERROR_AFTER_APPLY")
    emit("OWNER_IMMEDIATE_POST_APPLY_SMOKE_REQUIRED", "YES")
    if not can_run_public_smoke():
        return finish_pending_public_smoke(src)
    run_public_smoke()
    assert_no_write_calls()
    emit("POST_APPLY_REGRESSION_PASS", "YES")
    emit("PRODUCTION_IMPACT_VERIFIED", "YES")
    emit("ROLLBACK_REVIEW_REQUIRED", "NO")
    return finish_success(src)


def finish_pending_public_smoke(src: Path) -> int:
    emit("OWNER_IMMEDIATE_POST_APPLY_SMOKE_DONE", "NO")
    emit("PUBLIC_UI_CHECKED", "NO")
    emit("PUBLIC_API_HEALTH_CHECKED", "NO")
    emit("PUBLIC_PREDICTIONS_CHECKED", "NO")
    emit("POST_APPLY_REGRESSION_PASS", "PENDING_PUBLIC_SMOKE")
    emit("PRODUCTION_IMPACT_VERIFIED", "PARTIAL")
    emit("ROLLBACK_REVIEW_REQUIRED", "NO")
    emit("OWNER_APPLY_STATUS", "PENDING_PUBLIC_SMOKE")
    emit("SITE_UI_VISUAL_CHECKED", "NO")
    emit_common_after_commit(src)
    emit("AUDIT_CLOSED", "YES")
    STATE.audit_closed = True
    return 3


def emit_common_after_commit(src: Path) -> None:
    live = (not test_mode()) and str(src.resolve()) == CANONICAL_SOURCE
    emit("APPLY_EXECUTED", "YES")
    emit("LIVE_CANONICAL_APPLY", live)
    emit("MIGRATION_022_APPLIED", "YES")
    emit("POST_REMAINS_DISABLED", "YES")
    emit("PREDICTION_RUNS_ENABLED_MUST_STAY", "0")
    emit("SITE_SWITCHED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("MIGRATION_MAY_PROCEED", "NO")
    emit("POST_ENABLE_IS_SEPARATE_STEP", "YES")


def finish_success(src: Path) -> int:
    emit("OWNER_APPLY_STATUS", "SUCCESS")
    emit("SITE_UI_VISUAL_CHECKED", "NO")
    emit_common_after_commit(src)
    emit("AUDIT_CLOSED", "YES")
    STATE.audit_closed = True
    return 0


def main() -> int:
    try:
        return run()
    except Halt as exc:
        return fail_closed(exc.code)
    except sqlite3.Error:
        return fail_closed("SQLITE_ERROR")
    except Exception:
        return fail_closed("UNHANDLED_EXCEPTION")
    finally:
        os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
        if not STATE.audit_closed:
            fail_closed("AUDIT_CLOSE_FALLBACK")


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
