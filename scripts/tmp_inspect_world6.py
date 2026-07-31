#!/usr/bin/env python3
import json
import sqlite3
from collections import Counter
from pathlib import Path

c = Counter()
for p in Path("/home/ubuntu/KEIBA-Single-AI/fixtures").rglob("*.json"):
    try:
        b = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    txt = json.dumps(b, ensure_ascii=False)
    for w in [
        "core_world",
        "midupper_world",
        "midhole_world",
        "rank7_world",
        "bug_world",
        "mixed_world",
    ]:
        if w in txt:
            c[w] += 1
print("fixture world mentions", dict(c))

con = sqlite3.connect("/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db")
con.row_factory = sqlite3.Row
rows = con.execute(
    """
    SELECT p.race_id, p.bundle_json, c.surface, c.distance, c.class_label,
           c.age_group, m.going, m.weather, m.field_size, s.snapshot_id
    FROM predictions p
    LEFT JOIN research_prediction_corpus c ON c.race_id = p.race_id
    LEFT JOIN research_race_meta m ON m.race_id = p.race_id
    LEFT JOIN research_prediction_snapshots s
      ON s.race_id = p.race_id AND s.capture_status = 'complete'
    """
).fetchall()
wc = Counter()
sc = Counter()
evi = 0
for r in rows:
    b = json.loads(r["bundle_json"] or "{}")
    ev = b.get("evaluation") or {}
    w = ev.get("world")
    sub = ev.get("sub_world")
    if not w:
        continue
    wc[w] += 1
    if sub:
        sc[sub] += 1
    if r["snapshot_id"]:
        evi += 1
print("joined worlds", dict(wc), "subs", dict(sc), "with_evidence", evi, "n", len(rows))

# feature coverage on labeled+evidence
from app.research.evidence_discovery import EvidenceDiscoveryResearch
import sys
sys.path.insert(0, "/home/ubuntu/KEIBA-Single-AI/services/win5-ai")
