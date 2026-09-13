#!/usr/bin/env python3
from __future__ import annotations

import ast
import difflib
import hashlib
import os
import re
import sys
import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
if str(PACK) not in sys.path:
    sys.path.insert(0, str(PACK))

import apply_live_post_hunk as hunk  # noqa: E402

HEX64 = re.compile(r"^[0-9a-f]{64}$")

LIVE_MAIN_SHA = "7486a9ad7578e9ccdf883eaaac85f0b0de7ba329e286302b8d2f57db81d79235"
LIVE_REPO_SHA = "557713a95b0e9f5a8f798eeb5e525c85adab3063b2e6529ee0be2155bb29992b"
LIVE_BRIDGE_SHA = "e06e6ee971e2ae8d07bbcee4501ab9024052de52dd119ea007cb71481ae5272e"
HUNKED_MAIN_SHA = "a4970e70778da58f987df4a7316c9dfbd0a660c7a3bc31088d731869a4983a9c"
ORIGIN_MAIN_SHA = "a54f1eaa5b8540c2f08d8b0e656a3ccbb78142d4d1cb2c8951e4105f3630184e"
ORIGIN_DB_SHA = "8a86f514b1b08fde9a90a71acc99eac3f6fc9c2aeae200e8787721093592ef1a"
V6_MAIN_SHA = "7577973c16eb7aad395cd11acae3c8ef987a3c0533924c1994ae32afeaf818e5"
CAPTURE_ZIP_SHA = "f460685bcb59d837cca2f9b2c9154f51bf1d354f062ad6c26810bd86f2103a4a"
V6_ZIP_SHA = "548b274facc2b4f8ffba8b854a6e009d8b7455fb816dcde9550eb9b364329373"
OWNER_CAPTURE_ZIP = "live_source_capture_v3_windows_20260913.zip"

V6_CANDIDATE_SHA = {
    "services/win5-ai/app/data/db.py": "81fc91adbe53aa091841fd9ea097b7cbd63cf4ede4a3699bf66e1c7a2343136f",
    "services/win5-ai/app/data/repository/__init__.py": "9624699ec48d2af8b1fdc24ac81b8ae436c77ffa92a7f0b1378ecd17248b4c08",
    "services/win5-ai/app/core/feature_loader_bridge.py": "f3c25c7b87941138555158e051d0520fc705889e8a2a17e8889c7fc5325eae44",
    "services/win5-ai/app/data/migrations/022_prediction_run_idempotency.sql": "627910c7985276d516fbbbcc09ca15964081955452eae28ae8a773c38acf28a9",
    "services/win5-ai/app/predictions/__init__.py": "d4373c31ad5aac82a2d83a53d91bc2b95607bd891d7b9286c3c154478d5dc21c",
    "services/win5-ai/app/predictions/guards.py": "7e6d74dd77b6645364679187a325b42676cd64d6546f5576022f19d30e6dfc82",
    "services/win5-ai/app/predictions/runs.py": "d04bc99281474aa4e0e78b9951df6335f6b9995c9e7328b100afd552815f35c1",
    "services/win5-ai/app/predictions/feature_pin.py": "49794f3671589a5ec13bc622161bac8c10609ff922c51033343dca30a31fbc36",
    "services/win5-ai/app/predictions/provenance.py": "2cc2585d53a3dbdffd8c7a4dc56921aafaf4ce6cd5421d1928950a34194bb704",
    "services/win5-ai/app/predictions/snapshot.py": "2114c953b57461f73d0450384f38df2a2b086a51e53591c77cc70b448cbde5f7",
}

DEPLOY_RELS = [
    "services/win5-ai/app/main.py",
    *V6_CANDIDATE_SHA.keys(),
]

MUST_ABSENT = (
    "services/win5-ai/app/predictions/corpus.py",
    "services/win5-ai/app/predictions/raeval84_holdout.py",
    "services/win5-ai/app/predictions/data/raeval84_v1_holdout_race_ids.txt",
    "services/win5-ai/app/data/migrations_not_apply/019_prediction_run_idempotency.sql",
    "services/win5-ai/app/data/migrations/019_prediction_run_idempotency.sql",
)

FORBIDDEN_NAMES = (
    "OWNER_APPLY",
    "OWNER_DEPLOY",
    "ssh",
    "systemctl",
    "scp",
)

IMMUTABLE_ZIPS = (
    "production_disabled_post_code_deploy_review_20260912.zip",
    "production_disabled_post_code_deploy_review_v2_20260912.zip",
    "production_disabled_post_code_deploy_review_v3_20260912.zip",
    "production_disabled_post_code_deploy_review_v4_20260912.zip",
    "production_disabled_post_code_deploy_review_v5_20260912.zip",
    "production_disabled_post_code_deploy_review_v6_20260912.zip",
    "production_disabled_post_live_compare_readonly_v5_20260912.zip",
    "production_disabled_post_live_source_capture_readonly_20260912.zip",
    "production_disabled_post_live_source_capture_readonly_v2_20260912.zip",
    OWNER_CAPTURE_ZIP,
    "production_disabled_post_hunk_only_deploy_review_20260913.zip",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_flags(path: Path) -> dict[str, str]:
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


def class_named(tree: ast.AST, name: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError("class_missing:%s" % name)


def method_named(cls: ast.ClassDef, name: str) -> ast.FunctionDef:
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("method_missing:%s" % name)


def first_runs_import_index(fn: ast.FunctionDef) -> int | None:
    for i, stmt in enumerate(fn.body):
        if isinstance(stmt, ast.ImportFrom) and stmt.module == "predictions.runs":
            return i
        if isinstance(stmt, ast.ImportFrom) and (stmt.module or "").endswith("predictions.runs"):
            return i
    return None


def gate_index(fn: ast.FunctionDef) -> int | None:
    for i, stmt in enumerate(fn.body):
        src = ast.dump(stmt)
        if "PREDICTION_RUNS_ENABLED" in src:
            return i
    return None


class HunkOnlyReviewTests(unittest.TestCase):
    def test_live_canon_three_files_match_owner_capture(self) -> None:
        files = {
            PACK / "live_canon/app/main.py": (45983, LIVE_MAIN_SHA),
            PACK / "live_canon/app/data/repository/__init__.py": (12823, LIVE_REPO_SHA),
            PACK / "live_canon/app/core/feature_loader_bridge.py": (1408, LIVE_BRIDGE_SHA),
        }
        for path, (size, digest) in files.items():
            self.assertTrue(path.is_file(), path)
            self.assertEqual(path.stat().st_size, size, path)
            self.assertEqual(sha256_file(path), digest, path)

    def test_origin_refs_match_known_shas(self) -> None:
        self.assertEqual(sha256_file(PACK / "reference/origin_main_25a3f88/app/main.py"), ORIGIN_MAIN_SHA)
        self.assertEqual(sha256_file(PACK / "reference/origin_main_25a3f88/app/data/repository/__init__.py"), LIVE_REPO_SHA)
        self.assertEqual(sha256_file(PACK / "reference/origin_main_25a3f88/app/core/feature_loader_bridge.py"), LIVE_BRIDGE_SHA)
        self.assertEqual(sha256_file(PACK / "reference/origin_main_25a3f88/app/data/db.py"), ORIGIN_DB_SHA)

    def test_review_v6_main_is_reference_only(self) -> None:
        v6 = PACK / "reference/review_v6/app/main.py"
        self.assertEqual(sha256_file(v6), V6_MAIN_SHA)
        cand = PACK / "candidates/services/win5-ai/app/main.py"
        self.assertNotEqual(sha256_file(cand), V6_MAIN_SHA)
        self.assertNotEqual(sha256_file(cand), ORIGIN_MAIN_SHA)
        self.assertNotEqual(sha256_file(cand), LIVE_MAIN_SHA)

    def test_apply_hunk_reproduces_candidate_main(self) -> None:
        live = (PACK / "live_canon/app/main.py").read_text(encoding="utf-8")
        out = hunk.apply_hunks(live).encode("utf-8")
        self.assertEqual(len(out), 48345)
        self.assertEqual(hashlib.sha256(out).hexdigest(), HUNKED_MAIN_SHA)
        cand = (PACK / "candidates/services/win5-ai/app/main.py").read_bytes()
        self.assertEqual(out, cand)

    def test_hunk_tool_rejects_wrong_live_sha(self) -> None:
        rc = hunk.main(["--src", str(PACK / "reference/origin_main_25a3f88/app/main.py")])
        self.assertEqual(rc, 2)

    def test_diff_is_exactly_two_insertions(self) -> None:
        live = (PACK / "live_canon/app/main.py").read_text(encoding="utf-8").splitlines(True)
        cand = (PACK / "candidates/services/win5-ai/app/main.py").read_text(encoding="utf-8").splitlines(True)
        ops = [
            (tag, i1, i2, j1, j2)
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=live, b=cand).get_opcodes()
            if tag != "equal"
        ]
        self.assertEqual([tag for tag, *_ in ops], ["insert", "insert"])
        first = "".join(cand[ops[0][3] : ops[0][4]])
        second = "".join(cand[ops[1][3] : ops[1][4]])
        self.assertIn("    def _handle_prediction_runs_post(self) -> None:\n", first)
        self.assertIn("from .predictions.runs import handle_post_prediction_run", first)
        self.assertEqual(second, hunk.INSERTION_2)
        restored = list(cand)
        for _tag, _i1, _i2, j1, j2 in reversed(ops):
            del restored[j1:j2]
        self.assertEqual(restored, live)

    def test_hunk_doc_contains_both_insertions(self) -> None:
        doc = (PACK / "01_docs/main_py_post_route_hunk.txt").read_text(encoding="utf-8")
        self.assertIn("def _handle_prediction_runs_post(self) -> None:", doc)
        self.assertIn('if path == "/v1/prediction-runs":', doc)
        self.assertIn("self._handle_prediction_runs_post()", doc)
        self.assertIn("Disabled check must run before importing the POST implementation", doc)

    def test_production_markers_remain(self) -> None:
        text = (PACK / "candidates/services/win5-ai/app/main.py").read_text(encoding="utf-8")
        live = (PACK / "live_canon/app/main.py").read_text(encoding="utf-8")
        for marker in ("WIN5 AI — PredictionBundle", "Optional integration facades"):
            self.assertIn(marker, live)
            self.assertIn(marker, text)
            self.assertEqual(live.count(marker), text.count(marker))
        v6 = (PACK / "reference/review_v6/app/main.py").read_text(encoding="utf-8")
        self.assertNotIn("Optional integration facades", v6)
        self.assertIn("ChallengeLifecycle", live)
        self.assertIn("ChallengeLifecycle", text)
        self.assertNotIn("ChallengeLifecycle", v6)

    def test_candidate_main_compiles(self) -> None:
        src = (PACK / "candidates/services/win5-ai/app/main.py").read_text(encoding="utf-8")
        compile(src, "main.py", "exec")
        ast.parse(src)

    def test_gate_before_runs_import(self) -> None:
        src = (PACK / "candidates/services/win5-ai/app/main.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        handler = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                try:
                    handler = method_named(node, "_handle_prediction_runs_post")
                    break
                except AssertionError:
                    continue
        self.assertIsNotNone(handler)
        g = gate_index(handler)
        r = first_runs_import_index(handler)
        self.assertIsNotNone(g)
        self.assertIsNotNone(r)
        self.assertLess(g, r)

    def test_do_post_branch_before_check_key(self) -> None:
        src = (PACK / "candidates/services/win5-ai/app/main.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        fn = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                try:
                    fn = method_named(node, "do_POST")
                    break
                except AssertionError:
                    continue
        self.assertIsNotNone(fn)
        dumped = [ast.dump(stmt) for stmt in fn.body]
        branch_i = next(i for i, d in enumerate(dumped) if "prediction-runs" in d)
        check_i = next(i for i, d in enumerate(dumped) if "_check_key" in d)
        self.assertLess(branch_i, check_i)

    def test_do_patch_unchanged(self) -> None:
        live = (PACK / "live_canon/app/main.py").read_text(encoding="utf-8")
        cand = (PACK / "candidates/services/win5-ai/app/main.py").read_text(encoding="utf-8")
        live_tree = ast.parse(live)
        cand_tree = ast.parse(cand)

        def patch_src(tree: ast.Module, text: str) -> str:
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    try:
                        fn = method_named(node, "do_PATCH")
                    except AssertionError:
                        continue
                    return ast.get_source_segment(text, fn) or ""
            raise AssertionError("do_PATCH missing")

        self.assertEqual(patch_src(live_tree, live), patch_src(cand_tree, cand))
        self.assertNotIn("prediction-runs", patch_src(cand_tree, cand))

    def test_disabled_handler_returns_503_without_runs_import(self) -> None:
        src = (PACK / "candidates/services/win5-ai/app/main.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        fn = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                try:
                    fn = method_named(node, "_handle_prediction_runs_post")
                    break
                except AssertionError:
                    continue
        self.assertIsNotNone(fn)
        method_src = ast.get_source_segment(src, fn)
        self.assertIsNotNone(method_src)
        imported = {"runs": 0, "guards": 0}

        class Boom(Exception):
            pass

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
            if name.endswith("predictions.runs") or name == "predictions.runs":
                imported["runs"] += 1
                raise Boom("runs imported while disabled")
            if name.endswith("predictions.guards") or name == "predictions.guards":
                imported["guards"] += 1
                raise Boom("guards imported while disabled")
            return __import__(name, globals, locals, fromlist, level)

        def err(code: str, message: str, status: int):
            return status, {"error": code, "message": message}

        class Handler:
            def __init__(self) -> None:
                self.sent = None

            def _send(self, *args):
                self.sent = args

        ns = {
            "os": os,
            "json": __import__("json"),
            "err": err,
            "__import__": fake_import,
        }
        exec("import builtins\n", ns)
        # Bind method onto Handler by exec of the def, then replace imports.
        exec(method_src, ns)
        handler = Handler()
        handler._handle_prediction_runs_post = ns["_handle_prediction_runs_post"].__get__(handler, Handler)
        old = os.environ.get("PREDICTION_RUNS_ENABLED")
        os.environ["PREDICTION_RUNS_ENABLED"] = "0"
        try:
            handler._handle_prediction_runs_post()
        finally:
            if old is None:
                os.environ.pop("PREDICTION_RUNS_ENABLED", None)
            else:
                os.environ["PREDICTION_RUNS_ENABLED"] = old
        self.assertEqual(handler.sent[0], 503)
        self.assertEqual(handler.sent[1]["error"], "PREDICTION_RUNS_DISABLED")
        self.assertEqual(imported["runs"], 0)
        self.assertEqual(imported["guards"], 0)

    def test_non_main_candidates_match_review_v6(self) -> None:
        for rel, digest in V6_CANDIDATE_SHA.items():
            path = PACK / "candidates" / rel
            self.assertTrue(path.is_file(), rel)
            self.assertEqual(sha256_file(path), digest, rel)
            listed = parse_sums(PACK / "candidates/file_sha256.txt")
            self.assertEqual(listed[rel], digest, rel)

    def test_candidate_main_listed_sha(self) -> None:
        listed = parse_sums(PACK / "candidates/file_sha256.txt")
        self.assertEqual(listed["services/win5-ai/app/main.py"], HUNKED_MAIN_SHA)
        self.assertEqual(
            sha256_file(PACK / "candidates/services/win5-ai/app/main.py"),
            HUNKED_MAIN_SHA,
        )

    def test_must_absent_not_in_candidates(self) -> None:
        for rel in MUST_ABSENT:
            self.assertFalse((PACK / "candidates" / rel).exists(), rel)
        deploy = (PACK / "01_docs/deploy_files.txt").read_text(encoding="utf-8")
        excluded = deploy.split("Excluded from Production deploy", 1)[1]
        self.assertIn("corpus.py", excluded)
        self.assertIn("raeval84_holdout.py", excluded)
        before = deploy.split("Excluded from Production deploy", 1)[0]
        self.assertNotIn("corpus.py", before)
        self.assertNotIn("raeval84_holdout.py", before)

    def test_preconditions_cover_every_deploy_target(self) -> None:
        pre = (PACK / "01_docs/preconditions.txt").read_text(encoding="utf-8")
        self.assertIn(LIVE_MAIN_SHA, pre)
        self.assertIn(LIVE_REPO_SHA, pre)
        self.assertIn(LIVE_BRIDGE_SHA, pre)
        self.assertIn(ORIGIN_DB_SHA, pre)
        for rel in (
            "app/main.py",
            "app/data/repository/__init__.py",
            "app/core/feature_loader_bridge.py",
            "app/data/db.py",
            "app/data/migrations/022_prediction_run_idempotency.sql",
            "app/predictions/__init__.py",
            "app/predictions/guards.py",
            "app/predictions/runs.py",
            "app/predictions/feature_pin.py",
            "app/predictions/provenance.py",
            "app/predictions/snapshot.py",
        ):
            self.assertIn(rel, pre, rel)
        self.assertIn("PRECONDITION=ABSENT", pre)
        self.assertIn("IF_PRESENT=STOP", pre)
        self.assertIn("022_REAPPLY=NO", pre)
        self.assertGreaterEqual(pre.count("PRECONDITION=ABSENT"), 7)
        self.assertIn("c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e", pre)
        self.assertIn("40352ff56b3267533267d5de9c893f3bda8963d5fe121474f7785b0152594a12", pre)
        self.assertIn("app/ops/prediction_capacity.py", pre)
        self.assertIn("app/ops/final_prediction_store.py", pre)

    def test_flags_forbid_deploy_and_keep_disabled(self) -> None:
        flags = parse_flags(PACK / "FLAGS.txt")
        self.assertEqual(flags["PRODUCTION_CODE_DEPLOY_ALLOWED"], "NO")
        self.assertEqual(flags["OWNER_DEPLOY_APPROVED"], "NO")
        self.assertEqual(flags["POST_CODE_PRODUCTION_DEPLOYED"], "NO")
        self.assertEqual(flags["PREDICTION_RUNS_ENABLED"], "0")
        self.assertEqual(flags["EXPECT_AI_ALLOW_MIGRATION_022_SET"], "NO")
        self.assertEqual(flags["022_REAPPLY"], "NO")
        self.assertEqual(flags["MIGRATE"], "NO")
        self.assertEqual(flags["POST"], "NO")
        self.assertEqual(flags["RESTART"], "NO")
        self.assertEqual(flags["RELOAD"], "NO")
        self.assertEqual(flags["WHOLESALE_MAIN_PY_REPLACE"], "NO")
        self.assertEqual(flags["HUNK_ONLY_MAIN_PY"], "YES")
        self.assertEqual(flags["LIVE_MAIN_IS_BASE"], "YES")
        self.assertEqual(flags["CURSOR_PRODUCTION_SSH"], "NO")
        self.assertEqual(flags["DEPLOY_PACK"], "NO")
        self.assertEqual(flags["APPLY_PACK"], "NO")
        self.assertEqual(flags["OWNER_CAPTURE_ZIP_SHA256"], CAPTURE_ZIP_SHA)
        self.assertEqual(flags["V6_REVIEW_ZIP_SHA256"], V6_ZIP_SHA)
        self.assertEqual(flags["HUNKED_MAIN_PY_SHA256"], HUNKED_MAIN_SHA)
        self.assertEqual(flags["LIVE_MAIN_PY_SHA256"], LIVE_MAIN_SHA)
        self.assertTrue(HEX64.match(flags["OWNER_CAPTURE_ZIP_SHA256"]))
        self.assertEqual(flags["LIVE_OPS_PRESENT_IN_THIS_BUILD"], "NO")
        self.assertEqual(flags["PACK_AUTHOR_INDEPENDENT_TEST_EXECUTION_PASS"], "NO")
        self.assertEqual(flags["OVERLAY_SUITE"], "NOT_RUN")
        self.assertEqual(flags["STUB_OR_MOCK_SUCCESS"], "NO")

    def test_readme_and_donot_forbid_execution(self) -> None:
        readme = (PACK / "00_README.txt").read_text(encoding="utf-8")
        donot = (PACK / "07_DO_NOT_DEPLOY.txt").read_text(encoding="utf-8")
        for text in (readme, donot):
            self.assertIn("THIS IS NOT A PRODUCTION EXECUTION PACK", text)
            self.assertIn("PRODUCTION_CODE_DEPLOY_ALLOWED=NO", text)
            self.assertIn("INDEPENDENT_REVIEW_OF_HUNK_ONLY_V2_BUNDLE", text)
        self.assertIn("Do not deploy from this review bundle.", donot)
        self.assertIn(CAPTURE_ZIP_SHA, readme)
        self.assertIn(HUNKED_MAIN_SHA, readme)

    def test_rollback_is_per_file_restore(self) -> None:
        text = (PACK / "01_docs/rollback_plan.txt").read_text(encoding="utf-8")
        self.assertIn("BACKUP_DIR", text)
        self.assertIn("P.ABSENT", text)
        self.assertIn("SCHEMA_ROLLBACK=NO", text)
        self.assertIn("Do not DROP INDEX", text)
        self.assertIn("immediate pre-deploy backup", text)
        self.assertNotIn("sqlite3 .restore", text.lower())
        self.assertIn("PRODUCTION_CODE_DEPLOY_ALLOWED=NO", text)

    def test_no_execution_scripts(self) -> None:
        names = [p.name.lower() for p in PACK.rglob("*") if p.is_file()]
        self.assertNotIn("owner_apply.ps1", names)
        self.assertNotIn("owner_deploy.ps1", names)
        self.assertFalse(any("owner_apply" in n for n in names))
        self.assertFalse(any(n.endswith(".service") for n in names))
        for path in PACK.rglob("*"):
            if not path.is_file() or path.suffix in {".pyc"}:
                continue
            if path.name == "SHA256SUMS.txt":
                continue
            if path.suffix in {".py", ".txt"}:
                if path.name == "test_hunk_only_v2_review.py":
                    continue
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("PRODUCTION_CODE_DEPLOY_ALLOWED=YES", text, path)
                self.assertNotIn("ssh ubuntu@", text, path)

    def test_pack_does_not_contain_immutable_zips(self) -> None:
        found = [p.name for p in PACK.rglob("*.zip")]
        self.assertEqual(found, [])
        for name in IMMUTABLE_ZIPS:
            self.assertFalse((PACK / name).exists(), name)

    def test_sha256sums_last_and_complete(self) -> None:
        sums_path = PACK / "SHA256SUMS.txt"
        self.assertTrue(sums_path.is_file())
        listed = parse_sums(sums_path)
        self.assertNotIn("SHA256SUMS.txt", listed)
        files = []
        for path in PACK.rglob("*"):
            if not path.is_file():
                continue
            if path.name == "SHA256SUMS.txt":
                continue
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            files.append(path.relative_to(PACK).as_posix())
        self.assertEqual(sorted(listed), sorted(files))
        for rel, digest in listed.items():
            self.assertTrue(HEX64.match(digest), rel)
            self.assertEqual(sha256_file(PACK / rel), digest, rel)
        self.assertIn("FLAGS.txt", listed)
        self.assertIn("candidates/services/win5-ai/app/main.py", listed)
        self.assertEqual(listed["candidates/services/win5-ai/app/main.py"], HUNKED_MAIN_SHA)

    def test_three_way_doc_matches_bytes(self) -> None:
        text = (PACK / "01_docs/three_way_live_origin_v6.txt").read_text(encoding="utf-8")
        self.assertIn(LIVE_MAIN_SHA, text)
        self.assertIn(ORIGIN_MAIN_SHA, text)
        self.assertIn(V6_MAIN_SHA, text)
        self.assertIn(HUNKED_MAIN_SHA, text)
        self.assertIn("WHOLESALE=FORBIDDEN", text)
        self.assertIn("LIVE_EQUALS_ORIGIN", text)

    def test_live_repository_and_bridge_equal_origin(self) -> None:
        self.assertEqual(
            (PACK / "live_canon/app/data/repository/__init__.py").read_bytes(),
            (PACK / "reference/origin_main_25a3f88/app/data/repository/__init__.py").read_bytes(),
        )
        self.assertEqual(
            (PACK / "live_canon/app/core/feature_loader_bridge.py").read_bytes(),
            (PACK / "reference/origin_main_25a3f88/app/core/feature_loader_bridge.py").read_bytes(),
        )
        self.assertNotEqual(
            (PACK / "live_canon/app/main.py").read_bytes(),
            (PACK / "reference/origin_main_25a3f88/app/main.py").read_bytes(),
        )

    def test_identity_and_capture_canon(self) -> None:
        ident = (PACK / "live_canon/IDENTITY.txt").read_text(encoding="utf-8")
        canon = (PACK / "01_docs/capture_canon.txt").read_text(encoding="utf-8")
        for text in (ident, canon):
            self.assertIn(CAPTURE_ZIP_SHA, text)
            self.assertIn(LIVE_MAIN_SHA, text)
            self.assertIn(LIVE_REPO_SHA, text)
            self.assertIn(LIVE_BRIDGE_SHA, text)
            self.assertIn("SIZE=45983", text)

    def test_deploy_files_lists_eleven_candidates(self) -> None:
        text = (PACK / "01_docs/deploy_files.txt").read_text(encoding="utf-8")
        self.assertIn(HUNKED_MAIN_SHA, text)
        for rel in DEPLOY_RELS:
            self.assertIn(rel, text, rel)
        self.assertIn("FORBIDDEN=wholesale replace", text)
        self.assertIn("022_REAPPLY=NO", text)

    def test_origin_tar_bundled_for_overlay(self) -> None:
        tar = PACK / "base/origin_main_25a3f88.tar.gz"
        self.assertTrue(tar.is_file())
        self.assertEqual(sha256_file(tar), "d1e6b5847f1387d696d39b87ad0dbfa4e44f8322ad1caecb75ce0969bad5edff")
        flags = parse_flags(PACK / "FLAGS.txt")
        self.assertEqual(flags["BUNDLED_ORIGIN_TAR"], "YES")

    def test_changes_doc_explains_divergent_main(self) -> None:
        text = (PACK / "CHANGES_FROM_REVIEW_V6.txt").read_text(encoding="utf-8")
        self.assertIn(LIVE_MAIN_SHA, text)
        self.assertIn(V6_MAIN_SHA, text)
        self.assertIn("wholesale", text.lower())
        self.assertIn("two v6 insertions", text)

    def test_run_tests_does_not_rewrite_sums(self) -> None:
        src = (PACK / "run_tests.py").read_text(encoding="utf-8")
        self.assertIn("Does not rewrite SHA256SUMS.txt", src)
        self.assertNotIn("write_sha256sums", src)

    def test_apply_hunk_markers_are_unique_on_live(self) -> None:
        live = (PACK / "live_canon/app/main.py").read_text(encoding="utf-8")
        self.assertEqual(live.count(hunk.DO_OPTIONS_MARK), 1)
        self.assertEqual(live.count(hunk.DO_POST_BLOCK), 1)
        self.assertNotIn("_handle_prediction_runs_post", live)



    def test_live_ops_are_not_deploy_candidates(self) -> None:
        deploy = (PACK / "01_docs/deploy_files.txt").read_text(encoding="utf-8")
        before, after = deploy.split("Live canon bundled but NOT deploy candidates", 1)
        self.assertNotIn("prediction_capacity.py", before)
        self.assertNotIn("final_prediction_store.py", before)
        self.assertIn("DEPLOY_CANDIDATE=NO", after)
        flags = parse_flags(PACK / "FLAGS.txt")
        self.assertEqual(flags["LIVE_PREDICTION_CAPACITY_DEPLOY_CANDIDATE"], "NO")
        self.assertEqual(flags["LIVE_FINAL_PREDICTION_STORE_DEPLOY_CANDIDATE"], "NO")
        self.assertEqual(flags["LIVE_PREDICTION_CAPACITY_SHA256"], "c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e")
        self.assertEqual(flags["LIVE_FINAL_PREDICTION_STORE_SHA256"], "40352ff56b3267533267d5de9c893f3bda8963d5fe121474f7785b0152594a12")
        self.assertFalse((PACK / "candidates/services/win5-ai/app/ops/prediction_capacity.py").exists())
        self.assertFalse((PACK / "candidates/services/win5-ai/app/ops/final_prediction_store.py").exists())

    def test_hunk_v1_zip_not_in_pack(self) -> None:
        self.assertFalse((PACK / "production_disabled_post_hunk_only_deploy_review_20260913.zip").exists())
        flags = parse_flags(PACK / "FLAGS.txt")
        self.assertEqual(flags["HUNK_ONLY_V1_ZIP_SHA256"], "f194488073a98a54fc4fafcadb808f32d3e0b8e53665dcb317da7c7662824db4")
        self.assertEqual(flags["HUNK_ONLY_V1_NOT_OVERWRITTEN"], "YES")

    def test_v2_readme_requires_overlay_suite(self) -> None:
        text = (PACK / "00_README.txt").read_text(encoding="utf-8")
        self.assertIn("52 tests x2", text)
        self.assertIn("concurrency x20", text)
        self.assertIn("DEPLOY_CANDIDATE=NO", text)
        self.assertIn("c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e", text)
        self.assertIn("40352ff56b3267533267d5de9c893f3bda8963d5fe121474f7785b0152594a12", text)

    def test_extra_regression_file_present(self) -> None:
        path = PACK / "overlay_extra/services/win5-ai/tests/predictions/test_live_nonwrite_regression.py"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("test_get_list_and_detail_predictions_row_delta_zero", text)
        self.assertIn("list_active", text)
        self.assertIn("get_pipeline_status", text)

    def test_overlay_fail_closed_when_live_ops_missing(self) -> None:
        import run_tests as rt

        ready, reason = rt.live_ops_ready()
        self.assertFalse(ready)
        self.assertEqual(reason, "LIVE_CANON_OPS_MISSING")
        self.assertFalse((PACK / "live_canon/app/ops/prediction_capacity.py").exists())
        self.assertFalse((PACK / "live_canon/app/ops/final_prediction_store.py").exists())
        marker = (PACK / "live_canon/app/ops/LIVE_BYTES_REQUIRED.txt").read_text(encoding="utf-8")
        self.assertIn("STUB_OR_MOCK=NO", marker)
        src = (PACK / "run_tests.py").read_text(encoding="utf-8")
        self.assertIn('return 3', src)
        self.assertIn("OVERLAY_SUITE=NOT_RUN", src)
        self.assertNotIn("INDEPENDENT_TEST_EXECUTION_PASS\n", src.split("if not ready")[0])

    def test_ingest_rejects_capture_fixture(self) -> None:
        import ingest_owner_ops_canon as ingest

        fixture = b'"""CAPTURE_TOOL_FIXTURE - not Production bytes.\n"""\n'
        with self.assertRaises(SystemExit) as ctx:
            ingest.reject_fixture(fixture, "prediction_capacity.py")
        self.assertIn("fixture_rejected", str(ctx.exception))
        src = (PACK / "ingest_owner_ops_canon.py").read_text(encoding="utf-8")
        self.assertIn("c351bd9753d20994156e00141d564a55a42891983ecab5b2c5c55a32d9908f1e", src)
        self.assertIn("40352ff56b3267533267d5de9c893f3bda8963d5fe121474f7785b0152594a12", src)
        self.assertIn("Does not invent bytes", src)

    def test_owner_intake_doc_lists_return_zip_shas(self) -> None:
        text = (PACK / "01_docs/owner_return_intake.txt").read_text(encoding="utf-8")
        self.assertIn("c04f27e6bc9016927c9a902268ccfeb5a8ac8a62117ca74948b90bc7cbbea843", text)
        self.assertIn("f24d10d28ab99286894e36f60ff53fba3b89c087cac8afaa607c95a5b7670f8d", text)
        self.assertIn("STUB_OR_MOCK_SUCCESS=NO", text)
        self.assertIn("DEPLOY_CANDIDATE", (PACK / "ingest_owner_ops_canon.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
