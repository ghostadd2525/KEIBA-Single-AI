#!/usr/bin/env python3
import json
import sqlite3
from collections import Counter
from pathlib import Path

db = Path("/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db")
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row

KEYS = [
    "chaos_score", "race_leg_difficulty", "late_stop_risk_score",
    "sustained_run_possible_score", "high_pace_score", "pace_collapse_risk",
    "world_load_score", "traffic_score", "short_field_pressure",
    "world", "sub_world", "world_type",
]

def find_keys(obj, found=None, depth=0):
    if found is None:
        found = Counter()
    if depth > 5:
        return found
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in KEYS:
                found[k] += 1
            find_keys(v, found, depth+1)
    elif isinstance(obj, list) and obj and depth < 3:
        for x in obj[:3]:
            find_keys(x, found, depth+1)
    return found

# historical sample
hk = Counter()
n = 0
for row in con.execute("SELECT bundle_json FROM research_historical_bundles WHERE has_bundle=1 LIMIT 50"):
    n += 1
    try:
        b = json.loads(row["bundle_json"] or "{}")
    except Exception:
        continue
    hk.update(find_keys(b))
print("hist sample keys", dict(hk))

# labeled prediction full meta
row = con.execute(
    "SELECT bundle_json FROM predictions WHERE bundle_json LIKE '%midupper_world%' LIMIT 1"
).fetchone()
b = json.loads(row["bundle_json"])
print("labeled keys", dict(find_keys(b)))
# print evaluation and any scores
ev = b.get("evaluation") or {}
print("evaluation", {k: ev.get(k) for k in ev if k != "runners"})
# runners sample keys
rs = ev.get("runners") or []
if rs:
    print("runner keys", sorted(rs[0].keys())[:40])

# snapshots payload
sk = Counter(); sn=0; sw=Counter()
for row in con.execute(
    "SELECT payload_json FROM research_prediction_snapshots WHERE capture_status='complete' LIMIT 80"
):
    sn += 1
    try:
        p = json.loads(row["payload_json"] or "{}")
    except Exception:
        continue
    sk.update(find_keys(p))
    # try world
    for path in [
        (p.get("prediction_bundle") or {}).get("evaluation") if isinstance(p.get("prediction_bundle"), dict) else {},
        p.get("evaluation") if isinstance(p.get("evaluation"), dict) else {},
    ]:
        if isinstance(path, dict) and path.get("world"):
            sw[path.get("world")] += 1
print("snap keys", dict(sk))
print("snap worlds", dict(sw), "of", sn)

# Can we import classifier on EC2?
import sys
sys.path.insert(0, "/home/ubuntu")
sys.path.insert(0, "/home/ubuntu/win5-ai")
for mod in ["demo_ticket_optimizer_core"]:
    try:
        m = __import__(mod)
        print("import", mod, "ok", hasattr(m, "classify_world_line_type"))
    except Exception as e:
        print("import", mod, "FAIL", type(e).__name__, e)
