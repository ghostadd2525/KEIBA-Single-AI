# Version49 — Prediction Contract Lineage

**Date:** 2026-07-28  
**Type:** Audit only

## ② Contract Lineage（呼び出し経路）

### A. Real path（`AI_ENGINE=real`）

```text
HTTP GET /v1/predictions/{public_race_id}
  └─ PredictionAdapter.get_with_meta
       └─ RealAiPredictionSource._infer
            └─ diagnose_inference(public_race_id)
                 ├─ resolve_identity / resolve_core_race_id
                 ├─ FeatureLoader.classify_unavailable
                 └─ run_single_prediction_detailed(core_race_id)
                      └─ ai_platform.single.api.get_prediction
                           └─ single.prediction.predict
                                ├─ facade.predict_ranking(core_id)     ← CE 薄投影
                                │    └─ evaluate_candidates            ← 内部のみ
                                │         └─ CorePipeline.evaluate
                                │              （world は CE に在るが predict_ranking で落とす）
                                ├─ facade.predict_confidence(core_id)
                                ├─ build_bet_plan / build_bets
                                └─ models.prediction_response(...)   ← Single DTO
                 └─ prediction_response_to_bundle(...)              ← Expect DTO
                      └─ domains.normalize_prediction_bundle
                           └─ HTTP ok(bundle, provenance_meta)
```

### B. Mock / Fallback path

```text
HTTP / diagnose failure
  └─ MockPredictionSource / _mock_one
       ├─ public/data/mocks/bundle-*.json
       ├─ catalog_to_prediction_bundle(template)
       └─ normalize_prediction_bundle
            └─ PredictionBundle（実推論・CE 非経由）
```

### C. Contracts on the lineage（層別）

| 層 | Contract / DTO | World? |
|---|---|---|
| CorePipeline | CorePublicBundle（`evaluate_candidates`） | **Yes**（保持） |
| Facade | `predict_ranking` RankingResult | **No key** |
| Facade | `predict_confidence` | No |
| Single | `prediction_response`（S-04） | **No field** |
| Expect Public | `PredictionBundle` 2.0 | **`evaluation.world=None`** |
| HTTP envelope | provenance meta（Bundle 外） | N/A |
| Mock | fixture Bundle | fixture 依存（Real 契約と別源） |

---

## ④ Canonical Contract Proof

### Claim 1 — 公開正本は PredictionBundle

根拠:

- `main.py` L2: 「PredictionBundle を共通契約とする」
- `domains.BUNDLE_SCHEMA = "single-prediction-bundle/2.0"`
- `prediction_adapter.py` L4: 「契約: single-prediction-bundle/2.0」
- HTTP 200 body の data = Bundle

### Claim 2 — 生成は evaluate_candidates を公開契約にしない

根拠:

- `single.prediction.predict` は `predict_ranking` / `predict_confidence` のみ import（`evaluate_candidates` なし）
- `predict_ranking` 戻りに `world` キー無し（`core_facade.py` L79–84）
- Mapper は `prediction_response` のみ受け、CE Bundle を読まない

### Claim 3 — evaluate_candidates は内部副作用としてのみ存在

根拠:

- `predict_ranking` → `evaluate_candidates` → CE 全文生成後に **投影で削減**
- CE の `world` は RankingResult に写されない（情報はここで到達不能化）

### Verdict table

| 候補 | Prediction 公開正本か | 役割 |
|---|---|---|
| `evaluate_candidates` | **No** | AI Core CE Canonical（Prediction 非公開） |
| `predict_ranking` | **No（公開 DTO ではない）** | Real 生成の **入力ビュー** |
| `prediction_response` | **No** | Single 中間 |
| **`PredictionBundle`** | **Yes** | Expect / HTTP 公開正本 |

---

## ⑤ Duplicate Contract Audit

| Contract | 所有者 | 並存理由（コード） | Prediction との関係 |
|---|---|---|---|
| CorePublicBundle | AI Core facade | Canonical CE | Prediction 主経路 **未使用** |
| RankingResult (`predict_ranking`) | Facade 互換ビュー | “Compatibility views are projections from CE” | Real 経路が使用 |
| prediction_response | Single models S-04 | Product 応答 | Mapper 入力 |
| PredictionBundle 2.0 | Expect domains | 「契約スキーマは変更しない」 | **HTTP 正本** |
| Mock fixture Bundle | mocks/ | AI_ENGINE=mock / fallback | Real と **別生成源** |
| HTTP envelope meta | Adapter provenance | Bundle 契約外と明記 | 併送 |

**二重化（分裂）の定義該当:**

1. AI Core Canonical（CE+World）≠ Expect Public（Bundle, world=None）  
2. Real 生成系 ≠ Mock 生成系  
3. Single 中間 DTO ≠ Expect Bundle  
4. Facade が “Canonical = evaluate_candidates” と宣言しつつ Prediction はそれを公開しない  

→ **Prediction 契約は分裂している**（単一正本に収束していない）。
