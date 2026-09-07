# -*- coding: utf-8 -*-
"""PR-A baseline checks that remain valid on the P0 branch (HTTP 0)."""
from __future__ import annotations

import ast
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

# Snapshot-identical files that P0 does not rewrite.
SNAPSHOT_SHA256 = {
    "services/pi-keibanet-api/pi_keibanet/netkeiba/client.py":
        "b7fc3b90588608ba6f47da3a4b095d964d448d9030f326ea0e9495b2ad0a3f91",
    "services/pi-keibanet-api/pi_keibanet/c4_calendar/__init__.py":
        "0d55f913cd6ecc003f537a02d1140b58f8b4d4ea5dacd44f77c3aa5233f81dd2",
    "services/pi-keibanet-api/pi_keibanet/c4_calendar/config.py":
        "a324bca38da42920683e8cb618d6faa09e8a642166eecc5dd345c012a8809d68",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/__init__.py":
        "9e38a569907a655b5c603ac7aa44c422dc8cc4c0b04a689a289ae5e983e0e389",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/acquisition.py":
        "5e18f37373cca74e9670805e47ee8e3227f884c5d219924a9a56817b23320ea2",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/cache_probe.py":
        "4930f8d5ba52fcc3d925837f06c8b7363c16623e339ebb53f0d89a4b041124f4",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/queue.py":
        "9f1eb013a1db20275a7086fd1c68adb68689031439334ada68a617d77255c541",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/result_apply.py":
        "4e7f50feb971a93742de52feb16473362e7fc203ccd0417343e42e7efbe5cb07",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/result_parse.py":
        "0d56a94efbdacf6c662a50b21554b1637596c8611d15df4e3a211cbbfb8fe903",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/result_runner.py":
        "eea29dae63283c79e90da51be1e37967da6c6c16a1f01e17e814f8ebaf18a4df",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/result_store.py":
        "5855f79ae071f984b9131ddaa2c01d4fe07a5de01a0fedbc84be91f6252c655e",
    "services/pi-keibanet-api/pi_keibanet/w5_maiden_history/__init__.py":
        "6021e7aae9d3b4cafffa26813f46c7eb1dc6eb18ef99ee09444f02e99a9d5159",
    "services/pi-keibanet-api/pi_keibanet/w5_maiden_history/gate_monitor.py":
        "adaa9f432c141ef35c444f850322a0cf36f5e5eb9d8f41df0f70c173a1fb1246",
    "services/pi-keibanet-api/pi_keibanet/w5_maiden_history/handoff.py":
        "ea0fe789f34cf0a0f29cb28b4545b115592f6b7c3d05a05392d1c50be9740919",
    "services/pi-keibanet-api/pi_keibanet/w5_maiden_history/hd5_recover.py":
        "afdc340790a0024e015ef8761dbddbf44cb25a602f07697cff81c3575f7b9fde",
    "services/pi-keibanet-api/pi_keibanet/w5_maiden_history/queue.py":
        "1564102b5d2f58adc5c4cbde5f662fade0b04eb0b2e4ed24c0e09792145aef5d",
    "services/pi-keibanet-api/pi_keibanet/w5_maiden_history/store.py":
        "09268767b4d964f20d04491ee2cd953416eca48ae1a07ea687040f74ceddf9dc",
    "services/pi-keibanet-api/pi_keibanet/w2_haron/config.py":
        "4aca0494bdfef6a7f0f00e347de6fb7459040e1d72350fb59803fcb4df724084",
    "services/pi-keibanet-api/pi_keibanet/w2_haron/p1_lock.py":
        "3259dd4a24912e4bce9c38b727afcea692cefd54d45019fb4e6d241d8af18a83",
    "services/pi-keibanet-api/pi_keibanet/w2_haron/source_health.py":
        "46e5848ad52f8d2f66b8ac0323799b76a9ef0ecc4bcb7dd70745a3d15e215666",
    "services/pi-keibanet-api/pi_keibanet/page_a1_store.py":
        "ce4f1747bf01657ee7ea3d8f00d2fd69affe6318160e10dd7fcde22b0f7fe519",
    "services/pi-keibanet-api/pi_keibanet/page_a1_coverage.py":
        "ee53bcd2dfcbdc9478f1a55a14a3c43239f4a67d47e7c9a80f08db249e3ddf96",
    "services/pi-keibanet-api/scripts/w3_maiden_handoff_run.py":
        "df222ea8be38be192f4c51402f6dd59a497071a6fc79770efce27986391f15cd",
    "services/pi-keibanet-api/scripts/w3_maiden_result_parse_run.py":
        "a07f7aeb72d325bb3928d134ec906038506650a16515792fe3933adb1d526daa",
    "services/pi-keibanet-api/scripts/w5_maiden_history_handoff_run.py":
        "97b6708c78345ef09aa663e53cc6961ac51635b3c6a71e2782532b5077cd7444",
    "infra/aws/systemd/expect-w3c-page-c-maiden.service":
        "0757fb3c775cd23b2fe8237be75c1c2b34dbfbb0bcb97c17ef49b2c491a5949b",
    "infra/aws/systemd/expect-w3c-page-c-maiden.timer":
        "9989de522cf771c5641b40e1c480fc716e593f20cb257b3f9aca6b605bf3fcc9",
    "infra/aws/systemd/expect-w5-maiden-history.service":
        "eb42cc19b7da39d20b5bde60854aac24bdb90e1a5de95a35f0b7b7ae8abb7420",
    "infra/aws/systemd/expect-w5-maiden-history.timer":
        "a7bb39bbb1f23427c7fed8e474c1d621dce783583f3b5ecabb9416144902ddda",
}

RUNNERS = (
    "w3_maiden_page_c_acquire_run.py",
    "w3_maiden_handoff_run.py",
    "w3_maiden_result_parse_run.py",
    "w5_maiden_history_acquire_run.py",
    "w5_maiden_history_handoff_run.py",
)

MAIN_EXISTING_TESTS = (
    "tests.test_pi_api",
    "tests.test_web_races_api",
    "tests.test_pipeline",
    "tests.test_race_refresh",
    "tests.test_history_store_v74",
    "tests.test_horse_number_integrity",
    "tests.test_features_win5_leg",
    "tests.test_compare",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "pi_keibanet.c4_calendar.runner",
    "pi_keibanet.c4_calendar.queue",
    "pi_keibanet.c4_calendar.source_health",
    "pi_keibanet.c4_calendar.domain_halt",
    "pi_keibanet.c4_calendar.target_policy",
    "pi_keibanet.w2_haron.runner",
    "pi_keibanet.w2_haron.eligibility",
    "pi_keibanet.w2_haron.intake",
    "pi_keibanet.w2_haron.layer_b_store",
    "pi_keibanet.w2_haron.haron_parse",
    "pi_keibanet.w4_horse",
)

CLEAN_IMPORT_CODE = r"""
import urllib.request

calls = {"n": 0}

def _forbid(*_a, **_k):
    calls["n"] += 1
    raise AssertionError("HTTP is forbidden in clean import process")

urllib.request.urlopen = _forbid

import pi_keibanet.page_a1_store
import pi_keibanet.w3_maiden
import pi_keibanet.w5_maiden_history
import pi_keibanet.c4_calendar.config
from pi_keibanet.netkeiba.client import RaceListFetchResult, NetkeibaFetchError

assert RaceListFetchResult is pi_keibanet.page_a1_store.RaceListFetchResult
err = NetkeibaFetchError("compat")
assert err.http_status is None
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
    raise AssertionError("HTTP is forbidden in clean runner process")

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


def _iter_added_py() -> list[Path]:
    return [REPO / rel for rel in SNAPSHOT_SHA256 if rel.endswith(".py")]


def _module_from_rel(rel: str) -> str | None:
    if not rel.endswith(".py"):
        return None
    if "/scripts/" in rel or rel.startswith("infra/"):
        return None
    if "/pi_keibanet/" not in rel:
        return None
    body = rel.split("/pi_keibanet/", 1)[1]
    if body.endswith("/__init__.py"):
        body = body[: -len("/__init__.py")]
    else:
        body = body[: -len(".py")]
    return "pi_keibanet." + body.replace("/", ".")


def _resolve_from(path: Path, node: ast.ImportFrom) -> str | None:
    if node.module and node.module.startswith("pi_keibanet"):
        return node.module
    package = _module_from_rel(str(path.relative_to(REPO)).replace(os.sep, "/"))
    if not (node.level and package):
        return None
    parts = package.split(".")
    if path.name != "__init__.py":
        parts = parts[:-1]
    up = node.level - 1
    if up:
        parts = parts[:-up] if up < len(parts) else []
    base = ".".join(parts)
    name = node.module or ""
    resolved = f"{base}.{name}" if name else base
    return resolved.rstrip(".") or None


def _top_level_local_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("pi_keibanet"):
                    found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_from(path, node)
            if resolved and resolved.startswith("pi_keibanet"):
                found.add(resolved)
    return found


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env["W3W5_LIVE_HTTP"] = "0"
    env["W3A_BEFORE_W3C"] = "0"
    env["W3A_HANDOFF_DRY_RUN"] = "1"
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def _clean_process(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT),
        env=_clean_env(),
        capture_output=True,
        text=True,
        check=False,
    )


class MaidenRuntimeBaselineTests(unittest.TestCase):
    def test_snapshot_sha256_byte_identical(self) -> None:
        for rel, expected in SNAPSHOT_SHA256.items():
            path = REPO / rel
            self.assertTrue(path.is_file(), rel)
            self.assertEqual(_sha256(path), expected, rel)

    def test_client_py_is_snapshot_original(self) -> None:
        path = ROOT / "pi_keibanet" / "netkeiba" / "client.py"
        self.assertEqual(
            _sha256(path),
            "b7fc3b90588608ba6f47da3a4b095d964d448d9030f326ea0e9495b2ad0a3f91",
        )
        text = path.read_text(encoding="utf-8")
        self.assertIn("class RaceListFetchResult", text)
        self.assertIn("def fetch_race_list_result", text)

    def test_compileall_added_python(self) -> None:
        for path in _iter_added_py():
            ok = compileall.compile_file(str(path), quiet=1, force=True)
            self.assertTrue(ok, path)

    def test_static_import_closure_resolves(self) -> None:
        added_modules = {
            _module_from_rel(rel)
            for rel in SNAPSHOT_SHA256
            if _module_from_rel(rel)
        }
        added_modules.discard(None)
        existing_ok = {
            "pi_keibanet",
            "pi_keibanet.service",
            "pi_keibanet.venues",
            "pi_keibanet.netkeiba",
            "pi_keibanet.netkeiba.client",
            "pi_keibanet.netkeiba.horse_history",
            "pi_keibanet.netkeiba.parse",
            "pi_keibanet.w2_haron",
            "pi_keibanet.c4_calendar",
            "pi_keibanet.c4_calendar.config",
            "pi_keibanet.w3_maiden",
            "pi_keibanet.w3_maiden.config",
            "pi_keibanet.w3_maiden.handoff",
            "pi_keibanet.w5_maiden_history",
            "pi_keibanet.w5_maiden_history.config",
            "pi_keibanet.w5_maiden_history.acquisition",
        }
        closure: set[str] = set()
        for path in _iter_added_py():
            closure |= _top_level_local_imports(path)
        for name in sorted(closure):
            for banned in FORBIDDEN_IMPORT_PREFIXES:
                self.assertFalse(name.startswith(banned), name)
            if name in added_modules or name in existing_ok:
                continue
            parent = name.rsplit(".", 1)[0]
            self.assertTrue(
                name in added_modules or parent in added_modules or parent in existing_ok,
                f"unresolved import {name}",
            )

    def test_clean_process_package_imports(self) -> None:
        proc = _clean_process(CLEAN_IMPORT_CODE)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("IMPORT_OK", proc.stdout)
        self.assertIn("HTTP_CALLS 0", proc.stdout)

    def test_clean_process_runner_help(self) -> None:
        for script in RUNNERS:
            path = ROOT / "scripts" / script
            code = (
                "SCRIPT = %r\nSCRIPT_PATH = %r\n" % (script, str(path))
            ) + CLEAN_HELP_CODE
            proc = _clean_process(code)
            self.assertEqual(proc.returncode, 0, f"{script}\n{proc.stdout}\n{proc.stderr}")
            self.assertIn("HELP_EXIT 0", proc.stdout)
            self.assertIn("HTTP_CALLS 0", proc.stdout)

    def test_main_existing_tests_clean_process(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", *MAIN_EXISTING_TESTS, "-q"],
            cwd=str(ROOT),
            env=_clean_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_http_calls_remain_zero(self) -> None:
        self.assertEqual(HTTP_CALLS, 0)

    def test_no_research_or_full_snapshot_dump(self) -> None:
        self.assertFalse((REPO / "research" / "maiden_w3w5_patch").exists())
        self.assertFalse((ROOT / "pi_keibanet" / "w4_horse" / "__init__.py").is_file())
        self.assertTrue((ROOT / "pi_keibanet" / "c4_calendar" / "config.py").is_file())
        self.assertFalse((ROOT / "pi_keibanet" / "c4_calendar" / "runner.py").is_file())
        self.assertFalse((ROOT / "pi_keibanet" / "w2_haron" / "runner.py").is_file())


if __name__ == "__main__":
    unittest.main()
