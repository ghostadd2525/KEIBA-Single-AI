# -*- coding: utf-8 -*-
"""PR-A: Production W3/W5 runtime baseline (snapshot byte-identical, HTTP 0)."""
from __future__ import annotations

import ast
import compileall
import hashlib
import importlib
import os
import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HTTP_CALLS = 0

# Content SHA256 of 2026-09-07 Production snapshot originals.
SNAPSHOT_SHA256 = {
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/__init__.py":
        "9e38a569907a655b5c603ac7aa44c422dc8cc4c0b04a689a289ae5e983e0e389",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/acquisition.py":
        "5e18f37373cca74e9670805e47ee8e3227f884c5d219924a9a56817b23320ea2",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/cache_probe.py":
        "4930f8d5ba52fcc3d925837f06c8b7363c16623e339ebb53f0d89a4b041124f4",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/config.py":
        "cac5fd1df67fcf8cc1183ee92224a9cf0b12ba228cff2ba38f6916d2022d8239",
    "services/pi-keibanet-api/pi_keibanet/w3_maiden/handoff.py":
        "21e52fea90887c1b8f7e8af638d5fe9ef950f40d0293313b7f3687c2eb12f140",
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
    "services/pi-keibanet-api/pi_keibanet/w5_maiden_history/acquisition.py":
        "3131731d914f5a9860935e4554486e1831682a8c1d19fda203d4835de683b7ca",
    "services/pi-keibanet-api/pi_keibanet/w5_maiden_history/config.py":
        "7a32910c52003a1e9bd45ae27a1db6af0adb353c0272be2c36383f0d2a7300be",
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
    "services/pi-keibanet-api/scripts/w3_maiden_page_c_acquire_run.py":
        "3793f24554a57c9128d91ebae458dc9b42ecb4d747a4c3010432d5c8a3d8fc86",
    "services/pi-keibanet-api/scripts/w3_maiden_handoff_run.py":
        "df222ea8be38be192f4c51402f6dd59a497071a6fc79770efce27986391f15cd",
    "services/pi-keibanet-api/scripts/w3_maiden_result_parse_run.py":
        "a07f7aeb72d325bb3928d134ec906038506650a16515792fe3933adb1d526daa",
    "services/pi-keibanet-api/scripts/w5_maiden_history_acquire_run.py":
        "4904a9b3163ebdada390fafda6035f09f73ca85a954c411743cbdee06765413a",
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

MAIN_CLIENT_SHA256 = "e6586b06cee2982e1888c612094c58d82157d7e60b54d04d7fe1361403ac6c47"

RUNNERS = (
    "w3_maiden_page_c_acquire_run.py",
    "w3_maiden_handoff_run.py",
    "w3_maiden_result_parse_run.py",
    "w5_maiden_history_acquire_run.py",
    "w5_maiden_history_handoff_run.py",
)

PACKAGE_MODULES = (
    "pi_keibanet.w3_maiden",
    "pi_keibanet.w3_maiden.config",
    "pi_keibanet.w3_maiden.handoff",
    "pi_keibanet.w3_maiden.queue",
    "pi_keibanet.w3_maiden.cache_probe",
    "pi_keibanet.w3_maiden.acquisition",
    "pi_keibanet.w3_maiden.result_apply",
    "pi_keibanet.w3_maiden.result_parse",
    "pi_keibanet.w3_maiden.result_runner",
    "pi_keibanet.w3_maiden.result_store",
    "pi_keibanet.w5_maiden_history",
    "pi_keibanet.w5_maiden_history.config",
    "pi_keibanet.w5_maiden_history.acquisition",
    "pi_keibanet.w5_maiden_history.handoff",
    "pi_keibanet.w5_maiden_history.queue",
    "pi_keibanet.w5_maiden_history.store",
    "pi_keibanet.w5_maiden_history.gate_monitor",
    "pi_keibanet.w5_maiden_history.hd5_recover",
    "pi_keibanet.w2_haron.config",
    "pi_keibanet.w2_haron.p1_lock",
    "pi_keibanet.w2_haron.source_health",
    "pi_keibanet.page_a1_coverage",
    "pi_keibanet.page_a1_store",
)

# Snapshot W3/W5 static import closure. c4_calendar is not imported by Production W3-A.
FORBIDDEN_IMPORT_PREFIXES = (
    "pi_keibanet.c4_calendar",
    "pi_keibanet.w2_haron.runner",
    "pi_keibanet.w2_haron.eligibility",
    "pi_keibanet.w2_haron.intake",
    "pi_keibanet.w2_haron.layer_b_store",
    "pi_keibanet.w2_haron.haron_parse",
    "pi_keibanet.w4_horse",
)


def _forbid_http(*_a, **_k):
    global HTTP_CALLS
    HTTP_CALLS += 1
    raise AssertionError("HTTP is forbidden in baseline tests")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ensure_race_list_fetch_result() -> bool:
    """main client.py has no RaceListFetchResult; page_a1_store imports it.

    PR-A does not change client.py. Inject the Production dataclass shape so
    W3/W5 package imports can be proven against main's existing client.
    """
    from pi_keibanet.netkeiba import client

    if hasattr(client, "RaceListFetchResult"):
        return False

    @dataclass
    class RaceListFetchResult:
        merged_html: str
        parts: list = field(default_factory=list)
        kaisai_date: str = ""

    client.RaceListFetchResult = RaceListFetchResult
    return True


def _iter_added_py() -> list[Path]:
    out: list[Path] = []
    for rel in SNAPSHOT_SHA256:
        path = REPO / rel
        if path.suffix == ".py":
            out.append(path)
    return out


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
    """Module-level imports only. Nested try/except imports (e.g. optional W4) are not required."""
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


class MaidenRuntimeBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["W3W5_LIVE_HTTP"] = "0"
        os.environ["W3A_BEFORE_W3C"] = "0"
        os.environ.setdefault("W3A_HANDOFF_DRY_RUN", "1")
        cls._urlopen_patch = patch("urllib.request.urlopen", side_effect=_forbid_http)
        cls._urlopen_patch.start()
        _ensure_race_list_fetch_result()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._urlopen_patch.stop()

    def test_snapshot_sha256_byte_identical(self) -> None:
        for rel, expected in SNAPSHOT_SHA256.items():
            path = REPO / rel
            self.assertTrue(path.is_file(), rel)
            self.assertEqual(_sha256(path), expected, rel)

    def test_client_py_unchanged_from_main(self) -> None:
        path = ROOT / "pi_keibanet" / "netkeiba" / "client.py"
        self.assertEqual(_sha256(path), MAIN_CLIENT_SHA256)
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("class RaceListFetchResult", text)

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

    def test_real_package_imports(self) -> None:
        for name in PACKAGE_MODULES:
            importlib.import_module(name)

    def test_runner_help_no_http(self) -> None:
        import importlib.util

        before = HTTP_CALLS
        for script in RUNNERS:
            path = ROOT / "scripts" / script
            spec = importlib.util.spec_from_file_location(script.replace(".py", ""), path)
            assert spec and spec.loader
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            with patch.object(sys, "argv", [script, "--help"]):
                with self.assertRaises(SystemExit) as cm:
                    mod.main()
                self.assertEqual(cm.exception.code, 0, script)
        self.assertEqual(HTTP_CALLS, before)

    def test_http_calls_remain_zero(self) -> None:
        self.assertEqual(HTTP_CALLS, 0)

    def test_no_research_or_full_snapshot_dump(self) -> None:
        self.assertFalse((REPO / "research" / "maiden_w3w5_patch").exists())
        self.assertFalse((ROOT / "pi_keibanet" / "w4_horse").exists() or
                         (ROOT / "pi_keibanet" / "w4_horse" / "__init__.py").is_file())
        self.assertFalse((ROOT / "pi_keibanet" / "c4_calendar" / "config.py").is_file())
        self.assertFalse((ROOT / "pi_keibanet" / "w2_haron" / "runner.py").is_file())


if __name__ == "__main__":
    unittest.main()
