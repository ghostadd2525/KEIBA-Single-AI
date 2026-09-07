#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W4 Global-budget deny probe (staging).

W4 runner is not on this git tree. Snapshot would call
``pi_keibanet.w4_horse.acquisition.run_w4cd_acquire`` → ``NetkeibaClient.fetch``.
This probe uses the same component name ``w4`` and the same deny report/exit
contract without importing ``w4_horse`` or sending live HTTP.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.http_budget import BudgetDenied
from pi_keibanet.netkeiba.client import NetkeibaClient

# Snapshot D1 URL shape only (not a live fetch).
_D1_URL = "https://db.netkeiba.com/horse/2021100000/"


def main() -> int:
    os.environ.setdefault("GLOBAL_HTTP_BUDGET_COMPONENT", "w4")
    calls = {"n": 0}

    def opener(*_a, **_k):
        calls["n"] += 1
        raise AssertionError("W4 probe opener must not run after budget deny")

    report = {
        "component": "w4",
        "stopped_global_budget": False,
        "global_budget_reason": "",
        "http_request_count": 0,
        "errors": [],
        "stop_reason": "",
    }
    client = NetkeibaClient(min_interval_sec=0, opener=opener, component="w4")
    try:
        client.fetch(_D1_URL, label="w4_budget_probe")
    except BudgetDenied as exc:
        report["stopped_global_budget"] = True
        report["global_budget_reason"] = exc.reason
        report["errors"].append(f"global_budget_denied:{exc.reason}")
        report["stop_reason"] = "global_http_budget"
        report["http_request_count"] = calls["n"]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 5
    report["http_request_count"] = calls["n"]
    report["errors"].append("unexpected_budget_allow")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
