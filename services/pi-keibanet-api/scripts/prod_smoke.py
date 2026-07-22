#!/usr/bin/env python3
"""Production smoke test for PI API Version 1."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("EXPECT_KEIBANET_BASE_URL", "http://127.0.0.1:8081").rstrip("/")
DATE = os.environ.get("PI_SMOKE_DATE", "2026-07-25")
PUBLISHED_RACE_ID = os.environ.get("PI_SMOKE_PUBLISHED_RACE_ID", "2026-07-25-01-06")
UNPUBLISHED_RACE_ID = os.environ.get("PI_SMOKE_UNPUBLISHED_RACE_ID", "2026-07-25-01-01")


def fetch(path: str) -> tuple[int, dict | list | str]:
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    code, payload = fetch("/health")
    ok = code == 200 and isinstance(payload, dict) and payload.get("status") == "ok"
    results.append(("health", ok, f"HTTP {code}"))

    code, payload = fetch(f"/v1/races?date={DATE}")
    ok = (
        code == 200
        and isinstance(payload, dict)
        and isinstance(payload.get("venues"), list)
        and len(payload.get("venues", [])) > 0
    )
    venue_count = len(payload.get("venues", [])) if isinstance(payload, dict) else 0
    race_count = len(payload.get("races", [])) if isinstance(payload, dict) else 0
    results.append(("GET /v1/races", ok, f"HTTP {code} venues={venue_count} races={race_count}"))

    code, payload = fetch(f"/v1/races/{PUBLISHED_RACE_ID}")
    ok = code == 200 and isinstance(payload, dict) and payload.get("race_id") == PUBLISHED_RACE_ID
    results.append(("GET /v1/races/{published}", ok, f"HTTP {code}"))

    code, payload = fetch(f"/v1/predictions/{PUBLISHED_RACE_ID}")
    pred_ok = (
        code == 200
        and isinstance(payload, dict)
        and payload.get("prediction_available") is True
        and isinstance(payload.get("prediction"), dict)
    )
    msg = f"HTTP {code} prediction_available={payload.get('prediction_available') if isinstance(payload, dict) else '?'}"
    if isinstance(payload, dict) and not pred_ok:
        msg += f" error={payload.get('error')}"
    results.append(("GET /v1/predictions/{published}", pred_ok, msg))

    code, payload = fetch(f"/v1/races/{UNPUBLISHED_RACE_ID}")
    unpub_ok = code == 404 and isinstance(payload, dict) and payload.get("error") == "race_not_found"
    results.append(("unpublished race (404)", unpub_ok, f"HTTP {code} reason={payload.get('reason') if isinstance(payload, dict) else '?'}"))

    code, payload = fetch(
        f"/v1/static/race_meta?date={DATE}&venue=%E6%96%B0%E6%BD%9F&race_no=6"
    )
    legacy_ok = code == 200 and isinstance(payload, dict) and payload.get("race_no") == 6
    results.append(("GET /v1/static/race_meta", legacy_ok, f"HTTP {code}"))

    print(f"PI API smoke base={BASE}")
    failed = 0
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{status}] {name}: {detail}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
