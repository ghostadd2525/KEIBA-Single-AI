# Version 6 Phase 1 — Knowledge Contents Report

**Date:** 2026-07-25  
**Status:** COMPLETE  
**Scope:** Knowledge Source 正式コンテンツ化（FAQ / サービス / KAOBAガイド / 競馬一般 / 用語）  
**Freeze:** Knowledge Runtime · Provider · Retriever · Tool · Conversation Platform **未変更**

---

## 1. What changed

| Item | Path | Change |
|------|------|--------|
| Knowledge Contents | `app/conversation/v4/knowledge/contents/catalog.json` | 正式 30 docs |
| Knowledge Source | `app/conversation/v4/knowledge/source.py` | Stub 文書 → カタログ読込 + category/tag/keyword API |
| Knowledge Index | `.../contents/knowledge_index.json` · `docs/releases/v6-phase1-knowledge-contents-index.json` | 生成物 |
| Tests | `tests/ops/test_conversation_v6_knowledge_contents.py` | formal / search / Runtime·Tool 経路 |

**未変更:** `v5/knowledge/*` · `provider.py` · `retriever.py` · `tools/knowledge_tool.py` · Orchestrator / Agents / ADR / Memory

---

## 2. Category mapping

| ユーザー向け | category ID |
|--------------|-------------|
| FAQ | `faq` |
| サービス説明 | `service` |
| KAOBA利用ガイド | `help` |
| 競馬一般知識 | `general_keiba` |
| KAOBA独自用語 | `glossary` |

---

## 3. Search

| 方式 | Source API | Runtime / Retriever（既存） |
|------|------------|------------------------------|
| カテゴリ | `search_by_category` / `search(..., category=)` | `retrieve/search(..., category=)` |
| タグ | `search_by_tag` / `search(..., tag=)` | キーワードにタグ語を含めて照合（tags が blob に含まれる） |
| キーワード | `search_by_keyword` / `search(query)` | 既存キーワード照合 |

---

## 4. Stop condition evidence

| Path | Result |
|------|--------|
| Knowledge Runtime `search` | `source_meta.formal=true` · hits ≥ 1 |
| Tool Manager `search_knowledge`（Explain/Review が使う Tool 経路） | ok · formal=true |
| Personal Chat / Explain / Review `conversation.chat` | agent=chat/expert/review · orchestrator=true |

Memory / RAG 改善 / 追加学習には未着手。

---

## 5. Rebuild index

```bash
cd services/win5-ai
python scripts/build_knowledge_index.py
```
