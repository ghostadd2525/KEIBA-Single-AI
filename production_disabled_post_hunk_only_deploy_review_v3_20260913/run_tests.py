#!/usr/bin/env python3
"""Hunk-only v3 self-tests + live-dependency overlay suite.

Does not talk to Production. Does not SSH. Does not POST.
Does not rewrite SHA256SUMS.txt.
Does not treat bundled logs as success.
Does not stub app.ops.prediction_capacity or final_prediction_store.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parent
EXPECTED_STRUCT_TEST_COUNT = 39
EXPECTED_OVERLAY_TEST_COUNT = 52
CONCURRENCY_REPEAT = 20
FULL_SUITE_REPEAT = 2
BASE_COMMIT = "25a3f88b8aab61a5462c06efa133b21865ef6083"
CAPACITY_SHA = "c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e"
STORE_SHA = "40352ff56b3267533267d5de9c893f3bda8963d5fe121474f7785b0152594a12"
HUNKED_MAIN_SHA = "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c"
ORIGIN_TAR_SHA = "d1e6b5847f1387d696d39b87ad0dbfa4e44f8322ad1caecb75ce0969bad5edff"
TEST_MODULES = (
    "tests.predictions.test_disabled_post_deploy_prep",
    "tests.predictions.test_local_implementation",
    "tests.ops.test_feature_loader",
)
EXTRA_MODULE = "tests.predictions.test_live_nonwrite_regression"
CONCURRENCY_TEST = (
    "tests.predictions.test_local_implementation."
    "ReviewContractTests.test_separate_process_concurrency"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_identity(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        out[k] = v
    return out


def parse_sums(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, name = raw.split("  ", 1)
        out[name] = digest
    return out


def parse_ran_count(text: str) -> int | None:
    for line in text.splitlines():
        if line.startswith("Ran ") and " test" in line:
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
    return None


def suite_ok(proc: subprocess.CompletedProcess[str], text: str, expected: int) -> bool:
    ran = parse_ran_count(text)
    ok_line = "\nOK\n" in ("\n" + text + "\n")
    return proc.returncode == 0 and ok_line and ran == expected


def overlay_files(src: Path, dest: Path) -> int:
    count = 0
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        target = dest / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        count += 1
    return count


def live_ops_ready() -> tuple[bool, str]:
    cap = PACK / "live_canon/app/ops/prediction_capacity.py"
    store = PACK / "live_canon/app/ops/final_prediction_store.py"
    if not cap.is_file() or not store.is_file():
        return False, "LIVE_CANON_OPS_MISSING"
    if _sha256(cap) != CAPACITY_SHA:
        return False, "LIVE_CAPACITY_SHA_MISMATCH"
    if _sha256(store) != STORE_SHA:
        return False, "LIVE_STORE_SHA_MISMATCH"
    return True, "OK"


def extract_base(dest: Path) -> None:
    identity = parse_identity(PACK / "base/IDENTITY.txt")
    if identity.get("BASE_COMMIT") != BASE_COMMIT:
        raise RuntimeError("base_commit_mismatch")
    tar_path = PACK / "base" / identity["TAR_PATH"]
    if _sha256(tar_path) != identity["TAR_SHA256"]:
        raise RuntimeError("tar_sha256_mismatch")
    expected = parse_sums(PACK / "base/SHA256SUMS.txt")
    dest.mkdir(parents=True)
    seen: set[str] = set()
    with tarfile.open(tar_path, "r:gz") as tf:
        for member in tf.getmembers():
            name = member.name
            if name in (".",) or member.isdir():
                if member.isdir() and name not in (".",):
                    (dest / name).mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            if name.startswith("/") or ".." in Path(name).parts:
                raise RuntimeError("unsafe_tar_member:%s" % name)
            fh = tf.extractfile(member)
            if fh is None:
                raise RuntimeError("unreadable:%s" % name)
            data = fh.read()
            if hashlib.sha256(data).hexdigest() != expected[name]:
                raise RuntimeError("member_sha_mismatch:%s" % name)
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            seen.add(name)
    if len(seen) != int(identity["FILE_COUNT"]):
        raise RuntimeError("extracted_file_count_mismatch")


def run_python(win5: Path, env: dict[str, str], args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "unittest", *args],
        cwd=str(win5),
        env=env,
        capture_output=True,
        text=True,
    )


def run_struct_tests() -> int:
    loader = unittest.defaultTestLoader
    suite = loader.discover(str(PACK / "tests"), pattern="test_hunk_only_v3_review.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        print("STRUCT_SELF_TEST=FAIL")
        return 1
    if result.testsRun != EXPECTED_STRUCT_TEST_COUNT:
        print("STRUCT_TEST_COUNT_MISMATCH=%s expected=%s" % (
            result.testsRun, EXPECTED_STRUCT_TEST_COUNT
        ))
        return 2
    print("STRUCT_SELF_TEST=PASS RAN=%s" % result.testsRun)
    return 0


def run_overlay() -> int:
    ready, reason = live_ops_ready()
    if not ready:
        print("OVERLAY_SUITE=NOT_RUN")
        print("REASON=%s" % reason)
        print("STUB_OR_MOCK_SUCCESS=NO")
        print("INDEPENDENT_TEST_EXECUTION_PASS is not set")
        return 3
    tmp = tempfile.mkdtemp(prefix="hunk-only-v3-overlay-")
    try:
        tree = Path(tmp) / "tree"
        extract_base(tree)
        overlay_files(PACK / "overlay_v6", tree)
        hunked = PACK / "candidates/services/win5-ai/app/main.py"
        if _sha256(hunked) != HUNKED_MAIN_SHA:
            raise RuntimeError("hunked_main_sha_mismatch")
        shutil.copy2(hunked, tree / "services/win5-ai/app/main.py")
        shutil.copy2(
            PACK / "live_canon/app/ops/prediction_capacity.py",
            tree / "services/win5-ai/app/ops/prediction_capacity.py",
        )
        shutil.copy2(
            PACK / "live_canon/app/ops/final_prediction_store.py",
            tree / "services/win5-ai/app/ops/final_prediction_store.py",
        )
        overlay_files(PACK / "overlay_extra", tree)
        win5 = tree / "services/win5-ai"
        env = os.environ.copy()
        env.pop("PREDICTION_RUNS_ENABLED", None)
        env.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
        env.pop("EXPECT_AI_ALLOW_MIGRATION_019", None)
        for suite_idx in range(1, FULL_SUITE_REPEAT + 1):
            proc = run_python(win5, env, list(TEST_MODULES))
            text = proc.stdout + proc.stderr
            print(text.rstrip())
            if not suite_ok(proc, text, EXPECTED_OVERLAY_TEST_COUNT):
                print("FULL_SUITE_%s_FAIL rc=%s" % (suite_idx, proc.returncode))
                return 1
            print("FULL_SUITE_%s_PASS Ran %s tests" % (suite_idx, EXPECTED_OVERLAY_TEST_COUNT))
            if suite_idx == 1:
                for conc_idx in range(1, CONCURRENCY_REPEAT + 1):
                    cproc = run_python(win5, env, [CONCURRENCY_TEST])
                    ctext = cproc.stdout + cproc.stderr
                    if not suite_ok(cproc, ctext, 1):
                        print(ctext.rstrip())
                        print("CONCURRENCY_REPEAT_%s_FAIL" % conc_idx)
                        return 1
                    print("CONCURRENCY_REPEAT_%s_PASS" % conc_idx)
        extra = run_python(win5, env, [EXTRA_MODULE])
        etext = extra.stdout + extra.stderr
        print(etext.rstrip())
        if extra.returncode != 0 or "\nOK\n" not in ("\n" + etext + "\n"):
            print("EXTRA_LIVE_REGRESSION_FAIL")
            return 1
        print("EXTRA_LIVE_REGRESSION_PASS")
        print("INDEPENDENT_TEST_EXECUTION_PASS")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    print("BUNDLE=production_disabled_post_hunk_only_deploy_review_v3_20260913")
    print("PRODUCTION_CODE_DEPLOY_ALLOWED=NO")
    print("STUB_OR_MOCK_SUCCESS=NO")
    rc = run_struct_tests()
    if rc != 0:
        return rc
    rc = run_overlay()
    print("NEXT_STEP=INDEPENDENT_REVIEW_OF_HUNK_ONLY_V3_BUNDLE")
    print("OWNER_DEPLOY_APPROVED=NO")
    print("POST_CODE_PRODUCTION_DEPLOYED=NO")
    return rc


if __name__ == "__main__":
    sys.exit(main())
