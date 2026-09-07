# -*- coding: utf-8 -*-
import pathlib
import re

root = pathlib.Path(r"C:\win5-ai\KEIBA-Single-AI\public")
names = [
    "kaoba-fortune-fun",
    "kaoba-fortune-happy",
    "kaoba-fortune-angry",
    "kaoba-fortune-sad",
    "kaoba-fortune-dada",
    "ai-card-bg-honmei",
    "ai-card-bg-pedigree",
    "ai-card-bg-odds",
    "mascot-ka0ba",
    "mascot-ka0ba-login",
    "mascot-loading-run",
    "race-bg-1",
    "race-bg-2",
    "race-bg-3",
    "race-bg-4",
    "maintenance-ka0ba",
    "kaoba-emotion-joy",
    "kaoba-emotion-anger",
    "kaoba-emotion-tantrum",
]
exts = {".html", ".css", ".js"}
changed = []
for p in root.rglob("*"):
    if p.suffix.lower() not in exts:
        continue
    if "node_modules" in p.parts:
        continue
    text = p.read_text(encoding="utf-8")
    orig = text
    for n in names:
        text = re.sub(
            rf"{re.escape(n)}\.png(\?v=[^\"'\\s)]*)?",
            rf"{n}.webp\1",
            text,
        )
    if text != orig:
        p.write_text(text, encoding="utf-8", newline="\n")
        changed.append(str(p.relative_to(root)))
print("updated", len(changed))
for c in changed:
    print(c)
