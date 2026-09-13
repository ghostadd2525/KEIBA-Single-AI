#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
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
import extract_capture as ex  # noqa: E402
import generate_hashes  # noqa: E402
import live_source_capture as cap  # noqa: E402
import three_way_diff as tw  # noqa: E402

HEX64 = re.compile(r"^[0-9a-f]{64}$")
ORIGIN_DIR = PACK / "reference" / "origin_main_25a3f88"
V6_DIR = PACK / "reference" / "review_v6"
LEAK_DSN = "postgres://user:supersecret@example/db"
LEAK_BEARER = "BearerSecretValue"
DUMMY_SECRET = "SUPER_SECRET_TOKEN_XYZ"
DUMMY_ENV_SECRET = "ENV_RAW_SECRET_SHOULD_NEVER_PRINT"
LEAK_DBURL = "postgres://user:supersecret@example/db"
V5_ZIP_SHA = "09a75da0327182e5d50b2cbbe91ce2b7dbebdcb50e432a9c1fd7731f730672ba"
V6_ZIP_SHA = "548b274facc2b4f8ffba8b854a6e009d8b7455fb816dcde9550eb9b364329373"
OWNER_LOG_SHA = "4a65fd2ca5f54284268975d90d28e65222c785421b204567bb3bf1780be28c94"
ORIGIN_MAIN_PY = "a54f1eaa5b8540c2f08d8b0e656a3ccbb78142d4d1cb2c8951e4105f3630184e"
V6_MAIN_PY = "7577973c16eb7aad395cd11acae3c8ef987a3c0533924c1994ae32afeaf818e5"
IMMUTABLE_ZIPS = (
    "production_disabled_post_code_deploy_review_20260912.zip",
    "production_disabled_post_code_deploy_review_v2_20260912.zip",
    "production_disabled_post_code_deploy_review_v3_20260912.zip",
    "production_disabled_post_code_deploy_review_v4_20260912.zip",
    "production_disabled_post_code_deploy_review_v5_20260912.zip",
    "production_disabled_post_code_deploy_review_v6_20260912.zip",
    "production_disabled_post_live_compare_readonly_20260912.zip",
    "production_disabled_post_live_compare_readonly_v2_20260912.zip",
    "production_disabled_post_live_compare_readonly_v3_20260912.zip",
    "production_disabled_post_live_compare_readonly_v4_20260912.zip",
    "production_disabled_post_live_compare_readonly_v5_20260912.zip",
    "production_disabled_post_live_source_capture_readonly_20260912.zip",
)
V1_CAPTURE_ZIP_SHA = "c38c58ac567d9a3b99987e5c1c75b9ece84c509b5d7740849126f46fc47aae24"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_tree(src: Path, win5: Path) -> None:
    for rel in cap.CAPTURE_RELS:
        dst = win5 / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, dst)


def leaky_execstart() -> str:
    return (
        "{ path=/usr/bin/python3 ; "
        "argv[]=/usr/bin/python3 -m app.main "
        "--dsn %s --authorization %s DATABASE_URL=%s --token %s ; "
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
    }
    base.update(overrides)
    return base


def metadata_only(stdout: str) -> str:
    start = stdout.find("=== TAR_BASE64_BEGIN ===")
    end = stdout.find("=== TAR_BASE64_END ===")
    if start < 0 or end < 0:
        return stdout
    return stdout[:start] + stdout[end + len("=== TAR_BASE64_END ===") :]


def run_capture(
    win5: Path,
    *,
    fixture: dict[str, str] | None = None,
    systemd_error: str | None = None,
    prepare: Path | None = V6_DIR,
) -> tuple[int, str]:
    if prepare is not None:
        copy_tree(prepare, win5)
    show = {"_error": systemd_error} if systemd_error is not None else (fixture or systemd_fixture(win5))
    buf = io.StringIO()
    with patch.object(cap, "systemd_show", return_value=show):
        with redirect_stdout(buf):
            rc = cap.main()
    return rc, buf.getvalue()


def setUpModule() -> None:
    generate_hashes.main()
    build_owner_script.main()
    import importlib

    importlib.reload(tw)
    importlib.reload(cap)


class ReferenceHashTests(unittest.TestCase):
    def test_origin_and_v6_hashes_match_files(self) -> None:
        self.assertEqual(len(tw.ORIGIN), 3)
        self.assertEqual(len(tw.V6), 3)
        for rel, digest in tw.ORIGIN.items():
            self.assertRegex(digest, HEX64, msg=rel)
            self.assertEqual(digest, sha256_file(ORIGIN_DIR / rel), msg=rel)
        for rel, digest in tw.V6.items():
            self.assertRegex(digest, HEX64, msg=rel)
            self.assertEqual(digest, sha256_file(V6_DIR / rel), msg=rel)
        self.assertEqual(tw.ORIGIN["app/main.py"], ORIGIN_MAIN_PY)
        self.assertEqual(tw.V6["app/main.py"], V6_MAIN_PY)
        self.assertNotEqual(tw.ORIGIN["app/main.py"], tw.V6["app/main.py"])
        self.assertNotEqual(
            tw.ORIGIN["app/data/repository/__init__.py"],
            tw.V6["app/data/repository/__init__.py"],
        )
        self.assertNotEqual(
            tw.ORIGIN["app/core/feature_loader_bridge.py"],
            tw.V6["app/core/feature_loader_bridge.py"],
        )


class CaptureHappyPathTests(unittest.TestCase):
    def test_three_files_go_and_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            rc, stdout = run_capture(win5)
            self.assertEqual(rc, 0)
            self.assertIn("CAPTURE_RESULT=GO", stdout)
            self.assertIn("TAR_MEMBER_COUNT=3", stdout)
            self.assertIn("=== TAR_BASE64_BEGIN ===", stdout)
            self.assertIn("PRODUCTION_CODE_DEPLOY_ALLOWED=NO", stdout)
            self.assertIn("DEPLOY_EXECUTION_PACK=NO", stdout)
            for rel in cap.CAPTURE_RELS:
                self.assertIn("CAPTURE_REL=%s" % rel, stdout)
                self.assertIn("CAPTURE_OPEN=OK", stdout)
                self.assertIn("CAPTURE_SHA256=%s" % tw.V6[rel], stdout)
            transcript = Path(td) / "transcript.txt"
            transcript.write_text(stdout, encoding="utf-8")
            dest = Path(td) / "extracted"
            extract_rc = ex.main([str(transcript), "--out", str(dest)])
            self.assertEqual(extract_rc, 0)
            for rel in cap.CAPTURE_RELS:
                self.assertEqual(sha256_file(dest / rel), tw.V6[rel])
                self.assertEqual((dest / rel).read_bytes(), (V6_DIR / rel).read_bytes())
            manifest = (dest / "MANIFEST.txt").read_text(encoding="utf-8")
            self.assertIn("SHA256=%s" % tw.V6["app/main.py"], manifest)

    def test_origin_tree_records_origin_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            rc, stdout = run_capture(win5, prepare=ORIGIN_DIR)
            self.assertEqual(rc, 0)
            self.assertIn("CAPTURE_SHA256=%s" % ORIGIN_MAIN_PY, stdout)

    def test_missing_file_is_stop_and_omits_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            copy_tree(V6_DIR, win5)
            (win5 / "app" / "core" / "feature_loader_bridge.py").unlink()
            rc, stdout = run_capture(win5, prepare=None)
            self.assertNotEqual(rc, 0)
            self.assertIn("CAPTURE_RESULT=STOP", stdout)
            self.assertIn("STOP_REASON=capture_file_absent:app/core/feature_loader_bridge.py", stdout)
            self.assertIn("TAR_PAYLOAD=OMITTED_INCOMPLETE", stdout)
            self.assertNotIn("=== TAR_BASE64_BEGIN ===", stdout)

    def test_win5_missing_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "empty"
            win5.mkdir()
            rc, stdout = run_capture(win5, fixture=systemd_fixture(win5), prepare=None)
            self.assertNotEqual(rc, 0)
            self.assertIn("STOP_REASON=win5_root_not_found", stdout)
            self.assertIn("CAPTURE_RESULT=STOP", stdout)

    def test_systemd_fail_fallback_still_captures(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            known = Path("/home/ubuntu/KEIBA-Single-AI/services/win5-ai")
            # Use the real fallback only if we also patch discover to see our tree.
            win5 = Path(td) / "services" / "win5-ai"
            copy_tree(V6_DIR, win5)
            fixture = {"_error": "unit_not_found"}
            buf = io.StringIO()
            with patch.object(cap, "systemd_show", return_value=fixture):
                with patch.object(cap, "discover_win5", return_value=win5):
                    with redirect_stdout(buf):
                        rc = cap.main()
            stdout = buf.getvalue()
            self.assertEqual(rc, 0, msg=stdout)
            self.assertIn("SYSTEMD_SHOW=FAIL", stdout)
            self.assertIn("CAPTURE_RESULT=GO", stdout)
            _ = known


class SecretAndEnvTests(unittest.TestCase):
    def test_leaks_and_env_never_in_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            rc, stdout = run_capture(win5)
            meta = metadata_only(stdout)
            self.assertEqual(rc, 0)
            self.assertNotIn(LEAK_DSN, meta)
            self.assertNotIn(LEAK_BEARER, meta)
            self.assertNotIn("supersecret", meta)
            self.assertNotIn(DUMMY_SECRET, meta)
            self.assertNotIn(DUMMY_ENV_SECRET, meta)
            self.assertNotIn("DATABASE_URL=", meta)
            self.assertNotRegex(meta, r"(?m)^SYSTEMD_EXECSTART=")
            self.assertNotRegex(meta, r"(?m)^SYSTEMD_ENVIRONMENT=")
            self.assertNotRegex(meta, r"(?m)^PREDICTION_RUNS_ENABLED=")
            self.assertNotRegex(meta, r"(?m)^EXPECT_AI_ALLOW_MIGRATION_022=")
            self.assertNotRegex(meta, r"(?m)^EXPECT_AI_ALLOW_MIGRATION_019=")
            self.assertNotIn("EnvironmentFiles", meta)
            self.assertNotIn("/proc/", meta)

    def test_systemd_show_does_not_request_environment(self) -> None:
        src = (PACK / "live_source_capture.py").read_text(encoding="utf-8")
        self.assertIn('"-p",\n        "LoadState"', src)
        self.assertNotIn('"Environment"', src)
        self.assertNotIn('"EnvironmentFiles"', src)
        self.assertNotIn("/proc/", src)
        self.assertNotIn("sqlite3", src)
        self.assertNotIn("git", src.lower().replace("digit", ""))


class ReadonlyStaticTests(unittest.TestCase):
    def test_owner_scripts_do_not_write_restart_or_collect_secrets(self) -> None:
        texts = {
            "live_source_capture.py": (PACK / "live_source_capture.py").read_text(encoding="utf-8"),
            "OWNER_LIVE_SOURCE_CAPTURE.sh": (PACK / "OWNER_LIVE_SOURCE_CAPTURE.sh").read_text(
                encoding="utf-8"
            ),
            "OWNER_PASTE_COMMAND_BLOCK.sh": (PACK / "OWNER_PASTE_COMMAND_BLOCK.sh").read_text(
                encoding="utf-8"
            ),
        }
        forbidden = [
            r"systemctl\s+(restart|edit|enable|disable|daemon-reload|stop|start|mask)",
            r"\btee\b",
            r"PREDICTION_RUNS_ENABLED=1",
            r"EXPECT_AI_ALLOW_MIGRATION_022=1",
            r"EXPECT_AI_ALLOW_MIGRATION_019=1",
            r"shutil\.(copy|copy2|copytree|move)",
            r"Path\([^\n]+\)\.write_(text|bytes)",
            r"(?<!tarfile\.)open\([^\n]*(['\"])[wa+]",
            r"mode=rw",
            r"\bcurl\b",
            r"\bwget\b",
            r"\bscp\b",
            r"requests\.(post|put|patch|delete)",
            r"urllib\.request",
            r"migrate\(",
            r"sqlite3",
            r"\bgit\b",
            r"NamedTemporaryFile",
            r"os\.O_WRONLY",
            r"os\.O_RDWR",
        ]
        for name, text in texts.items():
            self.assertIn("os.O_RDONLY", text, msg=name)
            self.assertIn("THIS_SCRIPT_WRITES=NO", text, msg=name)
            for pat in forbidden:
                self.assertIsNone(re.search(pat, text), msg="%s matched %s" % (name, pat))

    def test_canonical_equals_presented_and_embeds_source(self) -> None:
        canon = (PACK / "OWNER_LIVE_SOURCE_CAPTURE.sh").read_bytes()
        presented = (PACK / "OWNER_PASTE_COMMAND_BLOCK.sh").read_bytes()
        self.assertEqual(canon, presented)
        self.assertGreater(len(canon), 1000)
        src = (PACK / "live_source_capture.py").read_text(encoding="utf-8")
        self.assertIn(src, canon.decode("utf-8"))

    def test_windows_ps1_does_not_write_production(self) -> None:
        text = (PACK / "OWNER_WINDOWS_SAVE.ps1").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"(?im)^\s*Get-Content\b", text))
        self.assertIn("[System.IO.File]::ReadAllBytes", text)
        self.assertIn("StandardInput.BaseStream", text)
        self.assertIn("IdentityFile", text)
        self.assertIn("EXTRACT_SKIPPED=YES", text)
        self.assertIn("SSH_TIMEOUT=YES", text)
        self.assertIn("SSH_START=FAIL", text)
        self.assertIn("WaitForExit", text)
        self.assertIsNone(re.search(r"(?im)^\s*scp\b", text))
        self.assertNotRegex(text, r"ssh[^\n]*bash\s+>")
        self.assertIn("PRODUCTION_WRITE=NO", text)
        self.assertIn("SCP_UPLOAD=NO", text)
        self.assertIn("$code -ne 0", text)


class ThreeWayTests(unittest.TestCase):
    def test_no_live_skips(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = tw.main([])
        self.assertEqual(rc, 0)
        self.assertIn("CAPTURE_RETURNED=NO", buf.getvalue())
        self.assertIn("DEPLOY_EXECUTION_PACK=NO", buf.getvalue())

    def test_live_equals_origin(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "live"
            copy_tree(ORIGIN_DIR, live)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tw.main(["--live", str(live)])
            stdout = buf.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("THREE_WAY_CLASS app/main.py MATCH_ORIGIN_MAIN", stdout)
            self.assertIn("THREE_WAY_CLASS app/data/repository/__init__.py MATCH_ORIGIN_MAIN", stdout)
            self.assertIn("THREE_WAY_CLASS app/core/feature_loader_bridge.py MATCH_ORIGIN_MAIN", stdout)

    def test_live_equals_v6(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "live"
            copy_tree(V6_DIR, live)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tw.main(["--live", str(live)])
            stdout = buf.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("THREE_WAY_CLASS app/main.py MATCH_V6", stdout)
            self.assertIn("MAIN_PY_LATER_MODE=ALREADY_CANDIDATE", stdout)

    def test_live_divergent_hunk_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "live"
            copy_tree(ORIGIN_DIR, live)
            main = live / "app" / "main.py"
            main.write_bytes(main.read_bytes() + b"\n# live-only marker\n")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tw.main(["--live", str(live)])
            stdout = buf.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("THREE_WAY_CLASS app/main.py DIVERGENT", stdout)
            self.assertIn("MAIN_PY_WHOLESALE_REPLACE_ALLOWED=NO", stdout)
            self.assertIn("MAIN_PY_LATER_MODE=HUNK_ONLY", stdout)
            self.assertIn("DIFF_ORIGIN_VS_LIVE_LINES=", stdout)
            self.assertIn("live-only marker", stdout)
            self.assertIn("PRODUCTION_CODE_DEPLOY_ALLOWED=NO", stdout)


class PackContractTests(unittest.TestCase):
    def test_flags_and_readme_hold_invariants(self) -> None:
        flags = (PACK / "FLAGS.txt").read_text(encoding="utf-8")
        readme = (PACK / "00_README.txt").read_text(encoding="utf-8")
        forbid = (PACK / "07_DO_NOT_WRITE.txt").read_text(encoding="utf-8")
        for text in (flags, readme, forbid):
            self.assertIn("PRODUCTION_CODE_DEPLOY_ALLOWED=NO", text)
            self.assertIn("OWNER_DEPLOY_APPROVED=NO", text)
            self.assertIn("POST_CODE_PRODUCTION_DEPLOYED=NO", text)
            self.assertIn("INDEPENDENT_REVIEW_OF_READONLY_LIVE_SOURCE_CAPTURE_V2", text)
        self.assertIn(V5_ZIP_SHA, flags)
        self.assertIn(V6_ZIP_SHA, flags)
        self.assertIn(V1_CAPTURE_ZIP_SHA, flags)
        self.assertIn(OWNER_LOG_SHA, flags)
        self.assertIn("SCP_UPLOAD=NO", flags)
        self.assertIn("GIT_PULL=NO", flags)
        self.assertIn(OWNER_LOG_SHA, readme)
        self.assertIn("COMPARE_RESULT=GO is not a deploy approval", readme)

    def test_pack_does_not_ship_old_zips(self) -> None:
        shipped = {p.name for p in PACK.rglob("*") if p.is_file()}
        for name in IMMUTABLE_ZIPS:
            self.assertNotIn(name, shipped)

    def test_capture_targets_are_exactly_three(self) -> None:
        self.assertEqual(cap.CAPTURE_RELS, tw.CAPTURE_RELS)
        self.assertEqual(len(cap.CAPTURE_RELS), 3)
        self.assertNotIn("app/data/db.py", cap.CAPTURE_RELS)


class ReadOnlyOpenTests(unittest.TestCase):
    def test_read_readonly_uses_o_rdonly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.py"
            path.write_bytes(b"abc")
            opened: list[int] = []
            real_open = os.open

            def wrapped(name, flags, *args, **kwargs):
                opened.append(flags)
                return real_open(name, flags, *args, **kwargs)

            with patch.object(os, "open", side_effect=wrapped):
                data = cap.read_readonly(path)
            self.assertEqual(data, b"abc")
            self.assertTrue(opened)
            self.assertTrue(all(flags == os.O_RDONLY for flags in opened))


if __name__ == "__main__":
    unittest.main()
