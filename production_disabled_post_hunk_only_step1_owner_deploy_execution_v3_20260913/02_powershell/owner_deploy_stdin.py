#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single SSH stdin payload for 工程1 hunk-only code deploy v3. Pregenerated. Do not concatenate. sudo -n restart only. Bounded readiness poll after restart."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import py_compile
import re
import sqlite3
import stat
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

PACK = "production_disabled_post_hunk_only_step1_owner_deploy_execution_v3_20260913"
REPO_ROOT = "/home/ubuntu/KEIBA-Single-AI"
WIN5_ROOT = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai"
CANONICAL_SOURCE = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db"
V1_APPROVAL = "OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED"
V2_APPROVAL = "OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED"
APPROVAL = "OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED"
RESTART_UNIT = "expect-ai.service"
RESTART_ARGV = ("sudo", "-n", "systemctl", "restart", RESTART_UNIT)
OLD_EXECUTION_PACK = "production_disabled_post_hunk_only_step1_owner_deploy_execution_20260913"
OLD_EXECUTION_ZIP_SHA256 = "a8d226c33d9825adf5c8a8cd269ba0665a304e9b268168350148e79a61afac13"
V2_EXECUTION_PACK = "production_disabled_post_hunk_only_step1_owner_deploy_execution_v2_20260913"
V2_EXECUTION_ZIP_SHA256 = "20a273c79e2fb925da46994259ec98dd3e1275ea760808b67146976ffdaffc17"
PARTIAL_INDEX = "uq_predictions_idempotency_key_not_null"
RACE_INDEX = "idx_predictions_race"
PERSIST_022 = "022_prediction_run_idempotency"
PERSIST_019 = "019_prediction_run_idempotency"
MAIN_PY_CANDIDATE_SHA256 = "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c"
MAIN_PY_CANDIDATE_SIZE = 48345
LIVE_MAIN_PY_SHA256 = "7486a9ad7578e9ccdf883eaaac85f0b0de7ba329e286302b8d2f57db81d79235"
ORIGIN_MAIN_PY_SHA256 = "a54f1eaa5b8540c2f08d8b0e656a3ccbb78142d4d1cb2c8951e4105f3630184e"
V6_MAIN_PY_SHA256 = "7577973c16eb7aad395cd11acae3c8ef987a3c0533924c1994ae32afeaf818e5"
HUNK_ONLY_V3_ZIP_SHA256 = "4d7cdcf6ba9e7d6cc94d903364a302ac7f63bf0ec0db590460b1745b8d9b37ab"
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
REMOTE_HARD_DEADLINE_S = 300
WRAPPER_TIMEOUT_MS = 400000
DRAIN_WAIT_MS = 20000
KILL_DRAIN_WAIT_MS = 8000
SAFETY_BUFFER_MS = 40000
HTTP_LOCAL_TIMEOUT_S = 3
HTTP_PUBLIC_TIMEOUT_S = 3
SUBPROCESS_TIMEOUT_S = 8
RESTART_TIMEOUT_S = 60
READINESS_POLL_TIMEOUT_S = 45
READINESS_POLL_INTERVAL_S = 1.0
READINESS_HTTP_TIMEOUT_S = 2
READINESS_MAX_ATTEMPTS = 45
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
CLASS_DISABLED_POST = "DISABLED_POST_PROBE"
WATCHED_ENV_KEYS = (
    "PREDICTION_RUNS_ENABLED",
    "EXPECT_AI_ALLOW_MIGRATION_022",
    "EXPECT_AI_ALLOW_MIGRATION_019",
)
PUBLIC_ORIGINS = (
    "https://expect-keiba.com",
    "https://keiba-single-ai.pages.dev",
)
PUBLIC_STATIC_PATHS = ("/", "/race.html", "/races.html")
PUBLIC_API_PATHS = ("/api/health", "/api/predictions")
ALLOWED_PUBLIC_HOSTS = ("expect-keiba.com", "keiba-single-ai.pages.dev")
SITE_IDENTIFIERS = ("Expect", "KEIBA")
PHASE_NOT_STARTED = "NOT_STARTED"
PHASE_PRECHECKS = "PRECHECKS"
PHASE_BACKED_UP = "BACKED_UP"
PHASE_REPLACED = "REPLACED"
PHASE_RESTARTED = "RESTARTED"
PHASE_VERIFIED = "VERIFIED"
PHASE_RESTORED = "RESTORED"
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
    "022_prediction_run_idempotency",
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
    "idempotency_key",
    "persist_source",
    "input_snapshot_hash",
    "prediction_semantic_hash",
)
NEW_COLS = (
    "idempotency_key",
    "persist_source",
    "input_snapshot_hash",
    "prediction_semantic_hash",
)
DEPLOY_TARGETS = (
    {
        "rel": "app/main.py",
        "pre": "LIVE_SHA",
        "live": "7486a9ad7578e9ccdf883eaaac85f0b0de7ba329e286302b8d2f57db81d79235",
        "cand": "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c",
    },
    {
        "rel": "app/data/db.py",
        "pre": "LIVE_SHA",
        "live": "8a86f514b1b08fde9a90a71acc99eac3f6fc9c2aeae200e8787721093592ef1a",
        "cand": "81fc91adbe53aa091841fd9ea097b7cbd63cf4ede4a3699bf66e1c7a2343136f",
    },
    {
        "rel": "app/data/repository/__init__.py",
        "pre": "LIVE_SHA",
        "live": "557713a95b0e9f5a8f798eeb5e525c85adab3063b2e6529ee0be2155bb29992b",
        "cand": "9624699ec48d2af8b1fdc24ac81b8ae436c77ffa92a7f0b1378ecd17248b4c08",
    },
    {
        "rel": "app/core/feature_loader_bridge.py",
        "pre": "LIVE_SHA",
        "live": "e06e6ee971e2ae8d07bbcee4501ab9024052de52dd119ea007cb71481ae5272e",
        "cand": "f3c25c7b87941138555158e051d0520fc705889e8a2a17e8889c7fc5325eae44",
    },
    {
        "rel": "app/data/migrations/022_prediction_run_idempotency.sql",
        "pre": "ABSENT",
        "live": "",
        "cand": "627910c7985276d516fbbbcc09ca15964081955452eae28ae8a773c38acf28a9",
    },
    {
        "rel": "app/predictions/__init__.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "d4373c31ad5aac82a2d83a53d91bc2b95607bd891d7b9286c3c154478d5dc21c",
    },
    {
        "rel": "app/predictions/guards.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "7e6d74dd77b6645364679187a325b42676cd64d6546f5576022f19d30e6dfc82",
    },
    {
        "rel": "app/predictions/runs.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "d04bc99281474aa4e0e78b9951df6335f6b9995c9e7328b100afd552815f35c1",
    },
    {
        "rel": "app/predictions/feature_pin.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "49794f3671589a5ec13bc622161bac8c10609ff922c51033343dca30a31fbc36",
    },
    {
        "rel": "app/predictions/provenance.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "2cc2585d53a3dbdffd8c7a4dc56921aafaf4ce6cd5421d1928950a34194bb704",
    },
    {
        "rel": "app/predictions/snapshot.py",
        "pre": "ABSENT",
        "live": "",
        "cand": "2114c953b57461f73d0450384f38df2a2b086a51e53591c77cc70b448cbde5f7",
    },
)
OPS_TARGETS = (
    {
        "rel": "app/ops/prediction_capacity.py",
        "live": "c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e",
    },
    {
        "rel": "app/ops/final_prediction_store.py",
        "live": "40352ff56b3267533267d5de9c893f3bda8963d5fe121474f7785b0152594a12",
    },
)
MUST_ABSENT = (
    "app/predictions/corpus.py",
    "app/predictions/raeval84_holdout.py",
    "app/predictions/data/raeval84_v1_holdout_race_ids.txt",
    "app/data/migrations/019_prediction_run_idempotency.sql",
    "app/data/migrations_not_apply/019_prediction_run_idempotency.sql",
)
CANDIDATE_PREFIX = "services/win5-ai/"
# BEGIN_CANDIDATE_TAR_GZ_B64
CANDIDATE_TAR_GZ_B64 = (
    "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"
    "xNZuDL6mXHbKWsQulfUrkqQqnusGyM7r/160NkYnRWtyjvVQ14JHsrQkAhR3ZgWELMfdWgSe+azV"
    "i/rkZ47Id+BMOlm6A/zhD++cvnL/7B+/8uB//shBLgd9sc/e+d7ZW28/+P791G9bWK4HuIvoNkqj"
    "Y9kLRbVQRhiyahrvXe5kXa3qx8zn2pawIt+gSglcY7frsUbo4a8bJWPQU188goGUOYjbYzfpLcuI"
    "mSYPbRRdvOv3kyXpaAt2aJGLeemeT2OhM+aJXft6GDg8jV1HcZlKotaVhJ+z36ta73DK3Nm1LZVR"
    "pNNXv3X66i8evPsa0A9L3Dr0inmViNP9n56++lOmdvzgb984Pfna6f3XWeRrjB/5q7dY2Mizr7x5"
    "9vXvnP36u3Ig2po+D6RdatTsn8qRn/7jl69RdOyzH/3l+/8Mv17HNvh4GbUik4a0ueK7uHQT80hG"
    "XM9KYbXEAnCJ7Lwh81jMEttCykHUqoXLo3t87g1CSc4pQB49lcRL0aEcbe1ACRvG6oX/f3tnr4Mg"
    "FEPh3adglTA4O/gixhBjjAvBRNx8ebm/9LS9/MTEqWcyERoulWO5lO92z9v5cMmAvb0E4uFp+dR1"
    "Dt5UdU2+JS3Ww+sW+xoVYhjZhbGf0goY8kbI8wimwEfxDPkMgS6pTTluv4N5k7E0vg73IXc+4Mog"
    "ch4ldKYy8gyMIkaU5LBCMn3zqmCaqjBP5AkzrukyzBOAnnDCEv6H9KWG9UtWJk5v/N7xvxVMF6ZM"
    "DeEOKu8Jyc8952SdFUSZrbuE2vG+uW/bWYZqYmK4iVK/n2Qw9dWJ879xeOQw3aD6LfzVzbUPNZCE"
    "hcoWBd7R+EcTewXAhK9dTFfNVhbnrPGo1M3/3A4UajiMHkpD91smHjjnZ94JhY/xyZM3UsSFkU39"
    "yNzIqIdBkYdOpi17pc8Jq37mRyF87CcvK/rZoqet8zXhbbJa5V33Cw4XUllqwVfLZpnFKZOFQNLh"
    "clq76wPfsGC0+6ZSyPayno9hZsr5cYsIfwuflxvoC3Qjt/3qul9ajC1qajKZTCaTyWQymUwmoS/U"
    "6qk7AFgCAA=="
)
# END_CANDIDATE_TAR_GZ_B64
DEFAULT_BFF_HEALTH_JSON = (
    '{"ok":true,"meta":{"service":"BffHealth","cache":"no-store"},'
    '"data":{"status":"ok","service":"bff","runtime":"cloudflare-pages-functions",'
    '"ai_proxy_configured":true}}'
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


class FileRec:
    rel: str
    pre: str
    dest: Path
    kind: str
    backup_bytes: bytes | None
    created: bool
    live_sha: str
    cand_sha: str


class State:
    deploy_phase = PHASE_NOT_STARTED
    deploy_executed = False
    files_replaced = False
    restart_executed = False
    recovery_restart_executed = False
    restored = False
    audit_closed = False
    http_calls: list[tuple[str, str]] = []
    restart_counts: dict[str, int] = {}
    ai_key = ""
    ai_port = 8000
    unit = RESTART_UNIT
    deadline: Deadline | None = None
    backup_dir: Path | None = None
    records: list[FileRec] = []
    ops_sha: dict[str, str] = {}
    pre_main_pid = ""
    pre_exec_ts = ""
    restart_outcome = ""
    readiness_probe_count = 0


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
    return (os.environ.get("OWNER_DEPLOY_PACK_TEST") or "").strip() == "1"


def test_fail_mode() -> str:
    return (os.environ.get("OWNER_DEPLOY_TEST_FAIL") or "").strip()


def candidate_sha_map() -> dict[str, str]:
    return {str(t["rel"]): str(t["cand"]) for t in DEPLOY_TARGETS}


def remote_hard_deadline_s() -> float:
    if test_mode():
        raw = (os.environ.get("OWNER_DEPLOY_TEST_DEADLINE_S") or "").strip()
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


def repo_root() -> Path:
    if test_mode():
        root = (os.environ.get("OWNER_DEPLOY_TEST_ROOT") or "").strip()
        if not root:
            raise Halt("TEST_ROOT_UNSET")
        return Path(root)
    return Path(REPO_ROOT)


def win5_root() -> Path:
    return repo_root() / "services" / "win5-ai"


def canonical_source() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_DEPLOY_TEST_SRC") or "").strip()
        if override:
            return Path(override)
    return Path(CANONICAL_SOURCE)


def refuse_unapproved() -> None:
    v1 = (os.environ.get(V1_APPROVAL) or "").strip()
    v2 = (os.environ.get(V2_APPROVAL) or "").strip()
    v3 = (os.environ.get(APPROVAL) or "").strip()
    emit("OLD_EXECUTION_PACK_RERUN_ALLOWED", "NO")
    emit("OLD_EXECUTION_PACK", OLD_EXECUTION_PACK)
    emit("OLD_EXECUTION_ZIP_SHA256", OLD_EXECUTION_ZIP_SHA256)
    emit("V2_EXECUTION_PACK", V2_EXECUTION_PACK)
    emit("V2_EXECUTION_ZIP_SHA256", V2_EXECUTION_ZIP_SHA256)
    emit("V2_RERUN_ALLOWED", "NO")
    if (v1 == "1" or v2 == "1") and v3 != "1":
        raise Halt("OLD_EXECUTION_PACK_RERUN_REFUSED")
    if v3 != "1":
        raise Halt("OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED_UNSET")


def _flag_01(raw: str | None) -> int:
    return 1 if (raw or "").strip().lower() in ("1", "true", "yes", "on") else 0


def file_sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def open_regular(path: Path, flags: int = os.O_RDONLY) -> int:
    fd = os.open(str(path), flags | O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            os.close(fd)
            raise Halt("NOT_REGULAR_FILE")
        return fd
    except Halt:
        raise
    except OSError:
        try:
            os.close(fd)
        except OSError:
            pass
        raise Halt("OPEN_FAIL")


def read_regular(path: Path) -> bytes:
    fd = open_regular(path)
    with os.fdopen(fd, "rb") as fh:
        return fh.read()


def file_sha_nofollow(path: Path) -> str:
    return file_sha_bytes(read_regular(path))


def lexical_join(root: Path, rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute() or any(part in ("..", "") for part in p.parts if part == ".."):
        raise Halt("PATH_ESCAPE")
    if any(part == ".." for part in p.parts):
        raise Halt("PATH_ESCAPE")
    dest = root.joinpath(*p.parts)
    root_s = str(root)
    dest_s = str(dest)
    if dest_s != root_s and not dest_s.startswith(root_s.rstrip("/") + "/"):
        raise Halt("PATH_ESCAPE")
    return dest


def exists_nofollow(path: Path) -> bool:
    try:
        os.lstat(str(path))
        return True
    except OSError:
        return False


def is_symlink(path: Path) -> bool:
    try:
        return stat.S_ISLNK(os.lstat(str(path)).st_mode)
    except OSError:
        return False


def extract_candidates() -> dict[str, bytes]:
    if CANDIDATE_TAR_GZ_B64 == "EMBED_CANDIDATE_TAR_GZ_B64":
        raise Halt("CANDIDATE_EMBED_MISSING")
    raw = base64.b64decode(CANDIDATE_TAR_GZ_B64.encode("ascii"))
    emit("CANDIDATE_TAR_GZ_SHA256", file_sha_bytes(raw))
    wanted = candidate_sha_map()
    out: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                raise Halt("CANDIDATE_TAR_NONFILE")
            name = member.name.replace("\\", "/")
            if name.startswith("./"):
                name = name[2:]
            if not name.startswith(CANDIDATE_PREFIX):
                raise Halt("CANDIDATE_TAR_PATH")
            rel = name[len(CANDIDATE_PREFIX) :]
            if rel not in wanted:
                raise Halt("CANDIDATE_UNEXPECTED")
            extracted = tf.extractfile(member)
            if extracted is None:
                raise Halt("CANDIDATE_TAR_EMPTY")
            data = extracted.read()
            got = file_sha_bytes(data)
            if got != wanted[rel]:
                raise Halt("CANDIDATE_SHA_MISMATCH")
            if rel == "app/main.py":
                if len(data) != MAIN_PY_CANDIDATE_SIZE:
                    raise Halt("MAIN_PY_CANDIDATE_SIZE_MISMATCH")
                if got in (ORIGIN_MAIN_PY_SHA256, V6_MAIN_PY_SHA256, LIVE_MAIN_PY_SHA256):
                    raise Halt("WHOLESALE_MAIN_PY_REPLACE")
                if got != MAIN_PY_CANDIDATE_SHA256:
                    raise Halt("MAIN_PY_CANDIDATE_SHA_MISMATCH")
                emit("MAIN_PY_HUNK_ONLY", "YES")
            out[rel] = data
    if len(out) != 11:
        raise Halt("DEPLOY_TARGET_COUNT_MISMATCH")
    emit("DEPLOY_TARGET_COUNT", len(out))
    emit("CANDIDATE_BYTES_VERIFIED", "YES")
    return out


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
    cols = [str(r[2] or "") for r in conn.execute("PRAGMA index_info(%s)" % PARTIAL_INDEX).fetchall()]
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


def verify_schema_readonly(path: Path, *, prefix: str = "") -> int:
    emit("%sSCHEMA_WRITE" % prefix, "NO")
    emit("%sMIGRATE" % prefix, "NO")
    emit("%sBEGIN_IMMEDIATE" % prefix, "NO")
    conn = sqlite3.connect("file:%s?mode=ro" % path.resolve().as_posix(), uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        migrations = migration_list(conn)
        cols = prediction_columns(conn)
        have = set(migrations)
        owner = set(OWNER_MIGRATIONS)
        missing = sorted(owner - have)
        extra = sorted(have - owner)
        emit("%sSCHEMA_MIGRATIONS_COUNT" % prefix, len(migrations))
        emit("%sSCHEMA_MIGRATIONS_UNIQUE_COUNT" % prefix, len(have))
        emit("%sPREDICTIONS_COLUMN_COUNT" % prefix, len(cols))
        emit("%sHAS_PERSIST_022" % prefix, PERSIST_022 in have)
        emit("%sHAS_PERSIST_019" % prefix, PERSIST_019 in have)
        emit("%sPARTIAL_UNIQUE_INDEX_STATE" % prefix, inspect_index(conn))
        emit("%sEXISTING_RACE_INDEX" % prefix, inspect_race_index(conn))
        rows = pred_row_count(conn)
        emit("%sPRED_ROW_COUNT" % prefix, rows)
        if PERSIST_019 in have:
            raise Halt("HAS_PERSIST_019")
        if len(migrations) != 23 or have != owner or missing or extra:
            raise Halt("SCHEMA_MIGRATIONS_MISMATCH")
        if cols != list(OWNER_PRED_COLUMNS):
            raise Halt("PREDICTIONS_COLUMNS_MISMATCH")
        if inspect_index(conn) != "ok":
            raise Halt("PARTIAL_UNIQUE_MISMATCH")
        if inspect_race_index(conn) != "ok":
            raise Halt("EXISTING_INDEX_MISSING_OR_MISMATCH")
        emit("%sSCHEMA_READONLY_PASS" % prefix, "YES")
        return rows
    finally:
        conn.close()


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


SECRET_LINE_RE = re.compile(
    r"(AWS_|SECRET|TOKEN|PASSWORD|API_KEY|AUTHORIZATION|BEARER|"
    r"EXPECT_AI_API|X-AI-Key|Environment=)",
    re.IGNORECASE,
)
BASE64_LINE_RE = re.compile(r"^[A-Za-z0-9+/]{80,}={0,2}$")


def argv_is_allowed_sudo_restart(args: list[str]) -> bool:
    return list(args) == list(RESTART_ARGV)


def redact_text(text: str, *, cap: int = 4096) -> str:
    out_lines: list[str] = []
    used = 0
    for line in (text or "").splitlines():
        if SECRET_LINE_RE.search(line):
            line = "REDACTED_SECRET_LINE"
        elif BASE64_LINE_RE.match(line.strip()):
            line = "REDACTED_BASE64_LINE"
        if used + len(line) + 1 > cap:
            out_lines.append("REDACTED_TRUNCATED")
            break
        out_lines.append(line)
        used += len(line) + 1
    return "\n".join(out_lines)


def run_cmd(args: list[str], *, timeout_s: float | None = None) -> tuple[int, str, str, bool]:
    if any(a == "sudo" or str(a).startswith("sudo") for a in args):
        if not argv_is_allowed_sudo_restart(args):
            raise Halt("SUDO_REFUSED")
    if args[:2] == ["systemctl", "restart"] or (len(args) >= 3 and args[-2:] == ["restart", RESTART_UNIT] and args[0] != "sudo"):
        raise Halt("RESTART_ARGV_REFUSED")
    try:
        default_t = float(RESTART_TIMEOUT_S if argv_is_allowed_sudo_restart(args) else SUBPROCESS_TIMEOUT_S)
        use_t = float(timeout_s) if timeout_s is not None else default_t
        use_t = min(use_t, max(1.0, deadline().remaining() - 1.0))
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=use_t,
            check=False,
        )
        return int(p.returncode), (p.stdout or ""), (p.stderr or ""), False
    except Halt:
        raise
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else ((exc.stdout or b"").decode("utf-8", errors="replace") if exc.stdout else "")
        err = exc.stderr if isinstance(exc.stderr, str) else ((exc.stderr or b"").decode("utf-8", errors="replace") if exc.stderr else "")
        return 124, out, (err or "TIMEOUT"), True
    except Exception:
        return 1, "", "", False


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
    prefix = "AFTER_" if after else "BEFORE_"
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_ENV") or "").strip() == "1":
        show = os.environ.get("OWNER_DEPLOY_TEST_SYSTEMD_SHOW") or ""
        proc_blob = os.environ.get("OWNER_DEPLOY_TEST_PROC_ENVIRON") or ""
        file_blob = os.environ.get("OWNER_DEPLOY_TEST_ENVFILE") or ""
        sd = parse_systemd_show(show)
        proc = parse_assignment_blob(
            proc_blob.replace(" ", "\0"),
            split_null=True,
            extra_keys=("AI_PORT", "AI_API_KEY", "AI_HOST"),
        ) if proc_blob else {}
        files = parse_assignment_blob(file_blob.replace(" ", "\0"), split_null=True) if file_blob else {}
        systemd_ok = bool(show) or (os.environ.get("OWNER_DEPLOY_TEST_SYSTEMD_OK") or "") == "1"
        proc_ok = bool(proc_blob) or (os.environ.get("OWNER_DEPLOY_TEST_PROC_OK") or "") == "1"
        files_ok = bool(file_blob) or (os.environ.get("OWNER_DEPLOY_TEST_FILES_OK") or "") == "1"
    else:
        rc, show, _err, _to = run_cmd(["systemctl", "show", RESTART_UNIT, "--property=Id,LoadState,ActiveState,SubState,MainPID,FragmentPath,Environment,EnvironmentFiles,ActiveEnterTimestamp,ExecMainStartTimestamp,NRestarts,Result"])
        sd = parse_systemd_show(show) if rc == 0 else {}
        systemd_ok = rc == 0 and bool(sd)
        pid = str(sd.get("MainPID") or "")
        proc_ok, proc = read_proc_environ(pid)
        files = {}
        files_ok = True
        for env_path in environment_file_paths(sd.get("EnvironmentFiles") or ""):
            parsed = parse_env_file(env_path)
            files.update(parsed)
        unit_env = parse_assignment_blob(sd.get("Environment") or "", split_null=False)
        files.update(unit_env)
    emit("%sSYSTEMD_COLLECT_OK" % prefix, systemd_ok)
    emit("%sPROC_COLLECT_OK" % prefix, proc_ok)
    emit("%sENVFILE_COLLECT_OK" % prefix, files_ok)
    emit("SYSTEMD_CHANGED", "NO")
    emit("ENV_CHANGED", "NO")
    merged: dict[str, str] = {}
    merged.update(files)
    merged.update(proc)
    for key in WATCHED_ENV_KEYS:
        raw = merged.get(key)
        emit("%s%s" % (prefix, key), raw if raw not in (None, "") else "UNSET")
        if _flag_01(raw) == 1:
            raise Halt("%s_EFFECTIVE_1" % key)
    port = merged.get("AI_PORT") or proc.get("AI_PORT")
    if port and str(port).isdigit():
        STATE.ai_port = int(port)
    key = merged.get("AI_API_KEY") or proc.get("AI_API_KEY") or ""
    STATE.ai_key = key
    STATE.unit = str(sd.get("Id") or RESTART_UNIT)
    if STATE.unit and STATE.unit != RESTART_UNIT:
        raise Halt("UNEXPECTED_SYSTEMD_UNIT")
    emit("%sUNIT" % prefix, STATE.unit)
    emit("%sUNIT_LOADSTATE" % prefix, str(sd.get("LoadState") or ""))
    emit("%sUNIT_ACTIVESTATE" % prefix, str(sd.get("ActiveState") or ""))
    emit("%sUNIT_SUBSTATE" % prefix, str(sd.get("SubState") or ""))
    emit("%sUNIT_MAINPID" % prefix, str(sd.get("MainPID") or ""))
    emit("%sUNIT_EXECMAINSTARTTIMESTAMP" % prefix, str(sd.get("ExecMainStartTimestamp") or ""))
    if not after:
        STATE.pre_main_pid = str(sd.get("MainPID") or "")
        STATE.pre_exec_ts = str(sd.get("ExecMainStartTimestamp") or sd.get("ActiveEnterTimestamp") or "")
    emit("AI_PORT", STATE.ai_port)
    return {"systemd": sd, "proc": proc, "files": files}


def verify_ops_live(root: Path) -> None:
    emit("LIVE_OPS_DEPLOY", "NO")
    for item in OPS_TARGETS:
        dest = lexical_join(root, item["rel"])
        if is_symlink(dest):
            raise Halt("OPS_SYMLINK")
        if not exists_nofollow(dest):
            raise Halt("OPS_ABSENT")
        got = file_sha_nofollow(dest)
        emit("OPS_SHA_%s" % item["rel"].replace("/", "_"), got)
        if got != item["live"]:
            raise Halt("OPS_SHA_MISMATCH")
        STATE.ops_sha[item["rel"]] = got
    emit("OPS_SHA_VERIFIED", "YES")
    emit("OPS_DEPLOYED", "NO")


def verify_must_absent(root: Path) -> None:
    for rel in MUST_ABSENT:
        dest = lexical_join(root, rel)
        if exists_nofollow(dest):
            emit("MUST_ABSENT_PRESENT", rel)
            raise Halt("MUST_ABSENT_PRESENT")
    emit("MUST_ABSENT_OK", "YES")


def verify_preconditions(root: Path) -> None:
    for item in DEPLOY_TARGETS:
        dest = lexical_join(root, item["rel"])
        present = exists_nofollow(dest)
        if is_symlink(dest):
            raise Halt("DEST_SYMLINK")
        if item["pre"] == "ABSENT":
            emit("PRECONDITION_%s" % item["rel"].replace("/", "_"), "ABSENT" if not present else "PRESENT")
            if present:
                raise Halt("PRECONDITION_ABSENT_MISMATCH")
            continue
        emit("PRECONDITION_%s" % item["rel"].replace("/", "_"), "LIVE_SHA")
        if not present:
            raise Halt("PRECONDITION_LIVE_SHA_ABSENT")
        got = file_sha_nofollow(dest)
        emit("LIVE_SHA_%s" % item["rel"].replace("/", "_"), got)
        if got != item["live"]:
            raise Halt("PRECONDITION_LIVE_SHA_MISMATCH")
    emit("PRECONDITIONS_PASS", "YES")


def backup_targets(root: Path) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_BACKUP_DIR") or "").strip():
        bdir = Path(os.environ["OWNER_DEPLOY_TEST_BACKUP_DIR"])
    else:
        bdir = repo_root() / "var" / "code_backups" / stamp
    bdir.mkdir(parents=True, exist_ok=True)
    STATE.backup_dir = bdir
    emit("BACKUP_DIR", str(bdir))
    records: list[FileRec] = []
    for item in DEPLOY_TARGETS:
        dest = lexical_join(root, item["rel"])
        rec = FileRec()
        rec.rel = item["rel"]
        rec.pre = item["pre"]
        rec.dest = dest
        rec.cand_sha = item["cand"]
        rec.created = False
        rec.live_sha = ""
        rec.backup_bytes = None
        if exists_nofollow(dest):
            if is_symlink(dest):
                raise Halt("DEST_SYMLINK")
            data = read_regular(dest)
            rec.kind = "FILE"
            rec.backup_bytes = data
            rec.live_sha = file_sha_bytes(data)
            outp = lexical_join(bdir, item["rel"])
            outp.parent.mkdir(parents=True, exist_ok=True)
            outp.write_bytes(data)
            emit("BACKUP_SHA_%s" % item["rel"].replace("/", "_"), rec.live_sha)
        else:
            rec.kind = "ABSENT"
            marker = bdir.joinpath(*Path(item["rel"] + ".ABSENT").parts)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_bytes(b"ABSENT\n")
            emit("BACKUP_ABSENT_%s" % item["rel"].replace("/", "_"), "YES")
        records.append(rec)
    STATE.records = records
    STATE.deploy_phase = PHASE_BACKED_UP
    emit("DEPLOY_PHASE", PHASE_BACKED_UP)
    emit("BACKUP_RECORDED", "YES")


def stage_replace(root: Path, candidates: dict[str, bytes]) -> None:
    if test_fail_mode() == "before_replace":
        raise Halt("INJECTED_BEFORE_REPLACE")
    for rec in STATE.records:
        data = candidates[rec.rel]
        if file_sha_bytes(data) != rec.cand_sha:
            raise Halt("CANDIDATE_SHA_MISMATCH")
        dest = rec.dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        created = not exists_nofollow(dest)
        rec.created = created
        tmp = dest.parent / (".step1_staging_" + dest.name)
        if exists_nofollow(tmp) or is_symlink(tmp):
            try:
                tmp.unlink()
            except OSError:
                raise Halt("STAGING_TMP_BUSY")
        tmp.write_bytes(data)
        if rec.rel.endswith(".py"):
            py_compile.compile(str(tmp), doraise=True)
            emit("SYNTAX_OK_%s" % rec.rel.replace("/", "_"), "YES")
        if file_sha_bytes(tmp.read_bytes()) != rec.cand_sha:
            raise Halt("STAGING_SHA_MISMATCH")
        if test_fail_mode() == "syntax" and rec.rel.endswith(".py"):
            raise Halt("INJECTED_SYNTAX_FAIL")
        os.replace(str(tmp), str(dest))
        got = file_sha_nofollow(dest)
        emit("POST_REPLACE_SHA_%s" % rec.rel.replace("/", "_"), got)
        if got != rec.cand_sha:
            raise Halt("POST_REPLACE_SHA_MISMATCH")
    STATE.files_replaced = True
    STATE.deploy_phase = PHASE_REPLACED
    emit("DEPLOY_PHASE", PHASE_REPLACED)
    emit("FILES_REPLACED", "YES")
    if test_fail_mode() == "after_replace":
        raise Halt("INJECTED_AFTER_REPLACE")


def restore_code_only() -> None:
    emit("SCHEMA_ROLLBACK", "NO")
    emit("CODE_RESTORE_ONLY", "YES")
    if not STATE.records:
        emit("CODE_RESTORED", "NO")
        return
    for rec in reversed(STATE.records):
        dest = rec.dest
        if rec.kind == "ABSENT":
            if exists_nofollow(dest) and rec.created:
                dest.unlink()
            continue
        if rec.backup_bytes is None:
            raise Halt("BACKUP_BYTES_MISSING")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.parent / (".step1_restore_" + dest.name)
        if exists_nofollow(tmp) or is_symlink(tmp):
            try:
                tmp.unlink()
            except OSError:
                raise Halt("RESTORE_TMP_BUSY")
        tmp.write_bytes(rec.backup_bytes)
        os.replace(str(tmp), str(dest))
        got = file_sha_nofollow(dest)
        if rec.live_sha and got != rec.live_sha:
            raise Halt("RESTORE_SHA_MISMATCH")
    STATE.restored = True
    STATE.deploy_phase = PHASE_RESTORED
    emit("DEPLOY_PHASE", PHASE_RESTORED)
    emit("CODE_RESTORED", "YES")


def snapshot_unit(*, after_restart: bool) -> dict[str, str]:
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_ENV") or "").strip() == "1":
        fail = (os.environ.get("OWNER_DEPLOY_TEST_RESTART_FAIL") or "").strip() == "1"
        if after_restart and not fail:
            show = os.environ.get("OWNER_DEPLOY_TEST_SYSTEMD_SHOW_AFTER") or os.environ.get("OWNER_DEPLOY_TEST_SYSTEMD_SHOW") or ""
        else:
            show = os.environ.get("OWNER_DEPLOY_TEST_SYSTEMD_SHOW") or ""
        return parse_systemd_show(show)
    rc, show, _err, _to = run_cmd(
        [
            "systemctl",
            "show",
            RESTART_UNIT,
            "--property=Id,LoadState,ActiveState,SubState,MainPID,FragmentPath,ActiveEnterTimestamp,ExecMainStartTimestamp,NRestarts,Result",
        ]
    )
    if rc != 0:
        return {}
    return parse_systemd_show(show)


def classify_restart(*, phase: str, rc: int, timed_out: bool, before_pid: str, before_ts: str, after: dict[str, str]) -> str:
    load = str(after.get("LoadState") or "")
    active = str(after.get("ActiveState") or "")
    pid = str(after.get("MainPID") or "")
    ts = str(after.get("ExecMainStartTimestamp") or after.get("ActiveEnterTimestamp") or "")
    pid_ok = False
    try:
        pid_ok = int(pid) > 0
    except ValueError:
        pid_ok = False
    unit_ok = load == "loaded" and active == "active" and pid_ok
    changed = False
    if pid and before_pid and pid != before_pid:
        changed = True
    if ts and before_ts and ts != before_ts:
        changed = True
    emit("RESTART_UNIT_LOADSTATE", load)
    emit("RESTART_UNIT_ACTIVESTATE", active)
    emit("RESTART_UNIT_MAINPID", pid)
    emit("RESTART_UNIT_EXECMAINSTARTTIMESTAMP", ts)
    emit("RESTART_MAINPID_CHANGED", "YES" if (pid and before_pid and pid != before_pid) else "NO")
    emit("RESTART_EXECMAINSTARTTIMESTAMP_CHANGED", "YES" if (ts and before_ts and ts != before_ts) else "NO")
    if not after:
        return "UNKNOWN"
    if phase == "RECOVERY":
        if unit_ok:
            return "SUCCESS"
        return "FAIL" if not timed_out else "UNKNOWN"
    if unit_ok and changed:
        return "SUCCESS"
    if unit_ok and not changed:
        return "FAIL"
    if not unit_ok:
        return "FAIL"
    if timed_out:
        return "UNKNOWN"
    return "FAIL"


def restart_once(phase: str) -> None:
    if phase not in ("DEPLOY", "RECOVERY"):
        raise Halt("RESTART_PHASE_INVALID")
    if STATE.restart_counts.get(phase, 0) >= 1:
        raise Halt("RESTART_COUNT_EXCEEDED")
    emit("RESTART_UNIT", RESTART_UNIT)
    emit("RESTART_COMMAND", " ".join(RESTART_ARGV))
    emit("RESTART_PHASE", phase)
    emit("SUDO_USED", "YES")
    emit("SUDO_N_FLAG", "YES")
    emit("RESTART_TIMEOUT_S", RESTART_TIMEOUT_S)
    argv = list(RESTART_ARGV)
    if argv != ["sudo", "-n", "systemctl", "restart", RESTART_UNIT]:
        raise Halt("RESTART_ARGV_REFUSED")
    before_pid = STATE.pre_main_pid
    before_ts = STATE.pre_exec_ts
    emit("RESTART_BEFORE_MAINPID", before_pid)
    emit("RESTART_BEFORE_EXECMAINSTARTTIMESTAMP", before_ts)
    timed_out = False
    rc = 1
    out = ""
    err = ""
    if test_mode():
        log = (os.environ.get("OWNER_DEPLOY_TEST_RESTART_LOG") or "").strip()
        if log:
            with open(log, "a", encoding="utf-8") as fh:
                fh.write("sudo -n systemctl restart %s\n" % RESTART_UNIT)
        if (os.environ.get("OWNER_DEPLOY_TEST_RESTART_FAIL") or "").strip() == "1":
            rc = int((os.environ.get("OWNER_DEPLOY_TEST_RESTART_RC") or "1").strip() or "1")
            err = os.environ.get("OWNER_DEPLOY_TEST_RESTART_STDERR") or "FAILED"
            timed_out = (os.environ.get("OWNER_DEPLOY_TEST_RESTART_TIMEOUT") or "").strip() == "1"
        elif (os.environ.get("OWNER_DEPLOY_TEST_RESTART_TIMEOUT") or "").strip() == "1":
            rc = 124
            err = "TIMEOUT"
            timed_out = True
        else:
            rc = 0
            err = ""
            timed_out = False
            STATE.restart_counts[phase] = STATE.restart_counts.get(phase, 0)
    else:
        rc, out, err, timed_out = run_cmd(argv, timeout_s=float(RESTART_TIMEOUT_S))
    emit("SYSTEMCTL_RESTART_EXIT", rc)
    emit("SYSTEMCTL_RESTART_TIMEOUT", "YES" if timed_out else "NO")
    emit("SYSTEMCTL_RESTART_STDOUT_REDACTED", redact_text(out, cap=2048))
    emit("SYSTEMCTL_RESTART_STDERR_REDACTED", redact_text(err, cap=2048))
    if test_mode() and rc == 0 and not timed_out:
        STATE.restart_counts[phase] = STATE.restart_counts.get(phase, 0) + 0
    after = snapshot_unit(after_restart=True)
    outcome = classify_restart(phase=phase, rc=rc, timed_out=timed_out, before_pid=before_pid, before_ts=before_ts, after=after)
    STATE.restart_outcome = outcome
    emit("RESTART_OUTCOME", outcome)
    if outcome == "UNKNOWN":
        raise Halt("RESTART_UNKNOWN")
    if outcome != "SUCCESS":
        raise Halt("RESTART_FAIL")
    load = str(after.get("LoadState") or "")
    active = str(after.get("ActiveState") or "")
    pid = str(after.get("MainPID") or "0")
    if load != "loaded" or active != "active":
        raise Halt("RESTART_UNIT_NOT_ACTIVE")
    try:
        if int(pid) <= 0:
            raise Halt("RESTART_MAINPID_INVALID")
    except ValueError:
        raise Halt("RESTART_MAINPID_INVALID")
    STATE.pre_main_pid = pid
    STATE.pre_exec_ts = str(after.get("ExecMainStartTimestamp") or after.get("ActiveEnterTimestamp") or "")
    STATE.restart_counts[phase] = STATE.restart_counts.get(phase, 0) + 1
    if phase == "DEPLOY":
        STATE.restart_executed = True
        STATE.deploy_phase = PHASE_RESTARTED
        emit("DEPLOY_PHASE", PHASE_RESTARTED)
        emit("RESTART_EXECUTED", "YES")
        emit("DEPLOY_RESTART_COUNT", 1)
    else:
        STATE.recovery_restart_executed = True
        emit("RECOVERY_RESTART_EXECUTED", "YES")
        emit("RECOVERY_RESTART_COUNT", 1)
    emit("RESTART_COUNT_%s" % phase, STATE.restart_counts[phase])


def readiness_poll_timeout_s() -> float:
    if test_mode():
        raw = (os.environ.get("OWNER_DEPLOY_TEST_READINESS_TIMEOUT_S") or "").strip()
        if raw:
            return float(raw)
    return float(READINESS_POLL_TIMEOUT_S)


def readiness_poll_interval_s() -> float:
    if test_mode():
        raw = (os.environ.get("OWNER_DEPLOY_TEST_READINESS_INTERVAL_S") or "").strip()
        if raw:
            return float(raw)
    return float(READINESS_POLL_INTERVAL_S)


def readiness_http_timeout_s() -> float:
    if test_mode():
        raw = (os.environ.get("OWNER_DEPLOY_TEST_READINESS_HTTP_TIMEOUT_S") or "").strip()
        if raw:
            return float(raw)
    return float(READINESS_HTTP_TIMEOUT_S)


def readiness_max_attempts() -> int:
    if test_mode():
        raw = (os.environ.get("OWNER_DEPLOY_TEST_READINESS_MAX_ATTEMPTS") or "").strip()
        if raw:
            return int(raw)
    return int(READINESS_MAX_ATTEMPTS)


def _unit_ready(unit: dict[str, str]) -> bool:
    load = str(unit.get("LoadState") or "")
    active = str(unit.get("ActiveState") or "")
    pid = str(unit.get("MainPID") or "0")
    try:
        pid_ok = int(pid) > 0
    except ValueError:
        pid_ok = False
    return load == "loaded" and active == "active" and pid_ok


def probe_readiness_health() -> tuple[str, int | None]:
    STATE.readiness_probe_count += 1
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_READINESS_NEVER") or "").strip() == "1":
        return "HTTP_FAIL", None
    fail_n_raw = (os.environ.get("OWNER_DEPLOY_TEST_READINESS_FAIL_COUNT") or "").strip() if test_mode() else ""
    fail_n = int(fail_n_raw) if fail_n_raw else 0
    if test_mode() and fail_n > 0 and STATE.readiness_probe_count <= fail_n:
        return "HTTP_FAIL", None
    url = localhost_ai("/health")
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_HTTP") or "").strip() == "1":
        st, health, _c, _f = _http_fixture(url, "GET")
        ok = st == 200 and isinstance(health, dict) and str(health.get("status") or "") == "ok"
        return ("PASS" if ok else "HEALTH_FAIL"), st
    timeout_s = min(readiness_http_timeout_s(), max(0.5, deadline().remaining() - 1.0))
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = read_limited(resp, HTTP_MAX_INTERNAL_HEALTH_BYTES, CLASS_INTERNAL_HEALTH)
            status = int(resp.getcode() or 0)
    except Halt:
        raise
    except urllib.error.HTTPError as exc:
        status = int(exc.code or 0)
        raw = read_limited(exc, HTTP_MAX_INTERNAL_HEALTH_BYTES, CLASS_INTERNAL_HEALTH) if exc.fp else b""
        try:
            health = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            health = {}
        ok = status == 200 and isinstance(health, dict) and str(health.get("status") or "") == "ok"
        return ("PASS" if ok else "HEALTH_FAIL"), status
    except Exception:
        return "HTTP_FAIL", None
    try:
        health = json.loads(raw.decode("utf-8")) if raw else {}
    except Exception:
        return "HEALTH_FAIL", status
    ok = status == 200 and isinstance(health, dict) and str(health.get("status") or "") == "ok"
    return ("PASS" if ok else "HEALTH_FAIL"), status


def wait_until_ready() -> None:
    timeout_s = readiness_poll_timeout_s()
    interval_s = readiness_poll_interval_s()
    max_attempts = readiness_max_attempts()
    emit("READINESS_POLL_TIMEOUT_S", timeout_s)
    emit("READINESS_POLL_INTERVAL_S", interval_s)
    emit("READINESS_HTTP_TIMEOUT_S", readiness_http_timeout_s())
    emit("READINESS_MAX_ATTEMPTS", max_attempts)
    emit("READINESS_SINGLE_SHOT", "NO")
    emit("READINESS_ARBITRARY_SLEEP_ONLY", "NO")
    deadline().require(min(timeout_s, 5.0), "INSUFFICIENT_TIME_READINESS")
    started = time.monotonic()
    attempt = 0
    last_health = "NONE"
    last_status: int | None = None
    last_unit: dict[str, str] = {}
    while attempt < max_attempts:
        if (time.monotonic() - started) >= timeout_s:
            break
        if deadline().remaining() < 1.0:
            raise Halt("INSUFFICIENT_TIME_READINESS")
        attempt += 1
        emit("READINESS_ATTEMPT", attempt)
        unit = snapshot_unit(after_restart=True)
        last_unit = unit
        load = str(unit.get("LoadState") or "")
        active = str(unit.get("ActiveState") or "")
        pid = str(unit.get("MainPID") or "")
        emit("READINESS_UNIT_LOADSTATE", load)
        emit("READINESS_UNIT_ACTIVESTATE", active)
        emit("READINESS_UNIT_MAINPID", pid)
        if active == "failed":
            emit("READINESS_OK", "NO")
            emit("READINESS_OUTCOME", "FAIL")
            raise Halt("READINESS_UNIT_FAIL")
        health_outcome, status = probe_readiness_health()
        last_health = health_outcome
        last_status = status
        emit("READINESS_HEALTH_OUTCOME", health_outcome)
        emit("READINESS_HEALTH_STATUS", status if status is not None else "NONE")
        if _unit_ready(unit) and health_outcome == "PASS":
            emit("READINESS_OK", "YES")
            emit("READINESS_OUTCOME", "PASS")
            emit("READINESS_ELAPSED_S", "%.3f" % (time.monotonic() - started))
            return
        elapsed = time.monotonic() - started
        remaining_poll = timeout_s - elapsed
        if remaining_poll <= 0:
            break
        time.sleep(min(interval_s, remaining_poll))
    emit("READINESS_OK", "NO")
    emit("READINESS_OUTCOME", "TIMEOUT")
    emit("READINESS_ELAPSED_S", "%.3f" % (time.monotonic() - started))
    emit("READINESS_LAST_HEALTH_OUTCOME", last_health)
    emit("READINESS_LAST_HEALTH_STATUS", last_status if last_status is not None else "NONE")
    emit("READINESS_LAST_UNIT_ACTIVESTATE", str(last_unit.get("ActiveState") or ""))
    raise Halt("READINESS_TIMEOUT")


def maybe_recovery_restart() -> None:
    if STATE.restored and (STATE.restart_executed or STATE.restart_outcome == "UNKNOWN"):
        restart_once("RECOVERY")
    else:
        emit("RECOVERY_RESTART_EXECUTED", "NO")
        emit("RECOVERY_RESTART_COUNT", 0)


def class_for_path(path: str, public: bool, method: str = "GET") -> str:
    if method == "POST":
        return CLASS_DISABLED_POST
    if public:
        if path in PUBLIC_STATIC_PATHS:
            return CLASS_PUBLIC_HTML
        return CLASS_PUBLIC_JSON
    if path == "/health" or path.endswith("/health"):
        return CLASS_INTERNAL_HEALTH
    if path == "/v1/predictions":
        return CLASS_INTERNAL_LIST
    if path.startswith("/v1/predictions/"):
        return CLASS_INTERNAL_DETAIL
    return CLASS_INTERNAL_HEALTH


def cap_for_class(endpoint_class: str) -> int:
    return {
        CLASS_INTERNAL_HEALTH: HTTP_MAX_INTERNAL_HEALTH_BYTES,
        CLASS_INTERNAL_LIST: HTTP_MAX_INTERNAL_LIST_BYTES,
        CLASS_INTERNAL_DETAIL: HTTP_MAX_INTERNAL_DETAIL_BYTES,
        CLASS_PUBLIC_JSON: HTTP_MAX_PUBLIC_JSON_BYTES,
        CLASS_PUBLIC_HTML: HTTP_MAX_PUBLIC_HTML_BYTES,
        CLASS_DISABLED_POST: HTTP_MAX_INTERNAL_HEALTH_BYTES,
    }[endpoint_class]


def read_limited(fp: object, max_bytes: int, endpoint_class: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        piece = fp.read(65536)  # type: ignore[attr-defined]
        if not piece:
            break
        total += len(piece)
        if total > max_bytes:
            emit("HTTP_ENDPOINT_CLASS", endpoint_class)
            emit("HTTP_BYTES_READ_AT_LEAST", total)
            emit("HTTP_LIMIT_BYTES", max_bytes)
            raise Halt("HTTP_BODY_OVERSIZED")
        chunks.append(piece)
    return b"".join(chunks)


def _parse_json_or_halt(raw: bytes) -> object:
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        raise Halt("HTTP_JSON_PARSE_FAIL")


def localhost_ai(path: str) -> str:
    return "http://127.0.0.1:%d%s" % (int(STATE.ai_port or 8000), path)


def ai_headers() -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if STATE.ai_key:
        headers["X-AI-Key"] = STATE.ai_key
    return headers


def redact_path(path: str) -> str:
    return path.split("?")[0]


def http_timeout_s(public: bool) -> float:
    base = float(HTTP_PUBLIC_TIMEOUT_S if public else HTTP_LOCAL_TIMEOUT_S)
    return min(base, max(1.0, deadline().remaining() - 1.0))


def _http_fixture(url: str, method: str) -> tuple[int, object, str, str]:
    parsed = urlparse(url)
    path = parsed.path or "/"
    final = url
    fail = test_fail_mode()
    if method == "POST":
        if path != "/v1/prediction-runs":
            raise Halt("POST_REFUSED")
        if fail == "post_enabled":
            return 200, {"ok": True}, "application/json", final
        return 503, {"error": {"code": "PREDICTION_RUNS_DISABLED", "message": "PREDICTION_RUNS_ENABLED is not 1"}}, "application/json", final
    if path == "/health":
        return 200, {"status": "ok", "db": "test", "fallback_reasons": [], "result_automation": {}}, "application/json", final
    if path == "/v1/predictions":
        raw = os.environ.get("OWNER_DEPLOY_TEST_GET_JSON") or '{"ok":true,"data":[{"race_id":"20260719_hanshin_11"}],"meta":{"count":1}}'
        return 200, json.loads(raw), "application/json", final
    if path.startswith("/v1/predictions/"):
        return 200, {"ok": True, "data": {}, "meta": {}}, "application/json", final
    if path == "/v1/conversation/health":
        return 200, {"ok": True, "data": {"status": "ok"}, "meta": {"service": "ConversationObservability"}}, "application/json", final
    if path == "/v1/challenge/active":
        status = int((os.environ.get("OWNER_DEPLOY_TEST_CHALLENGE_STATUS") or "401").strip() or "401")
        return status, {"ok": False, "error": {"code": "UNAUTHORIZED"}}, "application/json", final
    if path == "/v1/admin/results/status":
        return 200, {"ok": True, "data": {}, "meta": {}}, "application/json", final
    if path == "/api/health":
        return 200, json.loads(DEFAULT_BFF_HEALTH_JSON), "application/json", final
    if path in ("/", "/race.html", "/races.html"):
        return 200, DEFAULT_STATIC_HTML.encode("utf-8"), "text/html; charset=utf-8", final
    if path == "/api/predictions":
        return 503, json.loads(DEFAULT_BFF_PREDICTIONS_CLOSED_JSON), "application/json", final
    raise Halt("HTTP_FIXTURE_UNKNOWN_PATH")


def http_call(url: str, *, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None) -> tuple[int, object, str, str]:
    parsed = urlparse(url)
    path = parsed.path or "/"
    host = parsed.netloc.split(":")[0] if parsed.netloc else "127.0.0.1"
    public = host in ALLOWED_PUBLIC_HOSTS
    if method not in ("GET", "POST"):
        raise Halt("HTTP_METHOD_REFUSED")
    if method == "POST" and path != "/v1/prediction-runs":
        raise Halt("POST_REFUSED")
    if method == "GET" and path == "/v1/prediction-runs":
        raise Halt("GET_PREDICTION_RUNS_REFUSED")
    deadline().require(1.0, "INSUFFICIENT_TIME_HTTP")
    hdrs = dict(headers or {})
    hdrs.pop("Authorization", None)
    hdrs.pop("authorization", None)
    label = "%s %s" % (method, ("%s://%s%s" % (parsed.scheme or "http", parsed.netloc, redact_path(path))) if parsed.netloc else redact_path(path))
    STATE.http_calls.append((method, label))
    emit("HTTP_CALL", label)
    endpoint_class = class_for_path(path, public, method)
    max_bytes = cap_for_class(endpoint_class)
    emit("HTTP_ENDPOINT_CLASS", endpoint_class)
    emit("HTTP_LIMIT_BYTES", max_bytes)
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_HTTP") or "").strip() == "1":
        return _http_fixture(url, method)
    allowed = ALLOWED_PUBLIC_HOSTS if public else ("127.0.0.1", "localhost")
    if public and host not in allowed:
        raise Halt("HTTP_HOST_REFUSED")
    req = urllib.request.Request(url, data=body if method == "POST" else None, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=http_timeout_s(public)) as resp:
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
        raise Halt("HTTP_FAIL")
    wants_json = path.startswith("/api/") or path.startswith("/v1/") or path == "/health" or method == "POST"
    if wants_json:
        payload = _parse_json_or_halt(raw)
        return status, payload, ctype or "application/json", final
    if path in PUBLIC_STATIC_PATHS:
        return status, raw, ctype, final
    return status, raw, ctype, final


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


def row_delta_or_halt(src: Path, before: int, label: str) -> None:
    after = pred_row_count_ro(src)
    delta = after - before
    emit("%s_PRED_ROW_DELTA" % label, delta)
    if delta != 0:
        raise Halt("PRED_ROW_DELTA_NONEZERO")


def check_internal_regression(src: Path) -> None:
    before = pred_row_count_ro(src)
    emit("REGRESSION_PRED_ROW_BEFORE", before)
    st, health, _c, _f = http_call(localhost_ai("/health"), headers={"Accept": "application/json"})
    emit("HEALTH_STATUS", st)
    emit("HEALTH_OK", "YES" if st == 200 and isinstance(health, dict) and str(health.get("status") or "") == "ok" else "NO")
    if st != 200 or not isinstance(health, dict) or str(health.get("status") or "") != "ok":
        raise Halt("HEALTH_FAIL")
    row_delta_or_halt(src, before, "HEALTH")
    st, listing, _c, _f = http_call(localhost_ai("/v1/predictions"), headers=ai_headers())
    emit("GET_LIST_STATUS", st)
    if st != 200 or not isinstance(listing, dict) or listing.get("ok") is not True:
        raise Halt("GET_PREDICTIONS_FAIL")
    row_delta_or_halt(src, before, "GET_LIST")
    rid = first_list_race_id(listing)
    if not rid:
        emit("DETAIL_GET", "SKIPPED_EMPTY_LIST")
    else:
        st, detail, _c, _f = http_call(localhost_ai("/v1/predictions/%s" % rid), headers=ai_headers())
        emit("DETAIL_GET_STATUS", st)
        if st != 200 or not isinstance(detail, dict) or detail.get("ok") is not True:
            raise Halt("DETAIL_GET_FAIL")
        row_delta_or_halt(src, before, "GET_DETAIL")
    st, conv, _c, _f = http_call(localhost_ai("/v1/conversation/health"), headers=ai_headers())
    emit("CONVERSATION_HEALTH_STATUS", st)
    if st != 200:
        raise Halt("CONVERSATION_FAIL")
    row_delta_or_halt(src, before, "CONVERSATION")
    st, _ch, _c, _f = http_call(localhost_ai("/v1/challenge/active"), headers=ai_headers())
    emit("CHALLENGE_STATUS", st)
    if st not in (200, 401, 403):
        raise Halt("CHALLENGE_FAIL")
    row_delta_or_halt(src, before, "CHALLENGE")
    st, _ra, _c, _f = http_call(localhost_ai("/v1/admin/results/status"), headers=ai_headers())
    emit("RA_STATUS", st)
    if st not in (200, 401, 403):
        raise Halt("RA_FAIL")
    row_delta_or_halt(src, before, "RA")
    st, body, _c, _f = http_call(
        localhost_ai("/v1/prediction-runs"),
        method="POST",
        body=b'{"race_id":"20260719_hanshin_11"}',
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    emit("POST_PREDICTION_RUNS_PROBE", "YES")
    emit("POST_PREDICTION_RUNS_STATUS", st)
    code = ""
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        code = str(body["error"].get("code") or "")
    emit("POST_PREDICTION_RUNS_ERROR_CODE", code)
    if st != 503 or code != "PREDICTION_RUNS_DISABLED":
        raise Halt("POST_NOT_DISABLED")
    row_delta_or_halt(src, before, "DISABLED_POST")
    emit("PRED_ROW_DELTA_TOTAL", 0)
    forbidden = [c for c in STATE.http_calls if c[0] == "POST" and "/v1/prediction-runs" not in c[1]]
    if forbidden:
        raise Halt("POST_REFUSED")
    emit("POST_WRITE", "NO")
    emit("GET_UI_CONVERSATION_RA_CHALLENGE_CHANGED", "UNCHECKED")
    emit("INTERNAL_REGRESSION_PASS", "YES")


def can_run_public_smoke() -> bool:
    if test_mode():
        return (os.environ.get("OWNER_DEPLOY_TEST_PUBLIC_SMOKE") or "").strip() == "1"
    return True


def run_public_smoke() -> None:
    emit("SITE_UI_VISUAL_CHECKED", "NO")
    if not can_run_public_smoke():
        emit("PUBLIC_SMOKE", "SKIPPED")
        emit("PENDING_PUBLIC_SMOKE", "YES")
        return
    for origin in PUBLIC_ORIGINS:
        for path in PUBLIC_STATIC_PATHS + PUBLIC_API_PATHS:
            url = origin + path
            st, payload, ctype, _f = http_call(url, headers={"Accept": "*/*"})
            if path in PUBLIC_STATIC_PATHS:
                if st != 200 or "html" not in (ctype or "").lower():
                    raise Halt("PUBLIC_SMOKE_FAIL")
                text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else str(payload)
                if not all(token in text for token in SITE_IDENTIFIERS):
                    raise Halt("PUBLIC_STATIC_IDENTITY_FAIL")
            elif path == "/api/health":
                if st != 200 or not isinstance(payload, dict) or payload.get("ok") is not True:
                    raise Halt("PUBLIC_SMOKE_FAIL")
            elif path == "/api/predictions":
                if st not in (200, 503):
                    raise Halt("PUBLIC_SMOKE_FAIL")
    emit("PUBLIC_SMOKE", "PASS")
    emit("PENDING_PUBLIC_SMOKE", "NO")


def verify_ops_unchanged(root: Path) -> None:
    for item in OPS_TARGETS:
        dest = lexical_join(root, item["rel"])
        got = file_sha_nofollow(dest)
        if got != STATE.ops_sha.get(item["rel"]):
            raise Halt("OPS_CHANGED")
    emit("OPS_UNCHANGED", "YES")


def fail_closed(code: str) -> int:
    try:
        if STATE.files_replaced and not STATE.restored:
            restore_code_only()
            maybe_recovery_restart()
    except Halt as inner:
        emit("RESTORE_HALT", inner.code)
    emit("SCHEMA_ROLLBACK", "NO")
    emit("MIGRATE", "NO")
    emit("022_REAPPLY", "NO")
    emit("ENV_CHANGED", "NO")
    emit("SYSTEMD_CHANGED", "NO")
    emit("DEPLOY_EXECUTED", "YES" if STATE.files_replaced and not STATE.restored else "NO")
    emit("FILES_REPLACED", STATE.files_replaced)
    emit("RESTART_EXECUTED", STATE.restart_executed)
    emit("RECOVERY_RESTART_EXECUTED", STATE.recovery_restart_executed)
    emit("CODE_RESTORED", STATE.restored)
    emit("POST_CODE_PRODUCTION_DEPLOYED", "NO")
    emit("OWNER_DEPLOY_APPROVED", "NO")
    emit("PRODUCTION_CODE_DEPLOY_ALLOWED", "NO")
    emit("OWNER_DEPLOY_STATUS", "FAIL")
    emit("HALT_REASON", code)
    emit("AUDIT_CLOSED", "YES")
    STATE.audit_closed = True
    return 2


def run() -> int:
    STATE.deadline = Deadline(remote_hard_deadline_s())
    emit("PACK", PACK)
    emit("KIND", "OWNER_STEP1_CODE_DEPLOY_EXECUTION_V3")
    emit("PACK_VERSION", "v3")
    emit("ROOT_CAUSE_ADDRESSED", "POST_RESTART_STARTUP_WAIT_INSUFFICIENT")
    emit("V1_OWNER_DEPLOY_PS1_RERUN_ALLOWED", "NO")
    emit("V2_OWNER_DEPLOY_PS1_RERUN_ALLOWED", "NO")
    emit("HUNK_ONLY_V3_ZIP_SHA256", HUNK_ONLY_V3_ZIP_SHA256)
    emit("MAIN_PY_CANDIDATE_SHA256", MAIN_PY_CANDIDATE_SHA256)
    emit("WHOLESALE_MAIN_PY_REPLACE", "NO")
    emit("MIGRATE", "NO")
    emit("022_REAPPLY", "NO")
    emit("POST_WRITE", "NO")
    emit("SCHEMA_ROLLBACK", "NO")
    emit("SUDO_USED", "PAYLOAD_SUDO_N_RESTART_ONLY")
    emit("SCP_USED", "NO")
    emit("ENV_CHANGED", "NO")
    emit("SYSTEMD_CHANGED", "NO")
    emit("LIVE_OPS_DEPLOY", "NO")
    emit("REMOTE_HARD_DEADLINE_S", int(deadline().hard_s) if not test_mode() else deadline().hard_s)
    emit("WRAPPER_TIMEOUT_MS", WRAPPER_TIMEOUT_MS)
    emit("HTTP_MAX_INTERNAL_HEALTH_BYTES", HTTP_MAX_INTERNAL_HEALTH_BYTES)
    emit("HTTP_MAX_INTERNAL_LIST_BYTES", HTTP_MAX_INTERNAL_LIST_BYTES)
    emit("HTTP_MAX_INTERNAL_DETAIL_BYTES", HTTP_MAX_INTERNAL_DETAIL_BYTES)
    emit("HTTP_MAX_PUBLIC_JSON_BYTES", HTTP_MAX_PUBLIC_JSON_BYTES)
    emit("HTTP_MAX_PUBLIC_HTML_BYTES", HTTP_MAX_PUBLIC_HTML_BYTES)
    emit("READINESS_POLL_TIMEOUT_S", READINESS_POLL_TIMEOUT_S)
    emit("READINESS_POLL_INTERVAL_S", READINESS_POLL_INTERVAL_S)
    emit("READINESS_HTTP_TIMEOUT_S", READINESS_HTTP_TIMEOUT_S)
    emit("READINESS_MAX_ATTEMPTS", READINESS_MAX_ATTEMPTS)
    emit("DEPLOY_PHASE", PHASE_NOT_STARTED)
    emit("DEPLOY_EXECUTED", "NO")
    emit("RESTART_EXECUTED", "NO")
    emit("SITE_UI_VISUAL_CHECKED", "NO")
    emit("GET_UI_CONVERSATION_RA_CHALLENGE_CHANGED", "UNCHECKED")
    emit("PRODUCTION_CODE_DEPLOY_ALLOWED", "NO")
    emit("OWNER_DEPLOY_APPROVED", "NO")
    emit("POST_CODE_PRODUCTION_DEPLOYED", "NO")
    if not wrapper_budget_ok():
        raise Halt("WRAPPER_TIMEOUT_SHORTER_THAN_REMOTE")
    refuse_unapproved()
    STATE.deploy_phase = PHASE_PRECHECKS
    emit("DEPLOY_PHASE", PHASE_PRECHECKS)
    collect_production_env(after=False)
    root = win5_root()
    emit("WIN5_ROOT", str(root))
    src = canonical_source()
    if (not test_mode()) and str(src.resolve()) != CANONICAL_SOURCE:
        raise Halt("REFUSED_NON_CANONICAL_SOURCE")
    if not src.is_file():
        raise Halt("SOURCE_MISSING")
    verify_schema_readonly(src, prefix="PRE_")
    verify_ops_live(root)
    verify_must_absent(root)
    verify_preconditions(root)
    candidates = extract_candidates()
    backup_targets(root)
    stage_replace(root, candidates)
    verify_schema_readonly(src, prefix="POST_REPLACE_")
    verify_ops_unchanged(root)
    collect_production_env(after=True)
    restart_once("DEPLOY")
    if test_fail_mode() == "after_restart":
        raise Halt("INJECTED_AFTER_RESTART")
    wait_until_ready()
    verify_schema_readonly(src, prefix="POST_")
    check_internal_regression(src)
    run_public_smoke()
    collect_production_env(after=True)
    verify_ops_unchanged(root)
    STATE.deploy_phase = PHASE_VERIFIED
    emit("DEPLOY_PHASE", PHASE_VERIFIED)
    emit("DEPLOY_EXECUTED", "YES")
    emit("FILES_REPLACED", "YES")
    emit("RESTART_EXECUTED", "YES")
    emit("DEPLOY_RESTART_COUNT", 1)
    emit("RECOVERY_RESTART_COUNT", 0)
    public_pending = (not can_run_public_smoke()) or (
        test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_PUBLIC_SMOKE") or "").strip() != "1"
    )
    if test_mode() and (os.environ.get("OWNER_DEPLOY_TEST_PUBLIC_SMOKE") or "").strip() != "1":
        emit("POST_DEPLOY_REGRESSION_PASS", "PENDING_PUBLIC_SMOKE")
        emit("OWNER_DEPLOY_STATUS", "PENDING_PUBLIC_SMOKE")
        emit("POST_CODE_PRODUCTION_DEPLOYED", "NO")
        emit("AUDIT_CLOSED", "YES")
        STATE.audit_closed = True
        return 0
    emit("POST_DEPLOY_REGRESSION_PASS", "YES")
    emit("OWNER_DEPLOY_STATUS", "SUCCESS")
    emit("POST_CODE_PRODUCTION_DEPLOYED", "NO")
    emit("PRODUCTION_CODE_DEPLOY_ALLOWED", "NO")
    emit("OWNER_DEPLOY_APPROVED", "NO")
    emit("AUDIT_CLOSED", "YES")
    STATE.audit_closed = True
    return 0 if not public_pending else 0


def main() -> int:
    try:
        return run()
    except Halt as exc:
        return fail_closed(exc.code)


if __name__ == "__main__":
    raise SystemExit(main())
