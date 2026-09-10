#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production Single-AI prediction-path smoke v2 (Owner / EC2, read-only).

GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/v1/predictions
GET http://127.0.0.1:8000/v1/predictions/{race_id}
  — race_id は同じ実行の list GET が返したものだけ。

一覧が空なら DETAIL_GET_SKIPPED=NO_CURRENT_RACE。
read-only DB の過去 race_id で live detail 推論しない。
推測 race_id を使わない。
Never call /v1/prediction-runs.
POST /v1/prediction-runs は呼ばない。

一覧 GET が 5xx / timeout / 過大負荷なら detail へ進まない。
SQLite: SELECT COUNT / PRAGMA only, mode=ro。race_id 選定には使わない。
systemd: show / status / journalctl read-only。
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

PACK_NAME = "production_prediction_path_smoke_readonly_v2_20260910"
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
LIST_TIMEOUT_SEC = 60.0
DETAIL_TIMEOUT_SEC = 45.0
LIST_MAX_BYTES = 2000000
LIST_MAX_ELAPSED_SEC = 90.0
LIST_OVERLOAD_ITEM_COUNT = 80


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
    }
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8", errors="replace")
            out["status"] = int(getattr(res, "status", 200) or 200)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        out["status"] = int(exc.code)
        out["error"] = "HTTPError:%s" % exc.code
    except TimeoutError as exc:
        out["timeout"] = True
        out["error"] = "TimeoutError: %s" % exc
        raw = ""
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


def race_id_of(bundle: dict[str, Any] | None) -> str:
    if not bundle:
        return ""
    rid = str(bundle.get("race_id") or "").strip()
    if rid:
        return rid
    info = bundle.get("race_info") if isinstance(bundle.get("race_info"), dict) else {}
    return str((info or {}).get("race_id") or "").strip()


def list_race_ids(bundles: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for b in bundles:
        rid = race_id_of(b)
        if rid and rid not in ids:
            ids.append(rid)
    return ids


def pick_detail_race_id(bundles: list[dict[str, Any]]) -> tuple[str | None, str]:
    """Same-run list GET ids only. Never DB. Never synthesize."""
    ids = list_race_ids(bundles)
    if not ids:
        return None, "NO_CURRENT_RACE"
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    today_iso = now.strftime("%Y-%m-%d")
    today_compact = now.strftime("%Y%m%d")
    today = None
    nonempty: list[str] = []
    for b in bundles:
        rid = race_id_of(b)
        if not rid or rid not in ids:
            continue
        if bundle_runners(b):
            nonempty.append(rid)
            info = b.get("race_info") if isinstance(b.get("race_info"), dict) else {}
            date = str((info or {}).get("date") or "")
            if date in (today_iso, today_compact):
                today = rid
    if today:
        return today, "current_list_today_nonempty"
    if nonempty:
        return nonempty[0], "current_list_nonempty"
    return ids[0], "current_list_first"


def list_should_stop(result: dict[str, Any], item_count: int) -> tuple[bool, str]:
    if result.get("timeout"):
        return True, "TIMEOUT"
    status = int(result.get("status") or 0)
    if status == 0:
        return True, "UNREACHABLE"
    if status >= 500:
        return True, "INTERNAL_ERROR"
    payload = result.get("payload")
    if isinstance(payload, dict) and payload.get("ok") is False:
        err = payload.get("error") or {}
        code = ""
        if isinstance(err, dict):
            code = str(err.get("code") or "")
        if code in ("INTERNAL_ERROR", "AI_ERROR") or status >= 500:
            return True, "INTERNAL_ERROR"
    if int(result.get("nbytes") or 0) > LIST_MAX_BYTES:
        return True, "OVERSIZE"
    if float(result.get("elapsed_sec") or 0) > LIST_MAX_ELAPSED_SEC:
        return True, "OVERLOAD_ELAPSED"
    if item_count > LIST_OVERLOAD_ITEM_COUNT:
        return True, "OVERLOAD_ITEM_COUNT"
    if status != 200:
        return True, "LIST_HTTP_%s" % status
    return False, ""


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

    engine = str(meta.get("engine_source") or bundle.get("engine_source") or "").strip()
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


def _file_sig(path: str) -> tuple[int, int, int] | None:
    try:
        st = os.stat(path, follow_symlinks=False)
    except OSError:
        return None
    if not os.path.isfile(path):
        return None
    return (int(st.st_size), int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))), int(st.st_ino))


def watch_paths(db_path: str | None) -> list[str]:
    roots: list[str] = []
    if db_path:
        roots.append(os.path.dirname(db_path))
        roots.append(db_path)
        roots.append(db_path + "-wal")
        roots.append(db_path + "-shm")
    roots.extend(
        [
            "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var",
            "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/logs",
            "/opt/expect-ai/current/services/win5-ai/var",
            "/opt/expect-ai/current/services/win5-ai/var/logs",
            "/var/lib/expect-ai",
            "/tmp/expect-ai",
        ]
    )
    paths: list[str] = []
    seen: set[str] = set()

    def add(p: str) -> None:
        if p and p not in seen:
            seen.add(p)
            paths.append(p)

    for root in roots:
        add(root)
        if not os.path.isdir(root):
            continue
        try:
            names = os.listdir(root)
        except OSError:
            continue
        for name in names:
            if name.startswith("."):
                continue
            child = os.path.join(root, name)
            add(child)
            if name == "logs" and os.path.isdir(child):
                try:
                    for inner in os.listdir(child):
                        add(os.path.join(child, inner))
                except OSError:
                    continue
            if name == "cache" and os.path.isdir(child):
                try:
                    for inner in os.listdir(child):
                        add(os.path.join(child, inner))
                except OSError:
                    continue
    return paths


def snapshot_files(db_path: str | None) -> dict[str, tuple[int, int, int]]:
    out: dict[str, tuple[int, int, int]] = {}
    for p in watch_paths(db_path):
        sig = _file_sig(p)
        if sig is not None:
            out[p] = sig
    return out


def diff_snapshots(
    before: dict[str, tuple[int, int, int]],
    after: dict[str, tuple[int, int, int]],
) -> dict[str, Any]:
    new_files = sorted(set(after) - set(before))
    changed = sorted(p for p in after if p in before and after[p] != before[p])
    return {
        "new_count": len(new_files),
        "changed_count": len(changed),
        "new_names": [os.path.basename(p) for p in new_files[:12]],
        "changed_names": [os.path.basename(p) for p in changed[:12]],
    }


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


def empty_check() -> dict[str, Any]:
    return {
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
        "SCHEMA_ERRORS": ["detail_skipped"],
    }


def main() -> int:
    emit("PACK", PACK_NAME)
    emit("PACK_SUPERSEDES", "production_prediction_path_smoke_readonly_20260910")
    emit("V1_DO_NOT_RUN", "YES")
    emit("CURSOR_EC2_CONNECT", "NO")
    emit("PRODUCTION_CHANGED", "NO")
    emit("DB_CHANGED", "NO")
    emit("POST_ENDPOINT_CALLED", "NO")
    emit("CONVERSATION_TOUCHED", "NO")
    emit("RESULT_AUTOMATION_TOUCHED", "NO")
    emit("SYSTEMD_MUTATING", "NO")
    emit("HISTORICAL_DB_RACE_LIVE_INFERENCE_ALLOWED", "NO")
    emit("DETAIL_GET_ONLY_FROM_CURRENT_LIST", "YES")
    emit("OWNER_PACK_SAFE_RACE_SELECTION", "YES")
    emit("AI_INTERNAL_BASE", AI_BASE)

    health = _http_get(AI_BASE + "/health", timeout=8.0)
    emit("INTERNAL_HEALTH_HTTP", health["status"])
    if health["status"] != 200:
        emit("INTERNAL_HEALTH_ERROR", health["error"] or health["raw_head"])

    db_path = discover_db_path(health.get("payload"))
    emit("DB_PATH_FOUND", "YES" if db_path else "NO")
    conn = open_db_ro(db_path) if db_path else None
    snap_before = snapshot_files(db_path)
    before = count_predictions(conn)
    emit("PREDICTIONS_COUNT_BEFORE", before if before is not None else "UNAVAILABLE")

    listed = _http_get(AI_BASE + "/v1/predictions", timeout=LIST_TIMEOUT_SEC)
    emit("GET_V1_PREDICTIONS_HTTP", listed["status"])
    emit("GET_V1_PREDICTIONS_ELAPSED_SEC", listed["elapsed_sec"])
    emit("GET_V1_PREDICTIONS_BYTES", listed["nbytes"])
    if listed["error"]:
        emit("GET_V1_PREDICTIONS_ERROR", listed["error"])

    list_data = extract_data(listed.get("payload"))
    bundles = list_items(list_data) if listed["status"] == 200 else []
    emit("GET_V1_PREDICTIONS_ITEM_COUNT", len(bundles))
    list_meta = extract_meta(listed.get("payload")) if listed["status"] == 200 else {}

    stop, stop_reason = list_should_stop(listed, len(bundles) if listed["status"] == 200 else 0)
    emit("LIST_STOPPED", stop)
    if stop:
        emit("LIST_STOP_REASON", stop_reason)
        emit("DETAIL_GET_SKIPPED", stop_reason)
        emit("RACE_ID", "NONE")
        emit("RACE_ID_PICK_SOURCE", "stopped_before_detail")
        race_id = None
        detail = None
    else:
        race_id, pick_source = pick_detail_race_id(bundles)
        emit("RACE_ID_PICK_SOURCE", pick_source)
        if not race_id:
            emit("RACE_ID", "NONE")
            emit("DETAIL_GET_SKIPPED", "NO_CURRENT_RACE")
            detail = None
        else:
            emit("RACE_ID", race_id)
            emit("DETAIL_GET_SKIPPED", "NO")
            detail = _http_get(
                AI_BASE + "/v1/predictions/" + urllib.parse.quote(race_id, safe=""),
                timeout=DETAIL_TIMEOUT_SEC,
            )
            emit("GET_V1_PREDICTIONS_ID_HTTP", detail["status"])
            emit("GET_V1_PREDICTIONS_ID_ELAPSED_SEC", detail["elapsed_sec"])
            if detail["error"]:
                emit("GET_V1_PREDICTIONS_ID_ERROR", detail["error"])

    after = count_predictions(conn)
    snap_after = snapshot_files(db_path)
    file_diff = diff_snapshots(snap_before, snap_after)
    emit("PREDICTIONS_COUNT_AFTER", after if after is not None else "UNAVAILABLE")
    if before is None or after is None:
        write_count: Any = "UNAVAILABLE"
        write_ok = False
    else:
        write_count = after - before
        write_ok = write_count == 0
    emit("GET_DB_WRITE_COUNT", write_count)
    emit("GET_NEW_FILE_COUNT", file_diff["new_count"])
    emit("GET_FILE_CHANGED_COUNT", file_diff["changed_count"])
    emit("GET_CACHE_OR_FILE_WRITE", file_diff["new_count"] > 0 or file_diff["changed_count"] > 0)
    if file_diff["new_names"]:
        emit("GET_NEW_FILE_BASENAMES", ",".join(file_diff["new_names"]))
    if file_diff["changed_names"]:
        emit("GET_CHANGED_FILE_BASENAMES", ",".join(file_diff["changed_names"]))

    checked = empty_check()
    if detail and race_id:
        get_data = extract_data(detail.get("payload"))
        get_meta = extract_meta(detail.get("payload"))
        if not get_meta and isinstance(list_meta.get("items"), list):
            for it in list_meta["items"]:
                if isinstance(it, dict) and str(it.get("race_id") or "") == race_id:
                    get_meta = it
                    break
        checked = validate_bundle(
            get_data if isinstance(get_data, dict) else None,
            race_id,
            get_meta,
        )

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

    detail_ok = bool(detail) and int(detail.get("status") or 0) == 200
    emit("CURRENT_PRODUCTION_PREDICTION_HTTP_OK", "N_A_INTERNAL_ONLY" if detail_ok else "N_A_NO_DETAIL")
    health_verified = (
        (not stop)
        and detail_ok
        and checked["BUNDLE_SCHEMA_VALID"]
        and checked["REAL_AI_CONFIRMED"]
        and (not checked["FALLBACK_USED"])
        and write_ok
        and bool(sd["active"])
        and file_diff["new_count"] == 0
        and int(write_count) == 0
        if isinstance(write_count, int)
        else False
    )
    emit("CURRENT_PRODUCTION_PREDICTION_HEALTH_VERIFIED", health_verified)
    if conn is not None:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    sys.exit(main())
