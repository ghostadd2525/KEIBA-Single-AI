# -*- coding: utf-8 -*-
"""
Knowledge Source（Stub）— 共通知識のみ。

対象: FAQ / ヘルプ / サービス説明 / 用語集 / 競馬の一般知識
非対象: ユーザー固有情報 · Prediction の根拠 · Vector DB / Embedding
"""
from __future__ import annotations

from dataclasses import dataclass
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


# 共通知識のみ（Prediction 根拠・ユーザー固有は含めない）
_STUB_DOCUMENTS: tuple[KnowledgeDocument, ...] = (
    KnowledgeDocument(
        doc_id="faq-kaoba",
        category="faq",
        title="KAOBAとは？",
        body=(
            "KAOBA は Expect ～ KEIBA AI ～ の会話アシスタントです。"
            "予想の作成・変更は行いません。説明と相談のみ担当します。"
        ),
        tags=("kaoba", "faq", "assistant"),
    ),
    KnowledgeDocument(
        doc_id="faq-prediction-immutable",
        category="faq",
        title="予想は変更できる？",
        body=(
            "できません。Prediction AI が唯一の公式結果です。"
            "Conversation / Knowledge は予測根拠を上書きしません。"
        ),
        tags=("prediction", "faq", "immutable"),
    ),
    KnowledgeDocument(
        doc_id="help-explain-mode",
        category="help",
        title="◎の理由を聞く",
        body=(
            "レース画面の「KAOBAに◎の理由を聞く」（Explain Mode）を使うと、"
            "公式 Prediction に基づく説明を聞けます。"
        ),
        tags=("explain", "help", "honmei"),
    ),
    KnowledgeDocument(
        doc_id="help-review-mode",
        category="help",
        title="予想について相談する",
        body=(
            "「KAOBAに相談」（Review Mode）では、公式 Prediction を前提に"
            "強み・リスク・展開の見方をレビューします。印や買い目は変えません。"
        ),
        tags=("review", "help", "consult"),
    ),
    KnowledgeDocument(
        doc_id="service-overview",
        category="service",
        title="Expect ～ KEIBA AI ～ とは",
        body=(
            "競馬の予測（Prediction AI）と会話（Conversation AI）を組み合わせたサービスです。"
            "予測エンジンと会話レイヤーは役割が分離されています。"
        ),
        tags=("service", "expect", "overview"),
    ),
    KnowledgeDocument(
        doc_id="glossary-honmei",
        category="glossary",
        title="本命（◎）",
        body="本命は最も評価が高い軸候補を示す印です。本サービスでは Prediction AI が付与します。",
        tags=("glossary", "honmei", "mark"),
    ),
    KnowledgeDocument(
        doc_id="glossary-odds",
        category="glossary",
        title="オッズ",
        body="オッズは投票状況に応じた払戻倍率の目安です。予測スコアそのものではありません。",
        tags=("glossary", "odds"),
    ),
    KnowledgeDocument(
        doc_id="keiba-pace",
        category="general_keiba",
        title="ペース（展開）の基本",
        body=(
            "レース展開はペース配分と位置取りで大きく変わります。"
            "これは一般知識であり、特定レースの公式予測根拠ではありません。"
        ),
        tags=("keiba", "pace", "general"),
    ),
    KnowledgeDocument(
        doc_id="keiba-course",
        category="general_keiba",
        title="コース適性の一般論",
        body=(
            "距離・芝ダート・回り方などで適性の見え方が変わります。"
            "個別馬の評価は Prediction AI の領域です。"
        ),
        tags=("keiba", "course", "general"),
    ),
)

ALLOWED_CATEGORIES = frozenset(
    {"faq", "help", "service", "glossary", "general_keiba"}
)


class StubKnowledgeSource:
    """インメモリ共通知識 Stub。外部接続なし。"""

    stub = True
    connected_to_vector_db = False
    connected_to_embedding = False
    connected_to_external_api = False
    includes_user_private_data = False
    includes_prediction_rationale = False

    def __init__(self, documents: tuple[KnowledgeDocument, ...] | None = None) -> None:
        docs = documents if documents is not None else _STUB_DOCUMENTS
        self._documents = tuple(
            d for d in docs if d.category in ALLOWED_CATEGORIES
        )

    def list_documents(self) -> list[KnowledgeDocument]:
        return list(self._documents)

    def list_as_dicts(self) -> list[dict[str, Any]]:
        return [d.as_dict() for d in self._documents]

    def meta(self) -> dict[str, Any]:
        return {
            "stub": True,
            "vector_db": False,
            "embedding": False,
            "external_api": False,
            "user_private": False,
            "prediction_rationale": False,
            "categories": sorted(ALLOWED_CATEGORIES),
            "document_count": len(self._documents),
        }
