#!/usr/bin/env bash
# Read-only Production live compare. Paste on the Production SSH host.
# Do not copy files onto Production. Do not redirect this script to a file
# on the Production host. Stdout only.
# Forbids: write, restart, env change, migrate, POST, deploy, APPLY.
set -u
export LC_ALL=C

echo "===== BEGIN OWNER_READ_ONLY_LIVE_COMPARE ====="
echo "PACK=production_disabled_post_live_compare_readonly_20260912"
echo "V4_REVIEW_BUNDLE=PASS"
echo "V4_ZIP_SHA256=77ecd36924719fbcfd3cdb0a58e19fc8160013e6267201be48e1199634676f74"
echo "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
echo "OWNER_DEPLOY_APPROVED=NO"
echo "POST_CODE_PRODUCTION_DEPLOYED=NO"
echo "CURSOR_PRODUCTION_SSH=NO"
echo "THIS_SCRIPT_WRITES=NO"
echo "HOST=$(hostname 2>/dev/null || echo UNKNOWN)"
echo "WHEN_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo UNKNOWN)"

python3 - <<'PY'
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

BASE_COMMIT = "25a3f88b8aab61a5462c06efa133b21865ef6083"
MAIN_BASE = "a54f1eaa5b8540c2f08d8b0e656a3ccbb78142d4d1cb2c8951e4105f3630184e"
MAIN_CANDIDATE = "7577973c16eb7aad395cd11acae3c8ef987a3c0533924c1994ae32afeaf818e5"
DB_ORIGIN_MAIN = "8a86f514b1b08fde9a90a71acc99eac3f6fc9c2aeae200e8787721093592ef1a"
DB_CANDIDATE = "caa14ebd448a40164dab427d21b847bc85749087a103cbb2a9f49a008e126722"
UNIT = "expect-ai.service"
PERSIST_MIGRATION = "022_prediction_run_idempotency"
SUPERSEDED_019 = "019_prediction_run_idempotency"
NEW_COLS = (
    "idempotency_key",
    "persist_source",
    "input_snapshot_hash",
    "prediction_semantic_hash",
)
INDEX_NAME = "uq_predictions_idempotency_key_not_null"
WATCH_ENV = ("PREDICTION_RUNS_ENABLED", "EXPECT_AI_ALLOW_MIGRATION_022")

DEPLOY = {
    "app/main.py": MAIN_CANDIDATE,
    "app/data/db.py": DB_CANDIDATE,
    "app/data/repository/__init__.py": "70fab66425a142307eab738783e32fbb93ec8fb6859c438007c7c6cd94165f77",
    "app/core/feature_loader_bridge.py": "f3c25c7b87941138555158e051d0520fc705889e8a2a17e8889c7fc5325eae44",
    "app/data/migrations/022_prediction_run_idempotency.sql": "627910c7985276d516fbbbcc09ca15964081955452eae28ae8a773c38acf28a9",
    "app/predictions/__init__.py": "d4373c31ad5aac82a2d83a53d91bc2b95607bd891d7b9286c3c154478d5dc21c",
    "app/predictions/guards.py": "7e6d74dd77b6645364679187a325b42676cd64d6546f5576022f19d30e6dfc82",
    "app/predictions/runs.py": "d04bc99281474aa4e0e78b9951df6335f6b9995c9e7328b100afd552815f35c1",
    "app/predictions/feature_pin.py": "49794f3671589a5ec13bc622161bac8c10609ff922c51033343dca30a31fbc36",
    "app/predictions/provenance.py": "2cc2585d53a3dbdffd8c7a4dc56921aafaf4ce6cd5421d1928950a34194bb704",
    "app/predictions/snapshot.py": "2114c953b57461f73d0450384f38df2a2b086a51e53591c77cc70b448cbde5f7",
}
MUST_ABSENT = (
    "app/predictions/corpus.py",
    "app/predictions/raeval84_holdout.py",
    "app/predictions/data/raeval84_v1_holdout_race_ids.txt",
    "app/data/migrations_not_apply/019_prediction_run_idempotency.sql",
    "app/data/migrations_not_apply/README.txt",
    "app/data/migrations/019_prediction_run_idempotency.sql",
)

facts: dict[str, str] = {}
stops: list[str] = []
notes: list[str] = []


def out(msg: str) -> None:
    print(msg, flush=True)


def sh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_flag(raw: str | None) -> str:
    if raw is None:
        return "UNSET"
    val = raw.strip().lower()
    if val == "":
        return "UNSET"
    if val in {"0", "false", "no", "off"}:
        return "ZERO"
    if val in {"1", "true", "yes", "on"}:
        return "ONE"
    return "OTHER"


def systemd_show(unit: str) -> dict[str, str]:
    proc = sh("systemctl", "show", unit, "-p", "Id", "-p", "FragmentPath",
              "-p", "WorkingDirectory", "-p", "ExecStart", "-p", "Environment",
              "-p", "EnvironmentFiles", "-p", "MainPID", "-p", "User",
              "-p", "ActiveState", "-p", "UnitFileState")
    parsed: dict[str, str] = {}
    if proc.returncode != 0:
        parsed["_error"] = (proc.stderr or proc.stdout or "systemctl_show_failed").strip()
        return parsed
    for line in (proc.stdout or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            parsed[k] = v
    return parsed


def parse_env_assignments(blob: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for part in re.findall(r'(?:[A-Z0-9_]+)=(?:"[^"]*"|\'[^\']*\'|\S+)', blob):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        env[k] = v.strip().strip('"').strip("'")
    return env


def read_envfile_watched(path: str) -> dict[str, str | None]:
    found: dict[str, str | None] = {k: None for k in WATCH_ENV}
    p = Path(path)
    if not p.is_file():
        return found
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return found
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        if k in found:
            found[k] = v.strip().strip('"').strip("'")
    return found


def proc_environ_watched(pid: int) -> dict[str, str | None]:
    found: dict[str, str | None] = {k: None for k in WATCH_ENV}
    extra_path: dict[str, str | None] = {"EXPECT_AI_DB_PATH": None}
    path = Path("/proc/%d/environ" % pid)
    try:
        raw = path.read_bytes()
    except OSError:
        return {**found, **extra_path, "_error": "proc_environ_unreadable"}
    for item in raw.split(b"\0"):
        if not item or b"=" not in item:
            continue
        k, v = item.split(b"=", 1)
        try:
            key = k.decode("utf-8", "replace")
        except Exception:
            continue
        if key in found:
            found[key] = v.decode("utf-8", "replace")
        if key == "EXPECT_AI_DB_PATH":
            extra_path[key] = v.decode("utf-8", "replace")
    return {**found, **extra_path}


def discover_win5(show: dict[str, str]) -> Path | None:
    cands: list[Path] = []
    wd = (show.get("WorkingDirectory") or "").strip()
    if wd:
        cands.append(Path(wd))
        cands.append(Path(wd) / "services" / "win5-ai")
    exec_start = show.get("ExecStart") or ""
    for m in re.findall(r"(/[^ :]+)", exec_start):
        p = Path(m)
        if p.name.endswith(".py") or p.name == "run.py":
            cands.append(p.parent)
            cands.append(p.parent / "services" / "win5-ai")
        if p.is_dir():
            cands.append(p)
    cands.extend([
        Path("/home/ubuntu/KEIBA-Single-AI/services/win5-ai"),
        Path("/home/ubuntu/KEIBA-Single-AI"),
        Path("/opt/expect-ai/current/services/win5-ai"),
        Path("/opt/expect-ai/services/win5-ai"),
    ])
    seen: set[Path] = set()
    for cand in cands:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "app" / "main.py").is_file():
            return resolved
        if (resolved / "services" / "win5-ai" / "app" / "main.py").is_file():
            return resolved / "services" / "win5-ai"
    return None


def git_info(win5: Path) -> None:
    repo = None
    cur = win5
    for _ in range(6):
        if (cur / ".git").exists():
            repo = cur
            break
        if cur.parent == cur:
            break
        cur = cur.parent
    out("----- git -----")
    if repo is None:
        out("GIT_REPO=ABSENT")
        facts["GIT_REPO"] = "ABSENT"
        return
    out("GIT_REPO=%s" % repo)
    facts["GIT_REPO"] = str(repo)
    for args, key in (
        (("rev-parse", "HEAD"), "GIT_HEAD"),
        (("rev-parse", "--abbrev-ref", "HEAD"), "GIT_BRANCH"),
        (("rev-parse", "--is-inside-work-tree"), "GIT_INSIDE_WORKTREE"),
    ):
        proc = sh("git", "-C", str(repo), *args)
        val = proc.stdout.strip() if proc.returncode == 0 else "UNAVAILABLE"
        out("%s=%s" % (key, val))
        facts[key] = val
    proc = sh("git", "-C", str(repo), "status", "-sb", "--untracked-files=no")
    out("GIT_STATUS_SB=%s" % (proc.stdout.replace("\n", " | ").strip() if proc.returncode == 0 else "UNAVAILABLE"))
    proc = sh("git", "-C", str(repo), "worktree", "list")
    if proc.returncode == 0:
        for line in proc.stdout.splitlines():
            out("GIT_WORKTREE=%s" % line)
    proc = sh("git", "-C", str(repo), "cat-file", "-t", BASE_COMMIT)
    has_base = proc.returncode == 0 and proc.stdout.strip() == "commit"
    out("GIT_HAS_BASE_COMMIT_%s=%s" % (BASE_COMMIT[:8], "YES" if has_base else "NO"))
    facts["GIT_HAS_BASE_COMMIT"] = "YES" if has_base else "NO"
    if has_base:
        proc = sh("git", "-C", str(repo), "show", "%s:services/win5-ai/app/main.py" % BASE_COMMIT)
        if proc.returncode == 0:
            digest = hashlib.sha256(proc.stdout.encode("utf-8")).hexdigest()
            out("GIT_BASE_MAIN_PY_SHA256=%s" % digest)
            out("GIT_BASE_MAIN_PY_SHA256_MATCH=%s" % ("YES" if digest == MAIN_BASE else "NO"))


def main_py_class(digest: str | None) -> str:
    if digest is None:
        return "ABSENT"
    if digest == MAIN_BASE:
        return "MATCH_BASE"
    if digest == MAIN_CANDIDATE:
        return "MATCH_CANDIDATE"
    return "DIVERGENT"


def analyze_main_py(path: Path, klass: str) -> None:
    out("----- main.py compare -----")
    out("MAIN_PY_ORIGIN_MAIN_SHA256=%s" % MAIN_BASE)
    out("MAIN_PY_CANDIDATE_SHA256=%s" % MAIN_CANDIDATE)
    out("MAIN_PY_CLASS=%s" % klass)
    facts["MAIN_PY_CLASS"] = klass
    if klass == "ABSENT":
        out("MAIN_PY_HUNK_DIFF=ABSENT")
        notes.append("live main.py absent")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    has_route = "/v1/prediction-runs" in text
    has_handler = "def _handle_prediction_runs_post" in text
    has_flag = "PREDICTION_RUNS_ENABLED" in text
    import_idx = text.find("from .predictions.runs")
    if import_idx < 0:
        import_idx = text.find("import app.predictions.runs")
    gate_idx = text.find("PREDICTION_RUNS_ENABLED")
    disabled_idx = text.find("PREDICTION_RUNS_DISABLED")
    gate_before = (
        gate_idx >= 0
        and disabled_idx >= 0
        and import_idx > disabled_idx
        and "return" in text[disabled_idx:import_idx]
    ) if import_idx >= 0 else (has_flag and not has_handler)
    out("LIVE_HAS_PREDICTION_RUNS_ROUTE=%s" % ("YES" if has_route else "NO"))
    out("LIVE_HAS_HANDLER=%s" % ("YES" if has_handler else "NO"))
    out("LIVE_HAS_PREDICTION_RUNS_ENABLED=%s" % ("YES" if has_flag else "NO"))
    out("LIVE_HAS_RUNS_IMPORT=%s" % ("YES" if import_idx >= 0 else "NO"))
    if import_idx >= 0 and gate_idx >= 0:
        out("LIVE_GATE_BEFORE_RUNS_IMPORT=%s" % ("YES" if gate_before else "NO"))
        facts["LIVE_GATE_BEFORE_RUNS_IMPORT"] = "YES" if gate_before else "NO"
        if not gate_before:
            stops.append("live_main_py_imports_runs_before_disabled_gate")
    elif has_handler:
        out("LIVE_GATE_BEFORE_RUNS_IMPORT=UNKNOWN")
    else:
        out("LIVE_GATE_BEFORE_RUNS_IMPORT=ABSENT_NO_POST_CODE")
        facts["LIVE_GATE_BEFORE_RUNS_IMPORT"] = "ABSENT"
    if klass == "MATCH_BASE":
        out("MAIN_PY_HUNK_DIFF=LATER_APPLY_FULL_POST_HUNK")
        out("MAIN_PY_WHOLESALE_REPLACE_ALLOWED_LATER=YES_IF_STILL_BASE")
        facts["MAIN_PY_LATER_MODE"] = "WHOLESALE_OR_HUNK_OK"
    elif klass == "MATCH_CANDIDATE":
        out("MAIN_PY_HUNK_DIFF=NONE_ALREADY_CANDIDATE")
        out("MAIN_PY_WHOLESALE_REPLACE_ALLOWED_LATER=ALREADY_PRESENT")
        facts["MAIN_PY_LATER_MODE"] = "ALREADY_CANDIDATE"
    else:
        out("MAIN_PY_HUNK_DIFF=REQUIRED_DO_NOT_REPLACE_WHOLESALE")
        out("MAIN_PY_WHOLESALE_REPLACE_ALLOWED_LATER=NO")
        facts["MAIN_PY_LATER_MODE"] = "HUNK_ONLY"
        notes.append("live main.py SHA != origin/main and != v4 candidate; later deploy must apply POST hunk only")
    out("----- live main.py hunk-relevant lines -----")
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r"prediction-runs|PREDICTION_RUNS_ENABLED|_handle_prediction_runs_post|predictions\.runs", line):
            out("%d:%s" % (i, line.rstrip()[:240]))


def sqlite_readonly(db_path: Path) -> None:
    out("----- sqlite readonly -----")
    out("DB_PATH=%s" % db_path)
    out("DB_EXISTS=%s" % ("YES" if db_path.is_file() else "NO"))
    if not db_path.is_file():
        stops.append("db_file_absent")
        facts["SCHEMA_022"] = "UNAVAILABLE"
        return
    uri = "file:%s?mode=ro" % db_path.as_posix()
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        out("DB_OPEN=FAIL")
        out("DB_OPEN_ERROR=%s" % type(exc).__name__)
        stops.append("db_readonly_open_failed")
        return
    try:
        versions = [r[0] for r in conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()]
        out("SCHEMA_MIGRATIONS_COUNT=%s" % len(versions))
        out("SCHEMA_HAS_022=%s" % ("YES" if PERSIST_MIGRATION in versions else "NO"))
        out("SCHEMA_HAS_019_PERSIST=%s" % ("YES" if SUPERSEDED_019 in versions else "NO"))
        facts["SCHEMA_HAS_022"] = "YES" if PERSIST_MIGRATION in versions else "NO"
        if PERSIST_MIGRATION not in versions:
            stops.append("schema_022_missing")
        cols = [r[1] for r in conn.execute("PRAGMA table_info(predictions)").fetchall()]
        out("PREDICTIONS_COLUMN_COUNT=%s" % len(cols))
        for col in NEW_COLS:
            present = col in cols
            out("PRED_COL_%s=%s" % (col, "YES" if present else "NO"))
            if not present:
                stops.append("missing_col_%s" % col)
        idx_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
            (INDEX_NAME,),
        ).fetchone()
        sql = idx_sql[0] if idx_sql and idx_sql[0] else ""
        out("INDEX_SQL=%s" % (sql.replace("\n", " ") if sql else "ABSENT"))
        compact = " ".join(sql.lower().split())
        ok = (
            "unique" in compact
            and "idempotency_key" in compact
            and "where" in compact
            and "is not null" in compact
        )
        out("INDEX_CONTRACT=%s" % ("OK" if ok else ("MISMATCH" if sql else "MISSING")))
        facts["INDEX_CONTRACT"] = "OK" if ok else ("MISMATCH" if sql else "MISSING")
        if not ok:
            stops.append("idempotency_index_not_ok")
    except sqlite3.Error as exc:
        out("DB_QUERY=FAIL")
        out("DB_QUERY_ERROR=%s" % type(exc).__name__)
        stops.append("db_readonly_query_failed")
    finally:
        conn.close()


def main() -> int:
    out("----- systemd -----")
    show = systemd_show(UNIT)
    if "_error" in show:
        out("SYSTEMD_SHOW=FAIL")
        out("SYSTEMD_SHOW_DETAIL=%s" % show["_error"][:200])
        notes.append("systemctl show failed")
    else:
        out("SYSTEMD_UNIT=%s" % show.get("Id", UNIT))
        out("SYSTEMD_FRAGMENT=%s" % show.get("FragmentPath", "ABSENT"))
        out("SYSTEMD_ACTIVE=%s" % show.get("ActiveState", "UNKNOWN"))
        out("SYSTEMD_UNIT_FILE_STATE=%s" % show.get("UnitFileState", "UNKNOWN"))
        out("SYSTEMD_USER=%s" % show.get("User", "UNKNOWN"))
        out("SYSTEMD_WORKINGDIRECTORY=%s" % (show.get("WorkingDirectory") or "ABSENT"))
        out("SYSTEMD_EXECSTART=%s" % (show.get("ExecStart") or "ABSENT"))
        out("SYSTEMD_MAINPID=%s" % (show.get("MainPID") or "0"))
        envfiles = show.get("EnvironmentFiles") or ""
        out("SYSTEMD_ENVIRONMENTFILES=%s" % (envfiles or "ABSENT"))
    watched: dict[str, str] = {k: "UNSET" for k in WATCH_ENV}
    sources: dict[str, str] = {k: "none" for k in WATCH_ENV}
    unit_env = parse_env_assignments(show.get("Environment") or "")
    for k in WATCH_ENV:
        if k in unit_env:
            watched[k] = classify_flag(unit_env[k])
            sources[k] = "unit_Environment"
    envfile_paths = re.findall(r"(/[^ ]+)", show.get("EnvironmentFiles") or "")
    for ep in envfile_paths:
        got = read_envfile_watched(ep)
        for k in WATCH_ENV:
            if got.get(k) is not None:
                watched[k] = classify_flag(got[k])
                sources[k] = "EnvironmentFile"
    db_path_hint = None
    pid_s = (show.get("MainPID") or "0").strip()
    if pid_s.isdigit() and int(pid_s) > 0:
        got = proc_environ_watched(int(pid_s))
        if got.get("_error"):
            out("PROC_ENVIRON=%s" % got["_error"])
        else:
            for k in WATCH_ENV:
                if got.get(k) is not None:
                    watched[k] = classify_flag(got[k])
                    sources[k] = "process_environ"
            if got.get("EXPECT_AI_DB_PATH"):
                db_path_hint = got["EXPECT_AI_DB_PATH"]
    for k in WATCH_ENV:
        out("%s=%s" % (k, watched[k]))
        out("%s_SOURCE=%s" % (k, sources[k]))
        facts[k] = watched[k]
        if watched[k] == "ONE":
            stops.append("%s_is_ONE" % k)
        if watched[k] == "OTHER":
            notes.append("%s is OTHER (not 0/1/unset)" % k)

    out("----- paths -----")
    win5 = discover_win5(show)
    out("WIN5_ROOT=%s" % (win5 if win5 else "ABSENT"))
    facts["WIN5_ROOT"] = str(win5) if win5 else "ABSENT"
    if win5 is None:
        stops.append("win5_root_not_found")
        out("STOP_REASON=win5_root_not_found")
    else:
        repo_guess = win5.parents[1] if win5.name == "win5-ai" else win5
        out("REPO_ROOT_GUESS=%s" % repo_guess)
        out("RUNTIME_APP_MAIN=%s" % (win5 / "app" / "main.py"))
        git_info(win5)
        out("----- deploy_files existence + SHA256 -----")
        for rel, expected in DEPLOY.items():
            p = win5 / rel
            if not p.is_file():
                out("LIVE %s ABSENT expected=%s" % (rel, expected))
                facts["FILE_%s" % rel] = "ABSENT"
                continue
            digest = sha256_file(p)
            match = "MATCH_CANDIDATE" if digest == expected else "DIFFER"
            if rel == "app/main.py":
                klass = main_py_class(digest)
                match = klass
            if rel == "app/data/db.py":
                if digest == DB_CANDIDATE:
                    match = "MATCH_CANDIDATE"
                elif digest == DB_ORIGIN_MAIN:
                    match = "MATCH_ORIGIN_MAIN"
                else:
                    match = "DIVERGENT"
            out("LIVE %s %s %s" % (rel, digest, match))
            facts["FILE_%s" % rel] = match
        out("----- must-be-absent (not deploy_files) -----")
        for rel in MUST_ABSENT:
            p = win5 / rel
            state = "PRESENT" if p.is_file() else "ABSENT"
            out("LIVE %s %s" % (rel, state))
            if rel.endswith("migrations/019_prediction_run_idempotency.sql") and p.is_file():
                stops.append("active_019_persist_sql_present")
        migr = win5 / "app" / "data" / "migrations"
        if migr.is_dir():
            names = sorted(x.name for x in migr.iterdir() if x.is_file())
            out("MIGRATIONS=%s" % ",".join(names))
        main_path = win5 / "app" / "main.py"
        if main_path.is_file():
            analyze_main_py(main_path, main_py_class(sha256_file(main_path)))
        else:
            analyze_main_py(main_path, "ABSENT")

        db_candidates = []
        if db_path_hint:
            db_candidates.append(Path(db_path_hint))
        db_candidates.extend([
            win5 / "var" / "expect_ai.db",
            win5.parent.parent / "var" / "expect_ai.db",
        ])
        db_file = next((p for p in db_candidates if p.is_file()), None)
        if db_file is None:
            out("DB_PATH=ABSENT")
            stops.append("db_file_absent")
        else:
            sqlite_readonly(db_file)

    out("----- judgment -----")
    compare_incomplete = any(
        s in stops for s in (
            "win5_root_not_found",
            "db_file_absent",
            "db_readonly_open_failed",
            "db_readonly_query_failed",
        )
    )
    later_blocked = [s for s in stops if s not in {
        "win5_root_not_found",
        "db_file_absent",
        "db_readonly_open_failed",
        "db_readonly_query_failed",
    }]
    if compare_incomplete:
        compare = "STOP"
    else:
        compare = "GO"
    out("COMPARE_RESULT=%s" % compare)
    out("LATER_CODE_DEPLOY_ALLOWED=NO")
    out("OWNER_DEPLOY_APPROVED=NO")
    out("POST_CODE_PRODUCTION_DEPLOYED=NO")
    out("PREDICTION_RUNS_ENABLED_EFFECTIVE=%s" % facts.get("PREDICTION_RUNS_ENABLED", "UNKNOWN"))
    out("EXPECT_AI_ALLOW_MIGRATION_022_EFFECTIVE=%s" % facts.get("EXPECT_AI_ALLOW_MIGRATION_022", "UNKNOWN"))
    out("MAIN_PY_LATER_MODE=%s" % facts.get("MAIN_PY_LATER_MODE", "UNKNOWN"))
    if later_blocked:
        out("HARD_STOP_BEFORE_ANY_LATER_DEPLOY=YES")
        for s in later_blocked:
            out("STOP_REASON=%s" % s)
    else:
        out("HARD_STOP_BEFORE_ANY_LATER_DEPLOY=NO")
    if notes:
        for n in notes:
            out("NOTE=%s" % n)
    if compare == "GO":
        out("NEXT_FOR_OWNER=return this stdout transcript; do not deploy")
    else:
        out("NEXT_FOR_OWNER=fix evidence gaps listed in STOP_REASON; do not deploy")
    out("NEXT_STEP=OWNER_READ_ONLY_LIVE_COMPARE")
    return 0 if compare == "GO" else 2


if __name__ == "__main__":
    sys.exit(main())
PY

rc=$?
echo "===== END OWNER_READ_ONLY_LIVE_COMPARE ====="
exit "$rc"
