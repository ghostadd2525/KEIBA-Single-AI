#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single SSH stdin payload: GET-only response size measurement. No APPLY."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import sqlite3
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

PACK = "production_022_readonly_response_size_measure_20260911"
CANONICAL_SOURCE = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db"
BACKUP_PATH = "/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260911T175303Z/expect_ai.db"
BACKUP_SHA256 = "f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d"
INVENTORY_SOURCE_DEV = 66305
INVENTORY_SOURCE_INO = 349935
INVENTORY_SOURCE_SIZE = 105783296
BACKUP_DEV = 66305
BACKUP_INO = 287106
PERSIST_022 = "022_prediction_run_idempotency"
RACE_INDEX = "idx_predictions_race"
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
APPROVAL = "OWNER_PRODUCTION_022_MEASURE_APPROVED"
CLASS_INTERNAL_HEALTH = "INTERNAL_HEALTH"
CLASS_INTERNAL_LIST = "INTERNAL_LIST"
CLASS_INTERNAL_DETAIL = "INTERNAL_DETAIL"
CLASS_PUBLIC_JSON = "PUBLIC_JSON"
CLASS_PUBLIC_HTML = "PUBLIC_HTML"
# Measurement windows, not future APPLY limits.
# Inventory DB size is 105783296. 8 MiB list cap is ~12.6x smaller.
# 262144 is not reused as the internal list window.
MEASURE_INTERNAL_HEALTH_MAX_BYTES = 65536
MEASURE_INTERNAL_LIST_MAX_BYTES = 8388608
MEASURE_INTERNAL_DETAIL_MAX_BYTES = 2097152
MEASURE_PUBLIC_JSON_MAX_BYTES = 262144
MEASURE_PUBLIC_HTML_MAX_BYTES = 524288
MIN_DB_TO_LIST_CAP_RATIO = 8
REMOTE_HARD_DEADLINE_S = 90
WRAPPER_TIMEOUT_MS = 180000
DRAIN_WAIT_MS = 20000
KILL_DRAIN_WAIT_MS = 8000
SAFETY_BUFFER_MS = 40000
HTTP_TIMEOUT_S = 8
SUBPROCESS_TIMEOUT_S = 3
READ_CHUNK = 8192


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
    audit_closed = False
    http_calls: list[tuple[str, str]] = []
    ai_key = ""
    ai_port = 8000
    unit = ""
    deadline: Deadline | None = None
    list_cap = MEASURE_INTERNAL_LIST_MAX_BYTES
    body_oversized = False


STATE = State()


def emit(key: str, value: object) -> None:
    if value is True:
        text = "YES"
    elif value is False:
        text = "NO"
    elif value is None:
        text = "NONE"
    else:
        text = str(value)
    print("%s=%s" % (key, text.replace("\n", " ")))
    sys.stdout.flush()


def test_mode() -> bool:
    return (os.environ.get("OWNER_MEASURE_PACK_TEST") or "").strip() == "1"


def test_fail_mode() -> str:
    return (os.environ.get("OWNER_MEASURE_TEST_FAIL") or "").strip()


def deadline() -> Deadline:
    if STATE.deadline is None:
        STATE.deadline = Deadline(float(REMOTE_HARD_DEADLINE_S))
    return STATE.deadline


def wrapper_budget_ok() -> bool:
    need = int(REMOTE_HARD_DEADLINE_S * 1000) + DRAIN_WAIT_MS + KILL_DRAIN_WAIT_MS + SAFETY_BUFFER_MS
    return WRAPPER_TIMEOUT_MS >= need


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_source() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_MEASURE_TEST_SRC") or "").strip()
        if override:
            return Path(override)
    return Path(CANONICAL_SOURCE)


def backup_path() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_MEASURE_TEST_BACKUP") or "").strip()
        if override:
            return Path(override)
    return Path(BACKUP_PATH)


def expected_source_dev_ino() -> tuple[int, int]:
    if test_mode():
        return (
            int((os.environ.get("OWNER_MEASURE_TEST_SOURCE_DEV") or str(INVENTORY_SOURCE_DEV)).strip()),
            int((os.environ.get("OWNER_MEASURE_TEST_SOURCE_INO") or str(INVENTORY_SOURCE_INO)).strip()),
        )
    return INVENTORY_SOURCE_DEV, INVENTORY_SOURCE_INO


def expected_backup_dev_ino() -> tuple[int, int]:
    if test_mode():
        return (
            int((os.environ.get("OWNER_MEASURE_TEST_BACKUP_DEV") or str(BACKUP_DEV)).strip()),
            int((os.environ.get("OWNER_MEASURE_TEST_BACKUP_INO") or str(BACKUP_INO)).strip()),
        )
    return BACKUP_DEV, BACKUP_INO


def expected_backup_sha() -> str:
    if test_mode():
        return (os.environ.get("OWNER_MEASURE_TEST_BACKUP_SHA") or BACKUP_SHA256).strip()
    return BACKUP_SHA256


def refuse_unapproved() -> None:
    raw = (os.environ.get(APPROVAL) or "").strip()
    emit("APPROVAL_ENV_SET", "YES" if raw else "NO")
    if raw != "1":
        raise Halt("OWNER_PRODUCTION_022_MEASURE_APPROVED_UNSET")


def redact_path(path: str) -> str:
    if path.startswith("/v1/predictions/") and path != "/v1/predictions":
        return "/v1/predictions/{id}"
    return path


def cap_for_class(endpoint_class: str) -> int:
    if endpoint_class == CLASS_INTERNAL_HEALTH:
        return MEASURE_INTERNAL_HEALTH_MAX_BYTES
    if endpoint_class == CLASS_INTERNAL_LIST:
        return STATE.list_cap
    if endpoint_class == CLASS_INTERNAL_DETAIL:
        return MEASURE_INTERNAL_DETAIL_MAX_BYTES
    if endpoint_class == CLASS_PUBLIC_HTML:
        return MEASURE_PUBLIC_HTML_MAX_BYTES
    return MEASURE_PUBLIC_JSON_MAX_BYTES


def class_for_path(path: str, public: bool) -> str:
    if public:
        if path.startswith("/api/"):
            return CLASS_PUBLIC_JSON
        return CLASS_PUBLIC_HTML
    if path == "/health":
        return CLASS_INTERNAL_HEALTH
    if path == "/v1/predictions":
        return CLASS_INTERNAL_LIST
    if path.startswith("/v1/predictions/"):
        return CLASS_INTERNAL_DETAIL
    return CLASS_INTERNAL_LIST


def read_stream_limited(fp: object, max_bytes: int) -> tuple[bytes, int, bool]:
    chunks: list[bytes] = []
    n = 0
    oversized = False
    while True:
        want = READ_CHUNK
        if n + want > max_bytes + 1:
            want = (max_bytes + 1) - n
        if want <= 0:
            oversized = True
            break
        buf = fp.read(want)  # type: ignore[attr-defined]
        if not buf:
            break
        data = bytes(buf)
        chunks.append(data)
        n += len(data)
        if n > max_bytes:
            oversized = True
            break
    raw = b"".join(chunks)
    if oversized:
        return raw[:max_bytes], n, True
    return raw, n, False


def gunzip_limited(wire: bytes, max_decoded: int) -> tuple[bytes, int, bool, bool]:
    try:
        gf = gzip.GzipFile(fileobj=io.BytesIO(wire), mode="rb")
        chunks: list[bytes] = []
        n = 0
        while True:
            buf = gf.read(READ_CHUNK)
            if not buf:
                return b"".join(chunks), n, False, True
            chunks.append(buf)
            n += len(buf)
            if n > max_decoded:
                return b"".join(chunks)[:max_decoded], n, True, True
    except Exception:
        return b"", 0, False, False


def emit_oversized(endpoint_class: str, bytes_at_least: int, limit_bytes: int) -> None:
    STATE.body_oversized = True
    emit("HTTP_BODY_OVERSIZED", "YES")
    emit("HTTP_ENDPOINT_CLASS", endpoint_class)
    emit("HTTP_BYTES_READ_AT_LEAST", bytes_at_least)
    emit("HTTP_LIMIT_BYTES", limit_bytes)


def _parse_json(raw: bytes) -> object | None:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def summarize_json(payload: object, endpoint_class: str) -> None:
    emit("%s_JSON_PARSE" % endpoint_class, payload is not None)
    if payload is None:
        return
    if not isinstance(payload, dict):
        emit("%s_ENVELOPE_TYPE" % endpoint_class, type(payload).__name__)
        return
    keys = sorted(str(k) for k in payload.keys())
    emit("%s_ENVELOPE_KEYS" % endpoint_class, ",".join(keys))
    data = payload.get("data")
    if isinstance(data, list):
        emit("%s_DATA_COUNT" % endpoint_class, len(data))
        max_b = 0
        for item in data:
            encoded = json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if len(encoded) > max_b:
                max_b = len(encoded)
        emit("%s_MAX_ELEMENT_BYTES" % endpoint_class, max_b)
    elif "data" in payload:
        emit("%s_DATA_COUNT" % endpoint_class, "NA")
        encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        emit("%s_MAX_ELEMENT_BYTES" % endpoint_class, len(encoded))


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


def http_call_label(url: str) -> str:
    parsed = urlparse(url)
    path = redact_path(parsed.path or "/")
    if parsed.netloc:
        return "GET %s://%s%s" % (parsed.scheme or "http", parsed.netloc, path)
    return "GET %s" % path


def _http_fixture(url: str, endpoint_class: str, limit: int) -> tuple[int, bytes, str, str, str]:
    parsed = urlparse(url)
    path = redact_path(parsed.path or "/")
    fail = test_fail_mode()
    if fail == "public_post":
        raise Halt("HTTP_NON_GET_REFUSED")
    if path == "/v1/prediction-runs" or path.startswith("/v1/prediction-runs"):
        raise Halt("POST_PREDICTION_RUNS_REFUSED")
    ctype = "application/json"
    encoding = (os.environ.get("OWNER_MEASURE_TEST_CONTENT_ENCODING") or "identity").strip() or "identity"
    clen = os.environ.get("OWNER_MEASURE_TEST_CONTENT_LENGTH")
    if path == "/health":
        raw = (os.environ.get("OWNER_MEASURE_TEST_HEALTH_JSON") or '{"status":"ok"}').encode("utf-8")
        status = int((os.environ.get("OWNER_MEASURE_TEST_HEALTH_STATUS") or "200").strip() or "200")
    elif path == "/v1/predictions":
        if fail == "oversized_list":
            raw = b"x" * (limit + 1)
            status = 200
        elif fail == "gzip_list":
            inner = (os.environ.get("OWNER_MEASURE_TEST_GET_JSON") or '{"ok":true,"data":[],"meta":{}}').encode("utf-8")
            raw = gzip.compress(inner)
            encoding = "gzip"
            status = 200
        else:
            raw = (os.environ.get("OWNER_MEASURE_TEST_GET_JSON") or '{"ok":true,"data":[],"meta":{}}').encode("utf-8")
            status = int((os.environ.get("OWNER_MEASURE_TEST_GET_STATUS") or "200").strip() or "200")
    elif path == "/v1/predictions/{id}":
        raw = (os.environ.get("OWNER_MEASURE_TEST_DETAIL_JSON") or '{"ok":true,"data":{},"meta":{}}').encode("utf-8")
        status = int((os.environ.get("OWNER_MEASURE_TEST_DETAIL_STATUS") or "200").strip() or "200")
    else:
        raise Halt("HTTP_FIXTURE_UNKNOWN_PATH")
    if clen is None:
        clen = str(len(raw))
    return status, raw, ctype, encoding, clen


def measure_http(url: str, *, endpoint_class: str, headers: dict[str, str] | None = None) -> tuple[int, object | None, bool]:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path == "/v1/prediction-runs" or path.startswith("/v1/prediction-runs"):
        raise Halt("POST_PREDICTION_RUNS_REFUSED")
    deadline().require(2.0, "INSUFFICIENT_TIME_HTTP")
    limit = cap_for_class(endpoint_class)
    label = http_call_label(url)
    STATE.http_calls.append(("GET", label))
    emit("HTTP_CALL", label)
    emit("HTTP_ENDPOINT_CLASS", endpoint_class)
    emit("HTTP_LIMIT_BYTES", limit)
    hdrs = dict(headers or {})
    hdrs.pop("Authorization", None)
    hdrs.pop("authorization", None)
    if test_mode() and (os.environ.get("OWNER_MEASURE_TEST_HTTP") or "").strip() == "1":
        status, wire, ctype, encoding, clen = _http_fixture(url, endpoint_class, limit)
        stream_n = len(wire)
        oversized = stream_n > limit
        if oversized:
            stream_n = limit + 1
            wire = wire[:limit]
            emit_oversized(endpoint_class, stream_n, limit)
        return _finish_measure(status, wire, stream_n, oversized, ctype, encoding, clen, endpoint_class, limit)
    req = urllib.request.Request(url, method="GET", headers=hdrs)
    timeout_s = min(float(HTTP_TIMEOUT_S), max(1.0, deadline().remaining() - 1.0))
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = int(resp.getcode() or 0)
            ctype = str(resp.headers.get("Content-Type") or "")
            encoding = str(resp.headers.get("Content-Encoding") or "identity")
            clen_hdr = resp.headers.get("Content-Length")
            clen = str(clen_hdr) if clen_hdr is not None else ""
            wire, stream_n, oversized = read_stream_limited(resp, limit)
    except Halt:
        raise
    except urllib.error.HTTPError as exc:
        status = int(exc.code or 0)
        ctype = str(exc.headers.get("Content-Type") if exc.headers else "")
        encoding = str(exc.headers.get("Content-Encoding") if exc.headers else "identity")
        clen_hdr = exc.headers.get("Content-Length") if exc.headers else None
        clen = str(clen_hdr) if clen_hdr is not None else ""
        wire, stream_n, oversized = read_stream_limited(exc, limit) if exc.fp else (b"", 0, False)
    except Exception:
        raise Halt("HTTP_GET_FAIL")
    if oversized:
        emit_oversized(endpoint_class, stream_n, limit)
    return _finish_measure(status, wire, stream_n, oversized, ctype, encoding, clen, endpoint_class, limit)


def _finish_measure(
    status: int,
    wire: bytes,
    stream_n: int,
    oversized: bool,
    ctype: str,
    encoding: str,
    clen: str,
    endpoint_class: str,
    limit: int,
) -> tuple[int, object | None, bool]:
    emit("%s_HTTP_STATUS" % endpoint_class, status)
    emit("%s_CONTENT_TYPE" % endpoint_class, ctype or "UNSET")
    emit("%s_CONTENT_LENGTH_PRESENT" % endpoint_class, bool(clen))
    emit("%s_CONTENT_LENGTH" % endpoint_class, clen if clen else "NONE")
    emit("%s_STREAM_BYTES" % endpoint_class, stream_n if not oversized else "AT_LEAST_%d" % stream_n)
    emit("%s_CONTENT_ENCODING" % endpoint_class, encoding or "identity")
    if clen and str(clen).isdigit():
        emit("%s_CONTENT_LENGTH_MATCH" % endpoint_class, (not oversized) and int(clen) == stream_n)
    else:
        emit("%s_CONTENT_LENGTH_MATCH" % endpoint_class, "NA")
    enc_l = (encoding or "identity").lower()
    decoded = wire
    decoded_n = stream_n
    decoded_over = False
    if "gzip" in enc_l:
        emit("%s_GZIP" % endpoint_class, "YES")
        emit("%s_WIRE_BYTES" % endpoint_class, stream_n if not oversized else "AT_LEAST_%d" % stream_n)
        if oversized:
            emit("%s_DECODED_BYTES" % endpoint_class, "SKIPPED_WIRE_OVERSIZED")
            emit("%s_JSON_PARSE" % endpoint_class, "NO")
            return status, None, True
        decoded, decoded_n, decoded_over, ok = gunzip_limited(wire, limit)
        emit("%s_GZIP_DECODE_OK" % endpoint_class, ok)
        if not ok:
            emit("%s_JSON_PARSE" % endpoint_class, "NO")
            return status, None, False
        if decoded_over:
            emit_oversized(endpoint_class, decoded_n, limit)
            emit("%s_DECODED_BYTES" % endpoint_class, "AT_LEAST_%d" % decoded_n)
            emit("%s_JSON_PARSE" % endpoint_class, "NO")
            return status, None, True
        emit("%s_DECODED_BYTES" % endpoint_class, decoded_n)
    else:
        emit("%s_GZIP" % endpoint_class, "NO")
        emit("%s_WIRE_BYTES" % endpoint_class, stream_n if not oversized else "AT_LEAST_%d" % stream_n)
        emit("%s_DECODED_BYTES" % endpoint_class, stream_n if not oversized else "AT_LEAST_%d" % stream_n)
        if oversized:
            emit("%s_JSON_PARSE" % endpoint_class, "NO")
            return status, None, True
    payload = _parse_json(decoded)
    summarize_json(payload, endpoint_class)
    return status, payload, False


def run_cmd(args: list[str]) -> tuple[int, str]:
    try:
        timeout_s = min(float(SUBPROCESS_TIMEOUT_S), max(1.0, deadline().remaining() - 1.0))
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_s, check=False)
        return int(p.returncode), (p.stdout or "")
    except Exception:
        return 1, ""


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


def _flag_01(raw: str | None) -> int:
    return 1 if (raw or "").strip().lower() in ("1", "true", "yes", "on") else 0


def read_proc_environ(pid: str) -> tuple[bool, dict[str, str]]:
    if not pid.isdigit() or int(pid) <= 0:
        return False, {}
    try:
        with open("/proc/%s/environ" % pid, "rb") as fh:
            blob = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return False, {}
    return True, parse_assignment_blob(blob, split_null=True, extra_keys=("AI_PORT", "AI_API_KEY", "AI_HOST"))


def collect_production_env() -> dict[str, object]:
    if test_mode() and (os.environ.get("OWNER_MEASURE_TEST_ENV") or "").strip() == "1":
        show = os.environ.get("OWNER_MEASURE_TEST_SYSTEMD_SHOW") or ""
        proc_blob = os.environ.get("OWNER_MEASURE_TEST_PROC_ENVIRON") or ""
        file_blob = os.environ.get("OWNER_MEASURE_TEST_ENVFILE") or ""
        sd = parse_systemd_show(show)
        proc_ok = bool(proc_blob) or (os.environ.get("OWNER_MEASURE_TEST_PROC_OK") or "") == "1"
        proc = parse_assignment_blob(proc_blob.replace(" ", "\0"), split_null=True, extra_keys=("AI_PORT", "AI_API_KEY", "AI_HOST")) if proc_blob else {}
        files = parse_assignment_blob(file_blob.replace(" ", "\0"), split_null=True) if file_blob else {}
        systemd_ok = bool(show) or (os.environ.get("OWNER_MEASURE_TEST_SYSTEMD_OK") or "") == "1"
        files_ok = bool(file_blob) or (os.environ.get("OWNER_MEASURE_TEST_FILES_OK") or "") == "1"
        env_line = sd.get("Environment") or ""
        systemd_env = parse_assignment_blob(env_line.replace(" ", "\0"), split_null=True)
        file_paths = environment_file_paths(sd.get("EnvironmentFiles") or "")
        if file_blob:
            file_paths = file_paths or ["TEST"]
        mainpid = str(sd.get("MainPID") or "0").strip()
        return {
            "systemd_ok": systemd_ok,
            "proc_ok": proc_ok,
            "files_ok": files_ok,
            "proc": proc,
            "systemd": systemd_env,
            "files": files,
            "env_files": "SET" if file_paths else "UNSET",
            "mainpid": "SET" if mainpid not in ("", "0") else "UNSET",
            "unit": sd.get("Id") or "TEST",
            "unit_loaded": (sd.get("LoadState") or "") == "loaded",
            "file_paths_configured": bool(file_paths),
            "mainpid_set": mainpid not in ("", "0"),
            "load_state": sd.get("LoadState") or "UNSET",
            "active_state": sd.get("ActiveState") or "UNSET",
            "ai_port": int((os.environ.get("OWNER_MEASURE_TEST_AI_PORT") or proc.get("AI_PORT") or "8000").strip() or "8000"),
            "ai_key": (os.environ.get("OWNER_MEASURE_TEST_AI_KEY") or proc.get("AI_API_KEY") or ""),
        }
    show_out = ""
    show_rc = 1
    unit = ""
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


def verify_production_env() -> None:
    info = collect_production_env()
    STATE.unit = str(info["unit"] or "")
    STATE.ai_port = int(info["ai_port"] or 8000)
    STATE.ai_key = str(info.get("ai_key") or "")
    emit("PRODUCTION_ENV_UNIT", info["unit"])
    emit("PRODUCTION_ENV_ACTIVE_STATE", info["active_state"])
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
    emit("PRODUCTION_ENV_GATE", "PASS")


def verify_identity(path: Path, exp_dev: int, exp_ino: int, kind: str) -> os.stat_result:
    st = path.stat()
    emit("%s_DEV" % kind, st.st_dev)
    emit("%s_INO" % kind, st.st_ino)
    emit("%s_SIZE" % kind, st.st_size)
    emit("%s_MODE" % kind, oct(stat.S_IMODE(st.st_mode)))
    if (int(st.st_dev), int(st.st_ino)) != (int(exp_dev), int(exp_ino)):
        emit("DB_DRIFT", "YES")
        raise Halt("DB_DRIFT" if kind == "SOURCE" else "BACKUP_DRIFT")
    emit("DB_DRIFT", "NO")
    return st


def verify_backup(path: Path) -> None:
    if not path.is_file():
        raise Halt("BACKUP_MISSING")
    got = file_sha(path)
    emit("BACKUP_SHA256_MATCH", got == expected_backup_sha())
    if got != expected_backup_sha():
        raise Halt("BACKUP_SHA_MISMATCH")
    verify_identity(path, *expected_backup_dev_ino(), "BACKUP")


def open_ro(src: Path) -> sqlite3.Connection:
    conn = sqlite3.connect("file:%s?mode=ro" % src.resolve().as_posix(), uri=True)
    conn.execute("PRAGMA query_only=ON")
    return conn


def pred_row_count(src: Path) -> int:
    conn = open_ro(src)
    try:
        return int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
    finally:
        conn.close()


def verify_pre_schema(src: Path) -> None:
    conn = open_ro(src)
    try:
        versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")]
        cols = [r[1] for r in conn.execute("PRAGMA table_info(predictions)")]
        emit("SCHEMA_MIGRATIONS_COUNT", len(versions))
        emit("PREDICTIONS_COLUMN_COUNT", len(cols))
        emit("HAS_PERSIST_022", PERSIST_022 in versions)
        if list(OWNER_MIGRATIONS) != [v for v in versions if v != PERSIST_022] and set(OWNER_MIGRATIONS) - set(versions):
            missing = [v for v in OWNER_MIGRATIONS if v not in versions]
            if missing:
                raise Halt("OWNER_MIGRATIONS_MISSING")
        if cols[:8] != list(OWNER_PRED_COLUMNS):
            raise Halt("PREDICTIONS_COLUMNS_MISMATCH")
        idx = conn.execute("PRAGMA index_info(%s)" % RACE_INDEX).fetchall()
        if not idx:
            raise Halt("EXISTING_INDEX_MISSING_OR_MISMATCH")
        emit("SOURCE_SCHEMA_GATE", "PASS")
    finally:
        conn.close()


def bind_list_cap(db_bytes: int) -> None:
    emit("DB_FILE_BYTES", db_bytes)
    emit("INVENTORY_SOURCE_SIZE", INVENTORY_SOURCE_SIZE)
    emit("MEASURE_INTERNAL_LIST_MAX_BYTES_CONST", MEASURE_INTERNAL_LIST_MAX_BYTES)
    emit("MEASURE_INTERNAL_DETAIL_MAX_BYTES", MEASURE_INTERNAL_DETAIL_MAX_BYTES)
    emit("MEASURE_INTERNAL_HEALTH_MAX_BYTES", MEASURE_INTERNAL_HEALTH_MAX_BYTES)
    emit("MEASURE_PUBLIC_JSON_MAX_BYTES", MEASURE_PUBLIC_JSON_MAX_BYTES)
    emit("MEASURE_PUBLIC_HTML_MAX_BYTES", MEASURE_PUBLIC_HTML_MAX_BYTES)
    cap = MEASURE_INTERNAL_LIST_MAX_BYTES
    if db_bytes <= 0:
        raise Halt("DB_SIZE_UNKNOWN")
    if cap * MIN_DB_TO_LIST_CAP_RATIO > db_bytes:
        shrunk = max(1, db_bytes // MIN_DB_TO_LIST_CAP_RATIO)
        emit("MEASURE_LIST_CAP_SHRUNK", "YES")
        cap = shrunk
    else:
        emit("MEASURE_LIST_CAP_SHRUNK", "NO")
    if cap >= db_bytes:
        raise Halt("MEASURE_CAP_NOT_SMALLER_THAN_DB")
    STATE.list_cap = cap
    emit("MEASURE_LIST_CAP_BYTES", cap)
    emit("MEASURE_CAP_VS_DB_RATIO", "%.2f" % (float(db_bytes) / float(cap)))
    emit("MEASURE_CAP_LT_DB", "YES")
    emit("MEASURE_LIMITS_ARE_NOT_APPLY_LIMITS", "YES")


def localhost_ai(path: str) -> str:
    return "http://127.0.0.1:%d%s" % (int(STATE.ai_port or 8000), path)


def ai_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if STATE.ai_key:
        headers["X-AI-Key"] = STATE.ai_key
    return headers


def assert_no_write_calls() -> None:
    methods = sorted({m for m, _ in STATE.http_calls})
    labels = [p for _, p in STATE.http_calls]
    emit("HTTP_METHODS", ",".join(methods) if methods else "NONE")
    post_called = any(m != "GET" for m, _ in STATE.http_calls) or any("prediction-runs" in p for p in labels)
    emit("POST_PREDICTION_RUNS_CALLED", post_called)
    if post_called:
        raise Halt("POST_PREDICTION_RUNS_CALLED")
    if any(m != "GET" for m, _ in STATE.http_calls):
        raise Halt("NON_GET_HTTP_CALLED")


def fail_closed(code: str) -> int:
    try:
        assert_no_write_calls()
    except Halt:
        pass
    emit("MEASURE_EXECUTED", "YES")
    emit("APPLY_EXECUTED", "NO")
    emit("APPLY_PHASE", "NOT_STARTED")
    emit("OWNER_MEASURE_STATUS", "FAIL")
    emit("PRODUCTION_CHANGED", "NO")
    emit("DB_CHANGED", "NO")
    emit("CACHE_WRITE", "NO")
    emit("FILE_WRITE", "NO")
    emit("PERSISTENT_ENV_CHANGED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("PRODUCTION_022_APPLY_EXECUTION_ALLOWED", "NO")
    emit("HALT_REASON", code)
    emit("AUDIT_CLOSED", "YES")
    STATE.audit_closed = True
    return 2


def finish_success(*, partial: bool) -> int:
    emit("MEASURE_EXECUTED", "YES")
    emit("APPLY_EXECUTED", "NO")
    emit("APPLY_PHASE", "NOT_STARTED")
    emit("OWNER_MEASURE_STATUS", "PARTIAL" if partial else "SUCCESS")
    emit("PRODUCTION_CHANGED", "NO")
    emit("DB_CHANGED", "NO")
    emit("CACHE_WRITE", "NO")
    emit("FILE_WRITE", "NO")
    emit("PERSISTENT_ENV_CHANGED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("PRODUCTION_022_APPLY_EXECUTION_ALLOWED", "NO")
    emit("NEXT_STEP", "RECEIVE_MEASUREMENT_THEN_V5_APPLY_LIMITS")
    emit("AUDIT_CLOSED", "YES")
    STATE.audit_closed = True
    return 3 if partial else 0


def run() -> int:
    STATE.deadline = Deadline(float(REMOTE_HARD_DEADLINE_S))
    emit("PACK", PACK)
    emit("MEASURE_ONLY", "YES")
    emit("APPLY_IN_THIS_PACK", "NO")
    emit("V4_RERUN", "NO")
    emit("V4_ZIP_OVERWRITE", "NO")
    emit("V4_OWNER_LOG_OUTPUT_SHA256", "307fe722bbd75f650e4019a1d9eb600a0d39d3a15dd18245fd379536d14fa462")
    emit("REMOTE_HARD_DEADLINE_S", REMOTE_HARD_DEADLINE_S)
    emit("WRAPPER_TIMEOUT_MS", WRAPPER_TIMEOUT_MS)
    emit("WRAPPER_BUDGET_OK", wrapper_budget_ok())
    emit("SITE_UI_VISUAL_CHECKED", "NO")
    if not wrapper_budget_ok():
        raise Halt("WRAPPER_TIMEOUT_SHORTER_THAN_REMOTE")
    refuse_unapproved()
    verify_production_env()
    bak = backup_path()
    verify_backup(bak)
    src = canonical_source()
    if (not test_mode()) and str(src.resolve()) != CANONICAL_SOURCE:
        raise Halt("REFUSED_NON_CANONICAL_SOURCE")
    if not src.is_file():
        raise Halt("SOURCE_MISSING")
    src_st = verify_identity(src, *expected_source_dev_ino(), "SOURCE")
    bind_list_cap(int(src_st.st_size))
    verify_pre_schema(src)
    before = pred_row_count(src)
    emit("PRED_ROW_BEFORE", before)
    health_status, _health, health_over = measure_http(localhost_ai("/health"), endpoint_class=CLASS_INTERNAL_HEALTH, headers={"Accept": "application/json"})
    if health_over:
        raise Halt("HTTP_BODY_OVERSIZED")
    if health_status != 200:
        raise Halt("HEALTH_FAIL")
    list_status, list_payload, list_over = measure_http(localhost_ai("/v1/predictions"), endpoint_class=CLASS_INTERNAL_LIST, headers=ai_headers())
    if list_over:
        after = pred_row_count(src)
        emit("PRED_ROW_AFTER", after)
        emit("PRED_ROW_DELTA", after - before)
        emit("DETAIL_GET", "SKIPPED_LIST_OVERSIZED")
        assert_no_write_calls()
        if after != before:
            raise Halt("GET_PRED_ROW_DELTA_NONEZERO")
        return finish_success(partial=True)
    if list_status != 200:
        raise Halt("GET_PREDICTIONS_FAIL")
    rid = first_list_race_id(list_payload)
    if not rid:
        emit("DETAIL_GET", "SKIPPED_EMPTY_LIST")
    else:
        measure_http(localhost_ai("/v1/predictions/%s" % rid), endpoint_class=CLASS_INTERNAL_DETAIL, headers=ai_headers())
        emit("DETAIL_GET", "ATTEMPTED")
        emit("DETAIL_GET_AUTHORIZATION_SENT", "NO")
    after = pred_row_count(src)
    emit("PRED_ROW_AFTER", after)
    emit("PRED_ROW_DELTA", after - before)
    if after != before:
        raise Halt("GET_PRED_ROW_DELTA_NONEZERO")
    assert_no_write_calls()
    return finish_success(partial=STATE.body_oversized)


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
        if not STATE.audit_closed:
            fail_closed("AUDIT_CLOSE_FALLBACK")


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
