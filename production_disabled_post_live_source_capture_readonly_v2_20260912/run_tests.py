#!/usr/bin/env python3
"""Self-tests for the read-only live-source capture pack. No Production ops."""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parent


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
    import generate_hashes

    generate_hashes.main()
    build_owner_script.main()
    loader = unittest.defaultTestLoader
    suite = loader.discover(str(PACK / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        print("SELF_TEST=FAIL")
        return 1
    write_sha256sums()
    print("SELF_TEST=PASS")
    print("CANONICAL_PRESENTED_IDENTICAL=YES")
    print("NEXT_STEP=INDEPENDENT_REVIEW_OF_READONLY_LIVE_SOURCE_CAPTURE_V2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
