# -*- coding: utf-8 -*-
"""Build Knowledge Index artifact from formal catalog (no Platform changes)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = (
    ROOT
    / "app"
    / "conversation"
    / "v4"
    / "knowledge"
    / "contents"
    / "catalog.json"
)
OUT = ROOT / "app" / "conversation" / "v4" / "knowledge" / "contents" / "knowledge_index.json"
REPORT_OUT = (
    ROOT.parents[1]
    / "docs"
    / "releases"
    / "v6-phase1-knowledge-contents-index.json"
)


def main() -> None:
    raw = json.loads(CATALOG.read_text(encoding="utf-8"))
    docs = raw.get("documents") or []
    by_cat: dict[str, list[dict]] = {}
    by_tag: dict[str, list[str]] = {}
    for d in docs:
        cat = d.get("category") or "unknown"
        by_cat.setdefault(cat, []).append(
            {
                "doc_id": d.get("doc_id"),
                "title": d.get("title"),
                "tags": d.get("tags") or [],
            }
        )
        for tag in d.get("tags") or []:
            by_tag.setdefault(str(tag), []).append(d.get("doc_id"))
    index = {
        "version": raw.get("version"),
        "phase": raw.get("phase"),
        "formal": raw.get("formal"),
        "document_count": len(docs),
        "categories": raw.get("categories"),
        "by_category": by_cat,
        "by_tag": {k: sorted(set(v)) for k, v in sorted(by_tag.items())},
        "doc_ids": [d.get("doc_id") for d in docs],
    }
    OUT.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", OUT)
    print("wrote", REPORT_OUT)
    print("documents", len(docs), "categories", list(by_cat.keys()))


if __name__ == "__main__":
    main()
