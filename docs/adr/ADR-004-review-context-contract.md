# ADR-004 — ReviewContext Contract

**Status:** Accepted · Version 4 Final Freeze  
**Date:** 2026-07-25  
**Deciders:** Conversation Platform Freeze  
**Related:** Phase 4 Review Context · Phase 7/8 Builder

---

## Context

Review / Explain が個別 payload を直接読むと、Prediction 改変や根拠の不統一が起きる。統一 Context が必要である。

---

## Decision

### 責務

| コンポーネント | 責務 |
|----------------|------|
| `ReviewContext` | Review / Explain の **唯一の入力契約** |
| `ReviewContextBuilder` | Official Prediction · stubs · request · history を組み立てる **唯一の構築入口** |
| `ReviewAgent` | `review(context: ReviewContext)` のみ |
| `ExpertAgent.explain` | `explain(context: ReviewContext)`（Explain Mode） |
| `ConversationContext` / History | 短期対話履歴。ReviewContext の代替ではない |

### ReviewContext フィールド契約

| フィールド | 内容 | 備考 |
|------------|------|------|
| `mode` | `review` / `explain` 等 | |
| `prediction` | Official Prediction または null | request payload 由来禁止 |
| `prediction_meta` | used/connected/mutated/source/... | `mutated=false` 必須 |
| `buy_strategy` / `race` / `horse` / `user` | Stub 可 | 未接続明示 |
| `request` | message / race_id / intent / slots | |
| `history` | Prompt 用短期履歴 | 永続 Memory ではない |

### 唯一の入口

- 構築: `ReviewContextBuilder.build(...)`
- Agent 入力: `ReviewAgent.review(context)` / `ExpertAgent.explain(context)`

### 唯一の出口

- Agent 応答 dict（文章 · meta · citations）
- Context 自体を外部に永続化しない（V4）

### 依存方向

```text
Orchestrator → ReviewContextBuilder → ReviewContext → ReviewAgent | Expert.explain
Builder → ToolManager | Connector（ADR-002/003）
Agent ↛ Builder 再帰呼び出し禁止
Agent ↛ Prediction API
```

### 禁止事項

1. ReviewAgent が `prediction` 単体など Context 以外を公開 API で受け取ること
2. Explain が request payload prediction を Official 扱いすること
3. Context 内で Prediction を書き換えること
4. History / Memory を ReviewContext.prediction に混入すること
5. buy_strategy / race 等 Stub を「接続済み本データ」と偽ること

### Feature Flag

| Flag | 影響 |
|------|------|
| `F_V4_REVIEW_AGENT` | ReviewAgent 実行可否（Context 契約自体は不変） |
| `F_V4_TOOL_LAYER` | Builder 内の取得経路（Canonical vs Legacy） |
| Context 契約専用 Flag | **なし**（常時有効） |

### fail-open

Official Prediction 取得失敗時:

- Builder は `prediction=null` · `fail_open` meta を付けうる
- Orchestrator は固定メッセージで Platform 継続（停止しない）
- 代替予想の生成は禁止（ADR-003）

---

## Consequences

- Review / Explain の根拠は Official Prediction に単一化される
- Agent 公開 API の安定により Platform 凍結が可能
