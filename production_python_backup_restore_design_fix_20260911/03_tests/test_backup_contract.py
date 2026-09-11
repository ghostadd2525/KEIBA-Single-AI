#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-contained backup contract tests. No /workspace or app repository paths."""
from __future__ import annotations

import ast
import errno
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "02_code"
FLAGS = ROOT / "FLAGS.txt"
FIXTURE = Path(__file__).resolve().parent / "fixture_schema.sql"
PY = CODE / "backup_contract.py"

sys.path.insert(0, str(CODE))

import backup_contract as bc  # noqa: E402


def _expect_no_repo_path(text: str) -> None:
    lowered = text.lower()
    banned = (
        os.sep + os.path.join("workspace", "services", "win5-ai"),
        os.path.join("services", "win5-ai", "app", "data", "migrations"),
    )
    for needle in banned:
        if needle in lowered:
            raise AssertionError("test/code depends on %s" % needle)


class SeedHelper:
    @staticmethod
    def seed(path: Path, *, wal: bool = False) -> None:
        conn = sqlite3.connect(str(path))
        try:
            if wal:
                conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(FIXTURE.read_text(encoding="utf-8"))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def allow_env() -> dict[str, str]:
        env = os.environ.copy()
        env["ALLOW_LOCAL_SQLITE_BACKUP"] = "1"
        env.pop("OWNER_PRODUCTION_BACKUP_APPROVED", None)
        return env


class BackupContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="bak-design-fix-"))
        self.src = self.tmp / "src.db"
        self.dest_dir = self.tmp / "backups"
        self.dest = self.dest_dir / "explicit.db"
        SeedHelper.seed(self.src)
        self.env_patch = mock.patch.dict(os.environ, SeedHelper.allow_env(), clear=False)
        self.env_patch.start()

    def tearDown(self) -> None:
        self.env_patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ast_and_self_contained_paths(self) -> None:
        src = PY.read_text(encoding="utf-8")
        ast.parse(src)
        test_src = Path(__file__).read_text(encoding="utf-8")
        _expect_no_repo_path(src)
        _expect_no_repo_path(test_src)
        self.assertNotIn(os.sep + os.path.join("workspace", "services", "win5-ai"), src)
        self.assertIn("file:", src)
        self.assertIn("uri=True", src)
        self.assertIn("query_only", src)
        self.assertIn("OWNER_PRODUCTION_BACKUP_APPROVED", src)
        self.assertIn("DEST_EXISTS_OVERWRITE_FORBIDDEN", src)

    def test_flags_remain_unexecuted(self) -> None:
        flags = FLAGS.read_text(encoding="utf-8")
        self.assertIn("PRODUCTION_BACKUP_EXECUTED=NO", flags)
        self.assertIn("PRODUCTION_BACKUP_DESIGN_APPROVED=NO", flags)
        self.assertIn("PRODUCTION_APPLY_READY=NO", flags)
        self.assertIn("OWNER_APPLY_APPROVED=NO", flags)
        self.assertIn("LIVE_SCHEMA_EXACT_COMPATIBILITY=UNCONFIRMED", flags)
        self.assertIn("PRODUCTION_BACKUP_EXECUTION_PACK=NO", flags)

    def test_deny_without_allow_flag(self) -> None:
        os.environ.pop("ALLOW_LOCAL_SQLITE_BACKUP", None)
        code = bc.run_contract(self.src, self.dest)
        self.assertEqual(code, 2)

    def test_happy_path_permissions_and_design_flag(self) -> None:
        with mock.patch.object(bc, "emit") as emit:
            code = bc.run_contract(self.src, self.dest, restore_rehearse=True)
        self.assertEqual(code, 0)
        kv = {c.args[0]: c.args[1] for c in emit.call_args_list}
        self.assertTrue(self.dest.is_file())
        self.assertEqual(stat.S_IMODE(self.dest_dir.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.dest.stat().st_mode), 0o600)
        self.assertEqual(kv.get("BACKUP_OK"), "YES")
        self.assertEqual(kv.get("PRODUCTION_BACKUP_EXECUTED"), "NO")
        self.assertEqual(kv.get("MIGRATION_MAY_PROCEED"), "NO")
        self.assertEqual(kv.get("SOURCE_OPEN_QUERY_ONLY"), "ON")
        self.assertTrue(str(kv.get("SOURCE_OPEN_URI", "")).endswith("?mode=ro"))
        self.assertEqual(kv.get("SCHEMA_FINGERPRINT_MATCH"), True)
        self.assertEqual(kv.get("MASTER_SHA_MATCH"), True)
        self.assertEqual(kv.get("INDEX_SET_MATCH"), True)
        self.assertEqual(kv.get("TRIGGER_SET_MATCH"), True)
        self.assertEqual(kv.get("VIEW_SET_MATCH"), True)
        self.assertEqual(kv.get("SCHEMA_MIGRATIONS_MATCH"), True)
        self.assertEqual(kv.get("RESTORE_REHEARSE_OK"), "YES")
        self.assertEqual(kv.get("RESTORE_TO_LIVE"), "NO")
        self.assertNotIn("HIDE", "".join(str(c.args) for c in emit.call_args_list))

    def test_wal_committed_snapshot_excludes_uncommitted(self) -> None:
        wal_src = self.tmp / "wal-src.db"
        SeedHelper.seed(wal_src, wal=True)
        writer = sqlite3.connect(str(wal_src))
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("BEGIN IMMEDIATE")
        writer.execute(
            "INSERT INTO predictions(engine_source, payload, created_at) VALUES ('real_ai','UNCOMMITTED','t2')"
        )
        wal_file = wal_src.parent / (wal_src.name + "-wal")
        journal_mode = writer.execute("PRAGMA journal_mode").fetchone()[0]
        self.assertEqual(str(journal_mode).lower(), "wal")
        self.assertTrue(wal_file.exists() or (wal_src.parent / (wal_src.name + "-shm")).exists())
        dest = self.dest_dir / "wal.db"
        try:
            code = bc.run_contract(wal_src, dest)
            self.assertEqual(code, 0)
            ro = sqlite3.connect("file:%s?mode=ro" % dest, uri=True)
            try:
                ro.execute("PRAGMA query_only = ON")
                notes = [r[0] for r in ro.execute("SELECT payload FROM predictions ORDER BY id")]
            finally:
                ro.close()
            self.assertEqual(notes, ["HIDE"])
            self.assertNotIn("UNCOMMITTED", notes)
        finally:
            writer.rollback()
            writer.close()

    def test_overwrite_refused_leaves_existing_dest(self) -> None:
        self.dest_dir.mkdir(parents=True)
        self.dest.write_bytes(b"KEEP")
        before_src = self.src.read_bytes()
        with mock.patch.object(bc, "emit") as emit:
            code = bc.run_contract(self.src, self.dest)
        self.assertEqual(code, 2)
        kv = {c.args[0]: c.args[1] for c in emit.call_args_list}
        self.assertEqual(kv.get("FAIL_REASON"), "DEST_EXISTS_OVERWRITE_FORBIDDEN")
        self.assertEqual(self.dest.read_bytes(), b"KEEP")
        self.assertEqual(self.src.read_bytes(), before_src)
        self.assertEqual(kv.get("MIGRATION_MAY_PROCEED"), "NO")
        self.assertEqual(kv.get("PRODUCTION_BACKUP_EXECUTED"), "NO")

    def test_disk_full_refuses_and_leaves_no_dest(self) -> None:
        fake = types.SimpleNamespace(total=1, used=1, free=0)

        def _usage(_path: str):
            return fake

        with mock.patch.object(bc.shutil, "disk_usage", _usage), mock.patch.object(bc, "emit") as emit:
            code = bc.run_contract(self.src, self.dest)
        self.assertEqual(code, 2)
        kv = {c.args[0]: c.args[1] for c in emit.call_args_list}
        self.assertEqual(kv.get("FAIL_REASON"), "DEST_PARENT_INSUFFICIENT_SPACE")
        self.assertFalse(self.dest.exists())
        self.assertEqual(kv.get("MIGRATION_MAY_PROCEED"), "NO")

    def test_mid_backup_enospc_disposes_only_dest(self) -> None:
        before = self.src.read_bytes()

        def boom(src_conn, dest_conn):
            dest_conn.execute("CREATE TABLE partial(x INTEGER)")
            dest_conn.commit()
            raise OSError(errno.ENOSPC, "No space left on device")

        with mock.patch.object(bc, "perform_backup", boom), mock.patch.object(bc, "emit") as emit:
            code = bc.run_contract(self.src, self.dest)
        self.assertEqual(code, 2)
        kv = {c.args[0]: c.args[1] for c in emit.call_args_list}
        self.assertEqual(kv.get("MIGRATION_MAY_PROCEED"), "NO")
        self.assertEqual(kv.get("PARTIAL_BACKUP_DISPOSAL"), "DELETED")
        self.assertEqual(kv.get("PARTIAL_BACKUP_DEST_ONLY"), "YES")
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.src.read_bytes(), before)

    def test_integrity_failure_quarantines_dest_only(self) -> None:
        qdir = self.tmp / "quarantine"
        with mock.patch.object(bc, "read_integrity", return_value="not ok"), mock.patch.object(bc, "emit") as emit:
            code = bc.run_contract(self.src, self.dest, quarantine_dir=qdir)
        self.assertEqual(code, 2)
        kv = {c.args[0]: c.args[1] for c in emit.call_args_list}
        self.assertEqual(kv.get("FAIL_REASON"), "INTEGRITY_CHECK_FAILED")
        self.assertEqual(kv.get("PARTIAL_BACKUP_DISPOSAL"), "QUARANTINED")
        self.assertFalse(self.dest.exists())
        self.assertTrue(self.src.exists())
        quarantined = list(qdir.glob("*.quarantine"))
        self.assertTrue(quarantined)

    def test_schema_mismatch_disposes_dest(self) -> None:
        def tainted(src_conn, dest_conn):
            src_conn.backup(dest_conn, pages=64, sleep=0.05)
            dest_conn.execute("CREATE VIEW extra_mismatch AS SELECT 1 AS x")
            dest_conn.commit()

        with mock.patch.object(bc, "perform_backup", tainted), mock.patch.object(bc, "emit") as emit:
            code = bc.run_contract(self.src, self.dest)
        self.assertEqual(code, 2)
        kv = {c.args[0]: c.args[1] for c in emit.call_args_list}
        self.assertEqual(kv.get("FAIL_REASON"), "SCHEMA_MISMATCH")
        self.assertEqual(kv.get("VIEW_SET_MATCH"), False)
        self.assertEqual(kv.get("MASTER_SHA_MATCH"), False)
        self.assertEqual(kv.get("PARTIAL_BACKUP_DISPOSAL"), "DELETED")
        self.assertFalse(self.dest.exists())

    def test_permission_mismatch_dest_file(self) -> None:
        self.dest_dir.mkdir(parents=True)
        os.chmod(self.dest_dir, 0o700)
        self.dest.write_bytes(b"x")
        os.chmod(self.dest, 0o644)
        with self.assertRaises(bc.BackupError) as ctx:
            bc.verify_dest_permissions(self.dest_dir, self.dest)
        self.assertEqual(ctx.exception.code, "PERMISSION_MISMATCH_DEST_FILE")

    def test_permission_mismatch_dest_dir(self) -> None:
        self.dest_dir.mkdir(parents=True)
        os.chmod(self.dest_dir, 0o755)
        self.dest.write_bytes(b"x")
        os.chmod(self.dest, 0o600)
        with self.assertRaises(bc.BackupError) as ctx:
            bc.verify_dest_permissions(self.dest_dir, self.dest)
        self.assertEqual(ctx.exception.code, "PERMISSION_MISMATCH_DEST_DIR")

    def test_permission_mismatch_during_contract_disposes(self) -> None:
        real_chmod = os.chmod

        def selective(path, mode):
            if Path(path) == self.dest and mode == 0o600:
                real_chmod(path, 0o644)
                return
            real_chmod(path, mode)

        with mock.patch.object(bc.os, "chmod", selective), mock.patch.object(bc, "emit") as emit:
            code = bc.run_contract(self.src, self.dest)
        self.assertEqual(code, 2)
        kv = {c.args[0]: c.args[1] for c in emit.call_args_list}
        self.assertEqual(kv.get("FAIL_REASON"), "PERMISSION_MISMATCH_DEST_FILE")
        self.assertEqual(kv.get("PARTIAL_BACKUP_DISPOSAL"), "DELETED")
        self.assertFalse(self.dest.exists())

    def test_dest_same_path_as_source(self) -> None:
        with mock.patch.object(bc, "emit") as emit:
            code = bc.run_contract(self.src, self.src)
        self.assertEqual(code, 2)
        kv = {c.args[0]: c.args[1] for c in emit.call_args_list}
        self.assertEqual(kv.get("FAIL_REASON"), "DEST_SAME_PATH_AS_SOURCE")
        self.assertTrue(self.src.exists())

    def test_dest_same_inode_hardlink(self) -> None:
        self.dest_dir.mkdir(parents=True)
        os.link(self.src, self.dest)
        with mock.patch.object(bc, "emit") as emit:
            code = bc.run_contract(self.src, self.dest)
        self.assertEqual(code, 2)
        kv = {c.args[0]: c.args[1] for c in emit.call_args_list}
        self.assertEqual(kv.get("FAIL_REASON"), "DEST_SAME_INODE_AS_SOURCE")
        self.assertTrue(self.src.exists())
        self.assertTrue(self.dest.exists())

    def test_source_dev_ino_checked_around_open(self) -> None:
        real = bc.path_stat
        hits = {"n": 0}

        def flip(path: Path):
            st = real(path)
            if path.resolve() == self.src.resolve():
                hits["n"] += 1
                if hits["n"] >= 2:
                    return types.SimpleNamespace(
                        st_dev=st.st_dev,
                        st_ino=st.st_ino + 99,
                        st_size=st.st_size,
                        st_mtime=st.st_mtime,
                        st_mode=st.st_mode,
                    )
            return st

        with mock.patch.object(bc, "path_stat", flip):
            with self.assertRaises(bc.BackupError) as ctx:
                bc.open_readonly_source(self.src)
        self.assertEqual(ctx.exception.code, "SOURCE_DEV_INO_CHANGED")

    def test_production_path_refused_without_owner_approval(self) -> None:
        self.assertTrue(bc.is_production_path(Path(bc.PRODUCTION_DB_PATHS[0])))
        self.assertFalse(
            bc.production_backup_executed(self.src, True),
            "design fixture must not count as Production backup",
        )
        self.assertTrue(bc.production_backup_executed(Path(bc.PRODUCTION_DB_PATHS[0]), True))
        self.assertFalse(bc.production_backup_executed(Path(bc.PRODUCTION_DB_PATHS[0]), False))

    def test_cli_main_happy_path_stdout(self) -> None:
        dest = self.dest_dir / "cli.db"
        rc = bc.main(["--src", str(self.src), "--dest", str(dest), "--restore-rehearse"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
