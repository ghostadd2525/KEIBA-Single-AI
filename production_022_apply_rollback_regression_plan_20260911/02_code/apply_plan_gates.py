#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the 022 APPLY review plan. Never apply, migrate, or touch Production."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ROOT / "FLAGS.txt"
DOCS = ROOT / "01_docs"


class PlanError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def emit(key: str, value: object) -> None:
    if value is True:
        text = "YES"
    elif value is False:
        text = "NO"
    else:
        text = str(value)
    print("%s=%s" % (key, text.replace("\n", " ")))


def read_pack_text() -> str:
    parts = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.suffix.lower() in (".txt", ".md", ".py"):
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def refuse_execution_flags() -> None:
    if (os.environ.get("OWNER_APPLY_APPROVED") or "").strip() == "1":
        raise PlanError("REFUSED_OWNER_APPLY_APPROVED_SET_ON_PLAN_PACK")
    if (os.environ.get("EXPECT_AI_ALLOW_MIGRATION_022") or "").strip() in ("1", "true", "yes"):
        raise PlanError("REFUSED_MIGRATION_022_FLAG_SET_ON_PLAN_PACK")
    if (os.environ.get("PREDICTION_RUNS_ENABLED") or "").strip() in ("1", "true", "yes"):
        raise PlanError("REFUSED_PREDICTION_RUNS_ENABLED_ON_PLAN_PACK")


def require_flags() -> dict[str, str]:
    raw = FLAGS.read_text(encoding="utf-8")
    kv = {}
    for line in raw.splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()
    required = {
        "NOT_AN_EXECUTION_PACK": "YES",
        "PRODUCTION_022_APPLY_PLAN_COMPLETE": "YES",
        "PRODUCTION_APPLY_READY": "NO",
        "OWNER_APPLY_APPROVED": "NO",
        "APPLY_EXECUTED": "NO",
        "DEFAULT_PREDICTION_RUNS_ENABLED": "0",
        "POST_REMAINS_DISABLED_AFTER_022": "YES",
        "COLUMN_DELETE_FORBIDDEN": "YES",
        "ROW_DELETE_FORBIDDEN": "YES",
        "BUNDLE_JSON_UPDATE_FORBIDDEN": "YES",
        "POST_ENABLE_IS_SEPARATE_STEP": "YES",
        "APPLY_PRECONDITION": "OWNER_BACKUP_SUCCESS",
    }
    for key, want in required.items():
        if kv.get(key) != want:
            raise PlanError("FLAG_MISMATCH_%s" % key)
    return kv


def require_docs() -> None:
    text = read_pack_text()
    needles = (
        "APPLY_PRECONDITION_BACKUP_PASS",
        "PREDICTION_RUNS_ENABLED=0",
        "EXPECT_AI_ALLOW_MIGRATION_022",
        "DROP INDEX IF EXISTS uq_predictions_idempotency_key_not_null",
        "GET envelope",
        "/api/health",
        "Research Week",
        "systemctl",
        "journal",
        "POST_ENABLE_IS_SEPARATE_STEP",
        "bundle_json",
        "Conversation",
        "Challenge",
    )
    missing = [n for n in needles if n not in text]
    if missing:
        raise PlanError("PLAN_DOC_MISSING_%s" % missing[0].replace(" ", "_"))
    rollback = (DOCS / "03_rollback.txt").read_text(encoding="utf-8")
    i_enabled = rollback.find("PREDICTION_RUNS_ENABLED=0")
    i_unset = rollback.find("Unset EXPECT_AI_ALLOW_MIGRATION_022")
    i_drop = rollback.find("DROP INDEX IF EXISTS uq_predictions_idempotency_key_not_null")
    if not (0 <= i_enabled < i_unset < i_drop):
        raise PlanError("ROLLBACK_ORDER_INCORRECT")
    forbidden = (DOCS / "08_forbidden.txt").read_text(encoding="utf-8")
    for needle in ("DROP COLUMN", "DELETE FROM predictions", "bundle_json", "PR #23"):
        if needle not in forbidden:
            raise PlanError("FORBIDDEN_DOC_MISSING_%s" % needle.replace(" ", "_"))


def refuse_apply_request(argv: list[str]) -> None:
    joined = " ".join(argv).lower()
    banned = ("--apply", "--migrate", "--execute", "systemctl", "migrate(")
    for token in banned:
        if token in joined:
            raise PlanError("REFUSED_EXECUTION_TOKEN")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    emit("PACK", "production_022_apply_rollback_regression_plan_20260911")
    emit("NOT_AN_EXECUTION_PACK", "YES")
    emit("PRODUCTION_APPLY_READY", "NO")
    emit("OWNER_APPLY_APPROVED", "NO")
    emit("APPLY_EXECUTED", "NO")
    try:
        refuse_apply_request(argv)
        parser = argparse.ArgumentParser(description="022 APPLY review-plan gates (no execution)")
        parser.add_argument("--check", action="store_true", help="validate plan documents and flags")
        args = parser.parse_args(argv)
        if not args.check:
            raise PlanError("CHECK_FLAG_REQUIRED")
        refuse_execution_flags()
        require_flags()
        require_docs()
        emit("PLAN_GATES_OK", "YES")
        emit("PRODUCTION_022_APPLY_PLAN_COMPLETE", "YES")
        return 0
    except PlanError as exc:
        emit("PLAN_GATES_OK", "NO")
        emit("PRODUCTION_APPLY_READY", "NO")
        emit("FAIL_REASON", exc.code)
        return 2


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
