# ADR-002 — Tool Manager Contract

**Status:** Accepted · Version 4 Final Freeze  
**Date:** 2026-07-25  
**Deciders:** Conversation Platform Freeze  
**Related:** Phase 8 Tool Layer · Phase 9 Knowledge · Architecture Review R2/R3

---

## Context

Conversation Agent と外部データ源の間に Tool Layer を置き、個別 Tool / Provider 直呼びを防ぐ。一方で `F_V4_TOOL_LAYER=OFF` 時の Connector 直結と ExpertToolStub が二重経路を生んでいる。

---

## Decision

### 責務

| コンポーネント | 責務 |
|----------------|------|
| Tool Manager | Capability 保持 · Tool 選択 · Tool 実行の **唯一の窓口** |
| Capability | 利用可能 Tool の宣言（prediction / race_info / statistics / help / knowledge） |
| Individual Tools | 単一関心の Read 実行。Agent から直接呼ばない |
| ExpertToolStub | **Legacy**（非 Explain Expert intent 用）。正規経路外 |

### 正規経路（Canonical）

```text
ReviewContextBuilder / 呼び出し側
        ↓
Tool Manager.select / call / get_official_prediction / search_knowledge
        ↓
PredictionTool | KnowledgeTool | RaceInfoTool | StatisticsTool | HelpTool
```

### 唯一の入口

- `ToolManager.call(name, **kwargs)`
- `ToolManager.call_selected(...)`
- `ToolManager.get_official_prediction(race_id)`
- `ToolManager.search_knowledge(query, ...)`

### 唯一の出口

- `ToolResult`（`mutated=false` · `read_only` 明示）
- Prediction 系は Official Prediction 投影のみ（書込なし）

### 依存方向

```text
Builder /（将来 Agent）→ ToolManager → Tools → Connector|Provider
Tools は互いに呼び出さない
Agent は Provider / Connector / Embedding / VectorStore を直接 import しない
```

### Feature Flag 運用

| Flag | 既定 | 凍結後の意味 |
|------|------|----------------|
| `F_V4_TOOL_LAYER` | OFF | **ON = Canonical**。OFF = **Legacy 直結**（ADR-002 Legacy） |
| `F_V4_KNOWLEDGE_LAYER` | OFF | KnowledgeTool 実行許可 |
| `F_V4_KNOWLEDGE_INTEGRATION` | OFF | Retriever へ Adapter 配線（runtime 未接続） |

**推奨プロファイル（freeze-safe）:**

```text
F_V4_CONVERSATION_ENABLED=ON
F_V4_TOOL_LAYER=ON
F_V4_KNOWLEDGE_LAYER=ON   # Knowledge 利用時
F_V4_KNOWLEDGE_INTEGRATION=OFF  # 実 Embedding/Vector まで OFF
```

### Legacy 経路の扱い

| Legacy | 内容 | V4 扱い | 削除予定 |
|--------|------|---------|----------|
| L2-A | `F_V4_TOOL_LAYER=OFF` 時、Builder → `PredictionConnector` 直結 | **受理 · 互換維持** | 次 major（V5）で削除候補 |
| L2-B | `ExpertToolStub`（非 Explain Expert） | **受理 · 過渡** | Tool Manager Capability へ移行後削除 |

Legacy 利用時も Prediction **Write は禁止**（ADR-003 優先）。

### 禁止事項

1. Agent が個別 Tool / Knowledge Provider / Prediction Connector を直接呼ぶこと（Canonical 違反）
2. Tool が Prediction を変更・再計算すること
3. Tool Manager が Security Guard を代替・無効化すること
4. Capability に無い Tool 名を正規 API として公開すること
5. Race Info / Statistics の「実接続」を Stub のまま本番契約と偽ること

### Read Only 保証

- 全 Tool の `ToolResult.mutated = false`
- PredictionTool は Connector Read のみ
- KnowledgeTool は共通知識検索のみ（ユーザー固有・Prediction 根拠なし）

---

## Consequences

- Canonical は Tool Manager 単線
- OFF 直結は Legacy として文書化され、Architecture Review R2 を解決
- ExpertToolStub は意図的 Legacy（R3）
