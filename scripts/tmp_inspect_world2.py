#!/usr/bin/env python3
import json
import sqlite3
from collections import Counter
from pathlib import Path

db = Path("/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db")
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row

EXISTING = {
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "bug_world",
    "mixed_world",
}

def extract_world(b):
    if not isinstance(b, dict):
        return None, None, None
    paths = []
    ev = b.get("evaluation") if isinstance(b.get("evaluation"), dict) else {}
    pred = b.get("prediction") if isinstance(b.get("prediction"), dict) else {}
    pe = b.get("pe") if isinstance(b.get("pe"), dict) else {}
    meta = b.get("meta") if isinstance(b.get("meta"), dict) else {}
    candidates = [
        ("evaluation.world", ev.get("world"), ev.get("sub_world")),
        ("prediction.world", pred.get("world"), pred.get("sub_world")),
        ("root.world", b.get("world"), b.get("sub_world")),
        ("meta.world", meta.get("world") or meta.get("world_type"), meta.get("sub_world") or meta.get("sub_world_type")),
        ("pe.world", pe.get("world"), pe.get("sub_world")),
    ]
    # walk shallow for world key
    def walk(obj, prefix="", depth=0):
        if depth > 4 or not isinstance(obj, dict):
            return
        for k, v in obj.items():
            if k in {"world", "world_type", "_world_line_type", "race_world_type", "post_world_type"} and isinstance(v, str):
                paths.append((f"{prefix}.{k}", v))
            elif isinstance(v, dict):
                walk(v, f"{prefix}.{k}", depth + 1)
    walk(b, "b")
    for name, w, s in candidates:
        if w:
            return str(w), (str(s) if s else None), name
    if paths:
        return paths[0][1], None, paths[0][0]
    return None, None, None

# predictions
w_all = Counter(); sub_all = Counter(); src = Counter(); n=0; labeled=0
for row in con.execute("SELECT id, race_id, bundle_json FROM predictions"):
    n += 1
    try:
        b = json.loads(row["bundle_json"] or "{}")
    except Exception:
        continue
    w, s, path = extract_world(b)
    if w:
        labeled += 1
        w_all[w] += 1
        if s: sub_all[s] += 1
        src[path] += 1
print("predictions", n, "labeled", labeled)
print("worlds", dict(w_all))
print("subs", dict(sub_all.most_common(20)))
print("paths", dict(src))

# historical
hw = Counter(); hn=0; hl=0
for row in con.execute("SELECT race_id, bundle_json FROM research_historical_bundles WHERE has_bundle=1"):
    hn += 1
    try:
        b = json.loads(row["bundle_json"] or "{}")
    except Exception:
        continue
    w, s, path = extract_world(b)
    if w:
        hl += 1
        hw[w] += 1
print("historical", hn, "labeled", hl, dict(hw))

# snapshots payload
sn = 0; sl = 0; sw = Counter()
try:
    cols = [r[1] for r in con.execute("PRAGMA table_info(research_prediction_snapshots)")]
    print("snap cols", cols)
    # try payload path
except Exception as e:
    print(e)

# corpus join: how many races can we label via predictions.bundle
q = """
SELECT COUNT(*) AS n,
  SUM(CASE WHEN p.bundle_json LIKE '%\"world\"%' THEN 1 ELSE 0 END) AS with_world_str
FROM research_prediction_corpus c
LEFT JOIN predictions p ON p.id = c.prediction_id
"""
print(dict(con.execute(q).fetchone()))

# sample one midupper bundle structure
row = con.execute(
    "SELECT bundle_json FROM predictions WHERE bundle_json LIKE '%midupper_world%' LIMIT 1"
).fetchone()
if row:
    b = json.loads(row["bundle_json"])
    ev = b.get("evaluation") or {}
    print("ev keys", list(ev.keys())[:30])
    print("world", ev.get("world"), "sub", ev.get("sub_world"))
    # race meta-ish
    for k in ("race_info", "meta", "inputs"):
        if k in b and isinstance(b[k], dict):
            print(k, list(b[k].keys())[:20])
