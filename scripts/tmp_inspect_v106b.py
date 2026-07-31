#!/usr/bin/env python3
import json
from pathlib import Path
d = json.loads(Path("/home/ubuntu/KEIBA-Single-AI/evidence/research/reports/v106-resolver-governance.json").read_text(encoding="utf-8"))
c = d.get("cumulative") or {}
print("cum_keys", list(c.keys())[:30])
print("gate", c.get("gate"))
print("dashboard", d.get("dashboard"))
v22 = json.loads(Path("/home/ubuntu/KEIBA-Single-AI/evidence/research/reports/v22-continuous-research.json").read_text(encoding="utf-8"))
print("resolver", (v22.get("governance") or {}).get("resolver_status"))
print("pipeline_n", len((v22.get("pipeline") or {}).get("steps") or {}))
print("pipe_keys", list(((v22.get("pipeline") or {}).get("steps") or {}).keys()))
