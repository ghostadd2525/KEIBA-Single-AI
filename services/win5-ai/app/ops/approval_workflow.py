# -*- coding: utf-8 -*-
"""Version8.8 Approval Queue — thin Node CLI bridge (PE/CE/AI untouched)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    env = (os.environ.get("EXPECT_REPO_ROOT") or "").strip()
    if env:
        return Path(env)
    # services/win5-ai/app/ops → KEIBA-Single-AI
    return Path(__file__).resolve().parents[4]


def _run_cli(args: list[str]) -> dict[str, Any]:
    root = _repo_root()
    script = root / "scripts" / "ops" / "v8" / "approval-queue.mjs"
    cmd = ["node", str(script), *args]
    r = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    out = (r.stdout or "").strip()
    if not out:
        return {
            "ok": False,
            "error": "empty_cli_output",
            "stderr": (r.stderr or "")[:500],
            "exit_code": r.returncode,
        }
    try:
        # last JSON object in stdout
        data = json.loads(out)
    except json.JSONDecodeError:
        # try last line
        lines = [ln for ln in out.splitlines() if ln.strip().startswith("{")]
        if not lines:
            return {
                "ok": False,
                "error": "invalid_json",
                "stdout": out[:500],
                "exit_code": r.returncode,
            }
        data = json.loads(lines[-1])
    if r.returncode != 0 and data.get("ok") is not False:
        data.setdefault("exit_code", r.returncode)
    return data


def list_approvals(status: str | None = None) -> dict[str, Any]:
    args = ["--list"]
    if status:
        args.extend(["--status", status])
    return _run_cli(args)


def approve(approval_id: str, actor: str = "admin") -> dict[str, Any]:
    return _run_cli(["--approve", approval_id, "--actor", actor])


def reject(approval_id: str, reason: str, actor: str = "admin") -> dict[str, Any]:
    return _run_cli(
        ["--reject", approval_id, "--reason", reason, "--actor", actor]
    )


def expire() -> dict[str, Any]:
    return _run_cli(["--expire"])
