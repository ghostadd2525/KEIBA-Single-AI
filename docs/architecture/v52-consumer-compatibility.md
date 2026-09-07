# V52 — Consumer Compatibility（View Adapter）

**Date:** 2026-07-28  
**Adapter under test:** `CorePublicBundle` only → `PredictionBundle` 2.0  
**Legend:**

| Result | Meaning |
|---|---|
| **Yes** | Adapter alone fills this Consumer’s observed Bundle dependencies |
| **No** | Evidence shows required fields/paths outside CE |
| **Partial** | Subset OK; full path still needs non-CE inputs |
| **N/A** | Does not consume PredictionBundle / not on CE→Bundle path |

---

## Matrix

| Consumer | Result | Required Bundle fields (code evidence) | CE alone? | Blocker |
|---|---|---|---|---|
| **HTTP API detail** `/v1/predictions/{id}` | **No** | Full PredictionBundle via adapter `get_with_meta` | No | Serves Mapper output which needs prediction_response + race_meta; CE lacks race_info/bets |
| **HTTP API list** `/v1/predictions` | **No** | Bundle list; Real path mixes catalog / inference | No | List uses catalog / mock assembly; not CE→Adapter |
| **GUI** `prediction.js` / `prediction-bind.js` | **No** | `evaluation.runners` (+ mark), `ai_confidence`, `race_info`, `explain`, `betting_recommendations` | No | mark/race_info/bets not in CE; Guard validates Bundle shape |
| **Single** (`predict` / API) | **No** | Produces `prediction_response` with **bets**, not CE→Bundle | No | `build_bet_plan`/`build_bets` after `predict_ranking`; CE-only Adapter ≠ Single output |
| **Win5** Optimizer | **N/A** | Does not call `evaluate_candidates` or consume Bundle | N/A | Outside Adapter question |
| **CLI** `single_ai` | **No** | `get_prediction` → same as Single | No | Bets / full response not CE projection |
| **Functions** `predictionAdapter.js` / Ready | **No** | Proxies `/v1/predictions`; Ready needs runners≥1; UI/kaoba use mark/race_info | No | Upstream Bundle completeness; mock/PI/catalog branches |
| **Conversation** | **No** | `prediction_adapter`; `reason_builder` uses evaluation/ai_confidence/explain/race_info | No | Same Bundle gaps |
| **Challenge** | **Partial** | `axis_rivals_from_bundle` needs runners + **mark** (fallback model_rank) | Partial | mark は Rank→合成可能だが取得元は **stored Bundle / PI**。CE Adapter はライブ再生成時のみ関与 |
| **Mock** | **No** | `MockPredictionSource` / fixtures / `catalog_to_prediction_bundle` | No | Zero CE involvement |
| **Research** (CE scripts) | **N/A** | Many call `CorePipeline` / `evaluate_candidates` directly | N/A | Already Canonical; Adapter not required |
| **Research** (corpus / snapshots) | **No** | Stored PredictionBundle shapes | No | Historical Bundle ≠ CE Adapter output without re-pipeline |

---

## Evidence anchors

### HTTP / Adapter

- `main.py`: PredictionBundle を共通契約として `/v1/predictions` を返す  
- Real path: `run_single_prediction` → `prediction_response_to_bundle`（入力は **prediction_response**）  
- Mock path: fixtures / catalog — **CE なし**

### GUI

- `prediction-bind.js`: `runner.mark`, `win_prob`, `ai_confidence.score`, explain reasons  
- `prediction.js`: `ExpectContractGuard.validatePredictionBundle`  
- marks / bets 表示経路あり

### Single / CLI

```text
predict_ranking + predict_confidence
  → build_bet_plan → build_bets
  → prediction_response
```
（`ai_platform/single/prediction/__init__.py`）

CE 直結 Adapter はこの鎖の **Bet 段を飛ばす**ため CLI/Single 同等にならない。

### Functions

- `isReadyPredictionBundle`: runners length（CE→runners 変換があれば Ready 条件自体は満たし得る）  
- しかし `kaobaDomain.js` / `raceCardSummary.js` は **mark** と **race_info** に依存  
- catalog projection meta は CE Adapter と別系統

### Conversation / Challenge

- Conversation: Bundle fetch via prediction_adapter  
- Challenge: `bundle_json` or PI Bundle; marks for ◎○▲△

### Win5 / Research CE

- Optimizer: no CE/Bundle  
- Research CE: Adapter 不要（互換問題の外）

---

## Roll-up

| Bucket | Consumers |
|---|---|
| Adapter alone **fails** | HTTP, GUI, Single, CLI, Functions, Conversation, Mock, Research-corpus |
| Adapter alone **partial** | Challenge（mark 合成は可、取得経路は別） |
| **N/A** | Win5 Optimizer, Research-CE-direct |

**全 Consumer 救済: 不成立。**

---

*V52 Consumer Compatibility — research only.*
