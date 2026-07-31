# V51 — Consumer Matrix（ADR-050）

**Date:** 2026-07-28  
**Scope:** Research only — no implementation  
**Canonical (ADR-050):** `evaluate_candidates` → CorePublicBundle  
**Product View (non-canonical):** PredictionBundle 2.0

---

## Legend

| Label | Meaning |
|---|---|
| **変更が必要** | ADR-050 実装時に契約入口・スキーマ・マッピングの変更が必要 |
| **変更不要** | 既に CE / CorePublicBundle を正としており、追加変更は最小〜不要 |
| **影響なし** | CorePublicBundle / PredictionBundle 契約切替に依存しない |

---

## Full Matrix

| # | Consumer | Module / Path | Current Input | ADR-050 Impact | Notes |
|---|---|---|---|---|---|
| 1 | **Prediction HTTP list** | `win5-ai/app/main.py` `/v1/predictions` | PredictionBundle[] | **変更が必要** | 共通契約コメントが Bundle; CE 公開方針が必要 |
| 2 | **Prediction HTTP get** | `main.py` `/v1/predictions/{id}` | PredictionBundle | **変更が必要** | Adapter 経由; Canonical 露出 or Dual |
| 3 | **prediction_adapter** | `engine/adapters/prediction_adapter.py` | Real/Mock Bundle | **変更が必要** | 入口を CE→View に再配線 |
| 4 | **single_prediction_mapper** | `single_prediction_mapper.py` | prediction_response→Bundle | **変更が必要** | world=None は View defect; CE→Bundle View 再設計 |
| 5 | **Single.predict** | `ai_platform/single/prediction` | predict_ranking + confidence | **変更が必要** | Canonical 入口は evaluate_candidates |
| 6 | **Single API** | `ai_platform/single/api` | get_prediction | **変更が必要** | predict 依存 |
| 7 | **Single CLI** | `ai_platform/single/cli` | get_prediction | **変更が必要** | 同上 |
| 8 | **Platform Eval** | `ai_platform/evaluation` | get_prediction | **変更が必要** | Single 入口依存 |
| 9 | **Analytics core** | `ai_platform/analytics/core` | predict_ranking/confidence | **変更が必要** | Compatibility view 利用者 |
| 10 | **PI get_prediction** | `pi-keibanet-api/.../service.py` | CorePipeline / prediction | **変更が必要** | PI 公開形と CE 整合 |
| 11 | **Functions predictionAdapter** | `functions/_lib/adapters/predictionAdapter.js` | `/v1/predictions` Bundle | **変更が必要** | Proxy + Ready 判定 |
| 12 | **Functions domain.js** | `functions/_lib/domain.js` | PredictionBundle normalize | **変更が必要** | schema 2.0 固定 |
| 13 | **predictionReady** | `functions/_lib/predictionReady.js` | Bundle ready 判定 | **変更が必要** | CE 基準 or View 基準の定義 |
| 14 | **GUI prediction.js** | `public/assets/api/prediction.js` | PredictionBundle | **変更が必要** | ContractGuard.validatePredictionBundle |
| 15 | **GUI prediction-bind.js** | `public/assets/api/prediction-bind.js` | Bundle→UI | **変更が必要** | world 表示・バインド拡張時 |
| 16 | **ExpectContractGuard** | public assets / contracts | Bundle schema | **変更が必要** | Canonical 検証追加 or View 明示 |
| 17 | **Conversation connector** | `conversation/v4/prediction/connector.py` | prediction_adapter | **変更が必要** | 間接依存 |
| 18 | **Conversation tools** | `conversation/tools.py` | get_with_meta | **変更が必要** | 間接依存 |
| 19 | **Challenge service** | `challenge/service.py` | Stored PredictionBundle | **変更が必要** | ◎○▲ 抽出; 保存スキーマ |
| 20 | **Explain / Analysis HTTP** | `main.py` analysis paths | Bundle race_id キー | **変更不要*** | race_id 参照のみなら View 維持で可 |
| 21 | **Kaoba / Ticket HTTP** | adapters | Bundle race_id | **変更不要*** | 同上（*Bundle 形状破壊時は要） |
| 22 | **Win5 Optimizer** | `demo_ticket_optimizer_core` | 独自 Trigger | **影響なし** | evaluate_candidates 非使用 |
| 23 | **PE Feature/Scorer/Ranker** | core stages | 内部特徴 | **影響なし** | Bundle 非生成・非消費 |
| 24 | **WorldAssigner** | CE stage | Pipeline 内部 | **影響なし** | 既に CE 内; 公開契約切替の外 |
| 25 | **Research signal_lineage** | research | CE + views 比較 | **変更不要** | 既に CE 参照 |
| 26 | **Research world_signal_*** | research | CorePipeline | **変更不要** | 既に CE |
| 27 | **Research chaos / wic / difficulty** | research | CorePipeline | **変更不要** | 既に CE |
| 28 | **Research prediction_corpus** | research DB | corpus / snapshots | **変更が必要** | 保存契約が Bundle 前提なら移行設計 |
| 29 | **Mock / catalog** | mock + domain.js | Fixture Bundle | **変更が必要** | Canonical 整合 or View-only 明示 |
| 30 | **Ops tests (collect_c*)** | tests/ops | prediction_adapter | **変更が必要** | 期待 Bundle 形 |

\* Analysis / Kaoba / Ticket: race_id キー参照のみなら **変更不要**。HTTP が Bundle を破壊的に置き換える場合は **変更が必要** に昇格。

---

## Domain Roll-up

### Prediction
- **変更が必要** — HTTP, Adapter, Mapper, Ready判定, Ops tests

### Single
- **変更が必要** — predict / api / cli（入口を CE へ）

### Win5
- **影響なし** — Optimizer / Trigger は CE 非依存  
- Win5-ai HTTP の Prediction 面は Prediction ドメイン扱い（上表 1–4）

### GUI
- **変更が必要** — prediction.js, bind, ContractGuard

### Explain
- Conversation / tools: **変更が必要**（間接）  
- Analysis-by-race_id: **変更不要***（条件付き）

### API
- win5-ai `/v1/predictions*`: **変更が必要**  
- Functions proxy: **変更が必要**  
- PI prediction: **変更が必要**

### CLI
- `single_ai` / `platform_eval`: **変更が必要**

### Research
- CE 直接利用: **変更不要**  
- Corpus / snapshot（Bundle 保存）: **変更が必要**

---

## Producer → Consumer Edges（実装時に切る線）

```
CorePipeline.evaluate
    └── evaluate_candidates  ←── ADR-050 Canonical
            ├── [TODAY unused by Product HTTP]
            ├── Research (already)
            ├── predict_ranking ──► Single.predict ──► Mapper ──► PredictionBundle
            │                              ▲
            │                              └── HTTP / GUI / Functions / Conversation
            └── predict_confidence ────────┘
```

ADR-050 実装の本質: Product 入口を **Mapper←predict_*** から **View←evaluate_candidates**（または Dual）へ付け替える。

---

*V51 Consumer Matrix — research only.*
