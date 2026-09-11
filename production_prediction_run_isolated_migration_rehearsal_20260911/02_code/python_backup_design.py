#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local-only design of sqlite3.Connection.backup.

Owner approval is required before any Production backup.
This file refuses known Production DB paths and refuses to run
unless ALLOW_LOCAL_SQLITE_BACKUP=1.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

PRODUCTION_DB_PATHS = (
    "/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db",
    "/opt/expect-ai/current/services/win5-ai/var/expect_ai.db",
    "/var/lib/expect-ai/expect_ai.db",
)


def refuse_production_path(path: Path) -> None:
    resolved = str(path.resolve()) if path.exists() else str(path)
    for banned in PRODUCTION_DB_PATHS:
        if resolved == banned or resolved.startswith(banned):
            raise SystemExit("REFUSED Production DB path: %s" % resolved)
        if "KEIBA-Single-AI" in resolved and resolved.endswith("expect_ai.db"):
            raise SystemExit("REFUSED host expect_ai.db path: %s" % resolved)


def backup(src: Path, dst: Path) -> None:
    if (os.environ.get("ALLOW_LOCAL_SQLITE_BACKUP") or "").strip() != "1":
        raise SystemExit("REFUSED: set ALLOW_LOCAL_SQLITE_BACKUP=1 for local rehearsal only")
    refuse_production_path(src)
    refuse_production_path(dst)
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        src_conn.backup(dst_conn, pages=64, sleep=0.05)
        dst_conn.commit()
        check = dst_conn.execute("PRAGMA integrity_check").fetchone()
        if not check or str(check[0]) != "ok":
            raise SystemExit("integrity_check failed")
    finally:
        dst_conn.close()
        src_conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Local sqlite backup design (not Production)")
    parser.add_argument("--src", required=True)
    parser.add_argument("--dst", required=True)
    args = parser.parse_args()
    backup(Path(args.src), Path(args.dst))
    print("LOCAL_BACKUP_OK=YES")
    print("PRODUCTION_BACKUP_EXECUTED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
