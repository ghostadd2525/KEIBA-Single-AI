# Version 4 — Migration Notes

**Date:** 2026-07-25  
**Applies to:** Conversation Platform V4 Final Freeze  
**Audience:** 実装者 · 運用 · 次 Phase 設計

---

## 1. 目的

Freeze 時点の **Canonical / Legacy / 次 major への移行方針** を固定する。本ノートはコード変更を伴わない。

---

## 2. Canonical（移行先 · 推奨）

| 領域 | Canonical |
|------|-----------|
| Platform 入口 | Orchestrator `chat` / `health` |
| Security | ADR-001（chat hard block + 履歴ゲート） |
| Prediction 取得 | Tool Manager → PredictionTool → Connector → `get_with_meta` |
| Review/Explain 入力 | ReviewContextBuilder → ReviewContext |
| Knowledge | Tool Manager → KnowledgeTool → Provider → Retriever → Source |
| History | 短期 FIFO · 非永続（Memory ではない） |

**推奨 Flag（新規環境）:**

```text
F_V4_CONVERSATION_ENABLED=true
F_V4_TOOL_LAYER=true
F_V4_REVIEW_AGENT=true          # Review 利用時
F_V4_PERSONAL_CHAT=true         # Chat 利用時
F_V4_KNOWLEDGE_LAYER=true       # Knowledge 利用時
F_V4_KNOWLEDGE_INTEGRATION=false
F_V4_CONVERSATION_OLLAMA=false  # LLM 不要なら false
```

---

## 3. Legacy（V4 で残置 · 互換）

### L-TOOL-OFF

- **現象:** `F_V4_TOOL_LAYER=false` のとき Builder が Connector 直結
- **互換理由:** Phase 7 経路の維持
- **制約:** ADR-003 Read-Only は適用。書込は不可
- **移行:** `F_V4_TOOL_LAYER=true` に切替。挙動差は取得経路のみ（Official 投影は同等）
- **削除目安:** V5

### L-EXPERT-STUB

- **現象:** 非 Explain Expert intent が `ExpertToolStub` を使用
- **互換理由:** Phase 8 以前の Expert 最小実装
- **移行:** Capability 対応 Tool へ段階移行（新 ADR 推奨）
- **削除目安:** Tool Manager 完全移行後

### L-HELP-FAQ

- **現象:** HelpTool と Knowledge Source FAQ の併存
- **移行:** Knowledge へ集約し Help は薄ラッパまたは廃止
- **削除目安:** Knowledge 本運用後

---

## 4. 移行手順（運用）

### 4.1 既存デプロイを Canonical に寄せる

1. `F_V4_CONVERSATION_ENABLED=true`
2. `F_V4_TOOL_LAYER=true` に変更
3. Review / Explain の smoke（Official Prediction · `mutated=false`）
4. fail-open（Prediction 不可時の固定文 · Platform 継続）を確認
5. Chat で Guard Block を確認（Ollama 非呼び出し）

### 4.2 Knowledge を有効化する場合

1. `F_V4_KNOWLEDGE_LAYER=true`
2. Tool Manager `search_knowledge` 経由のみ利用
3. `F_V4_KNOWLEDGE_INTEGRATION` は実 Embedding/Vector 接続 ADR まで OFF

### 4.3 やってはいけない移行

- Legacy 経路で Prediction Write API を足す
- Agent から Provider / Connector 直 import
- History を DB 永続して Memory と呼ぶ（別 ADR 必須）
- Guard を Flag で OFF

---

## 5. V5 以降への持ち越し

| 項目 | ノート |
|------|--------|
| 全 mode Guard hard block | 新 ADR（ADR-001 改訂） |
| L-TOOL-OFF 削除 | ADR-002 改訂 |
| ExpertToolStub 削除 | Tool Capability 拡充 |
| Embedding / Vector 本接続 | Knowledge Integration 実装 ADR |
| Memory | History と分離した新 Layer ADR |
| UI | Platform Freeze 外 |

---

## 6. 参照

- [ADR Index](../adr/README.md)
- [Freeze Report](./v4-conversation-platform-freeze.md)
- [Architecture Review](./v4-conversation-architecture-review.md)
