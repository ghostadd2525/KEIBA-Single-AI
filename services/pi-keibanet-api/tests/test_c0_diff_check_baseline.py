# -*- coding: utf-8 -*-
"""PR-C0: do not hide snapshot whitespace. Byte-identical baseline stays honest."""
from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]

# Snapshot original: d1_parse.py L120 has a trailing space in a comment.
# Keep the bytes. Do not suppress git diff --check via .gitattributes.
KNOWN_BASELINE_TRAILING_WHITESPACE = (
    (
        "services/pi-keibanet-api/pi_keibanet/w4_horse/d1_parse.py",
        120,
        '        # "小栗実 (栗東)" ',
    ),
)
KNOWN_BASELINE_CRLF = "services/pi-keibanet-api/pi_keibanet/w2_haron/runner.py"


def _main_tip() -> str:
    for ref in ("origin/main", "main"):
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    raise AssertionError("main ref not found")


class C0DiffCheckBaselineTests(unittest.TestCase):
    def test_gitattributes_does_not_suppress_whitespace(self) -> None:
        text = (REPO / ".gitattributes").read_text(encoding="utf-8")
        attr_lines = [
            line
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        joined = "\n".join(attr_lines)
        self.assertNotIn("whitespace=-trailing-space", joined)
        self.assertNotIn("whitespace=-cr-at-eol", joined)
        self.assertIn(
            "services/pi-keibanet-api/pi_keibanet/w2_haron/runner.py -text",
            text,
        )

    def test_snapshot_trailing_whitespace_is_documented(self) -> None:
        for rel, line_no, expected in KNOWN_BASELINE_TRAILING_WHITESPACE:
            lines = (REPO / rel).read_text(encoding="utf-8").splitlines()
            self.assertGreaterEqual(len(lines), line_no, rel)
            self.assertEqual(lines[line_no - 1], expected.rstrip("\n"))
            self.assertTrue(lines[line_no - 1].endswith(" "))

    def test_diff_check_known_baseline_exception(self) -> None:
        env = os.environ.copy()
        proc = subprocess.run(
            ["git", "diff", "--check", f"{_main_tip()}...HEAD"],
            cwd=str(REPO),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        combined = proc.stdout + proc.stderr
        self.assertNotEqual(
            proc.returncode,
            0,
            "snapshot whitespace must stay visible (DIFF_CHECK=KNOWN_BASELINE_EXCEPTION)",
        )
        self.assertIn("d1_parse.py:120: trailing whitespace", combined)
        unexpected = []
        for line in combined.splitlines():
            if "trailing whitespace" not in line and "cr-at-eol" not in line:
                continue
            if "d1_parse.py:120:" in line:
                continue
            if KNOWN_BASELINE_CRLF in line:
                continue
            unexpected.append(line)
        self.assertEqual(unexpected, [], unexpected)
        self.assertTrue((REPO / KNOWN_BASELINE_CRLF).read_bytes().count(b"\r\n") > 0)
        self.assertEqual(os.environ.get("W3W5_LIVE_HTTP", "0"), "0")


if __name__ == "__main__":
    unittest.main()
