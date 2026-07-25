# -*- coding: utf-8 -*-
"""
Knowledge Source — Version 6 Phase 1 正式コンテンツ。

対象: FAQ / サービス説明 / KAOBA利用ガイド / 競馬一般知識 / KAOBA独自用語
非対象: ユーザー固有情報 · Prediction の根拠 · Vector DB / Embedding

Retriever / Provider / Runtime / Tool / Platform は変更しない。
本モジュールはドキュメント供給のみ（StubKnowledgeSource クラス名は互換維持）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    category: str
    title: str
    body: str
    tags: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "category": self.category,
            "title": self.title,
            "body": self.body,
            "tags": list(self.tags),
        }


# カテゴリ ID は既存 Retriever / テスト互換を維持
# 表示名: FAQ / サービス説明 / KAOBA利用ガイド / 競馬一般知識 / KAOBA独自用語
ALLOWED_CATEGORIES = frozenset(
    {"faq", "help", "service", "glossary", "general_keiba"}
)

CATEGORY_LABELS_JA = {
    "faq": "FAQ",
    "service": "サービス説明",
    "help": "KAOBA利用ガイド",
    "general_keiba": "競馬一般知識",
    "glossary": "KAOBA独自用語",
}

_CONTENTS_DIR = Path(__file__).resolve().parent / "contents"
_CATALOG_PATH = _CONTENTS_DIR / "catalog.json"


def _load_catalog_documents() -> tuple[KnowledgeDocument, ...]:
    if not _CATALOG_PATH.is_file():
        return ()
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    docs: list[KnowledgeDocument] = []
    for item in raw.get("documents") or []:
        if not isinstance(item, dict):
            continue
        cat = str(item.get("category") or "")
        if cat not in ALLOWED_CATEGORIES:
            continue
        tags = item.get("tags") or ()
        if isinstance(tags, list):
            tag_t = tuple(str(t) for t in tags)
        else:
            tag_t = ()
        docs.append(
            KnowledgeDocument(
                doc_id=str(item.get("doc_id") or ""),
                category=cat,
                title=str(item.get("title") or ""),
                body=str(item.get("body") or ""),
                tags=tag_t,
            )
        )
    return tuple(d for d in docs if d.doc_id and d.title)


def _catalog_meta() -> dict[str, Any]:
    if not _CATALOG_PATH.is_file():
        return {"formal": False, "version": None, "phase": None}
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return {
        "formal": bool(raw.get("formal")),
        "version": raw.get("version"),
        "phase": raw.get("phase"),
        "category_labels": raw.get("categories") or CATEGORY_LABELS_JA,
    }


# 起動時に正式カタログを読む（欠落時は空 → 明示的に壊すより安全に空）
_FORMAL_DOCUMENTS: tuple[KnowledgeDocument, ...] = _load_catalog_documents()


class StubKnowledgeSource:
    """
    正式 Knowledge Contents を供給する Source。
    クラス名は V4/V5 配線互換のため維持。meta.formal=true。
    """

    stub = True  # 外部 Vector/Embedding 未接続（互換）
    connected_to_vector_db = False
    connected_to_embedding = False
    connected_to_external_api = False
    includes_user_private_data = False
    includes_prediction_rationale = False

    def __init__(self, documents: tuple[KnowledgeDocument, ...] | None = None) -> None:
        docs = documents if documents is not None else _FORMAL_DOCUMENTS
        self._documents = tuple(d for d in docs if d.category in ALLOWED_CATEGORIES)
        self._catalog = _catalog_meta()

    def list_documents(self) -> list[KnowledgeDocument]:
        return list(self._documents)

    def list_as_dicts(self) -> list[dict[str, Any]]:
        return [d.as_dict() for d in self._documents]

    def meta(self) -> dict[str, Any]:
        return {
            "stub": True,
            "formal": bool(self._catalog.get("formal")),
            "content_version": self._catalog.get("version"),
            "content_phase": self._catalog.get("phase"),
            "vector_db": False,
            "embedding": False,
            "external_api": False,
            "user_private": False,
            "prediction_rationale": False,
            "categories": sorted(ALLOWED_CATEGORIES),
            "category_labels": dict(CATEGORY_LABELS_JA),
            "document_count": len(self._documents),
            "supports": ["category", "tag", "keyword"],
        }

    def search_by_category(self, category: str, *, limit: int = 20) -> list[KnowledgeDocument]:
        cat = str(category or "").strip()
        lim = max(1, min(int(limit or 20), 50))
        return [d for d in self._documents if d.category == cat][:lim]

    def search_by_tag(self, tag: str, *, limit: int = 20) -> list[KnowledgeDocument]:
        t = str(tag or "").strip().lower()
        lim = max(1, min(int(limit or 20), 50))
        if not t:
            return []
        hits = [d for d in self._documents if t in {x.lower() for x in d.tags}]
        return hits[:lim]

    def search_by_keyword(self, query: str, *, limit: int = 20) -> list[KnowledgeDocument]:
        q = str(query or "").strip().lower()
        lim = max(1, min(int(limit or 20), 50))
        if not q:
            return list(self._documents)[:lim]
        scored: list[tuple[float, KnowledgeDocument]] = []
        for doc in self._documents:
            blob = f"{doc.title} {doc.body} {' '.join(doc.tags)}".lower()
            score = 0.0
            for token in q.replace("　", " ").split():
                if token and token in blob:
                    score += 1.0
            if score > 0 or q in blob:
                if q in blob and score == 0:
                    score = 0.5
                scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:lim]]

    def search(
        self,
        query: str | None = None,
        *,
        category: str | None = None,
        tag: str | None = None,
        limit: int = 5,
    ) -> list[KnowledgeDocument]:
        """カテゴリ / タグ / キーワードを組み合わせた Source 側検索。"""
        lim = max(1, min(int(limit or 5), 50))
        docs = list(self._documents)
        if category:
            docs = [d for d in docs if d.category == str(category)]
        if tag:
            t = str(tag).strip().lower()
            docs = [d for d in docs if t in {x.lower() for x in d.tags}]
        if query and str(query).strip():
            q = str(query).strip().lower()
            scored: list[tuple[float, KnowledgeDocument]] = []
            for doc in docs:
                blob = f"{doc.title} {doc.body} {' '.join(doc.tags)}".lower()
                score = 0.0
                for token in q.replace("　", " ").split():
                    if token and token in blob:
                        score += 1.0
                if score > 0 or q in blob:
                    if q in blob and score == 0:
                        score = 0.5
                    scored.append((score, doc))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [d for _, d in scored[:lim]]
        return docs[:lim]


# 互換エイリアス
FormalKnowledgeSource = StubKnowledgeSource
