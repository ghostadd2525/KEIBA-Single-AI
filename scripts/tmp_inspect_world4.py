#!/usr/bin/env python3
import json
import sqlite3
from collections import Counter
from pathlib import Path

con = sqlite3.connect("/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db")
con.row_factory = sqlite3.Row
tabs = [r[0] for r in con.execute(
    "select name from sqlite_master where type='table'"
).fetchall()]
for t in tabs:
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
    if any("world" in c.lower() for c in cols):
        print("table", t, cols)

WORLD = [
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "bug_world",
    "mixed_world",
]
c = Counter()
n = 0
paths = []
for p in Path("/home/ubuntu/KEIBA-Single-AI").rglob("*.json"):
    if n > 3000:
        break
    try:
        if p.stat().st_size > 3_000_000:
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    n += 1
    hit = False
    for w in WORLD:
        if w in txt:
            c[w] += 1
            hit = True
    if hit and len(paths) < 15:
        paths.append(str(p))
print("files scanned", n, "world file hits", dict(c))
print("examples", paths[:10])

# find optimizer
for p in Path("/home/ubuntu").rglob("demo_ticket_optimizer_core.py"):
    print("found", p)
