#!/usr/bin/env python3
"""Independently re-run overlay tests. Does not talk to Production.

Pass condition is a live unittest run after overlaying files/ onto
origin/main 25a3f88. Bundled tests/*.log is evidence of a prior run
only and is never treated as success.

If the base commit cannot be materialized, print
RECORDED_LOCAL_TESTS_ONLY and do not print
INDEPENDENT_TEST_EXECUTION_PASS.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PACK = "production_disabled_post_code_deploy_review_v2_20260912"
BASE_COMMIT = "25a3f88b8aab61a5462c06efa133b21865ef6083"
ROOT = Path(__file__).resolve().parent
FILES = ROOT / "files"
TEST_MODULES = (
    "tests.predictions.test_disabled_post_deploy_prep",
    "tests.predictions.test_local_implementation",
    "tests.ops.test_feature_loader",
)


def _print(msg: str) -> None:
    print(msg, flush=True)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )


def _has_base_commit(repo: Path) -> bool:
    if not repo.is_dir():
        return False
    git_entry = repo / ".git"
    if not git_entry.exists():
        return False
    proc = _git(repo, "cat-file", "-t", BASE_COMMIT)
    return proc.returncode == 0 and proc.stdout.strip() == "commit"


def find_git_repo() -> Path | None:
    pinned = (os.environ.get("EXPECT_AI_BUNDLE_BASE") or os.environ.get("BUNDLE_GIT_DIR") or "").strip()
    if pinned:
        path = Path(pinned)
        return path if _has_base_commit(path) else None
    candidates: list[Path] = []
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=str(Path.cwd()),
        )
        if top.returncode == 0 and top.stdout.strip():
            candidates.append(Path(top.stdout.strip()))
    except OSError:
        pass
    candidates.extend([ROOT, *ROOT.parents, Path.cwd(), *Path.cwd().parents])
    seen: set[Path] = set()
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if _has_base_commit(resolved):
            return resolved
    return None


def materialize_base(repo: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", BASE_COMMIT],
        check=True,
        stdout=subprocess.PIPE,
    )
    subprocess.run(
        ["tar", "-x", "-C", str(dest)],
        check=True,
        input=archive.stdout,
    )


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


def recorded_only(reason: str) -> int:
    _print("RECORDED_LOCAL_TESTS_ONLY")
    _print("INDEPENDENT_TEST_EXECUTION_PASS is not set")
    _print("REASON=%s" % reason)
    _print("Recorded logs in tests/ are not a pass condition.")
    _print("To re-run: set EXPECT_AI_BUNDLE_BASE to a git clone that contains")
    _print("commit %s and execute python3 run_tests.py" % BASE_COMMIT)
    return 2


def main() -> int:
    _print("BUNDLE=%s" % PACK)
    _print("PRODUCTION_CODE_DEPLOY_ALLOWED=NO")
    _print("BASE_COMMIT=%s" % BASE_COMMIT)
    if not FILES.is_dir():
        return recorded_only("files_directory_missing")

    repo = find_git_repo()
    if repo is None:
        return recorded_only("origin_main_25a3f88_unavailable")

    _print("GIT_REPO=%s" % repo)
    tmp = tempfile.mkdtemp(prefix="disabled-post-v2-overlay-")
    try:
        base = Path(tmp) / "tree"
        materialize_base(repo, base)
        copied = overlay_files(FILES, base)
        _print("OVERLAY_FILES=%s" % copied)
        win5 = base / "services" / "win5-ai"
        if not (win5 / "app" / "main.py").is_file():
            return recorded_only("overlay_missing_main_py")
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
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
        (log_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
        (log_dir / "combined.log").write_text(
            proc.stdout + proc.stderr, encoding="utf-8"
        )
        _print(proc.stderr.rstrip())
        if proc.stdout.strip():
            _print(proc.stdout.rstrip())
        text = proc.stderr + "\n" + proc.stdout
        ran = None
        for line in text.splitlines():
            if line.startswith("Ran ") and " test" in line:
                ran = line.strip()
        ok = proc.returncode == 0 and "\nOK\n" in ("\n" + text + "\n")
        if ok:
            _print("INDEPENDENT_TEST_EXECUTION_PASS")
            if ran:
                _print("INDEPENDENT_TEST_RESULT=%s" % ran)
            return 0
        _print("INDEPENDENT_TEST_EXECUTION_FAIL")
        if ran:
            _print("INDEPENDENT_TEST_RESULT=%s" % ran)
        return 1
    except (OSError, subprocess.CalledProcessError) as exc:
        return recorded_only("materialize_or_exec_error:%s" % exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
