# V51 — ADR-050 Impact Analysis

**Date:** 2026-07-28  
**Scope:** Research / Architecture Audit only  
**Locks:** Prediction / PE / CE / AI / World / Trigger / Signal / Production — **変更禁止・実装禁止**  
**Input:** ADR-050 Accepted (design intent) — Canonical = `CorePublicBundle` via `evaluate_candidates`

---

## 目的

ADR-050 を**実装した場合**の影響範囲を完全可視化する。  
本フェーズは改善・実装を行わない。

---

## ① Producer Analysis

### Canonical Producer（ADR-050 が正とする生成元）

| Producer | Path | Output | Notes |
|---|---|---|---|
| **P1 CorePipeline.evaluate** | `ai_platform/core/candidate_evaluation/__init__.py` | CorePublicBundle | Feature→Score→Rank→meta→Confidence→World→Projector |
| **P2 evaluate_candidates** | `ai_platform/core/facade/core_facade.py` | CorePublicBundle \| None | Declared Canonical public boundary |
| **P3 resolve_core** | same facade | CorePublicBundle projection | = evaluate_candidates（現状） |
| **P4 CorePipeline（overlay）** | `platform/core-overlay/.../candidate_evaluation` | CorePublicBundle | win5-ai overlay 経路 |
| **P5 PI CorePipeline** | `pi-keibanet-api/pi_keibanet/service.py` | Core evaluate | PI 側 loader 付き |

### Compatibility Producers（Canonical ではない投影）

| Producer | Path | Output | Relation to C1 |
|---|---|---|---|
| **P6 predict_ranking** | facade | RankingResult | CE から world 等を除去 |
| **P7 predict_confidence** | facade | ConfidenceResult | CE 投影 |
| **P8 Single.predict** | `ai_platform/single/prediction` | prediction_response | P6+P7 合成 |
| **P9 prediction_response_to_bundle** | `single_prediction_mapper.py` | PredictionBundle | Product View; world=None |
| **P10 prediction_adapter** | win5-ai adapters | PredictionBundle | Real/Mock 切替 |
| **P11 Mock fixtures** | mock catalog / domain.js | PredictionBundle | CE 非経由 |

### Research Producers（直接 CE / Pipeline）

| Producer | Path |
|---|---|
| signal_lineage_audit | evaluate_candidates + resolve_core + predict_ranking 比較 |
| world_signal_instrumentation | CorePipeline() |
| chaos_signal_trace | CorePipeline() |
| wic_shadow_ab | CorePipeline() |
| difficulty_signal_audit | CorePipeline() |

### 非 Producer（CorePublicBundle を生成しない）

| Module | Evidence |
|---|---|
| FeatureExtractor / Scorer / Ranker | PE 内部; Bundle を返さない |
| WorldAssigner / WorldConfidence | CE 内部 stage; Bundle 組み立ては Pipeline |
| demo_ticket_optimizer_core | Win5 Trigger; evaluate_candidates 非呼び出し |
| GUI / Functions | Bundle の Consumer / 正規化のみ |

---

## ② Consumer Analysis（要約）

詳細は `v51-consumer-matrix.md`。

| Domain | Primary contract today | Touches CE? |
|---|---|---|
| Prediction HTTP | PredictionBundle | No（Adapter→Mapper） |
| Single API/CLI | prediction_response | Via predict_ranking only |
| Win5 Optimizer | 独自スコア/Trigger | No |
| GUI | PredictionBundle | No |
| Explain / Conversation | PredictionBundle adapter | No |
| API (win5-ai / Functions) | PredictionBundle | No |
| CLI (single_ai) | get_prediction | No CE |
| Research | Mixed; many use CE directly | Yes（一部） |
| Challenge | Stored PredictionBundle | No |
| Analytics core | predict_ranking/confidence | Compatibility views |
| Evaluation CLI | get_prediction | No CE |

---

## ③ Impact Matrix（要約）

| Consumer | Classification |
|---|---|
| Prediction HTTP `/v1/predictions` | **変更が必要** |
| prediction_adapter / mapper | **変更が必要** |
| GUI prediction.js / ContractGuard | **変更が必要** |
| Functions predictionAdapter / domain.js | **変更が必要** |
| Conversation / tools | **変更が必要**（間接） |
| Single predict / CLI / Eval | **変更が必要**（入口切替） |
| Challenge (stored bundle) | **変更が必要**（読取スキーマ） |
| Research (CE direct) | **変更不要**〜軽微 |
| Win5 Optimizer | **影響なし** |
| PE Feature/Scorer/Ranker | **影響なし** |
| WorldAssigner 内部 | **影響なし**（既に CE 内） |
| Mock fixtures | **変更が必要**（契約整合） |

---

## ④ Compatibility（要約）

現行 `PredictionBundle`（`single-prediction-bundle/2.0`）と `CorePublicBundle` は **スキーマ非互換**。

| Aspect | PredictionBundle | CorePublicBundle |
|---|---|---|
| Schema id | single-prediction-bundle/2.0 | CorePublicBundle（frozen CE） |
| World | evaluation.world = None（hardcoded） | world / sub_world 保持 |
| Candidates | Product ranking + marks | CandidateID / Rank / Score / … |
| Confidence | ai_confidence Product shape | confidence ブロック |
| race_info | 豊富な UI メタ | Core 最小 |
| Producer | Mapper / Mock | evaluate_candidates |

**互換戦略（設計のみ・未実装）:**  
ADR-050 Decision D4 — PredictionBundle を **Product Public View** として残し、Canonical は CE。実装時は View Adapter 必須。破壊的置換は不可。

詳細: `v51-migration-impact.md`

---

## ⑤ Migration Risk（要約）

| Risk | Level | Area |
|---|---|---|
| Public HTTP / GUI ContractGuard 破壊 | **High** | Prediction / GUI / Functions |
| Mapper world=None 除去と View 再設計 | **High** | Mapper / Contract |
| Dual-contract 期間の二重真実 | **Medium** | API meta / docs |
| Conversation / Challenge / Explain | **Medium** | Product surfaces |
| Single CLI / Eval 入口 | **Medium** | Platform Single |
| Research CE 利用者 | **Low** | 既に Canonical 寄り |
| Win5 Optimizer / PE 内部 | **Low** | 非依存 |
| Production 即時 cutover | **High**（実施する場合） | 本フェーズは禁止 |

---

## ⑥ Rollback Point（要約）

| Boundary | Rollback 手段 |
|---|---|
| R0 ADR only | 現状 — 実装なし（本フェーズ） |
| R1 Dual-publish flag | Canonical CE 併記 + Bundle 維持 |
| R2 View Adapter | Bundle 生成を CE→View に変更; 旧 Mapper に戻せる |
| R3 Client ContractGuard | 旧 schema 検証に戻す |
| R4 Hard cutover | 不可逆に近い; Bundle 廃止は最終段のみ |

詳細: `v51-migration-impact.md`

---

## ⑦ Governance

**判定: C（広範囲）**

根拠: Canonical 切替は HTTP・GUI・Functions・Conversation・Single・Mapper・Mock・契約文書に波及。  
PE/Win5 内部は非対象でも、**Product Public 面が広い**。

→ `v51-governance.md`

---

## Diff Summary vs Pre-ADR

| Before (V49) | After ADR-050 (intent) |
|---|---|
| PredictionBundle = 事実上の公開契約 | CorePublicBundle = Canonical |
| predict_ranking = Real 入口 | evaluate_candidates = Real 入口 |
| world=None = 契約結果 | world=None = View defect |
| 二重契約未裁定 | 裁定済（未実装） |

---

## Expected Next Action（実装ではない）

1. Migration design（Shadow / Dual-publish / View Adapter）— 別フェーズ  
2. Client Contract impact inventory（GUI Guard 詳細）  
3. **実装は Decision Gate 通過後のみ**

---

*V51 Impact Analysis — research only. No code changes.*
