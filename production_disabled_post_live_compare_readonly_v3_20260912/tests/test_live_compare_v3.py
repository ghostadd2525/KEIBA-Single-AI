#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

PACK = Path(__file__).resolve().parents[1]
if str(PACK) not in sys.path:
    sys.path.insert(0, str(PACK))

import build_owner_script  # noqa: E402
import generate_hashes  # noqa: E402
import live_compare as lc  # noqa: E402

HEX64 = re.compile(r"^[0-9a-f]{64}$")
WRONG_SNAPSHOT = "2114c953b57461f73d0450384f38df2a2b086a397c77cc70b448cbde5f7"
V4_SNAPSHOT = "2114c953b57461f73d0450384f38df2a2b086a51e53591c77cc70b448cbde5f7"
REF_FILES = PACK / "v4_reference" / "files" / "services" / "win5-ai"
DUMMY_SECRET = "SUPER_SECRET_TOKEN_XYZ"
DUMMY_ENV_SECRET = "ENV_RAW_SECRET_SHOULD_NEVER_PRINT"
LEAK_DSN = "postgres://user:supersecret@example/db"
LEAK_BEARER = "BearerSecretValue"
LEAK_DBURL = "postgres://user:supersecret@example/db"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_good_db(path: Path, index_sql: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY)")
        conn.execute(
            "INSERT INTO schema_migrations(version) VALUES (?)",
            ("022_prediction_run_idempotency",),
        )
        conn.execute(
            """
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY,
                idempotency_key TEXT,
                persist_source TEXT,
                input_snapshot_hash TEXT,
                prediction_semantic_hash TEXT
            )
            """
        )
        if index_sql is None:
            index_sql = (
                "CREATE UNIQUE INDEX uq_predictions_idempotency_key_not_null "
                "ON predictions(idempotency_key) WHERE idempotency_key IS NOT NULL"
            )
        if index_sql:
            conn.execute(index_sql)
        conn.commit()
    finally:
        conn.close()


def copy_v4_tree(win5: Path, extra_present: str | None = None) -> None:
    for rel in lc.DEPLOY:
        src = REF_FILES / rel
        dst = win5 / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    if extra_present:
        target = win5 / extra_present
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("present-for-stop-test\n", encoding="utf-8")
    write_good_db(win5 / "var" / "expect_ai.db")


def leaky_execstart() -> str:
    return (
        "{ path=/usr/bin/python3 ; "
        "argv[]=/usr/bin/python3 -m app.main "
        "--dsn %s --authorization %s DATABASE_URL=%s --host 127.0.0.1 --token %s ; "
        "ignore_errors=no }" % (LEAK_DSN, LEAK_BEARER, LEAK_DBURL, DUMMY_SECRET)
    )


def systemd_fixture(win5: Path, **overrides: str) -> dict[str, str]:
    base = {
        "Id": "expect-ai.service",
        "LoadState": "loaded",
        "FragmentPath": "/etc/systemd/system/expect-ai.service",
        "WorkingDirectory": str(win5),
        "ExecStart": leaky_execstart(),
        "Environment": (
            "PREDICTION_RUNS_ENABLED=0 OTHER_SECRET=%s DATABASE_URL=%s"
            % (DUMMY_ENV_SECRET, LEAK_DBURL)
        ),
        "EnvironmentFiles": "",
        "MainPID": "4242",
        "User": "ubuntu",
        "ActiveState": "active",
        "UnitFileState": "enabled",
    }
    base.update(overrides)
    return base


def fake_proc(_pid: int) -> dict[str, str | None]:
    return {
        "PREDICTION_RUNS_ENABLED": "0",
        "EXPECT_AI_ALLOW_MIGRATION_022": None,
        "EXPECT_AI_DB_PATH": None,
    }


def run_compare(
    win5: Path,
    *,
    extra_present: str | None = None,
    fixture: dict[str, str] | None = None,
    proc=fake_proc,
    systemd_error: str | None = None,
    prepare_tree: bool = True,
) -> tuple[int, str]:
    if prepare_tree and (extra_present or not (win5 / "app" / "main.py").is_file()):
        copy_v4_tree(win5, extra_present=extra_present)
    show = {"_error": systemd_error} if systemd_error is not None else (fixture or systemd_fixture(win5))
    buf = io.StringIO()
    with patch.object(lc, "systemd_show", return_value=show):
        with patch.object(lc, "proc_environ_watched", side_effect=proc):
            with redirect_stdout(buf):
                rc = lc.main()
    return rc, buf.getvalue()


def setUpModule() -> None:
    generate_hashes.main()
    build_owner_script.main()
    import importlib

    importlib.reload(lc)


class GeneratedHashTests(unittest.TestCase):
    def test_all_11_expected_sha_are_64_hex(self) -> None:
        self.assertEqual(len(lc.DEPLOY), 11)
        for rel, digest in lc.DEPLOY.items():
            self.assertRegex(digest, HEX64, msg=rel)
            self.assertEqual(len(digest), 64, msg=rel)
        for digest in (lc.MAIN_BASE, lc.MAIN_CANDIDATE, lc.DB_ORIGIN_MAIN, lc.DB_CANDIDATE):
            self.assertRegex(digest, HEX64)

    def test_all_11_match_v4_actual_files_and_file_sha256(self) -> None:
        listed = generate_hashes.parse_sha_listing(generate_hashes.FILE_SHA256)
        for rel, digest in lc.DEPLOY.items():
            actual = sha256_file(REF_FILES / rel)
            self.assertEqual(digest, actual, msg=rel)
            self.assertEqual(listed["services/win5-ai/" + rel], actual, msg=rel)

    def test_snapshot_hash_is_correct_64_not_malformed_59(self) -> None:
        digest = lc.DEPLOY["app/predictions/snapshot.py"]
        self.assertEqual(digest, V4_SNAPSHOT)
        self.assertNotEqual(digest, WRONG_SNAPSHOT)
        self.assertEqual(len(digest), 64)
        self.assertEqual(len(WRONG_SNAPSHOT), 59)

    def test_correct_snapshot_py_is_match_candidate(self) -> None:
        digest = sha256_file(REF_FILES / "app/predictions/snapshot.py")
        self.assertEqual(lc.classify_live_file("app/predictions/snapshot.py", digest), "MATCH_CANDIDATE")
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            rc, stdout = run_compare(win5)
            self.assertIn("LIVE app/predictions/snapshot.py %s MATCH_CANDIDATE" % V4_SNAPSHOT, stdout)
            self.assertEqual(rc, 0)
            self.assertIn("COMPARE_RESULT=GO", stdout)


class IndexContractTests(unittest.TestCase):
    def _eval(self, index_sql: str | None) -> dict[str, str]:
        conn = sqlite3.connect(":memory:")
        conn.execute(
            """
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY,
                idempotency_key TEXT,
                persist_source TEXT,
                extra TEXT
            )
            """
        )
        if index_sql:
            conn.execute(index_sql)
        return lc.evaluate_index_contract(conn)

    def test_good_partial_unique_is_ok(self) -> None:
        got = self._eval(
            "CREATE UNIQUE INDEX uq_predictions_idempotency_key_not_null "
            "ON predictions(idempotency_key) WHERE idempotency_key IS NOT NULL"
        )
        self.assertEqual(got["INDEX_CONTRACT"], "OK")

    def test_word_presence_only_is_not_ok(self) -> None:
        sql = (
            "CREATE INDEX uq_predictions_idempotency_key_not_null "
            "ON predictions(persist_source) -- unique idempotency_key where is not null"
        )
        got = self._eval(sql)
        self.assertNotEqual(got["INDEX_CONTRACT"], "OK")

    def test_unique_without_predicate_is_not_ok(self) -> None:
        got = self._eval(
            "CREATE UNIQUE INDEX uq_predictions_idempotency_key_not_null "
            "ON predictions(idempotency_key)"
        )
        self.assertEqual(got["INDEX_CONTRACT"], "MISMATCH")

    def test_wrong_predicate_column_is_not_ok(self) -> None:
        got = self._eval(
            "CREATE UNIQUE INDEX uq_predictions_idempotency_key_not_null "
            "ON predictions(idempotency_key) WHERE persist_source IS NOT NULL"
        )
        self.assertEqual(got["INDEX_CONTRACT"], "MISMATCH")

    def test_extra_index_column_is_not_ok(self) -> None:
        got = self._eval(
            "CREATE UNIQUE INDEX uq_predictions_idempotency_key_not_null "
            "ON predictions(idempotency_key, persist_source) "
            "WHERE idempotency_key IS NOT NULL"
        )
        self.assertEqual(got["INDEX_CONTRACT"], "MISMATCH")

    def test_missing_index_is_not_ok(self) -> None:
        got = self._eval(None)
        self.assertEqual(got["INDEX_CONTRACT"], "MISSING")


class MustAbsentTests(unittest.TestCase):
    def test_each_must_absent_present_is_stop(self) -> None:
        for rel in lc.MUST_ABSENT:
            with self.subTest(rel=rel):
                with tempfile.TemporaryDirectory() as td:
                    win5 = Path(td) / "services" / "win5-ai"
                    rc, stdout = run_compare(win5, extra_present=rel)
                    reason = "STOP_REASON=must_absent_present:%s" % rel
                    self.assertIn(reason, stdout, msg=stdout)
                    self.assertIn("COMPARE_RESULT=STOP", stdout)
                    self.assertNotEqual(rc, 0)


class SystemdEvidenceGapTests(unittest.TestCase):
    def test_systemd_show_failed_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            rc, stdout = run_compare(win5, systemd_error="unit_not_found")
            self.assertIn("SYSTEMD_SHOW=FAIL", stdout)
            self.assertIn("STOP_REASON=systemd_show_failed", stdout)
            self.assertIn("COMPARE_RESULT=STOP", stdout)
            self.assertNotEqual(rc, 0)

    def test_loadstate_not_found_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            copy_v4_tree(win5)
            fixture = systemd_fixture(win5, LoadState="not-found", ActiveState="inactive", MainPID="0")
            rc, stdout = run_compare(win5, fixture=fixture, prepare_tree=False)
            self.assertIn("SYSTEMD_LOADSTATE=not-found", stdout)
            self.assertIn("STOP_REASON=systemd_unit_not_loaded", stdout)
            self.assertIn("COMPARE_RESULT=STOP", stdout)
            self.assertNotEqual(rc, 0)

    def test_execstart_absent_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            copy_v4_tree(win5)
            fixture = systemd_fixture(win5, ExecStart="", ActiveState="inactive", MainPID="0")
            rc, stdout = run_compare(win5, fixture=fixture, prepare_tree=False)
            self.assertIn("STOP_REASON=systemd_execstart_absent", stdout)
            self.assertIn("COMPARE_RESULT=STOP", stdout)
            self.assertNotEqual(rc, 0)

    def test_active_mainpid_proc_unreadable_is_effective_env_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            copy_v4_tree(win5)
            fixture = systemd_fixture(win5, ActiveState="active", MainPID="99")

            def bad_proc(_pid: int) -> dict[str, str | None]:
                return {
                    "PREDICTION_RUNS_ENABLED": None,
                    "EXPECT_AI_ALLOW_MIGRATION_022": None,
                    "EXPECT_AI_DB_PATH": None,
                    "_error": "proc_environ_unreadable",
                }

            rc, stdout = run_compare(win5, fixture=fixture, proc=bad_proc, prepare_tree=False)
            self.assertIn("STOP_REASON=effective_env_unverified", stdout)
            self.assertIn("COMPARE_RESULT=STOP", stdout)
            self.assertNotEqual(rc, 0)


class ExecStartAllowlistTests(unittest.TestCase):
    def test_leak_strings_never_in_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            rc, stdout = run_compare(win5)
            self.assertNotIn(LEAK_DSN, stdout)
            self.assertNotIn(LEAK_BEARER, stdout)
            self.assertNotIn("supersecret", stdout)
            self.assertNotIn(DUMMY_SECRET, stdout)
            self.assertNotIn(DUMMY_ENV_SECRET, stdout)
            self.assertNotIn("DATABASE_URL=", stdout)
            self.assertNotRegex(stdout, r"(?m)^SYSTEMD_EXECSTART=")
            self.assertNotRegex(stdout, r"(?m)^SYSTEMD_ENVIRONMENT=")
            self.assertEqual(rc, 0)

    def test_non_allowlisted_argv_is_redacted(self) -> None:
        safe = lc.redact_argv(
            [
                "/usr/bin/python3",
                "-m",
                "app.main",
                "--dsn",
                LEAK_DSN,
                "--authorization",
                LEAK_BEARER,
                "DATABASE_URL=%s" % LEAK_DBURL,
                "--host",
                "127.0.0.1",
            ]
        )
        self.assertEqual(
            safe,
            [
                "/usr/bin/python3",
                "-m",
                "app.main",
                "[REDACTED]",
                "[REDACTED]",
                "[REDACTED]",
                "[REDACTED]",
                "[REDACTED]",
                "[REDACTED]",
                "[REDACTED]",
            ],
        )
        joined = " ".join(safe)
        self.assertNotIn(LEAK_DSN, joined)
        self.assertNotIn(LEAK_BEARER, joined)
        self.assertNotIn("127.0.0.1", joined)

    def test_happy_path_shows_executable_and_module(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            rc, stdout = run_compare(win5)
            self.assertIn("SYSTEMD_EXECSTART_PATH=/usr/bin/python3", stdout)
            self.assertIn("-m app.main", stdout)
            self.assertIn("PREDICTION_RUNS_ENABLED=ZERO", stdout)
            self.assertEqual(rc, 0)


class ReadonlyStaticTests(unittest.TestCase):
    def test_owner_scripts_do_not_write_restart_migrate_or_post(self) -> None:
        texts = {
            "live_compare.py": (PACK / "live_compare.py").read_text(encoding="utf-8"),
            "OWNER_LIVE_COMPARE.sh": (PACK / "OWNER_LIVE_COMPARE.sh").read_text(encoding="utf-8"),
            "OWNER_PASTE_COMMAND_BLOCK.sh": (PACK / "OWNER_PASTE_COMMAND_BLOCK.sh").read_text(
                encoding="utf-8"
            ),
        }
        forbidden = [
            r"systemctl\s+(restart|edit|enable|disable|daemon-reload|stop|start|mask)",
            r"\btee\b",
            r"PREDICTION_RUNS_ENABLED=1",
            r"EXPECT_AI_ALLOW_MIGRATION_022=1",
            r"shutil\.(copy|copy2|copytree|move)",
            r"Path\([^\n]+\)\.write_(text|bytes)",
            r"open\([^\n]*(['\"])[wa+]",
            r"mode=rw",
            r"\bcurl\b",
            r"\bwget\b",
            r"requests\.(post|put|patch|delete)",
            r"urllib\.request",
            r"migrate\(",
        ]
        for name, text in texts.items():
            self.assertIn("mode=ro", text, msg=name)
            self.assertNotIn("mode=rw", text, msg=name)
            for pat in forbidden:
                self.assertIsNone(re.search(pat, text), msg="%s matched %s" % (name, pat))

    def test_canonical_equals_presented(self) -> None:
        canon = (PACK / "OWNER_LIVE_COMPARE.sh").read_bytes()
        presented = (PACK / "OWNER_PASTE_COMMAND_BLOCK.sh").read_bytes()
        self.assertEqual(canon, presented)
        self.assertGreater(len(canon), 1000)
        self.assertNotIn(WRONG_SNAPSHOT.encode("ascii"), canon)
        self.assertIn(V4_SNAPSHOT.encode("ascii"), canon)


class EmbeddedIdentityTests(unittest.TestCase):
    def test_shell_embeds_live_compare_py(self) -> None:
        shell = (PACK / "OWNER_LIVE_COMPARE.sh").read_text(encoding="utf-8")
        src = (PACK / "live_compare.py").read_text(encoding="utf-8")
        self.assertIn(src, shell)


if __name__ == "__main__":
    unittest.main()
