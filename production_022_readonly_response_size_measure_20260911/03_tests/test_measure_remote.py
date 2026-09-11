#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local GET measurement tests. Never open live Production DB."""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS = ROOT / "02_powershell"
sys.path.insert(0, str(PS))
import owner_measure_stdin as measure  # noqa: E402

PAYLOAD = (PS / "owner_measure_stdin.py").read_bytes()
OWNER_MIGRATIONS = measure.OWNER_MIGRATIONS
OWNER_PRED_COLUMNS = measure.OWNER_PRED_COLUMNS


def expect(cond: bool, name: str, failures: list[str]) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def seed_owner_schema(path: Path, rows: int = 2) -> None:
    conn = sqlite3.connect(str(path))
    cols = ", ".join("%s TEXT" % c if c != "id" else "id INTEGER PRIMARY KEY" for c in OWNER_PRED_COLUMNS)
    conn.execute("CREATE TABLE schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE predictions(%s)" % cols)
    conn.execute("CREATE INDEX idx_predictions_race ON predictions(race_id, created_at)")
    for ver in OWNER_MIGRATIONS:
        conn.execute("INSERT INTO schema_migrations VALUES (?, 't')", (ver,))
    for i in range(rows):
        conn.execute("INSERT INTO predictions(race_id, created_at) VALUES (?, 't')", ("local-%d" % i,))
    conn.commit()
    conn.close()


def env_ok() -> dict[str, str]:
    return {
        "OWNER_MEASURE_TEST_ENV": "1",
        "OWNER_MEASURE_TEST_SYSTEMD_OK": "1",
        "OWNER_MEASURE_TEST_PROC_OK": "1",
        "OWNER_MEASURE_TEST_FILES_OK": "1",
        "OWNER_MEASURE_TEST_HTTP": "1",
        "OWNER_MEASURE_TEST_SYSTEMD_SHOW": (
            "Id=expect-ai.service\nLoadState=loaded\nMainPID=1\nEnvironment=\nEnvironmentFiles=\nActiveState=active\n"
        ),
        "OWNER_MEASURE_TEST_PROC_ENVIRON": "",
        "OWNER_MEASURE_TEST_ENVFILE": "",
        "OWNER_MEASURE_TEST_HEALTH_JSON": '{"status":"ok"}',
        "OWNER_MEASURE_TEST_GET_JSON": '{"ok":true,"data":[{"race_id":"local-fixture-1"}],"meta":{"count":1}}',
        "OWNER_MEASURE_TEST_DETAIL_JSON": '{"ok":true,"data":{"x":1},"meta":{}}',
    }


def capture_main(env: dict[str, str]) -> tuple[int, str]:
    full = os.environ.copy()
    for k in list(full):
        if k.startswith("OWNER_MEASURE_") or k in (
            "OWNER_PRODUCTION_022_MEASURE_APPROVED",
            "OWNER_PRODUCTION_022_APPLY_APPROVED",
            "EXPECT_AI_ALLOW_MIGRATION_022",
            "PREDICTION_RUNS_ENABLED",
        ):
            full.pop(k, None)
    full.update(env)
    full["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run([sys.executable, "-"], input=PAYLOAD, capture_output=True, env=full)
    out = (p.stdout or b"").decode("utf-8", errors="replace")
    return int(p.returncode), out


def last_kv(out: str, key: str) -> str | None:
    found = None
    prefix = key + "="
    for line in out.splitlines():
        if line.startswith(prefix):
            found = line[len(prefix):]
    return found


def main() -> int:
    failures: list[str] = []
    expect(measure.MEASURE_INTERNAL_LIST_MAX_BYTES == 8388608, "list_cap_8mib", failures)
    expect(measure.MEASURE_PUBLIC_JSON_MAX_BYTES == 262144, "public_json_cap_separate", failures)
    expect(measure.MEASURE_INTERNAL_LIST_MAX_BYTES != 262144, "list_cap_not_just_256k", failures)
    expect(measure.INVENTORY_SOURCE_SIZE == 105783296, "inventory_size_embedded", failures)
    expect(measure.MEASURE_INTERNAL_LIST_MAX_BYTES * 8 <= measure.INVENTORY_SOURCE_SIZE, "list_cap_lt_inventory_db", failures)

    rc, out = capture_main({})
    expect(rc == 2, "refuse_unapproved", failures)
    expect("HALT_REASON=OWNER_PRODUCTION_022_MEASURE_APPROVED_UNSET" in out, "halt_unapproved", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "NO", "unapproved_apply_no", failures)

    tmp = Path(tempfile.mkdtemp(prefix="measure022-"))
    src = tmp / "src.db"
    bak = tmp / "bak.db"
    seed_owner_schema(src)
    shutil.copy2(src, bak)
    sst = src.stat()
    bst = bak.stat()
    bsha = measure.file_sha(bak)
    base = {
        "OWNER_PRODUCTION_022_MEASURE_APPROVED": "1",
        "OWNER_MEASURE_PACK_TEST": "1",
        "OWNER_MEASURE_TEST_SRC": str(src),
        "OWNER_MEASURE_TEST_BACKUP": str(bak),
        "OWNER_MEASURE_TEST_SOURCE_DEV": str(sst.st_dev),
        "OWNER_MEASURE_TEST_SOURCE_INO": str(sst.st_ino),
        "OWNER_MEASURE_TEST_BACKUP_DEV": str(bst.st_dev),
        "OWNER_MEASURE_TEST_BACKUP_INO": str(bst.st_ino),
        "OWNER_MEASURE_TEST_BACKUP_SHA": bsha,
    }
    base.update(env_ok())

    rc, out = capture_main(base)
    expect(rc == 0, "success_exit0", failures)
    expect("OWNER_MEASURE_STATUS=SUCCESS" in out, "success_status", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "NO", "success_apply_no", failures)
    expect(last_kv(out, "PRED_ROW_DELTA") == "0", "success_row_delta0", failures)
    expect("INTERNAL_HEALTH_JSON_PARSE=YES" in out, "health_parsed", failures)
    expect("INTERNAL_LIST_JSON_PARSE=YES" in out, "list_parsed", failures)
    expect("INTERNAL_LIST_DATA_COUNT=1" in out, "list_count", failures)
    expect("INTERNAL_LIST_ENVELOPE_KEYS=" in out, "list_keys", failures)
    expect("INTERNAL_LIST_MAX_ELEMENT_BYTES=" in out, "list_max_elem", failures)
    expect("DETAIL_GET=ATTEMPTED" in out, "detail_attempted", failures)
    expect("local-fixture-1" not in out, "race_id_not_logged", failures)
    expect("HTTP_CALL=GET http://127.0.0.1:8000/v1/predictions/{id}" in out, "detail_redacted", failures)
    expect("POST_PREDICTION_RUNS_CALLED=NO" in out, "no_post", failures)
    expect("CACHE_WRITE=NO" in out, "no_cache_write", failures)
    expect("MEASURE_LIMITS_ARE_NOT_APPLY_LIMITS=YES" in out, "caps_not_apply_limits", failures)
    expect("MEASURE_PUBLIC_JSON_MAX_BYTES=262144" in out, "public_cap_emitted", failures)
    expect("MEASURE_LIST_CAP_BYTES=" in out, "list_cap_emitted", failures)

    over = dict(base)
    over["OWNER_MEASURE_TEST_FAIL"] = "oversized_list"
    rc, out = capture_main(over)
    expect(rc == 3, "oversized_partial_exit3", failures)
    expect("HALT_REASON=HTTP_BODY_OVERSIZED" not in out or "OWNER_MEASURE_STATUS=PARTIAL" in out, "oversized_partial", failures)
    expect("HTTP_BODY_OVERSIZED=YES" in out, "oversized_flag", failures)
    expect("HTTP_ENDPOINT_CLASS=INTERNAL_LIST" in out, "oversized_class", failures)
    expect("HTTP_BYTES_READ_AT_LEAST=" in out, "oversized_at_least", failures)
    expect("HTTP_LIMIT_BYTES=" in out, "oversized_limit", failures)
    expect(last_kv(out, "APPLY_EXECUTED") == "NO", "oversized_apply_no", failures)
    expect("DETAIL_GET=SKIPPED_LIST_OVERSIZED" in out, "oversized_skip_detail", failures)
    expect(last_kv(out, "PRED_ROW_DELTA") == "0", "oversized_row_delta0", failures)

    gz = dict(base)
    gz["OWNER_MEASURE_TEST_FAIL"] = "gzip_list"
    rc, out = capture_main(gz)
    expect(rc == 0, "gzip_success", failures)
    expect("INTERNAL_LIST_GZIP=YES" in out, "gzip_flag", failures)
    expect("INTERNAL_LIST_WIRE_BYTES=" in out, "gzip_wire", failures)
    expect("INTERNAL_LIST_DECODED_BYTES=" in out, "gzip_decoded", failures)
    expect("INTERNAL_LIST_JSON_PARSE=YES" in out, "gzip_parsed", failures)

    post = dict(base)
    post["OWNER_MEASURE_TEST_PROC_ENVIRON"] = "PREDICTION_RUNS_ENABLED=1"
    rc, out = capture_main(post)
    expect(rc == 2, "post_enabled_halts", failures)
    expect("HALT_REASON=PREDICTION_RUNS_ENABLED_EFFECTIVE_1" in out, "halt_post", failures)

    print("ALL_PASS" if not failures else "FAIL_COUNT=%d %s" % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
