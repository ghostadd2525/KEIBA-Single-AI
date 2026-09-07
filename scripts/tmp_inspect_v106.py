#!/usr/bin/env python3
import json
from pathlib import Path
p = Path("/home/ubuntu/KEIBA-Single-AI/evidence/research/reports/v106-resolver-governance.json")
print("exists", p.exists())
if p.exists():
    d = json.loads(p.read_text(encoding="utf-8"))
    print("keys", list(d.keys())[:40])
    print("current_status", d.get("current_status"))
    print("eligible", d.get("eligible"))
    s = d.get("summary")
    print("summary_type", type(s).__name__)
    if isinstance(s, dict):
        print("summary_keys", list(s.keys())[:20])
        g = s.get("gate") or {}
        print("gate", g)
