#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production backup remote logic.

Embedded into owner_backup_stdin.py at pack-build time. Owner PS1 sends
that single pregenerated file byte-for-byte. Never dumps DB bytes.
Never applies 022. Never changes systemd or persistent env.
"""
from __future__ import annotations

import os
import sqlite3
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

CANONICAL_SOURCE = "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db"
DEST_ROOT = "/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups"
REVIEWED_CONTRACT_SHA256 = (
    "55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e"
)
PACK = "production_backup_owner_execution_v4_20260911"

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
OWNER_PRED_INDEX = "idx_predictions_race"
OWNER_PRED_INDEX_COLS = ("race_id", "created_at")
PERSIST_019 = "019_prediction_run_idempotency"
PERSIST_022 = "022_prediction_run_idempotency"
NEW_COLS = (
    "idempotency_key",
    "persist_source",
    "input_snapshot_hash",
    "prediction_semantic_hash",
)
PARTIAL_INDEX = "uq_predictions_idempotency_key_not_null"
# Owner live schema inventory identity (do not invent; these are the returned facts).
INVENTORY_SOURCE_DEV = 66305
INVENTORY_SOURCE_INO = 349935
INVENTORY_SOURCE_SIZE = 105783296
INVENTORY_SOURCE_MTIME = 1789143980
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


def _load_bc():
    if "run_contract" in globals():
        names = (
            "emit",
            "run_contract",
            "open_readonly_source",
            "schema_fingerprint",
            "compare_schema_dicts",
            "fingerprint_path",
            "file_sha",
            "production_backup_executed",
            "BackupError",
            "SHARED_DEST_DIRS",
        )
        missing = [n for n in names if n not in globals()]
        if missing:
            raise RuntimeError("contract_snapshot_missing:" + ",".join(missing))
        return SimpleNamespace(**{n: globals()[n] for n in names})
    here = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    import backup_contract as m  # type: ignore

    return m


bc = _load_bc()


class Halt(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def emit(key: str, value: object) -> None:
    bc.emit(key, value)


def test_mode() -> bool:
    return (os.environ.get("OWNER_BACKUP_PACK_TEST_SRC") or "").strip() == "1"


def inventory_dev_ino() -> tuple[int, int]:
    raw_dev = (os.environ.get("OWNER_BACKUP_TEST_INVENTORY_DEV") or "").strip()
    raw_ino = (os.environ.get("OWNER_BACKUP_TEST_INVENTORY_INO") or "").strip()
    if test_mode() and raw_dev and raw_ino:
        return int(raw_dev), int(raw_ino)
    return int(INVENTORY_SOURCE_DEV), int(INVENTORY_SOURCE_INO)


def canonical_source() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_BACKUP_TEST_SRC") or "").strip()
        if override:
            return Path(override)
    return Path(CANONICAL_SOURCE)


def dest_root() -> Path:
    if test_mode():
        override = (os.environ.get("OWNER_BACKUP_TEST_DEST_ROOT") or "").strip()
        if override:
            return Path(override)
    return Path(DEST_ROOT)


def refuse_unapproved() -> None:
    if (os.environ.get("OWNER_PRODUCTION_BACKUP_APPROVED") or "").strip() != "1":
        raise Halt("OWNER_PRODUCTION_BACKUP_APPROVED_UNSET")


def sqlite_version(conn: sqlite3.Connection) -> str:
    row = conn.execute("select sqlite_version()").fetchone()
    return str(row[0]) if row else ""


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


def index_columns(conn: sqlite3.Connection, name: str) -> list[str]:
    try:
        rows = conn.execute("PRAGMA index_info(%s)" % name).fetchall()
    except sqlite3.Error:
        return []
    ordered = sorted(rows, key=lambda r: int(r[0]))
    return [str(r[2] or "") for r in ordered]


def index_sql(conn: sqlite3.Connection, name: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
        (name,),
    ).fetchone()
    return str(row[0] or "") if row and row[0] else ""


def verify_owner_schema(conn: sqlite3.Connection) -> None:
    ver = sqlite_version(conn)
    emit("SQLITE_VERSION", ver)
    emit("SQLITE_VERSION_RECORDED", bool(ver))
    emit("INVENTORY_SQLITE_VERSION", "3.45.1")
    migrations = migration_list(conn)
    emit("SCHEMA_MIGRATIONS_COUNT", len(migrations))
    emit("OWNER_MIGRATION_COUNT", len(OWNER_MIGRATIONS))
    owner_set = set(OWNER_MIGRATIONS)
    have_set = set(migrations)
    emit("SEEDED_MISSING_COUNT", len(owner_set - have_set))
    emit("SEEDED_EXTRA_COUNT", len(have_set - owner_set))
    emit("MIGRATION_SET_MATCH_OWNER", have_set == owner_set)
    emit("HAS_PERSIST_019", PERSIST_019 in have_set)
    emit("HAS_PERSIST_022", PERSIST_022 in have_set)
    emit("HAS_019_FINAL_PREDICTIONS", "019_final_predictions" in have_set)
    cols = prediction_columns(conn)
    emit("PREDICTIONS_COLUMN_COUNT", len(cols))
    emit("PREDICTIONS_COLUMNS_MATCH_OWNER", cols == list(OWNER_PRED_COLUMNS))
    idx_cols = index_columns(conn, OWNER_PRED_INDEX)
    emit("PREDICTIONS_INDEX_NAME", OWNER_PRED_INDEX)
    emit("PREDICTIONS_INDEX_COLS_MATCH", idx_cols == list(OWNER_PRED_INDEX_COLS))
    emit("PREDICTIONS_INDEX_SQL_PRESENT", bool(index_sql(conn, OWNER_PRED_INDEX)))
    extra_cols = [c for c in NEW_COLS if c in cols]
    emit("NEW_PERSIST_COLUMNS_PRESENT", len(extra_cols))
    names = {
        str(r[0])
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    }
    emit("PARTIAL_UNIQUE_INDEX_PRESENT", PARTIAL_INDEX in names)
    reasons = []
    if extra_cols:
        reasons.append("NEW_PERSIST_COLUMNS_PRESENT")
    if PARTIAL_INDEX in names:
        reasons.append("PARTIAL_UNIQUE_INDEX_PRESENT")
    if PERSIST_019 in have_set:
        reasons.append("HAS_PERSIST_019")
    if PERSIST_022 in have_set:
        reasons.append("HAS_PERSIST_022")
    if have_set != owner_set:
        reasons.append("MIGRATION_SET_MISMATCH")
    if cols != list(OWNER_PRED_COLUMNS):
        reasons.append("PREDICTIONS_COLUMNS_MISMATCH")
    if idx_cols != list(OWNER_PRED_INDEX_COLS):
        reasons.append("PREDICTIONS_INDEX_MISMATCH")
    if reasons:
        emit("SOURCE_SCHEMA_GATE", "HALT")
        raise Halt(reasons[0])
    emit("SOURCE_SCHEMA_GATE", "PASS")


def verify_inventory_identity(src: Path) -> os.stat_result:
    st = src.stat()
    emit("SOURCE_PATH", str(src.resolve()) if src.exists() else str(src))
    emit("SOURCE_DEV", st.st_dev)
    emit("SOURCE_INO", st.st_ino)
    emit("SOURCE_SIZE", st.st_size)
    emit("SOURCE_MTIME", int(st.st_mtime))
    emit("SOURCE_MODE", oct(stat.S_IMODE(st.st_mode)))
    inv_dev, inv_ino = inventory_dev_ino()
    emit("INVENTORY_SOURCE_DEV", inv_dev)
    emit("INVENTORY_SOURCE_INO", inv_ino)
    emit("INVENTORY_SOURCE_SIZE", INVENTORY_SOURCE_SIZE)
    emit("INVENTORY_SOURCE_MTIME", INVENTORY_SOURCE_MTIME)
    emit("INVENTORY_DEV_INO_RECORDED", "YES")
    emit("INVENTORY_DEV_INO_ABSENT", "NO")
    emit("SOURCE_SIZE_EQUALS_INVENTORY", int(st.st_size) == int(INVENTORY_SOURCE_SIZE))
    emit("SOURCE_MTIME_EQUALS_INVENTORY", int(st.st_mtime) == int(INVENTORY_SOURCE_MTIME))
    if (int(st.st_dev), int(st.st_ino)) != (int(inv_dev), int(inv_ino)):
        emit("DB_DRIFT", "YES")
        emit("NEW_READONLY_INVENTORY_REQUIRED", "YES")
        raise Halt("DB_DRIFT")
    emit("DB_DRIFT", "NO")
    emit("NEW_READONLY_INVENTORY_REQUIRED", "NO")
    return st


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
    if test_mode() and (os.environ.get("OWNER_BACKUP_TEST_ENV") or "").strip() == "1":
        show = (os.environ.get("OWNER_BACKUP_TEST_SYSTEMD_SHOW") or "")
        proc_blob = (os.environ.get("OWNER_BACKUP_TEST_PROC_ENVIRON") or "")
        file_blob = (os.environ.get("OWNER_BACKUP_TEST_ENVFILE") or "")
        sd = parse_systemd_show(show)
        proc_ok = bool(proc_blob) or (os.environ.get("OWNER_BACKUP_TEST_PROC_OK") or "") == "1"
        proc = parse_assignment_blob(proc_blob.replace(" ", "\0"), split_null=True) if proc_blob else {}
        files = parse_assignment_blob(file_blob.replace(" ", "\0"), split_null=True) if file_blob else {}
        systemd_ok = bool(show) or (os.environ.get("OWNER_BACKUP_TEST_SYSTEMD_OK") or "") == "1"
        files_ok = bool(file_blob) or (os.environ.get("OWNER_BACKUP_TEST_FILES_OK") or "") == "1"
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
        }

    unit = ""
    show_out = ""
    show_rc = 1
    for cand in SERVICE_CANDIDATES:
        for args in (
            [
                "systemctl",
                "show",
                cand,
                "--no-pager",
                "-p",
                "Id",
                "-p",
                "MainPID",
                "-p",
                "LoadState",
                "-p",
                "ActiveState",
                "-p",
                "Environment",
                "-p",
                "EnvironmentFiles",
            ],
            [
                "systemctl",
                "--user",
                "show",
                cand,
                "--no-pager",
                "-p",
                "Id",
                "-p",
                "MainPID",
                "-p",
                "LoadState",
                "-p",
                "ActiveState",
                "-p",
                "Environment",
                "-p",
                "EnvironmentFiles",
            ],
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
    }


def verify_production_env() -> None:
    info = collect_production_env()
    emit("PRODUCTION_ENV_UNIT", info["unit"])
    emit("PRODUCTION_ENV_LOAD_STATE", info["load_state"])
    emit("PRODUCTION_ENV_UNIT_LOADED", "YES" if info["unit_loaded"] else "NO")
    emit("PRODUCTION_ENV_SYSTEMD_READ", info["systemd_ok"])
    emit("PRODUCTION_ENV_PROC_READ", info["proc_ok"])
    emit("PRODUCTION_ENV_FILES_READ", info["files_ok"])
    emit("PRODUCTION_ENV_MAINPID", info["mainpid"])
    emit("PRODUCTION_ENV_FILE_PRESENT", info["env_files"])
    determined = bool(
        info["unit_loaded"]
        and info["systemd_ok"]
        and (info["proc_ok"] or not info["mainpid_set"])
        and (info["files_ok"] or not info["file_paths_configured"])
    )
    emit("PRODUCTION_ENV_DETERMINED", determined)
    if not determined:
        raise Halt("PRODUCTION_ENV_UNDETERMINED")
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
        emit("%s_SET" % key, "SET" if present else "UNSET")
        emit("%s_EFFECTIVE" % key, effective)
        emit("%s_SOURCE" % key, source)
        if effective == 1:
            raise Halt("%s_EFFECTIVE_1" % key)
    emit("PRODUCTION_ENV_GATE", "PASS")


def dedicated_dest(src: Path) -> Path:
    root = dest_root()
    src_abs = Path(os.path.abspath(str(src)))
    root_abs = Path(os.path.abspath(str(root)))
    if root_abs == src_abs or root_abs == src_abs.parent:
        raise Halt("DEST_ROOT_IS_SOURCE_PARENT")
    shared = getattr(bc, "SHARED_DEST_DIRS", set())
    if root_abs in shared:
        raise Halt("DEST_ROOT_NOT_DEDICATED")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return root_abs / stamp / "expect_ai.db"


def emit_success(src: Path, dest: Path) -> None:
    dir_mode = stat.S_IMODE(dest.parent.stat().st_mode)
    file_mode = stat.S_IMODE(dest.stat().st_mode)
    dest_conn, _info = bc.open_readonly_source(dest)
    try:
        integrity = dest_conn.execute("PRAGMA integrity_check").fetchone()
        integrity_ok = bool(integrity) and str(integrity[0]) == "ok"
        dest_fp = bc.schema_fingerprint(dest_conn)
    finally:
        dest_conn.close()
    src_fp = bc.fingerprint_path(src)
    schema_ok = bc.compare_schema_dicts(src_fp, dest_fp)
    migration_ok = src_fp["schema_migrations"] == dest_fp["schema_migrations"]
    master_ok = src_fp["master_sha256"] == dest_fp["master_sha256"]
    src_st = src.stat()
    dest_st = dest.stat()
    distinct = (src_st.st_dev, src_st.st_ino) != (dest_st.st_dev, dest_st.st_ino)
    dest_sha = bc.file_sha(dest)
    emit("OWNER_BACKUP_STATUS", "SUCCESS")
    emit("BACKUP_INTEGRITY_OK", integrity_ok)
    emit("BACKUP_SCHEMA_OK", schema_ok)
    emit("BACKUP_MIGRATION_SET_OK", migration_ok)
    emit("BACKUP_MASTER_SHA_MATCH", master_ok)
    emit("BACKUP_DEST_SHA256", dest_sha)
    emit("BACKUP_SHA256_RECORDED", bool(dest_sha))
    emit("BACKUP_DISTINCT_INODE", distinct)
    emit("BACKUP_DIR_MODE", oct(dir_mode))
    emit("BACKUP_FILE_MODE", oct(file_mode))
    executed = bc.production_backup_executed(src, True)
    emit("PRODUCTION_BACKUP_EXECUTED", executed)
    passed = integrity_ok and schema_ok and migration_ok and master_ok and distinct
    if dir_mode != 0o700 or file_mode != 0o600 or not passed:
        raise Halt("OWNER_POST_BACKUP_VERIFY_FAILED")
    emit("APPLY_PRECONDITION_BACKUP_PASS", "YES")
    emit("APPLY_FORBIDDEN_AFTER_BACKUP_FAIL", "NO")
    emit("PRODUCTION_022_APPLY_IN_THIS_PACK", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("MIGRATION_MAY_PROCEED", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")


def fail_closed(code: str) -> int:
    emit("OWNER_BACKUP_STATUS", "FAIL")
    emit("BACKUP_OK", "NO")
    emit("PRODUCTION_BACKUP_EXECUTED", "NO")
    emit("APPLY_PRECONDITION_BACKUP_PASS", "NO")
    emit("APPLY_FORBIDDEN_AFTER_BACKUP_FAIL", "YES")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("MIGRATION_MAY_PROCEED", "NO")
    emit("HALT_REASON", code)
    return 2


def main() -> int:
    emit("PACK", PACK)
    emit("BACKUP_ONLY", "YES")
    emit("MIGRATION_022_IN_THIS_PACK", "NO")
    emit("SERVICE_CHANGE_IN_THIS_PACK", "NO")
    emit("PERSISTENT_ENV_CHANGED", "NO")
    emit("SCP_USED", "NO")
    emit("DB_BYTES_ON_STDOUT", "NO")
    emit("RAW_ENVIRONMENT_LOGGED", "NO")
    emit("INVENTORY_DEV_INO_ABSENT_WITHDRAWN", "YES")
    emit("REVIEWED_CONTRACT_SHA256", REVIEWED_CONTRACT_SHA256)
    emit("CANONICAL_SOURCE", CANONICAL_SOURCE)
    emit("MIGRATION_MAY_PROCEED", "NO")
    emit("PRODUCTION_APPLY_READY", "NO")
    try:
        refuse_unapproved()
        verify_production_env()
        src = canonical_source()
        if (not test_mode()) and str(src.resolve()) != CANONICAL_SOURCE:
            raise Halt("REFUSED_NON_CANONICAL_SOURCE")
        if not src.is_file():
            raise Halt("SOURCE_MISSING")
        contract_path = None
        if "backup_contract" in sys.modules:
            contract_path = getattr(sys.modules["backup_contract"], "__file__", None)
        if contract_path:
            got = bc.file_sha(Path(contract_path))
            emit("CONTRACT_SHA256", got)
            emit("CONTRACT_SHA_MATCH", got == REVIEWED_CONTRACT_SHA256)
            if got != REVIEWED_CONTRACT_SHA256:
                raise Halt("CONTRACT_SHA_MISMATCH")
        elif "run_contract" in globals():
            emit("CONTRACT_SHA256", REVIEWED_CONTRACT_SHA256)
            emit("CONTRACT_SHA_MATCH", "STDIN_EMBEDDED")
            emit("CONTRACT_REVIEWED_SHA256", REVIEWED_CONTRACT_SHA256)
        else:
            raise Halt("CONTRACT_NOT_RESOLVED")
        st = src.stat()
        emit("SOURCE_PATH", str(src.resolve()) if src.exists() else str(src))
        emit("SOURCE_DEV", st.st_dev)
        emit("SOURCE_INO", st.st_ino)
        emit("SOURCE_SIZE", st.st_size)
        emit("SOURCE_MTIME", int(st.st_mtime))
        emit("SOURCE_MODE", oct(stat.S_IMODE(st.st_mode)))
        src_conn, _info = bc.open_readonly_source(src)
        try:
            qo = src_conn.execute("PRAGMA query_only").fetchone()
            emit("SOURCE_OPEN_QUERY_ONLY", "ON" if qo and str(qo[0]) in ("1", "on", "ON") else "NO")
            verify_owner_schema(src_conn)
        finally:
            src_conn.close()
        verify_inventory_identity(src)
        dest = dedicated_dest(src)
        emit("DEDICATED_DEST_DIR", str(dest.parent))
        emit("DEST_PATH_PLAN", str(dest))
        os.environ["ALLOW_LOCAL_SQLITE_BACKUP"] = "1"
        emit("ALLOW_LOCAL_SQLITE_BACKUP_PROCESS_ONLY", "YES")
        rc = bc.run_contract(src, dest, restore_rehearse=False)
        if rc != 0:
            return fail_closed("BACKUP_CONTRACT_FAIL")
        emit_success(src, dest)
        return 0
    except Halt as exc:
        return fail_closed(exc.code)
    except bc.BackupError as exc:
        return fail_closed(exc.code)


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
