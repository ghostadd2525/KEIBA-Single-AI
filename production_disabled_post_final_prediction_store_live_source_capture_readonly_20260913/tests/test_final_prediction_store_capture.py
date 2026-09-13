#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import os
import re
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
import live_source_capture as cap  # noqa: E402

HEX64 = re.compile(r"^[0-9a-f]{64}$")
REL = "app/ops/final_prediction_store.py"
FIXTURE = PACK / "fixtures" / "capture_target"
HUNK_ZIP_SHA = "f194488073a98a54fc4fafcadb808f32d3e0b8e53665dcb317da7c7662824db4"
V6_ZIP_SHA = "548b274facc2b4f8ffba8b854a6e009d8b7455fb816dcde9550eb9b364329373"
V3_CAP_SHA = "06590a373b1730e01f1a445bf55e6c283afa1a0e412818ab655f50b4e2c250b2"
CAPACITY_PACK_SHA = "9f91bebe1646d8686ec182ff8b70e12b215526508e4c62b7eb86055c25b6a143"
CAPACITY_OWNER_SHA = "c04f27e6bc9016927c9a902268ccfeb5a8ac8a62117ca74948b90bc7cbbea843"
CAPACITY_FILE_SHA = "c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e"
LEAK_DSN = "postgres://user:supersecret@example/db"
DUMMY_SECRET = "SUPER_SECRET_TOKEN_XYZ"
IMMUTABLE_ZIPS = (
    "production_disabled_post_hunk_only_deploy_review_20260913.zip",
    "production_disabled_post_code_deploy_review_v6_20260912.zip",
    "production_disabled_post_live_source_capture_readonly_v3_20260912.zip",
    "production_disabled_post_live_source_capture_readonly_v2_20260912.zip",
    "production_disabled_post_live_source_capture_readonly_20260912.zip",
    "production_disabled_post_prediction_capacity_live_source_capture_readonly_20260913.zip",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_flags(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        out[k] = v
    return out


def copy_fixture(win5: Path) -> None:
    src = FIXTURE / REL
    dst = win5 / REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    (win5 / "app" / "main.py").parent.mkdir(parents=True, exist_ok=True)
    (win5 / "app" / "main.py").write_text("# discover marker\n", encoding="utf-8")


def systemd_fixture(win5: Path) -> dict[str, str]:
    return {
        "Id": "expect-ai.service",
        "LoadState": "loaded",
        "FragmentPath": "/etc/systemd/system/expect-ai.service",
        "WorkingDirectory": str(win5),
        "ExecStart": (
            "{ path=/usr/bin/python3 ; "
            "argv[]=/usr/bin/python3 -m app.main --dsn %s --token %s ; "
            "ignore_errors=no }" % (LEAK_DSN, DUMMY_SECRET)
        ),
    }


def run_capture(win5: Path, *, prepare: bool = True, show: dict | None = None) -> tuple[int, str]:
    if prepare:
        copy_fixture(win5)
    buf = io.StringIO()
    with patch.object(cap, "systemd_show", return_value=show or systemd_fixture(win5)):
        with redirect_stdout(buf):
            rc = cap.main()
    return rc, buf.getvalue()


class SearchAndContractTests(unittest.TestCase):
    def test_search_result_is_not_found(self) -> None:
        text = (PACK / "01_docs/search_result.txt").read_text(encoding="utf-8")
        self.assertIn("SEARCH_RESULT=NOT_FOUND", text)
        self.assertIn("IDENTITY_PROVEN=NO", text)
        self.assertIn(REL, text)
        self.assertIn("git log --all", text)
        self.assertIn("persistent_store_enabled", text)

    def test_flags_forbid_execute_and_stub_success(self) -> None:
        flags = parse_flags(PACK / "FLAGS.txt")
        self.assertEqual(flags["SEARCH_RESULT"], "NOT_FOUND")
        self.assertEqual(flags["IDENTITY_PROVEN"], "NO")
        self.assertEqual(flags["OWNER_EXECUTE_NOW"], "NO")
        self.assertEqual(flags["STUB_OR_MOCK_SUCCESS"], "NO")
        self.assertEqual(flags["OVERLAY_RETEST_INCLUDED"], "NO")
        self.assertEqual(flags["V6_SUITE_RERUN"], "NO")
        self.assertEqual(flags["PRODUCTION_CODE_DEPLOY_ALLOWED"], "NO")
        self.assertEqual(flags["CURSOR_PRODUCTION_SSH"], "NO")
        self.assertEqual(flags["CAPTURE_REL_1"], REL)
        self.assertEqual(flags["HUNK_ONLY_REVIEW_ZIP_SHA256"], HUNK_ZIP_SHA)
        self.assertEqual(flags["V6_REVIEW_ZIP_SHA256"], V6_ZIP_SHA)
        self.assertEqual(flags["V3_CAPTURE_PACK_ZIP_SHA256"], V3_CAP_SHA)
        self.assertEqual(flags["HUNK_ONLY_REVIEW_RESULT"], "CHANGES_REQUIRED")
        self.assertEqual(flags["EXECUTION_PACK"], "NO")
        self.assertEqual(flags["PREDICTION_CAPACITY_DEPLOY_CANDIDATE"], "NO")
        self.assertEqual(flags["FINAL_PREDICTION_STORE_DEPLOY_CANDIDATE"], "NO")
        self.assertEqual(flags["PREDICTION_CAPACITY_SHA256"], CAPACITY_FILE_SHA)
        self.assertEqual(flags["PREDICTION_CAPACITY_OWNER_ZIP_SHA256"], CAPACITY_OWNER_SHA)
        self.assertEqual(flags["PREDICTION_CAPACITY_PACK_ZIP_SHA256"], CAPACITY_PACK_SHA)
        self.assertEqual(flags["V6_OVERLAY_AFTER_CAPACITY"], "FAILED_3")

    def test_single_capture_rel(self) -> None:
        self.assertEqual(cap.CAPTURE_RELS, (REL,))
        self.assertEqual(ex.CAPTURE_RELS, (REL,))

    def test_fixture_is_not_live_and_not_success(self) -> None:
        text = (FIXTURE / REL).read_text(encoding="utf-8")
        self.assertIn("CAPTURE_TOOL_FIXTURE", text)
        self.assertIn("LIVE_BYTES=NO", text)
        self.assertIn("capture_tool_fixture_is_not_live_bytes", text)
        self.assertIn("def get_store", text)
        self.assertIn("def persistent_store_enabled", text)
        readme = (PACK / "fixtures/README.txt").read_text(encoding="utf-8")
        self.assertIn("IDENTITY_PROVEN=NO", readme)

    def test_pack_does_not_contain_immutable_zips(self) -> None:
        self.assertEqual(list(PACK.rglob("*.zip")), [])
        for name in IMMUTABLE_ZIPS:
            self.assertFalse((PACK / name).exists(), name)

    def test_readme_stops_at_review(self) -> None:
        text = (PACK / "00_README.txt").read_text(encoding="utf-8")
        self.assertIn("OWNER_EXECUTE_NOW=NO", text)
        self.assertIn("STUB_OR_MOCK_SUCCESS=NO", text)
        self.assertIn(HUNK_ZIP_SHA, text)
        self.assertIn("52 tests twice", text)
        self.assertIn("PREDICTION_CAPACITY_DEPLOY_CANDIDATE=NO", text)
        donot = (PACK / "07_DO_NOT_WRITE.txt").read_text(encoding="utf-8")
        self.assertIn("Do not stub or mock", donot)
        self.assertIn("execution pack", donot)

    def test_capacity_is_live_canon_not_deploy(self) -> None:
        text = (PACK / "01_docs/capacity_live_canon.txt").read_text(encoding="utf-8")
        self.assertIn("PREDICTION_CAPACITY_DEPLOY_CANDIDATE=NO", text)
        self.assertIn(CAPACITY_FILE_SHA, text)
        self.assertIn("LIVE_CANON_AND_SHA_PRECONDITION", text)
        self.assertIn("Do not add it to the 11 hunk-only deploy candidates", text)


class CaptureToolTests(unittest.TestCase):
    def test_happy_path_go_and_extract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            rc, stdout = run_capture(win5)
            self.assertEqual(rc, 0, stdout)
            self.assertIn("CAPTURE_RESULT=GO", stdout)
            self.assertIn("TAR_MEMBER_COUNT=1", stdout)
            self.assertIn("CAPTURE_REL=%s" % REL, stdout)
            self.assertIn("CAPTURE_OPEN=OK", stdout)
            self.assertIn("PRODUCTION_CODE_DEPLOY_ALLOWED=NO", stdout)
            self.assertNotIn(LEAK_DSN, stdout)
            self.assertNotIn(DUMMY_SECRET, stdout)
            expect = sha256_file(FIXTURE / REL)
            self.assertIn("CAPTURE_SHA256=%s" % expect, stdout)
            transcript = Path(td) / "transcript.txt"
            transcript.write_text(stdout, encoding="utf-8")
            dest = Path(td) / "extracted"
            self.assertEqual(ex.main([str(transcript), "--out", str(dest)]), 0)
            self.assertEqual(sha256_file(dest / REL), expect)
            self.assertIn("CAPTURE_TOOL_FIXTURE", (dest / REL).read_text(encoding="utf-8"))

    def test_absent_is_stop_omits_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            (win5 / "app").mkdir(parents=True)
            (win5 / "app" / "main.py").write_text("# discover\n", encoding="utf-8")
            rc, stdout = run_capture(win5, prepare=False)
            self.assertNotEqual(rc, 0)
            self.assertIn("CAPTURE_RESULT=STOP", stdout)
            self.assertIn("STOP_REASON=capture_file_absent:%s" % REL, stdout)
            self.assertIn("TAR_PAYLOAD=OMITTED_INCOMPLETE", stdout)
            self.assertNotIn("=== TAR_BASE64_BEGIN ===", stdout)

    def test_symlink_is_stop_omits_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td) / "outside.py"
            outside.write_text("SECRET_OUTSIDE\n", encoding="utf-8")
            win5 = Path(td) / "services" / "win5-ai"
            copy_fixture(win5)
            target = win5 / REL
            target.unlink()
            target.symlink_to(outside)
            rc, stdout = run_capture(win5, prepare=False)
            self.assertNotEqual(rc, 0)
            self.assertIn("STOP_REASON=capture_symlink:%s" % REL, stdout)
            self.assertNotIn("SECRET_OUTSIDE", stdout)
            self.assertNotIn("=== TAR_BASE64_BEGIN ===", stdout)

    def test_dir_symlink_outside_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td) / "outside_ops"
            outside.mkdir()
            (outside / "final_prediction_store.py").write_text("SECRET_DIR\n", encoding="utf-8")
            win5 = Path(td) / "services" / "win5-ai"
            copy_fixture(win5)
            ops = win5 / "app" / "ops"
            real = win5 / "app" / "ops.real"
            ops.rename(real)
            ops.symlink_to(outside)
            rc, stdout = run_capture(win5, prepare=False)
            self.assertNotEqual(rc, 0)
            self.assertIn("CAPTURE_RESULT=STOP", stdout)
            self.assertNotIn("SECRET_DIR", stdout)
            self.assertNotIn("=== TAR_BASE64_BEGIN ===", stdout)

    def test_win5_missing_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "empty"
            win5.mkdir()
            rc, stdout = run_capture(win5, prepare=False, show=systemd_fixture(win5))
            self.assertNotEqual(rc, 0)
            self.assertIn("STOP_REASON=win5_root_not_found", stdout)

    def test_extract_existing_outdir_is_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            rc, stdout = run_capture(win5)
            self.assertEqual(rc, 0)
            transcript = Path(td) / "t.txt"
            transcript.write_text(stdout, encoding="utf-8")
            dest = Path(td) / "extracted"
            dest.mkdir()
            self.assertEqual(ex.main([str(transcript), "--out", str(dest)]), 2)

    def test_extract_stop_when_result_not_go(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "out"
            transcript = Path(td) / "t.txt"
            transcript.write_text("CAPTURE_RESULT=STOP\n", encoding="utf-8")
            self.assertEqual(ex.main([str(transcript), "--out", str(dest)]), 2)
            self.assertFalse(dest.exists())

    def test_scripts_byte_identical(self) -> None:
        build_owner_script.main()
        a = (PACK / "OWNER_LIVE_SOURCE_CAPTURE.sh").read_bytes()
        b = (PACK / "OWNER_PASTE_COMMAND_BLOCK.sh").read_bytes()
        self.assertEqual(a, b)
        self.assertIn(b"OWNER_READ_ONLY_FINAL_PREDICTION_STORE_CAPTURE", a)
        self.assertIn(REL.encode(), a)
        self.assertIn(b"THIS_SCRIPT_WRITES=NO", a)

    def test_ps1_stops_on_existing_outdir_and_no_get_content_raw(self) -> None:
        ps1 = (PACK / "OWNER_WINDOWS_SAVE.ps1").read_text(encoding="utf-8")
        self.assertIn("OUTDIR_EXISTS=YES", ps1)
        self.assertIn("SSH_SKIPPED=YES", ps1)
        self.assertIn("ReadAllBytes", ps1)
        self.assertNotIn("Get-Content -Raw", ps1)
        self.assertIn("GET_CONTENT_RAW=NO", ps1)
        self.assertIn("final_prediction_store_capture_windows", ps1)

    def test_lstat_regular_and_nofollow_flags(self) -> None:
        self.assertTrue(hasattr(os, "O_NOFOLLOW"))
        src = Path(cap.__file__).read_text(encoding="utf-8")
        self.assertIn("O_NOFOLLOW", src)
        self.assertIn("lstat_regular_or_raise", src)
        self.assertIn("fstat", src)

    def test_sha256sums_complete_when_present(self) -> None:
        sums = PACK / "SHA256SUMS.txt"
        if not sums.is_file():
            self.skipTest("SHA256SUMS generated last by run_tests.py")
        listed = {}
        for raw in sums.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            digest, name = raw.split("  ", 1)
            listed[name] = digest
        self.assertNotIn("SHA256SUMS.txt", listed)
        files = []
        for path in PACK.rglob("*"):
            if not path.is_file():
                continue
            if path.name == "SHA256SUMS.txt" or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            files.append(path.relative_to(PACK).as_posix())
        self.assertEqual(sorted(listed), sorted(files))
        for rel, digest in listed.items():
            self.assertTrue(HEX64.match(digest), rel)
            self.assertEqual(sha256_file(PACK / rel), digest, rel)

    def test_after_capture_doc_forbids_stub_pass(self) -> None:
        text = (PACK / "01_docs/after_capture_retest.txt").read_text(encoding="utf-8")
        self.assertIn("Mocking", text)
        self.assertIn("app.ops.final_prediction_store", text)
        self.assertIn("52-test suite twice", text)
        self.assertIn("concurrency 20", text)
        self.assertIn(HUNK_ZIP_SHA, text)
        self.assertIn("not a deploy candidate", text)

    def test_no_execution_scripts(self) -> None:
        names = [p.name.lower() for p in PACK.rglob("*") if p.is_file()]
        self.assertNotIn("owner_apply.ps1", names)
        self.assertFalse(any("owner_apply" in n for n in names))
        src = (PACK / "live_source_capture.py").read_text(encoding="utf-8")
        self.assertIn("THIS_SCRIPT_WRITES=NO", src)
        self.assertIn("SQLITE=NO", src)

    def test_capture_rel_not_in_origin_listing_doc(self) -> None:
        text = (PACK / "01_docs/search_result.txt").read_text(encoding="utf-8")
        self.assertIn("origin ops/__init__.py does not export final_prediction_store", text)
        self.assertIn("f02c50e", text)

    def test_windows_procedure_mentions_one_file(self) -> None:
        text = (PACK / "01_docs/capture_procedure.txt").read_text(encoding="utf-8")
        self.assertIn(REL, text)
        self.assertIn("OWNER_EXECUTE_NOW=NO", text)
        self.assertIn("exactly one regular file", text)


class ExtraSafetyTests(unittest.TestCase):
    def test_leaky_execstart_not_printed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            rc, stdout = run_capture(win5)
            self.assertEqual(rc, 0)
            self.assertNotIn("DATABASE_URL", stdout)
            self.assertNotIn("authorization", stdout.lower())
            self.assertNotIn(DUMMY_SECRET, stdout)

    def test_extract_rejects_symlink_member(self) -> None:
        import base64
        import tarfile

        with tempfile.TemporaryDirectory() as td:
            win5 = Path(td) / "services" / "win5-ai"
            rc, stdout = run_capture(win5)
            self.assertEqual(rc, 0)
            begin = "=== TAR_BASE64_BEGIN ==="
            end = "=== TAR_BASE64_END ==="
            start = stdout.find(begin)
            stop = stdout.find(end)
            prefix = stdout[:start]
            suffix = stdout[stop + len(end) :]
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                info = tarfile.TarInfo(name=REL)
                info.type = tarfile.SYMTYPE
                info.linkname = "elsewhere"
                tar.addfile(info)
            blob = buf.getvalue()
            b64 = base64.b64encode(blob).decode("ascii")
            prefix = re.sub(r"(?m)^TAR_GZ_BYTES=\d+$", "TAR_GZ_BYTES=%s" % len(blob), prefix)
            prefix = re.sub(
                r"(?m)^TAR_GZ_SHA256=[0-9a-f]{64}$",
                "TAR_GZ_SHA256=%s" % hashlib.sha256(blob).hexdigest(),
                prefix,
            )
            prefix = re.sub(r"(?m)^TAR_B64_CHARS=\d+$", "TAR_B64_CHARS=%s" % len(b64), prefix)
            prefix = re.sub(
                r"(?m)^TAR_B64_SHA256=[0-9a-f]{64}$",
                "TAR_B64_SHA256=%s" % hashlib.sha256(b64.encode("ascii")).hexdigest(),
                prefix,
            )
            bad = prefix + begin + "\n" + b64 + "\n" + end + suffix
            transcript = Path(td) / "bad.txt"
            transcript.write_text(bad, encoding="utf-8")
            dest = Path(td) / "out"
            self.assertEqual(ex.main([str(transcript), "--out", str(dest)]), 2)
            self.assertFalse(dest.exists())

    def test_pack_name_consistency(self) -> None:
        flags = parse_flags(PACK / "FLAGS.txt")
        self.assertTrue(flags["PACK"].startswith("production_disabled_post_final_prediction_store_"))
        readme = (PACK / "00_README.txt").read_text(encoding="utf-8")
        self.assertIn(flags["PACK"], readme)

    def test_no_v6_main_wholesale_in_this_pack(self) -> None:
        mains = list(PACK.rglob("main.py"))
        self.assertEqual(mains, [])

    def test_go_stop_requires_single_rel(self) -> None:
        text = (PACK / "01_docs/go_stop.txt").read_text(encoding="utf-8")
        self.assertIn("exactly one REL=%s" % REL, text)
        self.assertIn("OWNER_EXECUTE_NOW=NO", text)

    def test_run_tests_rewrites_sums_last_only(self) -> None:
        src = (PACK / "run_tests.py").read_text(encoding="utf-8")
        self.assertIn("write_sha256sums()", src)
        self.assertIn("EXPECTED_TEST_COUNT = 29", src)

    def test_does_not_recapture_prediction_capacity(self) -> None:
        srcs = "\n".join(
            p.read_text(encoding="utf-8")
            for p in (PACK / "live_source_capture.py", PACK / "extract_capture.py")
        )
        self.assertNotIn("app/ops/prediction_capacity.py", srcs)
        self.assertIn(REL, srcs)


if __name__ == "__main__":
    unittest.main()
