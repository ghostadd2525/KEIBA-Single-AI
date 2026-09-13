#!/usr/bin/env python3
"""Self-tests for the final_prediction_store capture pack. No Production ops."""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parent
EXPECTED_TEST_COUNT = 29


def write_sha256sums() -> None:
    lines: list[str] = []
    for path in sorted(PACK.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "SHA256SUMS.txt":
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rel = path.relative_to(PACK).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append("%s  %s" % (digest, rel))
    (PACK / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    sys.path.insert(0, str(PACK))
    import build_owner_script

    build_owner_script.main()
    loader = unittest.defaultTestLoader
    suite = loader.discover(str(PACK / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        print("SELF_TEST=FAIL")
        return 1
    if result.testsRun != EXPECTED_TEST_COUNT:
        print("SELF_TEST=FAIL")
        print("TEST_COUNT_MISMATCH=%s expected=%s" % (result.testsRun, EXPECTED_TEST_COUNT))
        return 2
    write_sha256sums()
    print("SELF_TEST=PASS")
    print("RAN=%s" % result.testsRun)
    print("CANONICAL_PRESENTED_IDENTICAL=YES")
    print("OWNER_EXECUTE_NOW=NO")
    print("NEXT_STEP=INDEPENDENT_REVIEW_OF_READONLY_FINAL_PREDICTION_STORE_CAPTURE")
    print("PRODUCTION_CODE_DEPLOY_ALLOWED=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
