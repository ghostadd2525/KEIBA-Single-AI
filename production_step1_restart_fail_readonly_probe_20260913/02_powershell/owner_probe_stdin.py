#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single SSH stdin payload for step1 RESTART_FAIL read-only probe. Pregenerated. Do not concatenate."""
from __future__ import annotations

import hashlib
import json
import os
import re
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

PACK = "production_step1_restart_fail_readonly_probe_20260913"
REPO_ROOT = "/home/ubuntu/KEIBA-Single-AI"
WIN5_ROOT = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai"
CANONICAL_SOURCE = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db"
BACKUP_DIR_CANON = "/home/ubuntu/KEIBA-Single-AI/var/code_backups/20260913T061824Z"
APPROVAL = "OWNER_READONLY_STEP1_PROBE_APPROVED"
RESTART_UNIT = "expect-ai.service"
PARTIAL_INDEX = "uq_predictions_idempotency_key_not_null"
RACE_INDEX = "idx_predictions_race"
PERSIST_022 = "022_prediction_run_idempotency"
PERSIST_019 = "019_prediction_run_idempotency"
MAIN_PY_CANDIDATE_SHA256 = "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c"
LIVE_MAIN_PY_SHA256 = "7486a9ad7578e9ccdf883eaaac85f0b0de7ba329e286302b8d2f57db81d79235"
LIVE_MAIN_PY_SIZE = 45983
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
REMOTE_HARD_DEADLINE_S = 180
WRAPPER_TIMEOUT_MS = 300000
DRAIN_WAIT_MS = 20000
KILL_DRAIN_WAIT_MS = 8000
SAFETY_BUFFER_MS = 40000
HTTP_LOCAL_TIMEOUT_S = 3
SUBPROCESS_TIMEOUT_S = 8
JOURNALCTL_TIMEOUT_S = 30
HTTP_MAX_INTERNAL_HEALTH_BYTES = 65536
JOURNAL_MAX_BYTES = 65536
SUDO_NL_MAX_BYTES = 8192
TRANSCRIPT_PRED_ROW_COUNT = 344
WINDOW_START_UTC = datetime(2026, 9, 13, 6, 17, 0, tzinfo=timezone.utc)
WINDOW_END_UTC = datetime(2026, 9, 13, 6, 22, 0, tzinfo=timezone.utc)
FILES_REPLACED_UTC = datetime(2026, 9, 13, 6, 18, 24, tzinfo=timezone.utc)
JOURNAL_SINCE = "2026-09-13 06:17:00"
JOURNAL_UNTIL = "2026-09-13 06:22:00"
WATCHED_ENV_KEYS = (
    "PREDICTION_RUNS_ENABLED",
    "EXPECT_AI_ALLOW_MIGRATION_022",
    "EXPECT_AI_ALLOW_MIGRATION_019",
)
SYSTEMCTL_SHOW_PROPERTIES = (
    "Id,LoadState,ActiveState,SubState,MainPID,FragmentPath,User,Group,"
    "ActiveEnterTimestamp,ActiveEnterTimestampUSec,InactiveEnterTimestamp,"
    "NRestarts,Result,ExecMainStartTimestamp,Environment,EnvironmentFiles"
)
MUTATE_TOKENS = {
    "restart",
    "reload",
    "try-restart",
    "reload-or-restart",
    "start",
    "stop",
    "enable",
    "disable",
    "edit",
    "daemon-reload",
    "kill",
    "set-environment",
    "unset-environment",
    "mask",
    "unmask",
    "reset-failed",
}
SUDO_NL_ARGV = ("sudo", "-n", "-l")
SUDO_NL_U_ARGV = ("sudo", "-n", "-l", "-U", "ubuntu")
SECRET_LINE_RE = re.compile(
    r"(AWS_|SECRET|TOKEN|PASSWORD|API_KEY|AUTHORIZATION|BEARER|"
    r"EXPECT_AI_API|X-AI-Key|Environment=)",
    re.IGNORECASE,
)
BASE64_LINE_RE = re.compile(r"^[A-Za-z0-9+/]{80,}={0,2}$")
REQUEST_BODY_RE = re.compile(
    r"(request body|\"body\"\s*:|POST /|bundle_json|prompt\"\s*:)",
    re.IGNORECASE,
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
DEPLOY_TARGETS = (
    {
        "rel": "app/main.py",
        "pre": "LIVE_SHA",
        "live": "7486a9ad7578e9ccdf883eaaac85f0b0de7ba329e286302b8d2f57db81d79235",
    },
    {
        "rel": "app/data/db.py",
        "pre": "LIVE_SHA",
        "live": "8a86f514b1b08fde9a90a71acc99eac3f6fc9c2aeae200e8787721093592ef1a",
    },
    {
        "rel": "app/data/repository/__init__.py",
        "pre": "LIVE_SHA",
        "live": "557713a95b0e9f5a8f798eeb5e525c85adab3063b2e6529ee0be2155bb29992b",
    },
    {
        "rel": "app/core/feature_loader_bridge.py",
        "pre": "LIVE_SHA",
        "live": "e06e6ee971e2ae8d07bbcee4501ab9024052de52dd119ea007cb71481ae5272e",
    },
    {
        "rel": "app/data/migrations/022_prediction_run_idempotency.sql",
        "pre": "ABSENT",
        "live": "",
    },
    {"rel": "app/predictions/__init__.py", "pre": "ABSENT", "live": ""},
    {"rel": "app/predictions/guards.py", "pre": "ABSENT", "live": ""},
    {"rel": "app/predictions/runs.py", "pre": "ABSENT", "live": ""},
    {"rel": "app/predictions/feature_pin.py", "pre": "ABSENT", "live": ""},
    {"rel": "app/predictions/provenance.py", "pre": "ABSENT", "live": ""},
    {"rel": "app/predictions/snapshot.py", "pre": "ABSENT", "live": ""},
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
    probe_phase = "NOT_STARTED"
    probe_executed = False
    audit_closed = False
    findings: list[str] = []
    ai_port = 8000
    unit = RESTART_UNIT
    deadline: Deadline | None = None
    cmd_log: list[str] = []
    systemd: dict[str, str] = {}
    restore_disk_match = False
    main_py_still_candidate = False
    flags_unset_or_0 = False
    schema_pass = False
    health_ok = False
    row_delta = None
    sudo_nl_status = "UNKNOWN"
    systemd_show_ok = False


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


def note(code: str) -> None:
    if code not in STATE.findings:
        STATE.findings.append(code)
    emit("FINDING", code)


def test_mode() -> bool:
    return (os.environ.get("OWNER_PROBE_PACK_TEST") or "").strip() == "1"


def remote_hard_deadline_s() -> float:
    if test_mode():
        raw = (os.environ.get("OWNER_PROBE_TEST_DEADLINE_S") or "").strip()
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
        root = (os.environ.get("OWNER_PROBE_TEST_ROOT") or "").strip()
        if not root:
            raise Halt("TEST_ROOT_UNSET")
        return Path(root)
    return Path(REPO_ROOT)


def win5_root() -> Path:
    return repo_root() / "services" / "win5-ai"


def canonical_source() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_PROBE_TEST_SRC") or "").strip()
        if override:
            return Path(override)
    return Path(CANONICAL_SOURCE)


def backup_dir() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_PROBE_TEST_BACKUP_DIR") or "").strip()
        if override:
            return Path(override)
    return Path(BACKUP_DIR_CANON)


def refuse_unapproved() -> None:
    if (os.environ.get(APPROVAL) or "").strip() != "1":
        raise Halt("OWNER_READONLY_STEP1_PROBE_APPROVED_UNSET")
    if (os.environ.get("OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED") or "").strip() == "1":
        emit("DEPLOY_APPROVAL_PRESENT", "YES")
        emit("DEPLOY_APPROVAL_IGNORED", "YES")


def _flag_01(raw: str | None) -> int:
    return 1 if (raw or "").strip().lower() in ("1", "true", "yes", "on") else 0


def file_sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify_main_py(sha: str) -> str:
    if sha == LIVE_MAIN_PY_SHA256:
        return "LIVE"
    if sha == MAIN_PY_CANDIDATE_SHA256:
        return "CANDIDATE"
    return "OTHER"


def open_regular(path: Path, flags: int = os.O_RDONLY) -> int:
    if flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC):
        raise Halt("WRITE_REFUSED")
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
    if p.is_absolute() or any(part == ".." for part in p.parts):
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


def argv_is_sudo_nl(args: list[str]) -> bool:
    t = tuple(args)
    return t in (SUDO_NL_ARGV, SUDO_NL_U_ARGV)


def guard_argv(args: list[str]) -> None:
    if argv_is_sudo_nl(args):
        return
    if any(a == "sudo" or str(a).startswith("sudo") for a in args):
        raise Halt("SUDO_REFUSED")
    base = os.path.basename(str(args[0])) if args else ""
    if base == "systemctl":
        for a in args[1:]:
            if a in MUTATE_TOKENS or a.lstrip("-") in MUTATE_TOKENS:
                raise Halt("SYSTEMCTL_MUTATE_REFUSED")
    if base in ("kill", "systemctl-kill"):
        raise Halt("SYSTEMCTL_MUTATE_REFUSED")
    for a in args:
        if a in ("restart", "reload") and base != "echo":
            if base == "systemctl" or a in MUTATE_TOKENS:
                raise Halt("SYSTEMCTL_MUTATE_REFUSED")


def _test_cmd_result(args: list[str]) -> tuple[int, str, str]:
    key = " ".join(args)
    log_path = (os.environ.get("OWNER_PROBE_TEST_CMD_LOG") or "").strip()
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(key + "\n")
    if args[:2] == ["systemctl", "show"]:
        return 0, os.environ.get("OWNER_PROBE_TEST_SYSTEMD_SHOW") or "", ""
    if args[:2] == ["systemctl", "--version"]:
        return 0, os.environ.get("OWNER_PROBE_TEST_SYSTEMCTL_VERSION") or "systemd 249\n", ""
    if tuple(args) == SUDO_NL_ARGV or tuple(args) == SUDO_NL_U_ARGV:
        rc = int((os.environ.get("OWNER_PROBE_TEST_SUDO_NL_RC") or "0").strip() or "0")
        body = os.environ.get("OWNER_PROBE_TEST_SUDO_NL") or ""
        return rc, body, ""
    if args and os.path.basename(args[0]) == "journalctl":
        return 0, os.environ.get("OWNER_PROBE_TEST_JOURNAL") or "", ""
    if args == ["id"]:
        return 0, os.environ.get("OWNER_PROBE_TEST_ID") or "uid=1000(ubuntu) gid=1000(ubuntu)\n", ""
    return 1, "", "unhandled-test-cmd"


def run_cmd(args: list[str], *, timeout_s: float | None = None) -> tuple[int, str, str]:
    guard_argv(args)
    STATE.cmd_log.append(" ".join(args))
    if test_mode():
        return _test_cmd_result(args)
    try:
        default_t = float(JOURNALCTL_TIMEOUT_S if (args and os.path.basename(args[0]) == "journalctl") else SUBPROCESS_TIMEOUT_S)
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
        return int(p.returncode), (p.stdout or ""), (p.stderr or "")
    except Halt:
        raise
    except subprocess.TimeoutExpired:
        return 124, "", "TIMEOUT"
    except Exception:
        return 1, "", ""


def redact_text(text: str, *, cap: int) -> str:
    out_lines: list[str] = []
    used = 0
    for line in (text or "").splitlines():
        if SECRET_LINE_RE.search(line) or REQUEST_BODY_RE.search(line):
            line = "REDACTED_SECRET_OR_REQUEST_LINE"
        elif BASE64_LINE_RE.match(line.strip()):
            line = "REDACTED_BASE64_LINE"
        if used + len(line) + 1 > cap:
            out_lines.append("REDACTED_TRUNCATED")
            break
        out_lines.append(line)
        used += len(line) + 1
    return "\n".join(out_lines)


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
    rows = -1
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % path.resolve().as_posix(), uri=True)
    except sqlite3.Error:
        emit("%sSCHEMA_READONLY_PASS" % prefix, "NO")
        note("SCHEMA_OPEN_FAIL")
        STATE.schema_pass = False
        return rows
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
        ok = True
        if PERSIST_019 in have:
            note("HAS_PERSIST_019")
            ok = False
        if len(migrations) != 23 or have != owner or missing or extra:
            note("SCHEMA_MIGRATIONS_MISMATCH")
            ok = False
        if cols != list(OWNER_PRED_COLUMNS):
            note("PREDICTIONS_COLUMNS_MISMATCH")
            ok = False
        if inspect_index(conn) != "ok":
            note("PARTIAL_UNIQUE_MISMATCH")
            ok = False
        if inspect_race_index(conn) != "ok":
            note("EXISTING_INDEX_MISSING_OR_MISMATCH")
            ok = False
        STATE.schema_pass = ok
        emit("%sSCHEMA_READONLY_PASS" % prefix, "YES" if ok else "NO")
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


def parse_assignment_blob(blob: str, *, split_null: bool) -> dict[str, str]:
    out: dict[str, str] = {}
    raw = blob.replace("\n", "\0") if split_null else blob
    parts = raw.split("\0") if split_null else raw.split()
    wanted = set(WATCHED_ENV_KEYS)
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


def read_proc_environ(pid: str) -> tuple[bool, dict[str, str]]:
    if not pid.isdigit() or int(pid) <= 0:
        return False, {}
    if test_mode():
        blob = os.environ.get("OWNER_PROBE_TEST_PROC_ENVIRON") or ""
        parsed = parse_assignment_blob(blob.replace(" ", "\0"), split_null=True) if blob else {}
        return True, parsed
    try:
        with open("/proc/%s/environ" % pid, "rb") as fh:
            blob = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return False, {}
    return True, parse_assignment_blob(blob, split_null=True)


def read_proc_comm(pid: str) -> str:
    if test_mode():
        return (os.environ.get("OWNER_PROBE_TEST_PROC_COMM") or "python3").strip()
    try:
        with open("/proc/%s/comm" % pid, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def active_enter_unix(sd: dict[str, str]) -> float | None:
    usec = (sd.get("ActiveEnterTimestampUSec") or "").strip()
    if usec.isdigit():
        val = int(usec)
        if val > 10**15:
            return val / 1e6
        if val > 10**12:
            return val / 1e6
        return float(val)
    return None


def collect_unit_and_flags() -> None:
    emit("SYSTEMCTL_RESTART", "NO")
    emit("SYSTEMCTL_RELOAD", "NO")
    emit("SYSTEMCTL_MUTATE_ISSUED", "NO")
    rc_ver, ver_out, _e = run_cmd(["systemctl", "--version"])
    emit("SYSTEMCTL_VERSION_RC", rc_ver)
    emit("SYSTEMCTL_VERSION_HEAD", (ver_out.splitlines()[0] if ver_out.strip() else ""))
    rc_id, id_out, _e = run_cmd(["id"])
    emit("ID_RC", rc_id)
    emit("ID_TEXT", redact_text(id_out.strip(), cap=512))
    rc, show, err = run_cmd(
        ["systemctl", "show", RESTART_UNIT, "--property=" + SYSTEMCTL_SHOW_PROPERTIES]
    )
    sd = parse_systemd_show(show) if rc == 0 else {}
    STATE.systemd = sd
    systemd_ok = rc == 0 and bool(sd)
    STATE.systemd_show_ok = systemd_ok
    emit("SYSTEMCTL_SHOW_AS_UBUNTU", "YES" if systemd_ok else "NO")
    emit("SYSTEMCTL_SHOW_RC", rc)
    if err:
        emit("SYSTEMCTL_SHOW_STDERR_REDACTED", redact_text(err, cap=512))
    for key in (
        "Id",
        "LoadState",
        "ActiveState",
        "SubState",
        "MainPID",
        "FragmentPath",
        "User",
        "Group",
        "ActiveEnterTimestamp",
        "ActiveEnterTimestampUSec",
        "InactiveEnterTimestamp",
        "NRestarts",
        "Result",
        "ExecMainStartTimestamp",
    ):
        emit("UNIT_%s" % key.upper(), sd.get(key, ""))
    emit("UNIT_ENVIRONMENT_DUMPED", "NO")
    pid = str(sd.get("MainPID") or "")
    proc_ok, proc = read_proc_environ(pid)
    emit("PROC_COLLECT_OK", proc_ok)
    emit("PROC_COMM", read_proc_comm(pid) if pid.isdigit() and int(pid) > 0 else "")
    files: dict[str, str] = {}
    files_ok = True
    if test_mode():
        file_blob = os.environ.get("OWNER_PROBE_TEST_ENVFILE") or ""
        files = parse_assignment_blob(file_blob.replace(" ", "\0"), split_null=True) if file_blob else {}
        files_ok = bool(file_blob) or (os.environ.get("OWNER_PROBE_TEST_FILES_OK") or "") == "1"
    else:
        for env_path in environment_file_paths(sd.get("EnvironmentFiles") or ""):
            parsed = parse_env_file(env_path)
            files.update(parsed)
    unit_env = parse_assignment_blob(sd.get("Environment") or "", split_null=False)
    merged: dict[str, str] = {}
    merged.update(files)
    merged.update(unit_env)
    merged.update(proc)
    emit("ENVFILE_COLLECT_OK", files_ok)
    emit("ENV_CHANGED", "NO")
    emit("SYSTEMD_CHANGED", "NO")
    flag_ok = True
    for key in WATCHED_ENV_KEYS:
        raw = merged.get(key)
        emit(key, raw if raw not in (None, "") else "UNSET")
        if _flag_01(raw) == 1:
            note("%s_EFFECTIVE_1" % key)
            flag_ok = False
    STATE.flags_unset_or_0 = flag_ok
    emit("FLAGS_UNSET_OR_0", flag_ok)
    STATE.unit = str(sd.get("Id") or RESTART_UNIT)
    emit("UNIT", STATE.unit)
    ts = active_enter_unix(sd)
    if ts is not None:
        enter = datetime.fromtimestamp(ts, tz=timezone.utc)
        emit("ACTIVE_ENTER_UTC", enter.isoformat())
        in_window = WINDOW_START_UTC <= enter <= WINDOW_END_UTC
        emit("ACTIVE_ENTER_IN_DEPLOY_WINDOW", in_window)
        predates = enter < FILES_REPLACED_UTC
        emit("ACTIVE_ENTER_PREDATES_FILES_REPLACED", predates)
        if in_window:
            emit("RUNNING_PROCESS_MAY_HAVE_CANDIDATE_BYTES", "YES")
        elif predates:
            emit("RUNNING_PROCESS_LIKELY_PREDEPLOY_BYTES", "YES")
        else:
            emit("RUNNING_PROCESS_MAY_HAVE_CANDIDATE_BYTES", "NO")
    else:
        emit("ACTIVE_ENTER_UTC", "UNKNOWN")
        emit("RUNNING_PROCESS_MAY_HAVE_CANDIDATE_BYTES", "UNKNOWN")


def parse_sudo_nl(text: str) -> dict[str, str]:
    blob = (text or "").lower()
    compact = " ".join(blob.split())
    has_all = "nopasswd: all" in compact or "(all) nopasswd: all" in compact
    has_unrestricted = has_all or (
        "nopasswd: /usr/bin/systemctl" in compact and "restart" not in compact
    ) or (
        "nopasswd: /bin/systemctl" in compact and "restart" not in compact
    )
    restart_needles = (
        "systemctl restart expect-ai.service",
        "/usr/bin/systemctl restart expect-ai.service",
        "/bin/systemctl restart expect-ai.service",
        "/usr/bin/systemctl restart expect-ai",
    )
    has_restart = any(n in compact for n in restart_needles)
    if has_all:
        has_restart = True
        has_unrestricted = True
    return {
        "HAS_NOPASSWD_ALL": "YES" if has_all else "NO",
        "HAS_UNRESTRICTED_SYSTEMCTL": "YES" if has_unrestricted else "NO",
        "HAS_SYSTEMCTL_RESTART_EXPECT_AI": "YES" if has_restart else "NO",
    }


def collect_sudo_nl() -> None:
    emit("SUDO_ALLOWED", "SUDO_N_L_PERMISSION_LIST_ONLY")
    rc, out, err = run_cmd(list(SUDO_NL_ARGV))
    emit("SUDO_N_L_EXIT", rc)
    STATE.sudo_nl_status = "OK" if rc == 0 else "FAIL"
    emit("SUDO_N_L_STATUS", STATE.sudo_nl_status)
    redacted = redact_text(out, cap=SUDO_NL_MAX_BYTES)
    emit("SUDO_N_L_TEXT_REDACTED_LINES", len(redacted.splitlines()) if redacted else 0)
    parsed = parse_sudo_nl(out)
    for k, v in parsed.items():
        emit("SUDO_N_L_%s" % k, v)
    if rc != 0:
        emit("SUDO_N_L_STDERR_REDACTED", redact_text(err, cap=512))
        emit("UBUNTU_RESTART_NOPASSWD", "UNKNOWN")
        note("SUDO_N_L_FAIL")
        return
    emit("UBUNTU_RESTART_NOPASSWD", parsed["HAS_SYSTEMCTL_RESTART_EXPECT_AI"])
    rc2, out2, err2 = run_cmd(list(SUDO_NL_U_ARGV))
    emit("SUDO_N_L_U_EXIT", rc2)
    if rc2 == 0:
        parsed2 = parse_sudo_nl(out2)
        emit("SUDO_N_L_U_HAS_SYSTEMCTL_RESTART_EXPECT_AI", parsed2["HAS_SYSTEMCTL_RESTART_EXPECT_AI"])
    else:
        emit("SUDO_N_L_U_STDERR_REDACTED", redact_text(err2, cap=256))


def collect_journal() -> None:
    argv = [
        "journalctl",
        "-u",
        RESTART_UNIT,
        "--since",
        JOURNAL_SINCE,
        "--until",
        JOURNAL_UNTIL,
        "--no-pager",
        "-o",
        "short-iso",
    ]
    rc, out, err = run_cmd(argv, timeout_s=float(JOURNALCTL_TIMEOUT_S))
    emit("JOURNALCTL_UNIT_RC", rc)
    emit("JOURNALCTL_TIMEOUT_S", JOURNALCTL_TIMEOUT_S)
    emit("JOURNALCTL_SINCE", JOURNAL_SINCE)
    emit("JOURNALCTL_UNTIL", JOURNAL_UNTIL)
    emit("JOURNALCTL_PYTHON3_IDENTIFIER", "NO")
    redacted = redact_text(out, cap=JOURNAL_MAX_BYTES)
    emit("JOURNAL_SNIPPET_LINES", len(redacted.splitlines()) if redacted else 0)
    lowered = redacted.lower()
    emit("JOURNAL_HAS_ACCESS_DENIED", "access denied" in lowered)
    emit("JOURNAL_HAS_INTERACTIVE_AUTH", "interactive authentication required" in lowered)
    emit("JOURNAL_HAS_FAILED_TO_RESTART", "failed to restart" in lowered)
    emit("JOURNAL_HAS_TIMED_OUT", "timed out" in lowered or "timeout" in lowered)
    emit("JOURNAL_HAS_START_LIMIT", "start-limit" in lowered)
    if redacted:
        for i, line in enumerate(redacted.splitlines()[:80], 1):
            emit("JOURNAL_LINE_%02d" % i, line)
    if rc != 0:
        emit("JOURNALCTL_STDERR_REDACTED", redact_text(err, cap=512))
        note("JOURNALCTL_UNIT_FAIL")
    hist = "UNKNOWN"
    emit("HISTORICAL_RESTART_RC", hist)
    emit("HISTORICAL_RESTART_RC_SOURCE", "NOT_IN_ORIGINAL_PACK_STDOUT")


def verify_restore_disk(root: Path) -> None:
    emit("CANDIDATE_TAR_EMBEDDED", "NO")
    emit("PROBE_WRITES", "NO")
    emit("FILES_REPLACED_THIS_PROBE", "NO")
    match = True
    for item in DEPLOY_TARGETS:
        dest = lexical_join(root, item["rel"])
        token = item["rel"].replace("/", "_")
        if is_symlink(dest):
            emit("RESTORE_%s" % token, "SYMLINK")
            note("RESTORE_SYMLINK_%s" % token)
            match = False
            continue
        present = exists_nofollow(dest)
        if item["pre"] == "LIVE_SHA":
            if not present:
                emit("RESTORE_%s" % token, "ABSENT")
                note("RESTORE_LIVE_ABSENT_%s" % token)
                match = False
                continue
            got = file_sha_nofollow(dest)
            emit("FILE_SHA_%s" % token, got)
            emit("RESTORE_%s" % token, "LIVE_SHA" if got == item["live"] else "MISMATCH")
            if item["rel"] == "app/main.py":
                kind = classify_main_py(got)
                emit("MAIN_PY_CLASS", kind)
                emit("MAIN_PY_SIZE", os.lstat(str(dest)).st_size)
                emit("MAIN_PY_STILL_CANDIDATE", kind == "CANDIDATE")
                STATE.main_py_still_candidate = kind == "CANDIDATE"
                if kind != "LIVE":
                    match = False
                    note("MAIN_PY_NOT_LIVE")
            elif got != item["live"]:
                match = False
                note("RESTORE_SHA_MISMATCH_%s" % token)
        else:
            emit("ABSENT_%s" % token, "YES" if not present else "NO")
            if present:
                match = False
                note("RESTORE_SHOULD_BE_ABSENT_%s" % token)
    STATE.restore_disk_match = match
    emit("RESTORE_DISK_MATCH", match)
    emit("DEPLOY_TARGET_COUNT", len(DEPLOY_TARGETS))


def verify_ops_live(root: Path) -> None:
    emit("LIVE_OPS_DEPLOY", "NO")
    ok = True
    for item in OPS_TARGETS:
        dest = lexical_join(root, item["rel"])
        token = item["rel"].replace("/", "_")
        if is_symlink(dest) or not exists_nofollow(dest):
            emit("OPS_SHA_%s" % token, "MISSING")
            note("OPS_SHA_MISMATCH")
            ok = False
            continue
        got = file_sha_nofollow(dest)
        emit("OPS_SHA_%s" % token, got)
        if got != item["live"]:
            note("OPS_SHA_MISMATCH")
            ok = False
    emit("OPS_SHA_VERIFIED", ok)
    emit("OPS_UNCHANGED", ok)
    emit("OPS_DEPLOYED", "NO")


def verify_must_absent(root: Path) -> None:
    ok = True
    for rel in MUST_ABSENT:
        dest = lexical_join(root, rel)
        token = rel.replace("/", "_")
        present = exists_nofollow(dest)
        emit("MUST_ABSENT_%s" % token, "ABSENT" if not present else "PRESENT")
        if present:
            ok = False
            note("MUST_ABSENT_PRESENT")
    emit("MUST_ABSENT_OK", ok)


def list_backup_dir() -> None:
    path = backup_dir()
    emit("BACKUP_DIR", str(path))
    emit("BACKUP_DIR_WRITE", "NO")
    try:
        names = sorted(os.listdir(str(path)))
        emit("BACKUP_DIR_LIST_OK", "YES")
        emit("BACKUP_DIR_ENTRY_COUNT", len(names))
        for i, name in enumerate(names[:32], 1):
            emit("BACKUP_DIR_ENTRY_%02d" % i, name)
    except OSError:
        emit("BACKUP_DIR_LIST_OK", "NO")
        note("BACKUP_DIR_LIST_FAIL")


def http_get_health() -> None:
    emit("POST", "NO")
    src = canonical_source()
    try:
        before = pred_row_count_ro(src)
    except Exception:
        before = -1
        note("PRED_ROW_COUNT_FAIL")
    emit("HEALTH_PRED_ROW_BEFORE", before)
    emit("TRANSCRIPT_PRED_ROW_COUNT", TRANSCRIPT_PRED_ROW_COUNT)
    emit("PRED_ROW_VS_TRANSCRIPT", before - TRANSCRIPT_PRED_ROW_COUNT)
    url = "http://127.0.0.1:%d/health" % int(STATE.ai_port or 8000)
    emit("HTTP_CALL", "GET http://127.0.0.1:%d/health" % int(STATE.ai_port or 8000))
    emit("HTTP_ENDPOINT_CLASS", "INTERNAL_HEALTH")
    emit("HTTP_LIMIT_BYTES", HTTP_MAX_INTERNAL_HEALTH_BYTES)
    if test_mode() and (os.environ.get("OWNER_PROBE_TEST_HTTP") or "").strip() == "1":
        fail = (os.environ.get("OWNER_PROBE_TEST_HEALTH_FAIL") or "").strip()
        if fail == "1":
            st, payload = 500, {"status": "error"}
        else:
            st, payload = 200, {"status": "ok", "db": "test"}
    else:
        deadline().require(1.0, "INSUFFICIENT_TIME_HTTP")
        req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=float(HTTP_LOCAL_TIMEOUT_S)) as resp:
                raw = resp.read(HTTP_MAX_INTERNAL_HEALTH_BYTES + 1)
                if len(raw) > HTTP_MAX_INTERNAL_HEALTH_BYTES:
                    note("HTTP_BODY_OVERSIZED")
                    raw = raw[:HTTP_MAX_INTERNAL_HEALTH_BYTES]
                st = int(resp.getcode() or 0)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except Exception:
                    payload = {}
                    note("HTTP_JSON_PARSE_FAIL")
        except urllib.error.HTTPError as exc:
            st = int(exc.code or 0)
            payload = {}
            note("HEALTH_HTTP_ERROR")
        except Exception:
            st = 0
            payload = {}
            note("HEALTH_FAIL")
    emit("HEALTH_STATUS", st)
    if isinstance(payload, dict):
        emit("HEALTH_STATUS_FIELD", payload.get("status") or "")
        emit("HEALTH_JSON_KEYS", ",".join(sorted(str(k) for k in payload.keys())))
        STATE.health_ok = st == 200 and str(payload.get("status") or "") == "ok"
    else:
        STATE.health_ok = False
    emit("HEALTH_OK", STATE.health_ok)
    if not STATE.health_ok:
        note("HEALTH_NOT_OK")
    try:
        after = pred_row_count_ro(src)
    except Exception:
        after = -1
        note("PRED_ROW_COUNT_FAIL")
    delta = after - before if before >= 0 and after >= 0 else None
    STATE.row_delta = delta
    emit("HEALTH_PRED_ROW_AFTER", after)
    emit("HEALTH_PRED_ROW_DELTA", delta if delta is not None else "UNKNOWN")
    emit("PRED_ROW_DELTA_TOTAL", delta if delta is not None else "UNKNOWN")
    if delta is None or delta != 0:
        note("PRED_ROW_DELTA_NONEZERO")


def close_audit(code: str, executed: bool) -> int:
    if STATE.audit_closed:
        return 2 if code != "OK" else 0
    STATE.audit_closed = True
    emit("PROBE_PHASE", STATE.probe_phase)
    emit("PROBE_EXECUTED", "YES" if executed else "NO")
    emit("SYSTEMCTL_MUTATE_ISSUED", "NO")
    emit("SYSTEMCTL_RESTART", "NO")
    emit("SYSTEMCTL_RELOAD", "NO")
    emit("MIGRATE", "NO")
    emit("POST", "NO")
    emit("ENV_CHANGED", "NO")
    emit("SYSTEMD_CHANGED", "NO")
    emit("OWNER_DEPLOY_PS1_RERUN", "NO")
    emit("PRODUCTION_CODE_DEPLOY_ALLOWED", "NO")
    emit("POST_CODE_PRODUCTION_DEPLOYED", "NO")
    emit("REAPPLY_ALLOWED", "NO")
    emit("DIAGNOSIS_COMPLETE", "YES" if executed else "NO")
    emit("RESTORE_DISK_MATCH", STATE.restore_disk_match)
    emit("MAIN_PY_STILL_CANDIDATE", STATE.main_py_still_candidate)
    emit("FLAGS_UNSET_OR_0", STATE.flags_unset_or_0)
    emit("SCHEMA_READONLY_PASS", STATE.schema_pass)
    emit("FINDING_COUNT", len(STATE.findings))
    emit("HALT_REASON", code)
    emit("OWNER_PROBE_STATUS", "PASS" if code == "OK" else "FAIL")
    emit("AUDIT_CLOSED", "YES")
    return 2 if code != "OK" else 0


def run() -> int:
    emit("PACK", PACK)
    emit("KIND", "OWNER_READONLY_RESTART_FAIL_STATE_PROBE")
    emit("STEP1_DEPLOY_RESULT", "FAILED_AND_RESTORED")
    emit("TRANSCRIPT_RECEIVED", "YES")
    emit("TRANSCRIPT_REVIEWED", "YES")
    emit("REAPPLY_ALLOWED", "NO")
    emit("OWNER_DEPLOY_PS1_RERUN_ALLOWED", "NO")
    emit("PRODUCTION_CODE_DEPLOY_ALLOWED", "NO")
    emit("POST_CODE_PRODUCTION_DEPLOYED", "NO")
    emit("MIGRATE", "NO")
    emit("022_REAPPLY", "NO")
    emit("POST", "NO")
    emit("SCHEMA_ROLLBACK", "NO")
    emit("CANDIDATE_TAR_EMBEDDED", "NO")
    emit("SYSTEMCTL_MUTATE_ISSUED", "NO")
    emit("REMOTE_HARD_DEADLINE_S", REMOTE_HARD_DEADLINE_S)
    emit("WRAPPER_TIMEOUT_MS", WRAPPER_TIMEOUT_MS)
    emit("HTTP_MAX_INTERNAL_HEALTH_BYTES", HTTP_MAX_INTERNAL_HEALTH_BYTES)
    emit("WRAPPER_BUDGET_OK", wrapper_budget_ok())
    emit("PROBE_PHASE", STATE.probe_phase)
    emit("PROBE_EXECUTED", "NO")
    refuse_unapproved()
    deadline()
    STATE.probe_phase = "COLLECTING"
    emit("PROBE_PHASE", STATE.probe_phase)
    root = win5_root()
    emit("WIN5_ROOT", str(root))
    src = canonical_source()
    emit("CANONICAL_SOURCE", str(src))
    collect_unit_and_flags()
    collect_sudo_nl()
    collect_journal()
    verify_restore_disk(root)
    verify_ops_live(root)
    verify_must_absent(root)
    list_backup_dir()
    verify_schema_readonly(src, prefix="")
    http_get_health()
    STATE.probe_phase = "COMPLETE"
    STATE.probe_executed = True
    emit("PROBE_PHASE", STATE.probe_phase)
    emit("PROBE_EXECUTED", "YES")
    if STATE.findings:
        return close_audit(STATE.findings[0], True)
    return close_audit("OK", True)


def main() -> int:
    try:
        return run()
    except Halt as exc:
        emit("OWNER_PROBE_STATUS", "FAIL")
        return close_audit(exc.code, STATE.probe_executed)
    except Exception as exc:
        emit("OWNER_PROBE_STATUS", "FAIL")
        emit("UNHANDLED", type(exc).__name__)
        return close_audit("UNHANDLED", STATE.probe_executed)


if __name__ == "__main__":
    raise SystemExit(main())
