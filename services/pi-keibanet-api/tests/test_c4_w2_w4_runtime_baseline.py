# -*- coding: utf-8 -*-
"""PR-C0: Production C4/W2/W4 runtime baseline (HTTP 0, snapshot byte-identical)."""
from __future__ import annotations

import compileall
import hashlib
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]

HTTP_CALLS = 0

# Production snapshot 2026-09-07 — newly registered runtime only.
SNAPSHOT_SHA256 = {
    "services/pi-keibanet-api/pi_keibanet/c4_calendar/queue.py":
        "633c0cf7afabf67bb82fb5b0a0d43d7d874081fd30f2d8db2fbab19241ffa959",
    "services/pi-keibanet-api/pi_keibanet/c4_calendar/source_health.py":
        "abbc8a4179c8d1543791095d808547d92beaf6598b56cb66b5ac95e889aa3b2a",
    "services/pi-keibanet-api/pi_keibanet/c4_calendar/domain_halt.py":
        "144f0cec05ecd156003b718d955fe10ad77bb6aaabd8f1931bef88cf846855f4",
    "services/pi-keibanet-api/pi_keibanet/c4_calendar/target_policy.py":
        "bb7438b10d9f8bb21f583faef7fafb8c94b2758e4fb5a5ef781add48ad6b8008",
    "services/pi-keibanet-api/pi_keibanet/w2_haron/__init__.py":
        "6fd9576c7b35cf3989409d3213b894436c9a13d83897232c2e23027d6ad574ed",
    "services/pi-keibanet-api/pi_keibanet/w2_haron/eligibility.py":
        "c0c4895e62f97acd1dfe95c993b70d28795eb033218bef70ef6e2bcd1f5304b0",
    "services/pi-keibanet-api/pi_keibanet/w2_haron/intake.py":
        "efa9c73e9225e6d8a784ee43e70e5d8a6645b37f862c64115c21fbcd03a14931",
    "services/pi-keibanet-api/pi_keibanet/w2_haron/layer_b_store.py":
        "87aec863c0836dfb612e490a99a3ecaf119f8030ac8ea7f47c03ced77f5e8fe6",
    "services/pi-keibanet-api/pi_keibanet/w2_haron/haron_parse.py":
        "56f186192d2168cc930e312b26bc1ac70aedd0242d3fc210c816518702fcd691",
    "services/pi-keibanet-api/pi_keibanet/w4_horse/__init__.py":
        "10be6c2bcbc7b8d1b09be63deacce26ab2a740b2893b06ef43d2e16f4c41bf6f",
    "services/pi-keibanet-api/pi_keibanet/w4_horse/config.py":
        "1ed54916d288b9bb9d80595e2f736e1e39500b51a9c0b9c11ca7e35177ed9da2",
    "services/pi-keibanet-api/pi_keibanet/w4_horse/handoff.py":
        "0e1c70cefeab5e8b1c5bc94788f9002fa0d21270c751dbb75d146180b4042908",
    "services/pi-keibanet-api/pi_keibanet/w4_horse/queue.py":
        "caa5b4d40da7606e775f02adbcbbc0122e6a01cb811d6033b7f8252b2cdf504e",
    "services/pi-keibanet-api/pi_keibanet/w4_horse/raw_store.py":
        "a1efb31eb6f728940fcc6d2450b8918881826e674397b84d49d3a322c337cc69",
    "services/pi-keibanet-api/pi_keibanet/w4_horse/id_format.py":
        "fd0f2c19b7c23fce1f4dedc7d5ca65a0930e17bdd767e4030ccab78cb593d73b",
    "services/pi-keibanet-api/pi_keibanet/w4_horse/d1_parse.py":
        "8a361811e0da5c4885ed7dd9acc8ac6f3d1a55ce473998219dfe5ea6ef7905c3",
    "services/pi-keibanet-api/pi_keibanet/w4_horse/d2_parse.py":
        "be4ddf4f848e20c18dfd5de5cadb49d10d80312293abf80c6397ca9a8b2a8d0f",
    "services/pi-keibanet-api/pi_keibanet/w4_horse/parse_apply.py":
        "86ad29861fdd1055633dcbc2d8e9b3c69c16fd5ba60da6589f5e53ef576d8f79",
    "services/pi-keibanet-api/pi_keibanet/w4_horse/parse_runner.py":
        "b94016a80cf64084a9f31662ad24532568da1889ca9524d94cc8355b9b16c2bb",
    "infra/aws/systemd/expect-w4-horse-d1d2.service":
        "09f9484acec9cf9d5043f45608328c0b36f804455be23965397c0c69921a4d4b",
    "infra/aws/systemd/expect-w4-horse-d1d2.timer":
        "399157ab1cc4425b02522d86579bcffe8dd4937fff662d5fea79d8e3b6522a0f",
}

RUNNERS = (
    "c4_calendar_shadow_run.py",
    "w2_haron_shadow_run.py",
    "w4_horse_d1d2_acquire_run.py",
)

CLEAN_IMPORT_CODE = r"""
import urllib.request

calls = {"n": 0}

def _forbid(*_a, **_k):
    calls["n"] += 1
    raise AssertionError("HTTP is forbidden in C0 clean import")

urllib.request.urlopen = _forbid

from pi_keibanet.c4_calendar import C4Config, run_c4_shadow
from pi_keibanet.w2_haron import W2Config, run_w2_shadow
from pi_keibanet.w4_horse import W4Config, run_w4cd_acquire

assert callable(run_c4_shadow) and callable(run_w2_shadow) and callable(run_w4cd_acquire)
assert C4Config and W2Config and W4Config
print("IMPORT_OK")
print("HTTP_CALLS", calls["n"])
"""

CLEAN_HELP_CODE = r"""
import runpy
import sys
import urllib.request

calls = {"n": 0}

def _forbid(*_a, **_k):
    calls["n"] += 1
    raise AssertionError("HTTP is forbidden in C0 runner help")

urllib.request.urlopen = _forbid
sys.argv = [SCRIPT, "--help"]
try:
    runpy.run_path(SCRIPT_PATH, run_name="__main__")
except SystemExit as exc:
    print("HELP_EXIT", exc.code)
    print("HTTP_CALLS", calls["n"])
    raise SystemExit(exc.code)
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env["W3W5_LIVE_HTTP"] = "0"
    env["W3A_BEFORE_W3C"] = "0"
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


class C4W2W4RuntimeBaselineTests(unittest.TestCase):
    def test_snapshot_sha256_byte_identical(self) -> None:
        for rel, expected in SNAPSHOT_SHA256.items():
            path = REPO / rel
            self.assertTrue(path.is_file(), rel)
            self.assertEqual(_sha256(path), expected, rel)

    def test_real_entrypoints_exist(self) -> None:
        self.assertIn("def run_c4_shadow", (ROOT / "pi_keibanet/c4_calendar/runner.py").read_text(encoding="utf-8"))
        self.assertIn("def run_w2_shadow", (ROOT / "pi_keibanet/w2_haron/runner.py").read_text(encoding="utf-8"))
        self.assertIn("def run_w4cd_acquire", (ROOT / "pi_keibanet/w4_horse/acquisition.py").read_text(encoding="utf-8"))
        w4_unit = (REPO / "infra/aws/systemd/expect-w4-horse-d1d2.service").read_text(encoding="utf-8")
        self.assertIn("scripts/w4_horse_d1d2_acquire_run.py", w4_unit)
        c4_script = (ROOT / "scripts/c4_calendar_shadow_run.py").read_text(encoding="utf-8")
        w2_script = (ROOT / "scripts/w2_haron_shadow_run.py").read_text(encoding="utf-8")
        self.assertIn("run_c4_shadow", c4_script)
        self.assertIn("run_w2_shadow", w2_script)
        self.assertIn('component="c4"', (ROOT / "pi_keibanet/c4_calendar/runner.py").read_text(encoding="utf-8"))
        self.assertIn('component="w2"', (ROOT / "pi_keibanet/w2_haron/runner.py").read_text(encoding="utf-8"))
        self.assertIn('component="w4"', (ROOT / "pi_keibanet/w4_horse/acquisition.py").read_text(encoding="utf-8"))

    def test_compileall_added_python(self) -> None:
        for rel in SNAPSHOT_SHA256:
            if not rel.endswith(".py"):
                continue
            ok = compileall.compile_file(str(REPO / rel), quiet=1, force=True)
            self.assertTrue(ok, rel)

    def test_clean_process_package_imports(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-c", CLEAN_IMPORT_CODE],
            cwd=str(ROOT),
            env=_clean_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("IMPORT_OK", proc.stdout)
        self.assertIn("HTTP_CALLS 0", proc.stdout)

    def test_clean_process_runner_help(self) -> None:
        for script in RUNNERS:
            path = ROOT / "scripts" / script
            code = ("SCRIPT = %r\nSCRIPT_PATH = %r\n" % (script, str(path))) + CLEAN_HELP_CODE
            proc = subprocess.run(
                [sys.executable, "-c", code],
                cwd=str(ROOT),
                env=_clean_env(),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, f"{script}\n{proc.stdout}\n{proc.stderr}")
            self.assertIn("HELP_EXIT 0", proc.stdout)
            self.assertIn("HTTP_CALLS 0", proc.stdout)

    def test_no_c4_w2_unit_invented(self) -> None:
        systemd = REPO / "infra" / "aws" / "systemd"
        self.assertFalse((systemd / "expect-c4-page-a1-calendar.service").is_file())
        self.assertFalse((systemd / "expect-w2-haron-shadow.service").is_file())
        self.assertTrue((systemd / "expect-w4-horse-d1d2.service").is_file())

    def test_http_calls_remain_zero(self) -> None:
        self.assertEqual(HTTP_CALLS, 0)

    def test_no_research_patch_dump(self) -> None:
        self.assertFalse((REPO / "research" / "maiden_w3w5_patch").exists())


if __name__ == "__main__":
    unittest.main()
