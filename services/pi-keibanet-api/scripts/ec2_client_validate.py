#!/usr/bin/env python3
"""Verify Collector KeibaNetClient -> PI API -> Validator."""
import json
import os
import sys
import urllib.parse

sys.path.insert(0, "/home/ubuntu/KEIBA-Single-AI/services/win5-ai")
os.chdir("/home/ubuntu/KEIBA-Single-AI/services/win5-ai")

from app.data.collect.keibanet.client import KeibaNetClient
from app.data.collect.validator import (
    validate_entries_core,
    validate_race_meta,
)

base = os.environ.get("EXPECT_KEIBANET_BASE_URL", "http://127.0.0.1:8081")
client = KeibaNetClient(base_url=base)
params = urllib.parse.urlencode({"date": "2026-07-19", "venue": "福島", "race_no": "1"})

for path, validator in (
    (f"/v1/static/race_meta?{params}", validate_race_meta),
    (f"/v1/static/entries_core?{params}", validate_entries_core),
):
    resp = client.fetch(path)
    vr = validator(http_ok=resp.ok, body=resp.body)
    print(path.split("?")[0], "status", resp.status_code, "valid", vr.ok, vr.errors)
    if resp.ok:
        print(json.dumps(json.loads(resp.body.decode()), ensure_ascii=False)[:200])
