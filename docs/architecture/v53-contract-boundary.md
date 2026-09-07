# V53 — Contract Boundary（Inputs / Outputs / Layers）

**Date:** 2026-07-28  
**Scope:** Research only  
**Companion:** `v53-prediction-assembly-boundary.md`

---

## ③ Boundary Validation

### Layer map

```text
┌─────────────────────────────────────────────────────────────────┐
│ Presentation                                                     │
│  GUI: prediction.js / prediction-bind.js / ContractGuard          │
│  Responsibility: display, validate Bundle shape                  │
│  MUST NOT: call CE, RaceData DB, BetBuilder, invent Rank/World   │
└───────────────────────────────▲─────────────────────────────────┘
                                │ PredictionBundle
┌───────────────────────────────┴─────────────────────────────────┐
│ Product surfaces                                                 │
│  HTTP /v1/predictions*  Conversation  Challenge  Functions proxy │
│  Single API/CLI（prediction_response を直接扱う場合あり）          │
│  Responsibility: transport, auth, provenance envelope, storage   │
│  MUST NOT: recompute Rank/Confidence/World                       │
└───────────────────────────────▲─────────────────────────────────┘
                                │ Bundle / response
┌───────────────────────────────┴─────────────────────────────────┐
│ Prediction Assembly  ← audited boundary                          │
│  predict + prediction_response + Mapper + Adapter(+Mock/Catalog) │
│  Responsibility: compose multi-source → Product DTO              │
│  MUST: pass Core facts; attach RaceInfo; integrate Bets; marks   │
│  MUST NOT: own Canonical truth; null Core world; rescore         │
└──────────▲──────────▲──────────▲──────────▲──────────▲──────────┘
           │          │          │          │          │
    CorePublicBundle  RaceData   Catalog   Bet*     Identity/DB
    / ranking+conf     get_race   load_races plan+   resolve_*
                       race_meta  mocks     build    features check
┌──────────┴──────────────────────────────────────────────────────┐
│ AI Core                                                          │
│  CorePipeline / evaluate_candidates / World / Confidence / Rank  │
│  Responsibility: Canonical CorePublicBundle                      │
│  MUST NOT: PredictionBundle, Race card DTO, Bet slips, GUI marks │
└─────────────────────────────────────────────────────────────────┘
```

### Validation against code

| Boundary rule | Status | Evidence |
|---|---|---|
| Core ⊈ Product Bundle | **Hold** | Facade docstring forbids Product-stage |
| Presentation ⊈ Assembly | **Hold** | GUI consumes HTTP Bundle |
| Assembly composes RaceData+Bet | **Hold** | Mapper `_race_info`; Single `build_bets` |
| Assembly preserves Core World | **Violate** | Mapper `world: None` |
| Assembly input = Canonical CE | **Violate** | `predict` uses `predict_ranking` not `evaluate_candidates` |
| Single Bet isolated from CE | **Hold** | bet_builder: “No CE / ranking access” |

**境界種は正しい。現行遵守は部分的。**

---

## ④ Input Contract（Assembly 入力元）

| Input | Module / API | Used for | Required for full Bundle? |
|---|---|---|---|
| **CorePublicBundle** | `evaluate_candidates` | Canonical Rank/Conf/World/Meta | **Should**（ADR-050）; **現行 Real 経路では未使用** |
| **RankingResult** | `predict_ranking` | runners / bet targets | Yes（現行） |
| **ConfidenceResult** | `predict_confidence` | ai_confidence / bet conf | Yes（現行） |
| **RaceData** | `ai_platform.race_data.get_race` | race_info fields | Yes（detail UX） |
| **Catalog** | `data.load_races` / race row meta | list filters, race_meta, mock base | Yes（list/mock） |
| **BetStrategy** | `build_bet_plan` | plans from ranking+confidence | Yes（bets block） |
| **BetBuilder** | `build_bets` | slips → betting_recommendations | Yes（bets block） |
| **Identity / Resolver** | `resolve_identity`, `resolve_core_race_id` | public↔core id | Yes（Real） |
| **Feature availability** | `classify_feature_availability` | Real vs fallback gate | Yes（Real） |
| **DB（Challenge path）** | `predictions.bundle_json` | read prior Assembly output | Consumer-side; not Assembly input for live infer |
| **PI fetch** | `fetch_pi_prediction_bundle` | Challenge fallback Bundle | External assembled Bundle |
| **Mock fixtures / templates** | public mocks / domain helpers | fallback Bundle | When engine mock/fallback |
| **Clock / constants** | datetime, schema_version, PRODUCT_VERSION | stamps | Yes |
| **Other** | `explain_payload` (CE, flag) | unused by current Mapper | Optional future input |

### Input graph (current Real path)

```text
catalog race_meta ──┐
identity/core_id ───┤
predict_ranking ────┼──► predict ──► prediction_response ──► Mapper ──► Bundle
predict_confidence ─┤         │
build_bet_plan/bets ┘         │
get_race ─────────────────────┴──────────────────────────────► _race_info
```

Canonical CE は Research では入力、**Product Assembly 現行鎖では欠落**。

---

## ⑤ Output Contract（Assembly 出力先）

| Consumer | Receives | Path evidence |
|---|---|---|
| **HTTP** | PredictionBundle (+ meta) | `main.py` ← `prediction_adapter.get_with_meta` |
| **GUI** | PredictionBundle | `public/assets/api/prediction.js` ← Functions/HTTP |
| **Conversation** | Bundle via adapter | `conversation/tools.py`, v4 connector |
| **Single** | `prediction_response`（Assembly 中間出力） | `get_prediction` / `predict` — Bundle 前段 |
| **CLI** | `prediction_response` print | `ai_platform/single/cli` |
| **Functions** | Proxied Bundle / catalog projection | `functions/_lib/adapters/predictionAdapter.js` |
| **Challenge** | Stored or PI Bundle（Assembly 過去出力の読取） | `challenge/service.py` `latest_prediction_bundle` |
| **Ops / tests** | Bundle + provenance | collect_c* tests |
| **Research** | Often **bypasses** Assembly → CE direct | signal_lineage, CorePipeline scripts |

### Output notes

- Single/CLI は Bundle ではなく **中間 DTO** を消費しうる → Assembly は二段出力（response → Bundle）。  
- Challenge はライブ Assembly を呼ばず **永続化結果** を読む。  
- Research-CE は境界の外（Canonical 直接）。

---

## Contract boundary summary

| Contract | Layer |
|---|---|
| CorePublicBundle | AI Core Canonical |
| RankingResult / ConfidenceResult | AI Core Compatibility（Assembly 現行入力） |
| prediction_response | Assembly intermediate（Single Product） |
| PredictionBundle | Assembly output / Product Public View |
| HTTP meta provenance | Product envelope（Bundle 外） |
| GUI DOM state | Presentation |

---

*V53 Contract Boundary — research only.*
