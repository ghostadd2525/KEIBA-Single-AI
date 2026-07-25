# ADR-005 — Conversation Layer Contract

**Status:** Accepted · Version 4 Final Freeze  
**Date:** 2026-07-25  
**Deciders:** Conversation Platform Freeze  
**Related:** ADR-001〜004 · Phases 3–10

---

## Context

Version 4 Conversation AI を単一の Platform として凍結するため、レイヤー責務・依存方向・Flag・Legacy を一括定義する。

---

## Decision

### レイヤー責務

| Layer | 責務 | 非責務 |
|-------|------|--------|
| API / service | HTTP・エントリ | ビジネス判断の本体 |
| Orchestrator | ディスパッチ · Flag · fail-open · 履歴更新 | Prediction 生成 |
| Security Guard | 入力 Block（ADR-001） | Tool 実行 |
| Intent Router / Modes | intent · mode 解決 | データ取得 |
| Agents | 応答文章生成 | Prediction 変更 · Provider 直呼び |
| ReviewContextBuilder | ReviewContext 構築（ADR-004） | LLM 生成 |
| Tool Manager | Tool 単一窓口（ADR-002） | Guard 代替 |
| Prediction Edge | Read-Only 取得（ADR-003） | 予測エンジン本体 |
| Knowledge Edge | 共通知識検索（Retriever） | ユーザー Memory · Prediction 根拠 |
| History | 短期 FIFO · 非永続 | 長期 Memory · RAG 永続 |
| Prompts | system/user 組み立て | 外部 I/O |

### 依存方向（許可）

```text
API → Orchestrator → Guard / Router / History / Agents / Builder
Builder → ToolManager → Tools → Connector | KnowledgeProvider
KnowledgeProvider → Retriever → Source
Retriever ⇢ EmbeddingAdapter / VectorStoreAdapter（Interface · 未接続可）
Connector → Prediction API (read)
```

### 依存方向（禁止）

```text
Prediction API → Conversation
Agents → Connector | Provider | Embedding | VectorStore（直接）
Knowledge → Prediction（公式根拠化）
History → Memory への暗黙昇格
下位 Layer → Orchestrator（逆依存）
```

### 唯一の Platform 入口 / 出口

| | 定義 |
|---|------|
| 唯一の入口 | `conversation.v4` の `chat(body)` / `health()`（Orchestrator） |
| 唯一のユーザー向け出口 | Orchestrator が返す応答 dict（reply · meta · platform） |
| Prediction への唯一出口 | Connector Read（ADR-003） |
| Knowledge への唯一出口 | Tool Manager → KnowledgeTool（ADR-002） |

### Feature Flag 運用方針（Freeze）

| Flag | 既定 | 凍結後方針 |
|------|------|------------|
| `F_V4_CONVERSATION_ENABLED` | OFF | Platform マスタ。OFF 時は全機能停止メッセージ |
| `F_V4_CONVERSATION_OLLAMA` | OFF | LLM 呼び出し許可。OFF でも Platform・テンプレは動作可 |
| `F_V4_REVIEW_AGENT` | OFF | Review 実行 |
| `F_V4_PERSONAL_CHAT` | OFF | Personal Chat 実行（Guard は常時） |
| `F_V4_TOOL_LAYER` | OFF | ON=Canonical Tool 経路。OFF=Legacy Connector 直結 |
| `F_V4_KNOWLEDGE_LAYER` | OFF | KnowledgeTool 実行 |
| `F_V4_KNOWLEDGE_INTEGRATION` | OFF | Adapter 配線のみ。実 Embedding/Vector 接続は別 ADR |

**組み合わせ原則:**

1. 本番推奨は `TOOL_LAYER=ON`（Canonical）
2. Knowledge 利用時は `KNOWLEDGE_LAYER=ON`、Integration は実装接続まで OFF
3. Flag で ADR-001〜004 の禁止事項を解除してはならない

### Legacy 経路一覧（V4 受理）

| ID | 内容 | 削除目安 |
|----|------|----------|
| L-TOOL-OFF | Builder → Connector 直結 | V5 |
| L-EXPERT-STUB | ExpertToolStub | Tool Manager 移行後 |
| L-HELP-FAQ | HelpTool と Knowledge FAQ の併存 | Knowledge 集約後 |

### 凍結範囲に含めないもの（Out of Freeze Implementation）

- Memory
- 実 Embedding / Vector DB / 外部 Knowledge API
- UI
- Prediction AI / Ranking / Confidence / Purchase 本体変更
- Security Guard の全 mode hard block 化（将来 ADR）

### 禁止事項（Platform 全体）

1. Conversation による Prediction 変更
2. Agent による Provider / Connector 直呼び（Canonical 違反）
3. Security Guard の無効化
4. History の永続 DB 化を「Memory」と偽ること
5. 循環依存の導入（特に `knowledge ↔ tools`）
6. Freeze 後に ADR 改訂なしでレイヤー責務を侵食する変更

---

## Consequences

- Version 4 Platform は ADR-001〜005 により正式 Freeze 可能
- 以降の変更は ADR 改訂または V5 スコープとする
