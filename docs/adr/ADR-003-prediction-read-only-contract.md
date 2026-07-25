# ADR-003 — Prediction Read-Only Contract

**Status:** Accepted · Version 4 Final Freeze  
**Date:** 2026-07-25  
**Deciders:** Conversation Platform Freeze  
**Related:** Phase 7 Prediction Integration · Architecture Review R4

---

## Context

Conversation AI は Prediction AI の結果を説明・レビューする。Prediction の生成・変更は Prediction AI の専権であり、Conversation が侵食してはならない。

---

## Decision

### 責務分離

| 主体 | 責務 |
|------|------|
| Prediction AI / Prediction API | 公式予測の生成 · 唯一の正解 |
| Conversation Prediction Connector | **Read Only** 取得（`get_with_meta`） |
| Conversation Prediction Adapter | 非破壊投影（Official Prediction） |
| Conversation Agents | 文章生成のみ。印・順位・買い目・confidence を変更しない |

### 唯一の入口（Conversation → Prediction）

```text
PredictionConnector.fetch(race_id)
  → PredictionReadable.get_with_meta(race_id)
```

Canonical 呼び出しは Tool Manager → PredictionTool → Connector（ADR-002）。

### 唯一の出口（Prediction → Conversation）

```text
OfficialPredictionFetch
  → ConversationPredictionAdapter.adapt
  → Official Prediction dict + prediction_meta
  → ReviewContext.prediction
```

request payload の `prediction` は **根拠にしない**（公式 API 結果のみ）。

### Read Only 保証（V4 契約）

1. Connector は **取得のみ**。書込・再計算・再ランキング API を Conversation から呼ばない
2. Adapter は bundle を **in-place 変更しない**（新規 dict 投影）
3. `prediction_meta.mutated` は **常に `false`**
4. Review / Explain 出力に `updated_prediction` / `new_marks` 等の変更結果を含めない
5. Review Agent は出力テキストの書換表現をガードする（補助防御）
6. **Write Adapter / mutate API の Conversation 層への追加は禁止**（新 ADR + Platform 改訂なしでは不可）

### 依存方向

```text
Conversation (Connector) → Prediction API (read)
Prediction API ↛ Conversation（逆依存禁止）
Agents ↛ Prediction API（直接禁止）
```

### 禁止事項

1. Conversation からの Prediction 書込・パッチ・再計算
2. Ranking / Confidence / Purchase / History（予測側）の Conversation 内改変
3. request 偽 prediction を Official として採用すること
4. Knowledge / Memory に Prediction 根拠を「公式」として混入すること
5. fail-open 時に代替予想を生成すること（固定メッセージのみ）

### Feature Flag

- Prediction Read-Only 自体に Flag は無い（常時契約）
- `F_V4_TOOL_LAYER` は取得経路のみ切替。Read-Only は両経路で有効

### Legacy

- Connector 直結（Tool Layer OFF）でも本 ADR は適用される
- Legacy 削除後も本 ADR は存続する

### `prediction_meta.connected` の意味（凍結定義）

| 場所 | `connected` の意味 |
|------|---------------------|
| ReviewContextBuilder / Tool meta | Prediction API から Official を取得できたか |
| ReviewAgent 応答 meta | Agent 自身は API に接続しないため **応答上 `false` 固定を許容**（V4）。取得成否は `used` / `source` / citations で判断 |

---

## Consequences

- Prediction AI 責務は侵食されない
- 保証は主に規約・経路・メタ・テスト。型システムによる書込遮断は V4 範囲外（文書禁止で代替）
