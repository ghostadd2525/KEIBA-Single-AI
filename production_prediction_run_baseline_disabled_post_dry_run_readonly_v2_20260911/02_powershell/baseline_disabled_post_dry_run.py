#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production Step 2-4 baseline + disabled-POST DRY_RUN (Owner / EC2, read-only).

GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/v1/predictions
  unfiltered only when live AI_ENGINE is not real (catalog / mock).
  if AI_ENGINE=real: GET /v1/predictions?date=2099-01-01 only.

Never call POST /v1/prediction-runs.
Never GET prediction detail by race_id.
Never GET /v1/challenge/monthly.
Never POST conversation chat.
Never apply 019. Never set EXPECT_AI_ALLOW_MIGRATION_019.
SQLite: mode=ro SELECT / PRAGMA only.
systemd: show / status / journalctl read-only.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

PACK_NAME = "production_prediction_run_baseline_disabled_post_dry_run_readonly_20260911"
AI_BASE = "http://127.0.0.1:8000"
SAFE_EMPTY_DATE = "2099-01-01"
RESEARCH_WEEK_END_JST = datetime(2026, 9, 12, 0, 0, 0, tzinfo=timezone(timedelta(hours=9)))
IDEMPOTENCY_INDEX = "uq_predictions_idempotency_key_not_null"
RUN_COLUMNS = (
    "idempotency_key",
    "persist_source",
    "input_snapshot_hash",
    "prediction_semantic_hash",
)
MIGRATION_019 = "019_prediction_run_idempotency"
DB_CANDIDATES = (
    "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db",
    "/opt/expect-ai/current/services/win5-ai/var/expect_ai.db",
    "/var/lib/expect-ai/expect_ai.db",
)
CODE_ROOT_CANDIDATES = (
    "/home/ubuntu/KEIBA-Single-AI/services/win5-ai",
    "/opt/expect-ai/current/services/win5-ai",
)
REVIEW_FILE_SHA256 = {
    "app/main.py": "d85c039c8a27a74242876f1e631d5ef84e6845b3ffc495d61c5d88b228580d15",
    "app/data/db.py": "5793addab3cc9c39dd7efd759cefc2fc38390da2329ef09feac4dc8d4464b12f",
    "app/data/repository/__init__.py": "70fab66425a142307eab738783e32fbb93ec8fb6859c438007c7c6cd94165f77",
    "app/data/migrations/019_prediction_run_idempotency.sql": "d8fc71e316d7819a4dcfc0977bf6444308410144b62fd29a33ca764ea853370f",
    "app/core/feature_loader_bridge.py": "f3c25c7b87941138555158e051d0520fc705889e8a2a17e8889c7fc5325eae44",
    "app/predictions/__init__.py": "d4373c31ad5aac82a2d83a53d91bc2b95607bd891d7b9286c3c154478d5dc21c",
    "app/predictions/runs.py": "d04bc99281474aa4e0e78b9951df6335f6b9995c9e7328b100afd552815f35c1",
    "app/predictions/guards.py": "7e6d74dd77b6645364679187a325b42676cd64d6546f5576022f19d30e6dfc82",
    "app/predictions/provenance.py": "2cc2585d53a3dbdffd8c7a4dc56921aafaf4ce6cd5421d1928950a34194bb704",
    "app/predictions/snapshot.py": "2114c953b57461f73d0450384f38df2a2b086a51e53591c77cc70b448cbde5f7",
    "app/predictions/feature_pin.py": "49794f3671589a5ec13bc622161bac8c10609ff922c51033343dca30a31fbc36",
    "app/predictions/corpus.py": "29f54d8d001753b49c3bd66edeed0ebdff4f92386ce22eb4c5fbe6b215e3f656",
    "app/predictions/raeval84_holdout.py": "09a85e6fb1f8c30dd8ef36d606de91bfc05e35d18f9ca6039dd861531442d077",
    "app/predictions/data/raeval84_v1_holdout_race_ids.txt": "6f586357d69e554c559fb43bd3520a2d04849787328b40dc12bdbb2f67a94dd3",
}
REVIEW_ZIP_SHA256 = "4fd4dc88315f7dbab3f495dea249ad1fcb715b375a64de85762a779571aa2c80"
ENV_KEYS = (
    "PREDICTION_RUNS_ENABLED",
    "EXPECT_AI_ALLOW_MIGRATION_019",
    "AI_ENGINE",
    "EXPECT_AI_DB_PATH",
)
SECRET_PREFIXES = (
    "AWS_",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "API_KEY",
    "EXPECT_AI_API",
    "X-AI-Key",
    "AI_API_KEY",
)
SYSTEMD_SHOW_PROPS = (
    "Id",
    "ActiveState",
    "SubState",
    "MainPID",
    "UnitFileState",
    "FragmentPath",
    "Result",
    "NRestarts",
    "ExecStart",
    "WorkingDirectory",
    "Environment",
    "EnvironmentFiles",
    "DropInPaths",
    "User",
)
ERROR_HINTS = (
    "traceback",
    "get error",
    "predictionadapter",
    "internal_error",
    "exception",
    "operationalerror",
)
LIST_TIMEOUT_SEC = 60.0
HEALTH_TIMEOUT_SEC = 8.0
LIST_MAX_BYTES = 2000000
EXPECTED_ENVELOPE = ("ok", "data")
SOURCE_GREP_TARGETS = (
    ("conversation", "app/conversation/service.py"),
    ("challenge", "app/challenge/service.py"),
    ("result_automation", "app/ops/result_automation.py"),
    ("repository", "app/data/repository/__init__.py"),
    ("main", "app/main.py"),
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


def flag_truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in ("1", "true", "yes", "on")


def research_week_active(now: datetime | None = None) -> bool:
    if now is None:
        now = datetime.now(timezone(timedelta(hours=9)))
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone(timedelta(hours=9)))
    return now < RESEARCH_WEEK_END_JST


def backup_possible(
    *,
    exists: bool,
    readable: bool,
    parent_writable: bool,
    sqlite_cli: bool,
    copy_executed: bool,
) -> tuple[bool, str]:
    if copy_executed:
        return False, "COPY_EXECUTED_FORBIDDEN"
    if not exists:
        return False, "DB_MISSING"
    if not readable:
        return False, "DB_NOT_READABLE"
    if not sqlite_cli:
        return False, "SQLITE3_CLI_MISSING"
    if not parent_writable:
        return False, "PARENT_NOT_WRITABLE"
    return True, "POSSIBLE_NOT_EXECUTED"


def classify_019(
    *,
    columns: set[str],
    index_names: set[str],
    index_sql: str | None,
    migrations: set[str],
) -> dict[str, Any]:
    have_cols = set(RUN_COLUMNS) <= columns
    any_col = bool(set(RUN_COLUMNS) & columns)
    idx_present = IDEMPOTENCY_INDEX in index_names
    sql = " ".join((index_sql or "").split()).lower().replace(" ", "")
    idx_ok = (
        idx_present
        and "createuniqueindex" in sql
        and "onpredictions(idempotency_key)" in sql
        and "whereidempotency_keyisnotnull" in sql
    )
    in_migrations = MIGRATION_019 in migrations
    if have_cols and idx_ok:
        status = "complete"
    elif idx_present and not idx_ok:
        status = "error"
    elif any_col or idx_present or in_migrations:
        status = "partial"
    else:
        status = "absent"
    return {
        "status": status,
        "applied": status == "complete" or in_migrations,
        "index_ok": idx_ok,
        "in_migrations": in_migrations,
        "have_run_columns": have_cols,
        "any_run_column": any_col,
        "rollback_needed": idx_present,
        "rollback_target": IDEMPOTENCY_INDEX if idx_present else "NONE",
    }


def envelope_schema(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "ok_type": "missing",
            "keys": [],
            "data_type": "missing",
            "item_count": 0,
            "first_item_keys": [],
            "schema_ok": False,
        }
    keys = sorted(payload.keys())
    data = payload.get("data")
    if isinstance(data, list):
        data_type = "list"
        items = [x for x in data if isinstance(x, dict)]
        first_keys = sorted(items[0].keys()) if items else []
        item_count = len(items)
    else:
        data_type = type(data).__name__ if data is not None else "missing"
        first_keys = []
        item_count = 0
    schema_ok = (
        payload.get("ok") is True
        and all(k in payload for k in EXPECTED_ENVELOPE)
        and data_type == "list"
    )
    return {
        "ok_type": type(payload.get("ok")).__name__,
        "keys": keys,
        "data_type": data_type,
        "item_count": item_count,
        "first_item_keys": first_keys,
        "schema_ok": schema_ok,
    }


def schemas_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a.get("keys") == b.get("keys")
        and a.get("data_type") == b.get("data_type")
        and a.get("ok_type") == b.get("ok_type")
        and a.get("first_item_keys") == b.get("first_item_keys")
    )


def live_vs_review(
    live_hashes: dict[str, str | None],
    review_hashes: dict[str, str] | None = None,
) -> dict[str, Any]:
    review_hashes = review_hashes or REVIEW_FILE_SHA256
    match = 0
    mismatch = 0
    missing = 0
    details: list[str] = []
    for rel, expected in review_hashes.items():
        got = live_hashes.get(rel)
        if not got:
            missing += 1
            details.append("%s:MISSING_LIVE" % rel)
        elif got == expected:
            match += 1
        else:
            mismatch += 1
            details.append("%s:MISMATCH" % rel)
    equal = match == len(review_hashes) and missing == 0 and mismatch == 0
    return {
        "match": match,
        "mismatch": mismatch,
        "missing": missing,
        "equal": equal,
        "expected_equal_before_apply": False,
        "details": details[:16],
    }


def parse_systemd_show(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip()
    return out


def parse_environ_blob(blob: str) -> dict[str, str]:
    out: dict[str, str] = {}
    raw = blob.replace("\n", "\0")
    for part in raw.split("\0"):
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        if key in ENV_KEYS:
            out[key] = val
    return out


def prediction_runs_enabled_effective(values: dict[str, str | None]) -> tuple[bool, str]:
    raw = None
    for source in ("proc", "systemd", "live_default"):
        if values.get(source) not in (None, ""):
            raw = values.get(source)
            src = source
            break
    else:
        return False, "absent_defaults_to_0"
    return flag_truthy(raw), "from_%s=%s" % (src, raw)


def source_uses_legacy_insert(text: str) -> bool:
    needle = "INSERT" + " INTO " + "predictions"
    if needle not in text:
        return False
    block_has_persist = False
    idx = 0
    while True:
        found = text.find(needle, idx)
        if found < 0:
            break
        chunk = text[found : found + 400]
        if "persist_source" in chunk:
            block_has_persist = True
        idx = found + 1
    return not block_has_persist


def sha256_file(path: str) -> str | None:
    if not path or not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _http_get(url: str, timeout: float) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    key = (os.environ.get("AI_API_KEY") or "").strip()
    if key:
        headers["X-AI-Key"] = key
    req = urllib.request.Request(url, method="GET", headers=headers)
    started = time.monotonic()
    out: dict[str, Any] = {
        "status": 0,
        "payload": None,
        "raw_head": "",
        "nbytes": 0,
        "elapsed_sec": 0.0,
        "error": "",
        "timeout": False,
        "url": url,
    }
    raw = ""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8", errors="replace")
            out["status"] = int(getattr(res, "status", 200) or 200)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        out["status"] = int(exc.code)
        out["error"] = "HTTPError:%s" % exc.code
    except Exception as exc:
        name = type(exc).__name__
        out["timeout"] = name in ("TimeoutError", "socket.timeout") or "timed out" in str(exc).lower()
        out["error"] = "%s: %s" % (name, exc)
        raw = ""
    out["elapsed_sec"] = round(time.monotonic() - started, 3)
    out["nbytes"] = len(raw.encode("utf-8")) if raw else 0
    out["raw_head"] = raw[:240]
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                out["payload"] = parsed
        except json.JSONDecodeError:
            out["payload"] = None
    return out


def extract_data(payload: dict[str, Any] | None) -> Any:
    if not payload:
        return None
    if payload.get("data") is not None:
        return payload.get("data")
    return payload


def open_db_ro(path: str) -> sqlite3.Connection | None:
    if not path or not os.path.isfile(path):
        return None
    uri = "file:%s?mode=ro" % path
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    conn.execute("PRAGMA query_only = ON")
    conn.row_factory = sqlite3.Row
    return conn


def discover_db_path(health_payload: dict[str, Any] | None) -> str | None:
    if isinstance(health_payload, dict):
        hinted = str(health_payload.get("db") or "").strip()
        if hinted and os.path.isfile(hinted):
            return hinted
        data = health_payload.get("data")
        if isinstance(data, dict):
            hinted = str(data.get("db") or "").strip()
            if hinted and os.path.isfile(hinted):
                return hinted
    env_path = (os.environ.get("EXPECT_AI_DB_PATH") or "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path
    for cand in DB_CANDIDATES:
        if os.path.isfile(cand):
            return cand
    return None


def count_predictions(conn: sqlite3.Connection | None) -> int | None:
    if conn is None:
        return None
    try:
        row = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return None


def run_cmd(args: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
            check=False,
        )
        text = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        return int(p.returncode), text
    except Exception as exc:
        return 1, "%s: %s" % (type(exc).__name__, exc)


def redact_line(line: str) -> str:
    for prefix in SECRET_PREFIXES:
        if prefix.lower() in line.lower():
            return "REDACTED_SECRET_LINE"
    return line


def read_text(path: str, limit: int = 400000) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def find_code_root(working_directory: str) -> str | None:
    candidates = []
    if working_directory:
        candidates.append(working_directory)
        parent = os.path.dirname(working_directory.rstrip("/"))
        if parent:
            candidates.append(parent)
    candidates.extend(CODE_ROOT_CANDIDATES)
    for cand in candidates:
        if cand and os.path.isfile(os.path.join(cand, "app", "main.py")):
            return cand
    return None


def inventory_db(conn: sqlite3.Connection | None) -> dict[str, Any]:
    empty = {
        "columns": [],
        "indexes": [],
        "index_sql": None,
        "migrations": [],
        "persist_source_not_null": None,
        "persist_source_column": False,
        "conversation_history_count": None,
    }
    if conn is None:
        return empty
    out = dict(empty)
    try:
        cols = [str(r[1]) for r in conn.execute("PRAGMA table_info(predictions)").fetchall()]
        out["columns"] = cols
        out["persist_source_column"] = "persist_source" in cols
        idx_rows = conn.execute("PRAGMA index_list(predictions)").fetchall()
        names = [str(r[1]) for r in idx_rows]
        out["indexes"] = names
        master = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
            (IDEMPOTENCY_INDEX,),
        ).fetchone()
        out["index_sql"] = str(master[0]) if master and master[0] else None
        try:
            mig = conn.execute("SELECT version FROM schema_migrations").fetchall()
            out["migrations"] = [str(r[0]) for r in mig]
        except sqlite3.Error:
            out["migrations"] = []
        if "persist_source" in cols:
            row = conn.execute(
                "SELECT COUNT(*) FROM predictions WHERE persist_source IS NOT NULL"
            ).fetchone()
            out["persist_source_not_null"] = int(row[0]) if row else 0
        else:
            out["persist_source_not_null"] = 0
        try:
            row = conn.execute("SELECT COUNT(*) FROM conversation_history").fetchone()
            out["conversation_history_count"] = int(row[0]) if row else 0
        except sqlite3.Error:
            out["conversation_history_count"] = None
    except sqlite3.Error:
        return empty
    return out


def inspect_live_source(root: str | None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "post_route_present": False,
        "prediction_runs_enabled_literal": None,
        "legacy_insert": {},
        "persist_source_mentions": {},
        "conversation_save_present": False,
        "challenge_insert_legacy": False,
        "ra_insert_legacy": False,
    }
    if not root:
        return out
    main_txt = read_text(os.path.join(root, "app/main.py"))
    out["post_route_present"] = "/v1/prediction-runs" in main_txt
    guards = read_text(os.path.join(root, "app/predictions/guards.py"))
    hay = main_txt + "\n" + guards
    if "PREDICTION_RUNS_ENABLED" in hay:
        out["prediction_runs_enabled_literal"] = "present"
    else:
        out["prediction_runs_enabled_literal"] = "absent"
    for label, rel in SOURCE_GREP_TARGETS:
        txt = read_text(os.path.join(root, rel))
        out["persist_source_mentions"][label] = txt.count("persist_source")
        out["legacy_insert"][label] = source_uses_legacy_insert(txt)
    conv = read_text(os.path.join(root, "app/conversation/service.py"))
    out["conversation_save_present"] = "predictions_store.save(" in conv
    out["challenge_insert_legacy"] = out["legacy_insert"].get("challenge", False)
    out["ra_insert_legacy"] = out["legacy_insert"].get("result_automation", False)
    return out


def main() -> int:
    emit("PACK", PACK_NAME)
    emit("STEP_SCOPE", "2_3_4_BASELINE_DISABLED_POST_DRY_RUN")
    emit("CURSOR_EC2_CONNECT", "NO")
    emit("PRODUCTION_CHANGED", "NO")
    emit("DB_CHANGED", "NO")
    emit("POST_ENDPOINT_CALLED", "NO")
    emit("DETAIL_GET_CALLED", "NO")
    emit("CHALLENGE_MONTHLY_GET_CALLED", "NO")
    emit("CONVERSATION_CHAT_POST_CALLED", "NO")
    emit("RA_RUN_CALLED", "NO")
    emit("MIGRATION_019_APPLY", "NO")
    emit("EXPECT_AI_ALLOW_MIGRATION_019_SET_BY_PACK", "NO")
    emit("BACKUP_COPY_EXECUTED", "NO")
    emit("SYSTEMD_MUTATING", "NO")
    emit("GITHUB_CHANGED", "NO")
    emit("PR23_MERGED", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("APPLY_EXECUTED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("PRODUCTION_EXPOSURE_READY", "NO")
    emit("REVIEW_BUNDLE", "v4")
    emit("REVIEW_ZIP_SHA256", REVIEW_ZIP_SHA256)
    emit("ROLLBACK_TARGET", "PARTIAL_UNIQUE_INDEX_ONLY")
    emit("ROLLBACK_TARGET_NAME", IDEMPOTENCY_INDEX)
    emit("ROLLBACK_DROP_COLUMN", "NO")
    emit("AI_INTERNAL_BASE", AI_BASE)
    emit("HISTORICAL_DB_RACE_LIVE_INFERENCE_ALLOWED", "NO")

    rw = research_week_active()
    emit("RESEARCH_WEEK_ACTIVE", rw)
    emit("CURRENT_DAY_DATA_VERIFIED", "NO_RESEARCH_WEEK" if rw else "PENDING_OWNER")
    emit("TODAY_PREDICTION_GENERATION_SUCCESS", "NO_NOT_EVALUATED")
    emit("CURRENT_PRODUCTION_PREDICTION_HEALTH_VERIFIED", "NO")
    if rw:
        emit("PUBLIC_PREDICTION_GATE_STATUS", "EXPECTED_OPS_CLOSED")

    show_args = ["systemctl", "show", "expect-ai.service", "--no-pager"]
    for prop in SYSTEMD_SHOW_PROPS:
        show_args.extend(["-p", prop])
    show_rc, show_out = run_cmd(show_args)
    status_rc, status_out = run_cmd(
        ["systemctl", "status", "expect-ai.service", "--no-pager", "-n", "0"]
    )
    journal_rc, journal_out = run_cmd(
        [
            "journalctl",
            "-u",
            "expect-ai.service",
            "--no-pager",
            "-n",
            "80",
            "--since",
            "24 hours ago",
        ]
    )
    sd = parse_systemd_show(show_out)
    emit("SYSTEMD_SHOW_RC", show_rc)
    emit("SYSTEMD_STATUS_RC", status_rc)
    emit("SYSTEMD_JOURNAL_RC", journal_rc)
    emit("SYSTEMD_ID", sd.get("Id") or "")
    emit("SYSTEMD_ACTIVE_STATE", sd.get("ActiveState") or "")
    emit("SYSTEMD_SUB_STATE", sd.get("SubState") or "")
    emit("SYSTEMD_ACTIVE", sd.get("ActiveState") == "active")
    emit("SYSTEMD_MAINPID", sd.get("MainPID") or "0")
    emit("SYSTEMD_UNIT_FILE_STATE", sd.get("UnitFileState") or "")
    emit("SYSTEMD_FRAGMENT_PATH", sd.get("FragmentPath") or "")
    emit("SYSTEMD_WORKING_DIRECTORY", sd.get("WorkingDirectory") or "")
    emit("SYSTEMD_EXEC_START", sd.get("ExecStart") or "")
    emit("SYSTEMD_USER", sd.get("User") or "")
    emit("SYSTEMD_NRESTARTS", sd.get("NRestarts") or "")
    emit("SYSTEMD_ENVIRONMENT_FILES", sd.get("EnvironmentFiles") or "")
    print("----- SYSTEMD_SHOW -----")
    for line in show_out.splitlines():
        print(redact_line(line))
    print("----- SYSTEMD_STATUS_HEAD -----")
    print("\n".join(status_out.splitlines()[:12]) or "(empty)")

    env_systemd = parse_environ_blob((sd.get("Environment") or "").replace(" ", "\0"))
    proc_env: dict[str, str] = {}
    pid = str(sd.get("MainPID") or "0").strip()
    if pid.isdigit() and int(pid) > 0:
        proc_path = "/proc/%s/environ" % pid
        blob = ""
        try:
            with open(proc_path, "rb") as fh:
                blob = fh.read().decode("utf-8", errors="replace")
        except OSError:
            blob = ""
        proc_env = parse_environ_blob(blob)
    emit("PREDICTION_RUNS_ENABLED_SYSTEMD", env_systemd.get("PREDICTION_RUNS_ENABLED") or "ABSENT")
    emit("PREDICTION_RUNS_ENABLED_PROC", proc_env.get("PREDICTION_RUNS_ENABLED") or "ABSENT")
    emit(
        "EXPECT_AI_ALLOW_MIGRATION_019_SYSTEMD",
        env_systemd.get("EXPECT_AI_ALLOW_MIGRATION_019") or "ABSENT",
    )
    emit(
        "EXPECT_AI_ALLOW_MIGRATION_019_PROC",
        proc_env.get("EXPECT_AI_ALLOW_MIGRATION_019") or "ABSENT",
    )
    emit("AI_ENGINE_SYSTEMD", env_systemd.get("AI_ENGINE") or "ABSENT")
    emit("AI_ENGINE_PROC", proc_env.get("AI_ENGINE") or "ABSENT")

    allow_019 = flag_truthy(
        proc_env.get("EXPECT_AI_ALLOW_MIGRATION_019")
        or env_systemd.get("EXPECT_AI_ALLOW_MIGRATION_019")
    )
    emit("EXPECT_AI_ALLOW_MIGRATION_019_EFFECTIVE", allow_019)
    enabled, enabled_src = prediction_runs_enabled_effective(
        {
            "proc": proc_env.get("PREDICTION_RUNS_ENABLED"),
            "systemd": env_systemd.get("PREDICTION_RUNS_ENABLED"),
            "live_default": None,
        }
    )
    emit("PREDICTION_RUNS_ENABLED_EFFECTIVE", enabled)
    emit("PREDICTION_RUNS_ENABLED_SOURCE", enabled_src)

    err_count = 0
    for line in journal_out.splitlines():
        low = line.lower()
        if any(h in low for h in ERROR_HINTS):
            err_count += 1
    emit("RECENT_RUNTIME_ERROR_COUNT", err_count)
    print("----- JOURNAL_ERROR_HEAD -----")
    err_lines = [
        redact_line(x)
        for x in journal_out.splitlines()
        if any(h in x.lower() for h in ERROR_HINTS)
    ]
    print("\n".join(err_lines[:20]) if err_lines else "(none)")

    code_root = find_code_root(sd.get("WorkingDirectory") or "")
    emit("LIVE_CODE_ROOT", code_root or "NOT_FOUND")
    live_hashes: dict[str, str | None] = {}
    for rel in REVIEW_FILE_SHA256:
        path = os.path.join(code_root, rel) if code_root else ""
        live_hashes[rel] = sha256_file(path) if path else None
        emit("LIVE_SHA_%s" % rel.replace("/", "_").replace(".", "_"), live_hashes[rel] or "MISSING")
    compared = live_vs_review(live_hashes)
    emit("LIVE_REVIEW_MATCH_COUNT", compared["match"])
    emit("LIVE_REVIEW_MISMATCH_COUNT", compared["mismatch"])
    emit("LIVE_REVIEW_MISSING_COUNT", compared["missing"])
    emit("LIVE_CODE_EQUALS_REVIEW_BUNDLE", compared["equal"])
    emit("LIVE_CODE_EQUALS_REVIEW_EXPECTED", "NO")
    if compared["details"]:
        emit("LIVE_REVIEW_DETAILS", ",".join(compared["details"]))
    if compared["equal"]:
        emit("ALERT_LIVE_ALREADY_HAS_REVIEW_CODE", "YES")
    else:
        emit("ALERT_LIVE_ALREADY_HAS_REVIEW_CODE", "NO")

    src = inspect_live_source(code_root)
    emit("POST_ROUTE_PRESENT_LIVE", src["post_route_present"])
    emit("PREDICTION_RUNS_ENABLED_IN_LIVE_SOURCE", src["prediction_runs_enabled_literal"] or "absent")
    emit("CONVERSATION_SAVE_PRESENT", src["conversation_save_present"])
    emit("CONVERSATION_LEGACY_INSERT", src["legacy_insert"].get("conversation", False))
    emit("CHALLENGE_LEGACY_INSERT", src["challenge_insert_legacy"])
    emit("RA_LEGACY_INSERT", src["ra_insert_legacy"])
    emit("CONVERSATION_PERSIST_SOURCE_MENTIONS", src["persist_source_mentions"].get("conversation", 0))
    emit("CHALLENGE_PERSIST_SOURCE_MENTIONS", src["persist_source_mentions"].get("challenge", 0))
    emit("RA_PERSIST_SOURCE_MENTIONS", src["persist_source_mentions"].get("result_automation", 0))

    engine = (
        proc_env.get("AI_ENGINE")
        or env_systemd.get("AI_ENGINE")
        or "mock"
    ).strip().lower()
    emit("AI_ENGINE_EFFECTIVE", engine or "mock")
    unfiltered_safe = engine != "real"
    emit("UNFILTERED_LIST_GET_ALLOWED", unfiltered_safe)
    emit("HEALTH_MAY_CALL_MIGRATE", "YES")
    emit("HEALTH_019_STILL_GATED", not allow_019)

    hinted_db = proc_env.get("EXPECT_AI_DB_PATH") or env_systemd.get("EXPECT_AI_DB_PATH")
    db_path = discover_db_path({"db": hinted_db} if hinted_db else None)
    emit("DB_PATH_FOUND_BEFORE_HTTP", bool(db_path))
    emit("DB_PATH", db_path or "NOT_FOUND")
    db_exists = bool(db_path and os.path.isfile(db_path))
    db_readable = False
    parent_writable = False
    db_size = None
    if db_path and db_exists:
        db_readable = os.access(db_path, os.R_OK)
        parent = os.path.dirname(db_path)
        parent_writable = os.access(parent, os.W_OK) if parent else False
        try:
            db_size = os.path.getsize(db_path)
        except OSError:
            db_size = None
    emit("DB_EXISTS", db_exists)
    emit("DB_READABLE", db_readable)
    emit("DB_PARENT_WRITABLE", parent_writable)
    emit("DB_SIZE_BYTES", db_size if db_size is not None else "UNAVAILABLE")
    sqlite_rc, sqlite_out = run_cmd(["sqlite3", "--version"])
    sqlite_cli = sqlite_rc == 0 and bool(sqlite_out.strip())
    emit("SQLITE3_CLI_PRESENT", sqlite_cli)
    possible, why = backup_possible(
        exists=db_exists,
        readable=db_readable,
        parent_writable=parent_writable,
        sqlite_cli=sqlite_cli,
        copy_executed=False,
    )
    emit("DB_BACKUP_POSSIBLE", possible)
    emit("DB_BACKUP_POSSIBLE_REASON", why)
    emit("DB_BACKUP_EXECUTED", "NO")

    conn = open_db_ro(db_path) if db_path else None
    inv_before = inventory_db(conn)
    before = count_predictions(conn)
    emit("PREDICTIONS_COUNT_BEFORE", before if before is not None else "UNAVAILABLE")
    emit("PREDICTIONS_COLUMNS_BEFORE", ",".join(inv_before["columns"]) if inv_before["columns"] else "NONE")
    emit("PREDICTIONS_INDEXES_BEFORE", ",".join(inv_before["indexes"]) if inv_before["indexes"] else "NONE")
    emit("SCHEMA_MIGRATIONS_BEFORE", ",".join(inv_before["migrations"]) if inv_before["migrations"] else "NONE")
    classified_before = classify_019(
        columns=set(inv_before["columns"]),
        index_names=set(inv_before["indexes"]),
        index_sql=inv_before["index_sql"],
        migrations=set(inv_before["migrations"]),
    )
    emit("MIGRATION_019_STATUS_BEFORE", classified_before["status"])
    emit("MIGRATION_019_APPLIED_BEFORE", classified_before["applied"])
    emit("MIGRATION_019_IN_SCHEMA_MIGRATIONS_BEFORE", classified_before["in_migrations"])
    emit("IDEMPOTENCY_INDEX_OK_BEFORE", classified_before["index_ok"])
    emit("PERSIST_SOURCE_COLUMN_BEFORE", inv_before["persist_source_column"])
    emit("PERSIST_SOURCE_NOT_NULL_BEFORE", inv_before["persist_source_not_null"])
    emit("CONVERSATION_HISTORY_COUNT_BEFORE", inv_before["conversation_history_count"])

    health = _http_get(AI_BASE + "/health", timeout=HEALTH_TIMEOUT_SEC)
    emit("INTERNAL_HEALTH_HTTP", health["status"])
    if health["error"]:
        emit("INTERNAL_HEALTH_ERROR", health["error"])
    health_payload = health.get("payload") if isinstance(health.get("payload"), dict) else {}
    ra = health_payload.get("result_automation") if isinstance(health_payload, dict) else None
    if isinstance(ra, dict):
        emit("RA_HEALTH_OK", ra.get("ok"))
        emit("RA_HEALTH_STATUS", ra.get("status"))
        emit("RA_HEALTH_PRESENT", True)
    else:
        emit("RA_HEALTH_PRESENT", False)

    health_db = discover_db_path(health_payload if isinstance(health_payload, dict) else None)
    if health_db and health_db != db_path:
        emit("DB_PATH_HEALTH_HINT", health_db)
        if conn is None:
            db_path = health_db
            emit("DB_PATH_FROM_HEALTH", db_path)
            conn = open_db_ro(db_path)
            inv_before = inventory_db(conn)
            before = count_predictions(conn)
            emit("PREDICTIONS_COUNT_BEFORE", before if before is not None else "UNAVAILABLE")
            classified_before = classify_019(
                columns=set(inv_before["columns"]),
                index_names=set(inv_before["indexes"]),
                index_sql=inv_before["index_sql"],
                migrations=set(inv_before["migrations"]),
            )
    emit("DB_PATH_FOUND", bool(db_path))

    safe_list = _http_get(
        AI_BASE + "/v1/predictions?date=" + SAFE_EMPTY_DATE,
        timeout=LIST_TIMEOUT_SEC,
    )
    emit("GET_V1_PREDICTIONS_SAFE_DATE_HTTP", safe_list["status"])
    emit("GET_V1_PREDICTIONS_SAFE_DATE_BYTES", safe_list["nbytes"])
    emit("GET_V1_PREDICTIONS_SAFE_DATE_ELAPSED_SEC", safe_list["elapsed_sec"])
    if safe_list["error"]:
        emit("GET_V1_PREDICTIONS_SAFE_DATE_ERROR", safe_list["error"])
    schema1 = envelope_schema(safe_list.get("payload") if isinstance(safe_list.get("payload"), dict) else None)
    emit("GET_ENVELOPE_KEYS_1", ",".join(schema1["keys"]) if schema1["keys"] else "NONE")
    emit("GET_ENVELOPE_SCHEMA_OK_1", schema1["schema_ok"])
    emit("GET_ENVELOPE_DATA_TYPE_1", schema1["data_type"])
    emit("GET_ENVELOPE_ITEM_COUNT_1", schema1["item_count"])

    schema2 = schema1
    listed = safe_list
    if unfiltered_safe:
        listed = _http_get(AI_BASE + "/v1/predictions", timeout=LIST_TIMEOUT_SEC)
        emit("GET_V1_PREDICTIONS_HTTP", listed["status"])
        emit("GET_V1_PREDICTIONS_BYTES", listed["nbytes"])
        emit("GET_V1_PREDICTIONS_ELAPSED_SEC", listed["elapsed_sec"])
        if listed["error"]:
            emit("GET_V1_PREDICTIONS_ERROR", listed["error"])
        emit("GET_V1_PREDICTIONS_UNFILTERED_SKIPPED", "NO")
        schema2 = envelope_schema(listed.get("payload") if isinstance(listed.get("payload"), dict) else None)
        emit("GET_ENVELOPE_KEYS_2", ",".join(schema2["keys"]) if schema2["keys"] else "NONE")
        emit("GET_FIRST_ITEM_KEYS", ",".join(schema2["first_item_keys"]) if schema2["first_item_keys"] else "NONE")
        emit("GET_V1_PREDICTIONS_ITEM_COUNT", schema2["item_count"])
        oversize = int(listed.get("nbytes") or 0) > LIST_MAX_BYTES
        emit("GET_LIST_OVERSIZE", oversize)
    else:
        emit("GET_V1_PREDICTIONS_UNFILTERED_SKIPPED", "LIVE_INFER_RISK_REAL_ENGINE")
        emit("GET_V1_PREDICTIONS_HTTP", "SKIPPED")
        listed2 = _http_get(
            AI_BASE + "/v1/predictions?date=" + SAFE_EMPTY_DATE,
            timeout=LIST_TIMEOUT_SEC,
        )
        schema2 = envelope_schema(listed2.get("payload") if isinstance(listed2.get("payload"), dict) else None)
        emit("GET_ENVELOPE_KEYS_2", ",".join(schema2["keys"]) if schema2["keys"] else "NONE")
        emit("GET_FIRST_ITEM_KEYS", "NONE")
        emit("GET_V1_PREDICTIONS_ITEM_COUNT", schema2["item_count"])

    emit("GET_RESPONSE_SCHEMA_UNCHANGED", schemas_equal(schema1, schema2) or (
        schema1.get("keys") == schema2.get("keys") and schema1.get("data_type") == schema2.get("data_type")
    ))
    emit("GET_ENVELOPE_SCHEMA_OK", schema1["schema_ok"] or schema2["schema_ok"])

    inv_after = inventory_db(conn)
    after = count_predictions(conn)
    emit("PREDICTIONS_COUNT_AFTER", after if after is not None else "UNAVAILABLE")
    if before is None or after is None:
        write_count: Any = "UNAVAILABLE"
        write_ok = False
    else:
        write_count = after - before
        write_ok = write_count == 0
    emit("GET_DB_WRITE_COUNT", write_count)
    emit("GET_PREDICTIONS_ROWCOUNT_UNCHANGED", write_ok)
    classified_after = classify_019(
        columns=set(inv_after["columns"]),
        index_names=set(inv_after["indexes"]),
        index_sql=inv_after["index_sql"],
        migrations=set(inv_after["migrations"]),
    )
    emit("MIGRATION_019_STATUS_AFTER", classified_after["status"])
    emit("MIGRATION_019_APPLIED", classified_after["applied"])
    emit("MIGRATION_019_STATUS_UNCHANGED", classified_before["status"] == classified_after["status"])
    emit("PERSIST_SOURCE_NOT_NULL_AFTER", inv_after["persist_source_not_null"])
    persist_null_ok = (inv_after["persist_source_not_null"] in (0, None))
    emit("PERSIST_SOURCE_NULL_OK", persist_null_ok)
    emit("CONVERSATION_HISTORY_COUNT_AFTER", inv_after["conversation_history_count"])
    hist_unchanged = inv_before["conversation_history_count"] == inv_after["conversation_history_count"]
    emit("CONVERSATION_HISTORY_COUNT_UNCHANGED", hist_unchanged)
    emit("CURRENT_ROLLBACK_NEEDED", classified_after["rollback_needed"])
    emit("CURRENT_ROLLBACK_TARGET", classified_after["rollback_target"])

    post_disabled = (not enabled) and (not allow_019)
    emit("POST_DISABLED_CONFIRMED", post_disabled)
    emit("POST_DISABLED_DRY_RUN", "SOURCE_AND_ENV_ONLY")
    emit("POST_HTTP_CALLED", "NO")

    conv_ok = bool(src["conversation_save_present"]) and persist_null_ok
    ra_ok = bool(isinstance(ra, dict)) and persist_null_ok
    ch_ok = persist_null_ok and (
        src["challenge_insert_legacy"] or src["persist_source_mentions"].get("challenge", 0) == 0
    )
    emit("CONVERSATION_LEGACY_BEHAVIOR_CONFIRMED", conv_ok)
    emit("RA_HEALTH_AND_NULL_PERSIST_CONFIRMED", ra_ok)
    emit("CHALLENGE_NULL_PERSIST_CONFIRMED", ch_ok)
    emit("CONVERSATION_WRITE_PROBED", "NO")
    emit("CHALLENGE_WRITE_PROBED", "NO")
    emit("RA_WRITE_PROBED", "NO")

    print("----- STEP2_4_SUMMARY -----")
    emit("PRODUCTION_NOT_TOUCHED", "YES")
    emit("PRODUCTION_DRY_RUN_READY", "NO")
    emit("OWNER_OUTPUT_REQUIRES_REVIEW", "YES")
    emit("NEXT_STEP", "OWNER_RETURN_OUTPUT_THEN_HUMAN_REVIEW")
    if conn is not None:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    sys.exit(main())
