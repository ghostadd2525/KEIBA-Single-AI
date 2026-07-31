# V52 — Projection Analysis（CE → PredictionBundle）

**Date:** 2026-07-28  
**Sources:**

- CE producer: `CorePipeline.evaluate` → CorePublicBundle  
- Bundle contract: `contracts/single-prediction-bundle/2.0/PredictionBundle.d.ts`  
- Current Product mapper: `prediction_response_to_bundle`（**not** CE→Bundle）

---

## A. CorePublicBundle field inventory（code）

From `CorePipeline.evaluate` return dict:

| CE field | Type / content |
|---|---|
| `race_id` | str |
| `candidates[]` | CandidateID, Rank, Confidence, HorseNumber, WorldMeta, SubWorldMeta |
| `context` | source path, feature_source, feature_metadata, field_size |
| `world` | str |
| `sub_world` | str |
| `overall_confidence` | float |
| `confidence_factors` | list |
| `meta` | `detect_race_meta` / classifier meta |
| `core_version` | str |
| `explain_payload` | optional (Explain v2 flag) |

---

## B. PredictionBundle field inventory（contract）

| Bundle field | Required by contract shape |
|---|---|
| `schema_version` | `"single-prediction-bundle/2.0"` |
| `race_id` | yes |
| `generated_at`, `model_version`, `core_version`, `product_version` | optional but populated today |
| `status`, `warnings` | optional |
| `race_info` | **required** in interface |
| `evaluation` | status, world, sub_world, **runners** |
| `ai_confidence` | score, band, factors, inputs_ref, … |
| `explain` | meta, reasons, narrative |
| `betting_recommendations` | items, by_bet_type |

Runner fields used by Consumers: `horse_number`, `horse_name`, `model_rank`, `win_prob`, **`mark`**, `mark_rank`, `candidate_id`.

---

## C. Projection class per CE → Bundle

### そのまま投影（direct）

| CE | Bundle target |
|---|---|
| `race_id` | `race_id`（※ public_race_id 写像は別問題） |
| `core_version` | `core_version` |
| `world` | `evaluation.world` |
| `sub_world` | `evaluation.sub_world` |
| `candidates[].HorseNumber` | `runners[].horse_number` |
| `candidates[].CandidateID` | `runners[].horse_name`（現行 Ranking view と同型） |
| `candidates[].Rank` | `runners[].model_rank` |
| `candidates[].Confidence` | `runners[].win_prob`（現行は score を win_prob 欄へ） |
| `overall_confidence` | `ai_confidence.score` |
| `confidence_factors` | `ai_confidence.factors` |
| `context.field_size` | `race_info.field_size`（部分） |

### 変換（transform）

| From | To | Rule evidence |
|---|---|---|
| Rank | `mark` / `mark_rank` | Mapper `_MARK_BY_RANK`（1=honmei…）— **Product rule**, not CE field |
| CandidateID+HorseNumber | `candidate_id` | Mapper `_candidate_id` → `c{NN}` |
| overall | `ai_confidence.band` | Mapper `_band` |
| CE candidates | `evaluation.runners[]` | shape rename |
| CE `explain_payload` | Bundle `explain` | **形状不一致**; 現行は別合成（top3 narrative） |
| public vs core race id | `warnings` / inputs_ref | Mapper identity bridge |

### 削除（drop if Adapter is CE-only and Bundle has no slot / unused）

| CE-only | Why dropped today / in pure Adapter |
|---|---|
| `context.source` / `feature_metadata` | Bundle に正式スロットなし（`feature_source` は拡張として Mapper が別経路で付与） |
| `meta`（detect_race_meta） | Bundle `race_info` ではない; Win5 classifier 用 |
| per-row `WorldMeta` / `SubWorldMeta` | Bundle runners に非存在（race-level world のみ） |
| raw CE structure | frozen CE ≠ Bundle schema |

### 追加生成（must invent — **not in CE**）

| Bundle field | Actual source today | In CE? |
|---|---|---|
| `schema_version` | constant | No |
| `race_info.date/venue/race_no/distance/surface/course/class_label/grade/post_time/...` | `get_race` + catalog `race_meta` | **No**（field_size のみ context に部分） |
| `race_info.date_label/date_full/bg` | UI catalog | **No** |
| `product_version` | Product response | **No** |
| `generated_at` | clock / response | **No** |
| `betting_recommendations.*` | `build_bets` / slips | **No** |
| `evaluation.status` | Product constant `"ok"` | **No** |
| `ai_confidence.inputs_ref` / notes / computed_at | Mapper synthesis | **No** |
| `explain.reasons` / `narrative` | Mapper from top runners + factors | **Synthesized**（CE explain_payload と非同一） |
| Mock/list empty structures | domain.js catalog | **No** |

---

## D. One-way projection test

### Claim under test

> Projection is a complete one-way function CE → Bundle, no reverse needed.

### Result: **FAIL for full contract; PASS for ranking/world/confidence subset**

| Test | Result | Evidence |
|---|---|---|
| Inject CE → produce valid Bundle type | **Fail** | Missing required `race_info` contents + `betting_recommendations` |
| Inject CE → produce GUI-usable Bundle | **Fail** | GUI uses mark (synth OK) but also race_info / bets |
| Inject CE → recover world on Bundle | **Pass (one-way)** | CE has world; current Mapper drops it — Adapter **could** pass through |
| Bundle → reconstruct CE | **Fail** | Cannot recover `meta`, `context`, true CE confidence structure, explain_payload from Bundle |
| Consumer needs reverse CE←Bundle | **Not observed** | Consumers read Bundle; problem is forward info deficit |

**逆変換が必要になる箇所:** 契約充足の意味では **無し**。不足はすべて **正向の欠落と追加生成依存**。

---

## E. Hidden dependency summary

### Bundle-only information

1. Race card / schedule identity (`race_info`)  
2. Betting slips / recommendations  
3. Product marks（規則は Rank 依存だが **定義は Product**）  
4. Schema / product versioning & timestamps  
5. Mock & catalog projection payloads  

### CE-only information

1. `context` / feature load provenance  
2. Classifier `meta`  
3. Per-candidate world labels  
4. Optional `explain_payload`  
5. Canonical world retained（今日の Bundle では None）

### Overlap (true shared semantics)

- race_id, ranking order, per-horse confidence-like score, race-level world/sub_world, core_version, overall confidence

---

## F. Implication for “View Adapter”

A function `f(CorePublicBundle) -> PredictionBundle` that:

1. only reads CE, and  
2. satisfies `PredictionBundle` TypeScript interface **and** current Consumer field usage  

**does not exist in the current architecture and cannot be total** without inventing Bundle-only fields from outside CE.

Therefore pure View Adapter is at most a **partial projector**, not a full Consumer compatibility layer.

---

*V52 Projection Analysis — research only.*
