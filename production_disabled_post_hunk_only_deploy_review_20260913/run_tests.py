#!/usr/bin/env python3
"""Independently re-run hunk-only review tests from this ZIP alone.

Does not talk to Production. Does not SSH. Does not POST.
Does not require an external git clone.
Does not rewrite SHA256SUMS.txt (generated last by pack author).
Bundled logs are never treated as success.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parent
EXPECTED_TEST_COUNT = 31


def main() -> int:
    loader = unittest.defaultTestLoader
    suite = loader.discover(str(PACK / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    ran = result.testsRun
    if not result.wasSuccessful():
        print("INDEPENDENT_TEST_EXECUTION_PASS is not set")
        print("SELF_TEST=FAIL")
        return 1
    if ran != EXPECTED_TEST_COUNT:
        print("INDEPENDENT_TEST_EXECUTION_PASS is not set")
        print("TEST_COUNT_MISMATCH=%s expected=%s" % (ran, EXPECTED_TEST_COUNT))
        return 2
    print("SELF_TEST=PASS")
    print("RAN=%s" % ran)
    print("INDEPENDENT_TEST_EXECUTION_PASS=YES")
    print("NEXT_STEP=INDEPENDENT_REVIEW_OF_HUNK_ONLY_CODE_DEPLOY_BUNDLE")
    print("PRODUCTION_CODE_DEPLOY_ALLOWED=NO")
    print("OWNER_DEPLOY_APPROVED=NO")
    print("POST_CODE_PRODUCTION_DEPLOYED=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
