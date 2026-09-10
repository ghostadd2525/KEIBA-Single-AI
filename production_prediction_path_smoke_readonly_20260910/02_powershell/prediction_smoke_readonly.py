#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production Single-AI prediction-path smoke (Owner / EC2, read-only).

GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/v1/predictions
GET http://127.0.0.1:8000/v1/predictions/{race_id}

Never POST. Never call /v1/prediction-runs.
SQLite: SELECT / PRAGMA only, mode=ro.
systemd: show / status / journalctl read-only.
Does not print secrets, horse names, or env file contents.
Does not invent race_id.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

PACK_NAME = "production_prediction_path_smoke_readonly_20260910"
AI_BASE = "http://127.0.0.1:8000"
ALLOWED_MARKS = frozenset({"honmei", "taikou", "ana", "chuuken", "none"})
MOCK_ENGINE_SOURCES = frozenset(
    {
        "mock",
        "bff_mock",
        "mock_fallback",
        "pi_catalog_projection",
        "prediction_unavailable",
    }
)
REAL_ENGINE_SOURCES = frozenset({"real_ai", "real"})
ERROR_HINTS = (
    "traceback",
    "get error",
    "predictionadapter",
    "ai_platform",
    "platform_missing",
    "internal_error",
    "exception",
)
DB_CANDIDATES = (
    "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db",
    "/opt/expect-ai/current/services/win5-ai/var/expect_ai.db",
    "/var/lib/expect-ai/expect_ai.db",
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
    # single-line only
    print("%s=%s" % (key, text.replace("\n", " ").replace("\r", "")))


def _http_get(url: str, timeout: float = 45.0) -> tuple[int, dict[str, Any] | None, str]:
    headers = {"Accept": "application/json"}
    key = (os.environ.get("AI_API_KEY") or "").strip()
    if key:
        headers["X-AI-Key"] = key
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8", errors="replace")
            status = int(getattr(res, "status", 200) or 200)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        status = int(exc.code)
    except Exception as exc:
        return 0, None, "%s: %s" % (type(exc).__name__, exc)
    payload = None
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = None
    return status, payload, raw[:240]


def extract_data(payload: dict[str, Any] | None) -> Any:
    if not payload:
        return None
    if payload.get("data") is not None:
        return payload.get("data")
    return payload


def extract_meta(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload or not isinstance(payload, dict):
        return {}
    meta = payload.get("meta")
    return meta if isinstance(meta, dict) else {}


def list_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        rows = data.get("items")
        if isinstance(rows, list):
            return [x for x in rows if isinstance(x, dict)]
    return []


def bundle_runners(bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not bundle or not isinstance(bundle, dict):
        return []
    ev = bundle.get("evaluation") or {}
    runners = ev.get("runners") if isinstance(ev, dict) else None
    if not isinstance(runners, list):
        runners = bundle.get("runners")
    if not isinstance(runners, list):
        return []
    return [r for r in runners if isinstance(r, dict)]


def pick_existing_race_id(
    bundles: list[dict[str, Any]],
    db_ids: list[str],
) -> tuple[str | None, str]:
    """Pick an existing race_id only. Never synthesize."""
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    today_iso = now.strftime("%Y-%m-%d")
    today_compact = now.strftime("%Y%m%d")
    today = None
    nonempty: list[str] = []
    any_ids: list[str] = []
    for b in bundles:
        rid = str(b.get("race_id") or "").strip()
        if not rid:
            info = b.get("race_info") if isinstance(b.get("race_info"), dict) else {}
            rid = str((info or {}).get("race_id") or "").strip()
        if not rid:
            continue
        any_ids.append(rid)
        if bundle_runners(b):
            nonempty.append(rid)
            info = b.get("race_info") if isinstance(b.get("race_info"), dict) else {}
            date = str((info or {}).get("date") or "")
            if date in (today_iso, today_compact):
                today = rid
    if today:
        return today, "api_list_today_nonempty"
    if nonempty:
        return nonempty[0], "api_list_nonempty_first"
    if any_ids:
        return any_ids[0], "api_list_first"
    if db_ids:
        return db_ids[0], "readonly_db_existing"
    return None, "none_found"


def validate_bundle(
    bundle: dict[str, Any] | None,
    requested_race_id: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = meta or {}
    out: dict[str, Any] = {
        "BUNDLE_SCHEMA_VALID": False,
        "RACE_ID_MATCH": False,
        "RUNNER_COUNT": 0,
        "HORSE_NUMBER_UNIQUE": False,
        "WIN_PROB_VALID": False,
        "MODEL_RANK_VALID": False,
        "MARK_VALID": False,
        "REAL_AI_CONFIRMED": False,
        "FALLBACK_USED": False,
        "ENGINE_SOURCE": None,
        "FALLBACK_REASON": None,
        "MODEL_VERSION": None,
        "SCHEMA_ERRORS": [],
    }
    errors: list[str] = []
    if not isinstance(bundle, dict):
        errors.append("bundle_not_object")
        out["SCHEMA_ERRORS"] = errors
        return out

    schema = str(bundle.get("schema_version") or "")
    if schema != "single-prediction-bundle/2.0":
        errors.append("schema_version")
    for key in (
        "race_id",
        "race_info",
        "evaluation",
        "ai_confidence",
        "explain",
        "betting_recommendations",
    ):
        if key not in bundle:
            errors.append("missing_%s" % key)

    race_id = str(bundle.get("race_id") or "").strip()
    info = bundle.get("race_info") if isinstance(bundle.get("race_info"), dict) else {}
    info_id = str((info or {}).get("race_id") or "").strip()
    out["RACE_ID_MATCH"] = bool(race_id) and race_id == str(requested_race_id).strip()
    if info_id and info_id != race_id:
        errors.append("race_info_race_id_mismatch")
        out["RACE_ID_MATCH"] = False

    if not isinstance(bundle.get("evaluation"), dict):
        errors.append("evaluation_not_object")
    if not isinstance(bundle.get("ai_confidence"), dict):
        errors.append("ai_confidence_not_object")
    if not isinstance(bundle.get("explain"), dict):
        errors.append("explain_not_object")
    if not isinstance(bundle.get("betting_recommendations"), dict):
        errors.append("betting_recommendations_not_object")

    runners = bundle_runners(bundle)
    out["RUNNER_COUNT"] = len(runners)
    if not runners:
        errors.append("runners_empty")

    nums: list[int] = []
    ranks: list[int] = []
    win_ok = True
    mark_ok = True
    rank_ok = True
    pairs: list[tuple[float, int]] = []
    for r in runners:
        hn = r.get("horse_number")
        if not isinstance(hn, int) or hn < 1:
            win_ok = False
            errors.append("horse_number_invalid")
            continue
        nums.append(hn)
        wp = r.get("win_prob")
        if not isinstance(wp, (int, float)) or isinstance(wp, bool):
            win_ok = False
        elif not (0.0 <= float(wp) <= 1.0):
            win_ok = False
        mark = r.get("mark")
        if mark is not None and str(mark) not in ALLOWED_MARKS:
            mark_ok = False
        mr = r.get("model_rank")
        if mr is not None:
            if not isinstance(mr, int) or mr < 1:
                rank_ok = False
            else:
                ranks.append(mr)
                if isinstance(wp, (int, float)) and not isinstance(wp, bool):
                    pairs.append((float(wp), mr))

    out["HORSE_NUMBER_UNIQUE"] = bool(nums) and len(nums) == len(set(nums))
    if nums and not out["HORSE_NUMBER_UNIQUE"]:
        errors.append("horse_number_duplicate")
    out["WIN_PROB_VALID"] = bool(runners) and win_ok
    out["MARK_VALID"] = bool(runners) and mark_ok

    if ranks and len(ranks) != len(set(ranks)):
        # existing contract allows null ranks; present ranks must be unique
        rank_ok = False
        errors.append("model_rank_duplicate")
    for wp, mr in pairs:
        for wp2, mr2 in pairs:
            if wp > wp2 and mr > mr2:
                rank_ok = False
                errors.append("win_prob_rank_inversion")
                break
        if not rank_ok:
            break
    out["MODEL_RANK_VALID"] = bool(runners) and rank_ok

    engine = str(
        meta.get("engine_source")
        or bundle.get("engine_source")
        or ""
    ).strip()
    reason = meta.get("fallback_reason")
    if reason is None:
        reason = bundle.get("fallback_reason")
    model_version = meta.get("model_version")
    if model_version is None:
        model_version = bundle.get("model_version")
    out["ENGINE_SOURCE"] = engine or None
    out["FALLBACK_REASON"] = reason if reason not in (None, "") else None
    out["MODEL_VERSION"] = model_version if model_version not in (None, "") else None

    dummy = "dummy-model" in str(model_version or "").lower()
    fallback = bool(out["FALLBACK_REASON"]) or engine in MOCK_ENGINE_SOURCES
    out["FALLBACK_USED"] = fallback
    out["REAL_AI_CONFIRMED"] = (engine in REAL_ENGINE_SOURCES) and (not fallback) and (not dummy)

    out["BUNDLE_SCHEMA_VALID"] = (
        not errors
        and out["RACE_ID_MATCH"]
        and out["RUNNER_COUNT"] > 0
        and out["HORSE_NUMBER_UNIQUE"]
        and out["WIN_PROB_VALID"]
        and out["MODEL_RANK_VALID"]
        and out["MARK_VALID"]
    )
    out["SCHEMA_ERRORS"] = errors
    return out


def open_db_ro(path: str) -> sqlite3.Connection | None:
    if not path or not os.path.isfile(path):
        return None
    uri = "file:%s?mode=ro" % path
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    conn.execute("PRAGMA query_only = ON")
    return conn


def discover_db_path(health_payload: dict[str, Any] | None) -> str | None:
    data = extract_data(health_payload)
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


def existing_race_ids_from_db(conn: sqlite3.Connection | None) -> list[str]:
    if conn is None:
        return []
    ids: list[str] = []
    queries = (
        "SELECT race_id FROM predictions WHERE race_id IS NOT NULL AND TRIM(race_id) != '' "
        "ORDER BY created_at DESC LIMIT 20",
        "SELECT race_id FROM races WHERE race_id IS NOT NULL AND TRIM(race_id) != '' LIMIT 20",
    )
    for sql in queries:
        try:
            for row in conn.execute(sql).fetchall():
                rid = str(row[0] or "").strip()
                if rid and rid not in ids:
                    ids.append(rid)
        except sqlite3.Error:
            continue
    return ids


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


def systemd_readonly() -> dict[str, Any]:
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
            "120",
            "--since",
            "24 hours ago",
        ]
    )
    active = False
    for line in show_out.splitlines():
        if line.startswith("ActiveState="):
            active = line.split("=", 1)[1].strip() == "active"
    err_count = 0
    adapter_hits = 0
    for line in journal_out.splitlines():
        low = line.lower()
        if any(h in low for h in ERROR_HINTS):
            err_count += 1
        if "predictionadapter" in low or "ai_platform" in low:
            adapter_hits += 1
    return {
        "show_rc": show_rc,
        "status_rc": status_rc,
        "journal_rc": journal_rc,
        "active": active,
        "error_count": err_count,
        "adapter_hits": adapter_hits,
        "show_out": show_out.strip(),
        "status_head": "\n".join(status_out.splitlines()[:12]),
    }


def main() -> int:
    emit("PACK", PACK_NAME)
    emit("CURSOR_EC2_CONNECT", "NO")
    emit("PRODUCTION_CHANGED", "NO")
    emit("DB_CHANGED", "NO")
    emit("POST_ENDPOINT_CALLED", "NO")
    emit("CONVERSATION_TOUCHED", "NO")
    emit("RESULT_AUTOMATION_TOUCHED", "NO")
    emit("SYSTEMD_MUTATING", "NO")
    emit("AI_INTERNAL_BASE", AI_BASE)

    health_status, health_payload, health_err = _http_get(AI_BASE + "/health", timeout=8.0)
    emit("INTERNAL_HEALTH_HTTP", health_status)
    if health_status != 200:
        emit("INTERNAL_HEALTH_ERROR", health_err)

    db_path = discover_db_path(health_payload)
    emit("DB_PATH_FOUND", "YES" if db_path else "NO")
    conn = open_db_ro(db_path) if db_path else None
    before = count_predictions(conn)
    emit("PREDICTIONS_COUNT_BEFORE", before if before is not None else "UNAVAILABLE")

    list_status, list_payload, list_err = _http_get(AI_BASE + "/v1/predictions", timeout=45.0)
    emit("GET_V1_PREDICTIONS_HTTP", list_status)
    if list_status != 200:
        emit("GET_V1_PREDICTIONS_ERROR", list_err)

    list_data = extract_data(list_payload)
    bundles = list_items(list_data)
    emit("GET_V1_PREDICTIONS_ITEM_COUNT", len(bundles))
    list_meta = extract_meta(list_payload)
    db_ids = existing_race_ids_from_db(conn)
    race_id, pick_source = pick_existing_race_id(bundles, db_ids)
    emit("RACE_ID_PICK_SOURCE", pick_source)
    if race_id:
        emit("RACE_ID", race_id)
    else:
        emit("RACE_ID", "NONE")

    get_status = 0
    get_payload = None
    get_err = ""
    if race_id:
        get_status, get_payload, get_err = _http_get(
            AI_BASE + "/v1/predictions/" + urllib.parse.quote(race_id, safe=""),
            timeout=45.0,
        )
    emit("GET_V1_PREDICTIONS_ID_HTTP", get_status if race_id else "SKIPPED_NO_RACE")
    if race_id and get_status != 200:
        emit("GET_V1_PREDICTIONS_ID_ERROR", get_err)

    after = count_predictions(conn)
    emit("PREDICTIONS_COUNT_AFTER", after if after is not None else "UNAVAILABLE")
    if before is None or after is None:
        write_count = "UNAVAILABLE"
        write_ok = False
    else:
        write_count = after - before
        write_ok = write_count == 0
    emit("GET_DB_WRITE_COUNT", write_count)

    get_data = extract_data(get_payload)
    get_meta = extract_meta(get_payload)
    if not get_meta and isinstance(list_meta.get("items"), list) and race_id:
        for it in list_meta["items"]:
            if isinstance(it, dict) and str(it.get("race_id") or "") == race_id:
                get_meta = it
                break
    checked = validate_bundle(get_data if isinstance(get_data, dict) else None, race_id or "", get_meta)
    emit("BUNDLE_SCHEMA_VALID", checked["BUNDLE_SCHEMA_VALID"])
    emit("RACE_ID_MATCH", checked["RACE_ID_MATCH"])
    emit("RUNNER_COUNT", checked["RUNNER_COUNT"])
    emit("HORSE_NUMBER_UNIQUE", checked["HORSE_NUMBER_UNIQUE"])
    emit("WIN_PROB_VALID", checked["WIN_PROB_VALID"])
    emit("MODEL_RANK_VALID", checked["MODEL_RANK_VALID"])
    emit("MARK_VALID", checked["MARK_VALID"])
    emit("REAL_AI_CONFIRMED", checked["REAL_AI_CONFIRMED"])
    emit("FALLBACK_USED", checked["FALLBACK_USED"])
    emit("ENGINE_SOURCE", checked["ENGINE_SOURCE"])
    emit("FALLBACK_REASON", checked["FALLBACK_REASON"])
    emit("MODEL_VERSION", checked["MODEL_VERSION"])
    if checked["SCHEMA_ERRORS"]:
        emit("SCHEMA_ERRORS", ",".join(checked["SCHEMA_ERRORS"][:12]))

    sd = systemd_readonly()
    emit("SYSTEMD_ACTIVE", sd["active"])
    emit("SYSTEMD_SHOW_RC", sd["show_rc"])
    emit("SYSTEMD_STATUS_RC", sd["status_rc"])
    emit("SYSTEMD_JOURNAL_RC", sd["journal_rc"])
    emit("RECENT_RUNTIME_ERROR_COUNT", sd["error_count"])
    emit("ADAPTER_OR_PLATFORM_JOURNAL_HITS", sd["adapter_hits"])
    print("----- SYSTEMD_SHOW -----")
    print(sd["show_out"] or "(empty)")
    print("----- SYSTEMD_STATUS_HEAD -----")
    print(sd["status_head"] or "(empty)")

    list_ok = list_status == 200
    get_ok = bool(race_id) and get_status == 200
    emit("CURRENT_PRODUCTION_PREDICTION_HTTP_OK", list_ok and get_ok)
    health_verified = (
        list_ok
        and get_ok
        and checked["BUNDLE_SCHEMA_VALID"]
        and checked["REAL_AI_CONFIRMED"]
        and (not checked["FALLBACK_USED"])
        and write_ok
        and bool(sd["active"])
    )
    emit("CURRENT_PRODUCTION_PREDICTION_HEALTH_VERIFIED", health_verified)
    if conn is not None:
        conn.close()
    return 0 if health_verified else 1


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    sys.exit(main())
