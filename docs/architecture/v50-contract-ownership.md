# Version50 — Contract Ownership

**Date:** 2026-07-28  
**Parent ADR:** `v50-canonical-contract-adr.md`  
**Type:** Design only

## ② Contract Owner / Producer / Consumer

| ID | Contract | Owner | Producer | Consumer | ADR Role |
|---|---|---|---|---|---|
| C1 | CorePublicBundle | **AI Core** | `CorePipeline.evaluate` via `evaluate_candidates` | Research tools; **should be** all Prediction truth consumers | **CANONICAL** |
| C2 | RankingResult | AI Core Facade | `predict_ranking` | Single `predict` | Compatibility Projection |
| C3 | ConfidenceResult | AI Core Facade | `predict_confidence` | Single `predict` | Compatibility Projection |
| C4 | resolve_core bundle | AI Core Facade | `resolve_core` | Research / legacy S-01 | Compatibility Projection（World 保持） |
| C5 | prediction_response | **Single Product** | `single.models.prediction_response` | Mapper | Product Intermediate |
| C6 | PredictionBundle 2.0 | **Expect Product / domains** | Mapper / Mock / catalog | HTTP API, GUI, Challenge, Ops | Product Public View |
| C7 | HTTP envelope meta | Expect Adapter | `provenance_item` | API clients（運用） | Envelope（Bundle 外） |
| C8 | Mock Bundle | Expect mocks | fixtures / template | Adapter fallback, tests | Fallback View |
| C9 | explain_payload | AI Core explain | `build_explain_payload` | CE consumers when Flag ON | Explain View |
| C10 | Bundle explain | Expect Mapper | `prediction_response_to_bundle` | GUI explain UI | Explain View（別系統） |

---

## Ownership Rules（設計）

1. **Canonical facts**（Rank, Confidence, World, SubWorld, meta）の Owner は **AI Core** のみ。  
2. Product / GUI / API は Canonical の **Consumer** であり、事実の再定義権限を持たない。  
3. Mapper / Mock は **Producer of Views** であって Canonical Producer ではない。  
4. 同一フィールド（例: `world`）について Product View の値が Canonical と矛盾する場合、**Canonical が正しい**（設計）。現行実装の `None` は View 欠陥であり Core 真理ではない。

---

## ④ Duplication Map

### Contract 重複

| 重複セット | 問題 |
|---|---|
| C1 vs C6 | 両方とも「予測の正本」として扱われうる → ADR で C1 のみ Canonical |
| C1 vs C2/C3 | Facade が Canonical と Compatibility を併記 → C2/C3 を非正本と明示 |
| C6 vs C8 | 同スキーマ名・別生成源 → Mock を Fallback View に格下げ |
| C9 vs C10 | Explain 二重 → どちらも非 Canonical（説明 View） |

### 責務重複

| 責務 | 重複箇所 | ADR 整理 |
|---|---|---|
| 順位の正本 | C1 行 Rank / C2 ranking / C6 runners.model_rank | 正本 = C1；他は投影 |
| 信頼度の正本 | C1 overall+行 / C3 / C6 ai_confidence | 正本 = C1 |
| World の正本 | C1 world / C6 evaluation.world=None | 正本 = C1；C6 None は非権威 |
| 説明文 | C9 / C10 | 正本外；将来は C1 付帯を優先する設計指針 |

### DTO 重複

| 概念 | DTO 名の乱立 |
|---|---|
| 馬行 | CE candidate row / ranking row / Bundle runner |
| レース評価封筒 | CorePublicBundle / prediction_response / PredictionBundle |
| 信頼度 | confidence dict ×3 形 |

ADR 後の設計指針: **新しい「第4の予測 DTO」を増やさない**。View が必要なら C1 からの明示投影として文書化する。

---

## Producer/Consumer Matrix（Canonical 視点）

```text
                    PRODUCER                CONSUMER
AI Core      [CorePipeline] ----C1----►  Product Mapper (should)
                              ----C1----►  Research / resolve_core
                              ----C2----►  Single predict (today)
Product      [Mapper/Mock]  ----C6----►  HTTP / GUI
                              (must not override C1 facts)
```
