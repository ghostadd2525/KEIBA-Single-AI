#!/usr/bin/env python3
"""Independently re-run overlay tests from this ZIP alone.

Does not talk to Production. Does not SSH. Does not POST.
Does not require an external git clone.

Pass condition is a live unittest run after:
  1. verifying the bundled origin/main 25a3f88 base tar/SHA
  2. extracting that base into a temporary directory
  3. overlaying files/
  4. executing unittest
  5. asserting Ran 51 tests and OK

Bundled tests/*.log is never treated as success.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PACK = "production_disabled_post_code_deploy_review_v4_20260912"
BASE_COMMIT = "25a3f88b8aab61a5462c06efa133b21865ef6083"
EXPECTED_TEST_COUNT = 51
ROOT = Path(__file__).resolve().parent
FILES = ROOT / "files"
BASE_DIR = ROOT / "base"
IDENTITY_PATH = BASE_DIR / "IDENTITY.txt"
TAR_NAME = "origin_main_25a3f88.tar.gz"
TEST_MODULES = (
    "tests.predictions.test_disabled_post_deploy_prep",
    "tests.predictions.test_local_implementation",
    "tests.ops.test_feature_loader",
)


def _print(msg: str) -> None:
    print(msg, flush=True)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_identity(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key] = value
    return out


def parse_sums(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, name = raw.split("  ", 1)
        out[name] = digest
    return out


def fail_verify(reason: str) -> int:
    _print("BASE_VERIFY_FAIL")
    _print("INDEPENDENT_TEST_EXECUTION_PASS is not set")
    _print("REASON=%s" % reason)
    _print("Recorded logs in tests/ are not a pass condition.")
    return 2


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


def parse_ran_count(text: str) -> int | None:
    for line in text.splitlines():
        if line.startswith("Ran ") and " test" in line:
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
    return None


def verify_and_extract_base(dest: Path) -> dict[str, str]:
    if not IDENTITY_PATH.is_file():
        raise RuntimeError("identity_missing")
    identity = parse_identity(IDENTITY_PATH)
    if identity.get("BASE_COMMIT") != BASE_COMMIT:
        raise RuntimeError(
            "base_commit_mismatch:%s" % identity.get("BASE_COMMIT")
        )
    tar_name = identity.get("TAR_PATH") or TAR_NAME
    tar_path = BASE_DIR / tar_name
    if not tar_path.is_file():
        raise RuntimeError("base_tar_missing")
    actual_tar = _sha256(tar_path)
    expected_tar = identity.get("TAR_SHA256") or ""
    if actual_tar != expected_tar:
        raise RuntimeError("tar_sha256_mismatch")
    sums_path = BASE_DIR / "SHA256SUMS.txt"
    if not sums_path.is_file():
        raise RuntimeError("base_sha256sums_missing")
    expected_files = parse_sums(sums_path)
    expected_count = int(identity.get("FILE_COUNT") or "0")
    if expected_count != len(expected_files):
        raise RuntimeError("identity_file_count_mismatch")
    dest.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    tar_mode = "r:gz" if tar_path.name.endswith(".tar.gz") else "r:"
    with tarfile.open(tar_path, tar_mode) as tf:
        for member in tf.getmembers():
            name = member.name
            if name in (".",):
                continue
            if name.startswith("/") or ".." in Path(name).parts:
                raise RuntimeError("unsafe_tar_member:%s" % name)
            if member.isdir():
                (dest / name).mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            if name not in expected_files:
                raise RuntimeError("unexpected_tar_member:%s" % name)
            fh = tf.extractfile(member)
            if fh is None:
                raise RuntimeError("tar_member_unreadable:%s" % name)
            data = fh.read()
            digest = _sha256_bytes(data)
            if digest != expected_files[name]:
                raise RuntimeError("member_sha256_mismatch:%s" % name)
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            seen.add(name)
    missing = sorted(set(expected_files) - seen)
    if missing:
        raise RuntimeError("missing_tar_members:%s" % ",".join(missing[:5]))
    if len(seen) != expected_count:
        raise RuntimeError("extracted_file_count_mismatch")
    return identity


def main() -> int:
    _print("BUNDLE=%s" % PACK)
    _print("PRODUCTION_CODE_DEPLOY_ALLOWED=NO")
    _print("BASE_COMMIT=%s" % BASE_COMMIT)
    _print("EXPECTED_TEST_COUNT=%s" % EXPECTED_TEST_COUNT)
    if not FILES.is_dir():
        return fail_verify("files_directory_missing")
    if not BASE_DIR.is_dir():
        return fail_verify("bundled_base_missing")

    tmp = tempfile.mkdtemp(prefix="disabled-post-v3-overlay-")
    try:
        tree = Path(tmp) / "tree"
        identity = verify_and_extract_base(tree)
        _print("BASE_COMMIT_VERIFIED=%s" % identity["BASE_COMMIT"])
        _print("WIN5_TREE_SHA=%s" % identity.get("WIN5_TREE_SHA", ""))
        _print("TAR_SHA256_VERIFIED=%s" % identity["TAR_SHA256"])
        _print("BASE_FILE_COUNT=%s" % identity["FILE_COUNT"])
        copied = overlay_files(FILES, tree)
        _print("OVERLAY_FILES=%s" % copied)
        win5 = tree / "services" / "win5-ai"
        if not (win5 / "app" / "main.py").is_file():
            return fail_verify("overlay_missing_main_py")
        env = os.environ.copy()
        env.pop("PREDICTION_RUNS_ENABLED", None)
        env.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
        env.pop("EXPECT_AI_ALLOW_MIGRATION_019", None)
        cmd = [sys.executable, "-m", "unittest", *TEST_MODULES]
        proc = subprocess.run(
            cmd,
            cwd=str(win5),
            env=env,
            capture_output=True,
            text=True,
        )
        log_dir = ROOT / "tests"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
            (log_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
            (log_dir / "combined.log").write_text(
                proc.stdout + proc.stderr, encoding="utf-8"
            )
        except OSError:
            pass
        if proc.stderr.strip():
            _print(proc.stderr.rstrip())
        if proc.stdout.strip():
            _print(proc.stdout.rstrip())
        text = proc.stderr + "\n" + proc.stdout
        ran = parse_ran_count(text)
        ok_line = "\nOK\n" in ("\n" + text + "\n")
        if ran != EXPECTED_TEST_COUNT:
            _print("INDEPENDENT_TEST_EXECUTION_FAIL")
            _print("INDEPENDENT_TEST_COUNT_MISMATCH expected=%s actual=%s" % (
                EXPECTED_TEST_COUNT,
                ran,
            ))
            return 1
        if proc.returncode == 0 and ok_line:
            _print("INDEPENDENT_TEST_EXECUTION_PASS")
            _print("INDEPENDENT_TEST_RESULT=Ran %s tests" % ran)
            return 0
        _print("INDEPENDENT_TEST_EXECUTION_FAIL")
        return 1
    except (OSError, RuntimeError, tarfile.TarError, ValueError) as exc:
        return fail_verify("materialize_or_verify_error:%s" % exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
