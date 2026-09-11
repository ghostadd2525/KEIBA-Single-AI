#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single SSH stdin payload for 022 schema APPLY. Pregenerated. Do not concatenate."""
from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PACK = "production_022_apply_owner_execution_20260911"
CANONICAL_SOURCE = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db"
BACKUP_PATH = "/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups/20260911T175303Z/expect_ai.db"
BACKUP_SHA256 = "f840b475b232fb183a74be5b5159ece7e81b99e514d3b8d71055b9ad1721b60d"
INVENTORY_SOURCE_DEV = 66305
INVENTORY_SOURCE_INO = 349935
BACKUP_DEV = 66305
BACKUP_INO = 287106
PERSIST_022 = "022_prediction_run_idempotency"
PERSIST_019 = "019_prediction_run_idempotency"
PARTIAL_INDEX = "uq_predictions_idempotency_key_not_null"
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


class Halt(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def emit(key: str, value: object) -> None:
    if value is True:
        text = "YES"
    elif value is False:
        text = "NO"
    else:
        text = str(value)
    print("%s=%s" % (key, text.replace("\n", " ")))


def test_mode() -> bool:
    return (os.environ.get("OWNER_APPLY_PACK_TEST") or "").strip() == "1"


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


def backup_path() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_APPLY_TEST_BACKUP") or "").strip()
        if override:
            return Path(override)
    return Path(BACKUP_PATH)


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
    return BACKUP_DEV, BACKUP_INO


def expected_backup_sha() -> str:
    if test_mode():
        override = (os.environ.get("OWNER_APPLY_TEST_BACKUP_SHA") or "").strip()
        if override:
            return override
    return BACKUP_SHA256


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


def verify_pre_schema(conn: sqlite3.Connection) -> int:
    migrations = migration_list(conn)
    cols = prediction_columns(conn)
    have = set(migrations)
    owner = set(OWNER_MIGRATIONS)
    emit("SCHEMA_MIGRATIONS_COUNT", len(migrations))
    emit("PREDICTIONS_COLUMN_COUNT", len(cols))
    emit("HAS_PERSIST_022", PERSIST_022 in have)
    emit("HAS_PERSIST_019", PERSIST_019 in have)
    emit("NEW_PERSIST_COLUMNS_PRESENT", sum(1 for c in NEW_COLS if c in cols))
    emit("PARTIAL_UNIQUE_INDEX_STATE", inspect_index(conn))
    rows = pred_row_count(conn)
    emit("PRED_ROW_COUNT_BEFORE", rows)
    if PERSIST_022 in have or inspect_index(conn) != "missing" or any(c in cols for c in NEW_COLS):
        raise Halt("ALREADY_APPLIED_OR_PARTIAL")
    if have != owner:
        raise Halt("MIGRATION_SET_MISMATCH")
    if cols != list(OWNER_PRED_COLUMNS):
        raise Halt("PREDICTIONS_COLUMNS_MISMATCH")
    emit("SOURCE_SCHEMA_GATE", "PASS")
    return rows


def verify_post_schema(conn: sqlite3.Connection, rows_before: int) -> None:
    migrations = migration_list(conn)
    cols = prediction_columns(conn)
    have = set(migrations)
    emit("SCHEMA_MIGRATIONS_COUNT_AFTER", len(migrations))
    emit("PREDICTIONS_COLUMN_COUNT_AFTER", len(cols))
    emit("HAS_PERSIST_022", PERSIST_022 in have)
    emit("PARTIAL_UNIQUE_INDEX_STATE", inspect_index(conn))
    rows = pred_row_count(conn)
    emit("PRED_ROW_COUNT_AFTER", rows)
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
    if inspect_index(conn) != "ok":
        raise Halt("APPLY_INDEX_MISMATCH")
    if rows != rows_before:
        raise Halt("PRED_ROW_COUNT_CHANGED")
    emit("SOURCE_SCHEMA_AFTER", "PASS")


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
    if not path.is_file():
        raise Halt("BACKUP_MISSING")
    got = file_sha(path)
    emit("BACKUP_SHA256", got)
    emit("BACKUP_SHA256_EXPECTED", expected_backup_sha())
    emit("BACKUP_SHA256_MATCH", got == expected_backup_sha())
    if got != expected_backup_sha():
        raise Halt("BACKUP_SHA_MISMATCH")
    verify_identity(path, *expected_backup_dev_ino(), "BACKUP")
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


def parse_assignment_blob(blob: str, *, split_null: bool) -> dict[str, str]:
    out: dict[str, str] = {}
    raw = blob.replace("\n", "\0") if split_null else blob
    parts = raw.split("\0") if split_null else raw.split()
    for part in parts:
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        if key in WATCHED_ENV_KEYS:
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
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
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
    return True, parse_assignment_blob(blob, split_null=True)


def collect_production_env() -> dict[str, object]:
    if test_mode() and (os.environ.get("OWNER_APPLY_TEST_ENV") or "").strip() == "1":
        show = os.environ.get("OWNER_APPLY_TEST_SYSTEMD_SHOW") or ""
        proc_blob = os.environ.get("OWNER_APPLY_TEST_PROC_ENVIRON") or ""
        file_blob = os.environ.get("OWNER_APPLY_TEST_ENVFILE") or ""
        sd = parse_systemd_show(show)
        proc_ok = bool(proc_blob) or (os.environ.get("OWNER_APPLY_TEST_PROC_OK") or "") == "1"
        proc = parse_assignment_blob(proc_blob.replace(" ", "\0"), split_null=True) if proc_blob else {}
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
            "active_state": sd.get("ActiveState") or "UNSET",
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
    info = collect_production_env()
    emit("PRODUCTION_ENV_UNIT", info["unit"])
    emit("PRODUCTION_ENV_LOAD_STATE", info["load_state"])
    emit("PRODUCTION_ENV_ACTIVE_STATE", info["active_state"])
    emit("PRODUCTION_ENV_UNIT_LOADED", "YES" if info["unit_loaded"] else "NO")
    emit("PRODUCTION_ENV_SYSTEMD_READ", info["systemd_ok"])
    emit("PRODUCTION_ENV_PROC_READ", info["proc_ok"])
    emit("PRODUCTION_ENV_FILES_READ", info["files_ok"])
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
    return eff


def apply_022(src: Path) -> None:
    if (os.environ.get("EXPECT_AI_ALLOW_MIGRATION_022") or "").strip() != "1":
        raise Halt("APPLY_WINDOW_022_UNSET")
    conn = sqlite3.connect(str(src))
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        for stmt in ALTER_SQL:
            conn.execute(stmt)
        conn.execute(INDEX_SQL)
        conn.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, datetime('now'))",
            (PERSIST_022,),
        )
        conn.commit()
    finally:
        conn.close()


def fail_closed(code: str) -> int:
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
    emit("OWNER_APPLY_STATUS", "FAIL")
    emit("APPLY_EXECUTED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("MIGRATION_MAY_PROCEED", "NO")
    emit("POST_REMAINS_DISABLED", "YES")
    emit("HALT_REASON", code)
    return 2


def main() -> int:
    emit("PACK", PACK)
    emit("APPLY_ONLY", "YES")
    emit("POST_ENABLE_IN_THIS_PACK", "NO")
    emit("SITE_SWITCH_IN_THIS_PACK", "NO")
    emit("SERVICE_CHANGE_IN_THIS_PACK", "NO")
    emit("PERSISTENT_ENV_CHANGED", "NO")
    emit("SCP_USED", "NO")
    emit("SUDO_USED", "NO")
    emit("RAW_ENVIRONMENT_LOGGED", "NO")
    emit("CANONICAL_SOURCE", CANONICAL_SOURCE)
    emit("BACKUP_PATH_CANON", BACKUP_PATH)
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    try:
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
            rows_before = verify_pre_schema(src_ro)
        finally:
            src_ro.close()
        os.environ["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
        emit("PROCESS_022_WINDOW", "OPEN")
        emit("PROCESS_ONLY_022", "YES")
        apply_022(src)
        os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
        emit("PROCESS_022_WINDOW", "CLOSED")
        src_after = sqlite3.connect("file:%s?mode=ro" % src.resolve().as_posix(), uri=True)
        try:
            src_after.execute("PRAGMA query_only=ON")
            verify_post_schema(src_after, rows_before)
        finally:
            src_after.close()
        after_st = src.stat()
        if (int(after_st.st_dev), int(after_st.st_ino)) != (int(src_st.st_dev), int(src_st.st_ino)):
            raise Halt("SOURCE_IDENTITY_CHANGED")
        verify_production_env(after=True)
        executed = (not test_mode()) and str(src.resolve()) == CANONICAL_SOURCE
        emit("OWNER_APPLY_STATUS", "SUCCESS")
        emit("APPLY_EXECUTED", executed)
        emit("MIGRATION_022_APPLIED", "YES")
        emit("POST_REMAINS_DISABLED", "YES")
        emit("PREDICTION_RUNS_ENABLED_MUST_STAY", "0")
        emit("SITE_SWITCHED", "NO")
        emit("GET_UI_CONVERSATION_RA_CHALLENGE_CHANGED", "NO")
        emit("PRODUCTION_APPLY_READY", "NO")
        emit("OWNER_APPLY_APPROVED", "NO")
        emit("MIGRATION_MAY_PROCEED", "NO")
        emit("POST_ENABLE_IS_SEPARATE_STEP", "YES")
        return 0
    except Halt as exc:
        return fail_closed(exc.code)


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
