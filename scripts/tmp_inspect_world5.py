#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

WORLD = Counter()
SUB = Counter()
n = 0
root = Path("/home/ubuntu/KEIBA-Single-AI/public/data/predictions")
for p in sorted(root.glob("*.pi.json")):
    try:
        b = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    n += 1
    ev = b.get("evaluation") if isinstance(b.get("evaluation"), dict) else {}
    # nested prediction
    if not ev.get("world"):
        pred = b.get("prediction") if isinstance(b.get("prediction"), dict) else {}
        ev2 = pred.get("evaluation") if isinstance(pred.get("evaluation"), dict) else {}
        if ev2.get("world"):
            ev = ev2
        elif pred.get("world"):
            WORLD[str(pred.get("world"))] += 1
            if pred.get("sub_world"):
                SUB[str(pred.get("sub_world"))] += 1
            continue
    w = ev.get("world")
    s = ev.get("sub_world")
    if w:
        WORLD[str(w)] += 1
    if s:
        SUB[str(s)] += 1
print("pi files", n)
print("worlds", dict(WORLD))
print("subs", dict(SUB))

# also evidence prediction-snapshots dir
snap = Path("/home/ubuntu/KEIBA-Single-AI/evidence/research/prediction-snapshots")
if snap.exists():
    c = Counter(); m = 0
    for p in snap.rglob("*.json"):
        m += 1
        if m > 500:
            break
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
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
    print("snap files scanned", m, dict(c))
else:
    print("no snap dir")
