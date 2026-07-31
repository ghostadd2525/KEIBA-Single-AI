# Version9.0 Design — Challenge Benchmark Layer

**Status:** Production Standard（Feature Flag `V9_BENCHMARK_LAYER` / default **ON**）  
**Date:** 2026-07-27  
**Scope:** Challenge API / UI / Ops Dashboard only  
**Non-goals:** PE / CE / AI推論 / Research / ResultAutomation / Prediction Logic

関連: `docs/design/v9-benchmark-strategy.md`（戦略選定） / `docs/design/v9-prediction-lifecycle.md`

---

## 1. 目的

Challenge の AI 実績を **Prediction 性能** と **購入戦略（フォーメーション）** に分離する。

| 層 | 役割 | デフォルト表示 |
|----|------|----------------|
| **AI Benchmark** | 公式 AI 実績（正本） | メインカード |
| **User Challenge** | ユーザー個人台帳 | メインカード |
| **Purchase Lab** | 購入戦略の研究比較 | 折りたたみのみ |

現行 V8.9 の「馬連+ワイド+三連複+三連単（平均14.7点）」は購入ロジック評価になりがちで、AI 予測の可視化として不適切 → 公式は **◎単勝1点** に固定。

---

## 2. AI Benchmark（正本）

- 買い目: **◎（本命軸）単勝 1 点 × 100円**
- データ: Prediction Bundle + `race_results` のみ（ユーザー購入を見ない）
- 月次リセットの共有ベンチマーク（全ユーザー同一）

### 表示項目

- 利益 / 回収率 / 的中率 / 購入額 / 払戻額 / 対象レース数

### メタ（Ops / API）

```json
{
  "current_strategy": "◎単勝1点",
  "version": "9.0",
  "since": "2026-07",
  "last_updated": "2026-07-27"
}
```

---

## 3. User Challenge

V8.9.1 仕様を維持（変更なしの意図）:

- `user_id` 単位
- `users.created_at`（登録日）以降のレースのみ
- AI / Purchase Lab と完全分離
- 他ユーザー・共有履歴の混入禁止

---

## 4. Purchase Lab

研究用。**デフォルト非表示**（`<details>` 折りたたみ）。

| id | label | bet_types |
|----|-------|-----------|
| sanrentan | 三連単 | 三連単 |
| umaren | 馬連 | 馬連 |
| wide | ワイド | ワイド |
| place | 複勝 | 複勝 |
| win_place | 単勝＋複勝 | 単勝, 複勝 |

公式 KPI には含めない。比較バナー・メインカードは使わない。

---

## 5. API

`GET /v1/challenge/monthly?month=YYYY-MM`  
BFF: `GET /api/v1/challenge/monthly`

### Flag OFF（V8.9 互換）

```json
{
  "schema_version": "expect-challenge-compare/1.1",
  "feature_flags": { "v9_benchmark_layer": false },
  "ai": { "...": "4券種 book" },
  "user": { "...": "personal ledger" },
  "comparison": { "source": "ai_legacy_book", "ai_profit": 0 }
}
```

### Flag ON（V9）

```json
{
  "schema_version": "expect-challenge-compare/2.0",
  "feature_flags": { "v9_benchmark_layer": true },
  "benchmark": { "book": { "bet_types": ["単勝"] }, "summary": {} },
  "user": {},
  "purchase_lab": { "visible_by_default": false, "strategies": [] },
  "comparison": {
    "source": "benchmark",
    "ai_profit": 0,
    "benchmark_profit": 0,
    "user_profit": 0
  },
  "benchmark_strategy": {}
}
```

`comparison.ai_profit` / `benchmark_profit` は **benchmark（単勝）** 由来。  
互換のため ON 時も `ai` / `ai_summary` は benchmark を指すエイリアスを付与。

---

## 6. Feature Flag

| 層 | 変数 | 既定 |
|----|------|------|
| AI service | `V9_BENCHMARK_LAYER` | **ON**（unset 時も ON。rollback: `0`/`false`/`no`/`off`） |
| Pages BFF | `V9_BENCHMARK_LAYER`（`wrangler.toml`） | **`"true"`** |

- **ON（Production Standard）:** 3層 UI + V9 API（`comparison.source=benchmark`、◎単勝1点）
- **OFF（rollback）:** V8.9 legacy UI / API 形状（4券種 AI）

rollback 時は AI ホストと Pages の両方を `false` に揃えること。

---

## 7. Dashboard（Ops）

Operations Console → System に **Benchmark Strategy** カード:

- Current Strategy
- Version
- Since
- Last Updated

静的: `/ops-data/benchmark-strategy.json`

---

## 8. 境界

変更してよい: `app/challenge/*`, Challenge BFF, `challenge-dashboard.js`, `saved.html`, Ops console / ops-data, 本ドキュメント群。

変更禁止: PE / CE / AI推論 / Research / ResultAutomation / Prediction Logic / `race_result_settle` の settle ルール本体（Challenge から **呼び出しのみ**）。
