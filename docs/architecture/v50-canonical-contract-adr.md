# ADR-050 — Canonical Prediction Contract

**Status:** Accepted (design intent only — **not implemented**)  
**Date:** 2026-07-28  
**Deciders:** Architecture / Research (V47–V49 evidence)  
**Scope:** Design judgment only. No code, Production, Prediction, PE, CE, World, or Mapper changes in this phase.

---

## Context

V49 proved Prediction contracts are **structurally split**:

| Layer | Contract | World |
|---|---|---|
| AI Core Facade (declared Canonical) | `evaluate_candidates` → CorePublicBundle | retained |
| Compatibility view | `predict_ranking` RankingResult | dropped |
| Single Product DTO | `prediction_response` | absent |
| Expect HTTP Public | `PredictionBundle` 2.0 | hardcoded `None` |
| Mock | fixture Bundle | separate source |

Facade already states:

> Canonical public boundary: `evaluate_candidates(race_id) -> CorePublicBundle | None`  
> Compatibility views are projections from CE.

Yet Expect HTTP treats `PredictionBundle` as the common contract (`main.py`), while the Real path never publishes CE. This violates single-truth.

Upstream design (V32/V36/V43–V44): World is win-path classification at AI Core. A Prediction contract that nulls World cannot be AI Core truth.

---

## ① Contract Inventory

| ID | Contract / DTO | Schema / Entry |
|---|---|---|
| C1 | **CorePublicBundle** | `evaluate_candidates` |
| C2 | RankingResult | `predict_ranking` |
| C3 | ConfidenceResult | `predict_confidence` |
| C4 | resolve_core bundle | `resolve_core`（C1 投影） |
| C5 | prediction_response | Single `models.prediction_response` / `get_prediction` |
| C6 | **PredictionBundle** | `single-prediction-bundle/2.0` / HTTP `/v1/predictions` |
| C7 | HTTP envelope meta | Adapter provenance（Bundle 外） |
| C8 | Mock / fixture Bundle | `public/data/mocks`, catalog template |
| C9 | explain_payload | Core explain v2（CE 付帯・Flag） |
| C10 | Single Bundle explain | Mapper 独自 explain |

---

## Decision

### Canonical Prediction Contract（唯一の正本）

# **C1 — CorePublicBundle via `evaluate_candidates`**

**Name:** Canonical Prediction Contract (AI Core)  
**Entry:** `evaluate_candidates(race_id) -> CorePublicBundle | None`  
**Owner:** AI Core (`ai_platform.core.facade` / `candidate_evaluation`)

### Required contents（設計上の必須集合）

| Field group | Required in Canonical | Notes |
|---|---|---|
| Identity | `race_id` | |
| Rows | `CandidateID`, `Rank`, `Confidence` | existing facade Required CE fields |
| Win-path labels | **`world`, `sub_world`** | design-required for Canonical Prediction（現行 Bundle 行 Meta と整合） |
| Race meta | **`meta`** | detect_race_meta 由来 |
| Confidence summary | `overall_confidence`, `confidence_factors` | |
| Provenance | `context.feature_source`, `core_version` | |
| Explain | `explain_payload` optional | Flag 付き付帯。正本の必須ではない |

### Non-canonical（正本ではない）

| Contract | Classification after ADR |
|---|---|
| C2 RankingResult | **Compatibility Projection** — must not be treated as truth |
| C3 ConfidenceResult | Compatibility Projection |
| C5 prediction_response | **Product Intermediate DTO** |
| C6 PredictionBundle | **Product Public View**（HTTP/UI）— projection of Canonical, not Canonical |
| C8 Mock Bundle | **Fallback / Test View** — must not redefine Core truth |
| C9/C10 Explain | **Explain Views** — attached or rebuilt; not ranking truth |

### Hard rules（設計）

1. **Single Truth:** Prediction の事実（順位・信頼度・World・meta）の正本は CorePublicBundle のみ。  
2. **Projections may lose fields only if loss is explicit and non-authoritative.** Lossy views must not be cited as Core truth.  
3. **Product PredictionBundle must not invent or null Core facts as if authoritative.** (`world=None` as silent truth is forbidden at design level.)  
4. **Mock must be labeled non-canonical.** Same HTTP shape ≠ same contract authority.  
5. **No implementation in V50.** Binding Product/Mapper to Canonical is a future approved stage.

---

## ③ Canonical Candidate Comparison

| Candidate | Completeness | World retained | Already declared Canonical? | Aligns V43–V44? | Single-truth fit |
|---|---|---|---|---|---|
| C1 CorePublicBundle | High | Yes | **Yes**（facade） | Yes | **Best** |
| C2 predict_ranking | Low | No | No（compatibility） | No | Reject |
| C5 prediction_response | Medium− | No | No | No | Reject |
| C6 PredictionBundle | Product-shaped | **No（None）** | Declared by HTTP/Expect only | No | Reject as Core Canonical |
| New DTO | N/A | TBD | No | Possible | Unnecessary — C1 exists |

**Rejected alternatives**

- **Elevate PredictionBundle to Core Canonical:** Would canonize `world=None` and contradict World Semantic Contract (V43) and facade declaration.  
- **Elevate predict_ranking:** Intentionally lossy; facade calls it compatibility view.  
- **Create parallel Canonical:** Would worsen duplication (V49 C).

---

## Consequences

### Positive

- Restores single authority already named in AI Core facade.  
- Aligns Prediction truth with CE World retention (V48) and World-as-win-path (V43–V44).  
- Clarifies PredictionBundle as Product View, ending “HTTP Bundle = Core truth” ambiguity.

### Negative / Follow-on（実装はしない・設計上の含意のみ）

- Product path today violates Canonical rules (V49). Future migration must re-lineage HTTP → Canonical → View.  
- PredictionBundle schema evolution (if any) is out of V50; until then Views remain lossy and **non-authoritative**.

### Out of scope

- Code, Mapper, HTTP, Threshold, Trigger, Signal changes  
- Win5 optimizer contract  
- PE ranking formula changes  

---

## References

- V47 PE Responsibility / V48 CE Contract / V49 Prediction Contract Audit  
- `ai_platform/core/facade/core_facade.py` Canonical public boundary  
- `domains.BUNDLE_SCHEMA` / `prediction_adapter.py` Product contract notes  
- V32/V36 World = win-path; V43 Semantic Contract; V44 Trigger Spec  

---

## Document Index

| Doc | Content |
|---|---|
| `v50-canonical-contract-adr.md` | 本 ADR |
| `v50-contract-ownership.md` | Owner / Producer / Consumer |
| `v50-contract-boundary.md` | AI Core / Product / GUI / API / Explain |
| `v50-governance.md` | 統治 |
