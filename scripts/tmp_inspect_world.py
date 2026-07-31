#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

def find_db():
    for p in Path("/home/ubuntu/KEIBA-Single-AI").rglob("*.db"):
        try:
            con = sqlite3.connect(p)
            tabs = [r[0] for r in con.execute(
                "select name from sqlite_master where type='table'"
            ).fetchall()]
            con.close()
            if "research_prediction_corpus" in tabs:
                return p, tabs
        except Exception:
            pass
    return None, []

db, tabs = find_db()
print("db", db)
print("rel tabs", [t for t in tabs if "research" in t or "pred" in t][:40])
if not db:
    raise SystemExit(0)
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
# sample bundles for world
n = 0
worlds = {}
for row in con.execute(
    """
    SELECT race_id, bundle_json FROM research_historical_bundles
    WHERE has_bundle=1 LIMIT 200
    """
):
    try:
        b = json.loads(row["bundle_json"] or "{}")
    except Exception:
        continue
    ev = b.get("evaluation") if isinstance(b.get("evaluation"), dict) else {}
    # also nested
    if not ev and isinstance(b.get("prediction"), dict):
        ev = b["prediction"].get("evaluation") or {}
    world = ev.get("world") or b.get("world") or (b.get("prediction") or {}).get("world")
    sub = ev.get("sub_world") or b.get("sub_world")
    if world:
        worlds[str(world)] = worlds.get(str(world), 0) + 1
        n += 1
        if n <= 3:
            print("ex", row["race_id"], world, sub, list(ev.keys())[:20])
print("labeled", n, "worlds", worlds)

# also predictions table
pw = {}
pn = 0
try:
    for row in con.execute("SELECT id, race_id, bundle_json FROM predictions LIMIT 300"):
        try:
            b = json.loads(row["bundle_json"] or "{}")
        except Exception:
            continue
        ev = b.get("evaluation") if isinstance(b.get("evaluation"), dict) else {}
        world = ev.get("world") or (b.get("prediction") or {}).get("world")
        if world:
            pw[str(world)] = pw.get(str(world), 0) + 1
            pn += 1
except Exception as e:
    print("pred err", e)
print("pred labeled", pn, pw)
