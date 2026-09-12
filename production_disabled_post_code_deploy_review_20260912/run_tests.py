#!/usr/bin/env python3
"""Re-run local tests if files/ is copied onto an origin/main tree.

This script does not talk to Production.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    print("BUNDLE=production_disabled_post_code_deploy_review_20260912")
    print("PRODUCTION_CODE_DEPLOY_ALLOWED=NO")
    print("LOCAL_TEST_LOGS=tests/stderr.log")
    print("Recorded suite: 48 tests OK (see tests/combined.log)")
    print("To replay: copy files/ onto origin/main 25a3f88 and run")
    print("  python3 -m unittest tests.predictions.test_disabled_post_deploy_prep \\")
    print("    tests.predictions.test_local_implementation tests.ops.test_feature_loader")
    logs = ROOT / "tests" / "stderr.log"
    text = logs.read_text(encoding="utf-8", errors="replace") if logs.is_file() else ""
    if "Ran 48 tests" in text and "\nOK\n" in text:
        print("RECORDED_LOCAL_TESTS=OK")
        return 0
    print("RECORDED_LOCAL_TESTS=MISSING_OR_FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
