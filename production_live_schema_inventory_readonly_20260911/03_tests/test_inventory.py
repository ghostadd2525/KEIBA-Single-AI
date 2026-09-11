#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "02_powershell" / "live_schema_inventory.py"
PS1 = ROOT / "02_powershell" / "OWNER_READONLY.ps1"
FLAGS = ROOT / "FLAGS.txt"
WIN5 = Path("/workspace/services/win5-ai/app/data/migrations")


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def build_fixture(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    for sql in sorted(WIN5.glob("0*.sql")):
        if sql.stem.startswith("022"):
            continue
        conn.executescript(sql.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES (?, datetime('now'))",
            (sql.stem,),
        )
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS final_predictions (id INTEGER PRIMARY KEY, race_id TEXT, source_race_id TEXT);"
        "CREATE TABLE IF NOT EXISTS live_020_placeholder (id INTEGER PRIMARY KEY);"
        "CREATE TABLE IF NOT EXISTS live_021_placeholder (id INTEGER PRIMARY KEY);"
        "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES ('019_final_predictions', datetime('now'));"
        "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES ('020_live_schema_unknown', datetime('now'));"
        "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES ('021_live_schema_unknown', datetime('now'));"
        "INSERT INTO predictions(race_id, engine_source, bundle_json, created_at) "
        "VALUES ('2026-07-19-01-01','real_ai','SECRET_BUNDLE','t');"
    )
    conn.commit()
    conn.close()


def main() -> int:
    failures: list[str] = []
    src = PY.read_text(encoding="utf-8")
    ast.parse(src)
    expect(True, "python_ast_parse", failures)
    expect("mode=ro" in src, "sqlite_ro", failures)
    expect("PRAGMA query_only" in src, "query_only", failures)
    expect("urllib" not in src and "http://" not in src, "no_http", failures)
    expect("INSERT INTO" not in src, "no_insert", failures)
    expect("ALTER TABLE" not in src, "no_alter", failures)
    expect("Connection.backup" not in src, "no_backup", failures)
    expect("bundle_json" not in src or "BUNDLE_JSON_EMITTED" in src, "no_bundle_select", failures)
    expect("SELECT bundle_json" not in src, "no_select_bundle", failures)
    expect("SELECT race_id" not in src, "no_select_race_id", failures)
    flags = FLAGS.read_text(encoding="utf-8")
    expect("PRODUCTION_APPLY_READY=NO" in flags, "flag_apply_no", failures)
    expect("HTTP_CALLED=NO" in flags, "flag_no_http", failures)
    expect(
        "try { if ($null -ne $stdoutTask) { [void]$stdoutTask.Wait(2000) } } catch { }"
        in PS1.read_text(encoding="utf-8"),
        "ps_brace",
        failures,
    )

    tmp = Path(tempfile.mkdtemp(prefix="schema-inv-"))
    db = tmp / "fixture.db"
    build_fixture(db)
    env = os.environ.copy()
    env["EXPECT_AI_DB_PATH"] = str(db)
    r = subprocess.run([sys.executable, str(PY)], capture_output=True, text=True, env=env)
    out = r.stdout or ""
    print(out)
    expect(r.returncode == 0, "inventory_exit0", failures)
    expect("AUDIT_STATUS=SUCCESS" in out, "audit_success", failures)
    expect("019_final_predictions" in out, "has_019_final", failures)
    expect("020_live_schema_unknown" in out, "has_020", failures)
    expect("021_live_schema_unknown" in out, "has_021", failures)
    expect("HAS_PERSIST_022=NO" in out, "persist_022_absent", failures)
    expect("CREATE TABLE" in out and "predictions" in out, "predictions_ddl", failures)
    expect("SECRET_BUNDLE" not in out, "no_bundle_value", failures)
    expect("2026-07-19-01-01" not in out, "no_race_id_value", failures)
    expect("HTTP_CALLED=NO" in out, "http_no", failures)
    expect("PRODUCTION_APPLY_READY=NO" in out, "apply_no", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d" % len(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
