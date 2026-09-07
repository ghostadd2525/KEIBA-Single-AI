# V54 — Module Map（ADR → Code）

**Date:** 2026-07-28  
**Status:** Blueprint mapping only — **no code changes**  
**Parent:** `v54-blueprint.md`

---

## How to read

| Column | Meaning |
|---|---|
| ADR | Authority document |
| Module / Path | Where a future approved Stage would land |
| Reflects | What the ADR requires of that module |
| Track | W = World/Trigger, P = Prediction/Assembly |

---

## V43 — World Semantic Contract

| Module / Path | Reflects | Track |
|---|---|---|
| Design docs only（現行コード非変更が正） | Purpose / Winning / Required / Forbidden per World | W |
| Research: `DESIGN_SHARE` / world catalogs | Design mix reference | W |
| **Not** `TRIGGER_RULES` as semantic authority | Trigger ≠ Semantic owner（V42/V43） | W |

実装時: Semantic は Spec 正本のまま。コードは V44/V46 経由でのみ触る。

---

## V44 — World Trigger Specification

| Module / Path | Reflects | Track |
|---|---|---|
| Spec docs: Logic Form / Must / Aux / Forbidden | Positive Match; no DEFAULT-as-core | W |
| Future: Shadow evaluator（Research） | Dual-Eval vs Legacy | W |
| Future: Production Trigger | `demo_ticket_optimizer_core.classify_world_line_type` | W |
| Future: Research mirror `TRIGGER_RULES` | Must stay aligned with Spec after S6/S7 | W |
| `ai_platform.core.world.WorldClassifier` | Consumes classifier; **downstream of Trigger truth** | W→P |
| Signal suppliers（existing helpers） | Must readiness targets（V46 S2） | W |

**Forbidden in V44 alone:** numeric thresholds in Spec; silent Production rewrite.

---

## V46 — Migration Plan（Stage → Module）

| V46 Stage | Primary modules | Mode |
|---|---|---|
| S0 | Docs / governance lock | Freeze |
| S1 | Research Shadow Dual-Eval jobs（new or existing research scripts） | Shadow |
| S2 | Readiness ledger vs `get_context_top_gap` 等既存関数 | Shadow |
| S3 | New Polarity ADR doc（not code） | Design |
| S4–S5 | Shadow profiles / compliance reports | Shadow |
| S6 | `classify_world_line_type` **behind flag**; Legacy path retained | Soft Dual |
| S7 | Remove core DEFAULT / R8 residual path | Cutover |
| S8 | SubWorld / Role / Pool / optional PE binding — **separate** | Later |

| Do not touch in V46 S0–S7 | Reason |
|---|---|
| `prediction_response_to_bundle` | Track P |
| HTTP `/v1/predictions` contract kill | Track P |
| PE Feature/Scorer/Ranker | Downstream Isolation |
| GUI ContractGuard schema replace | Track P |

---

## V50 — ADR-050 Canonical Contract

| Module / Path | Reflects | Track |
|---|---|---|
| `ai_platform/core/facade/core_facade.py` | `evaluate_candidates` = Canonical entry | P |
| `ai_platform/core/candidate_evaluation` | CorePublicBundle producer | P |
| `predict_ranking` / `predict_confidence` | Compatibility only — not truth | P |
| `single/prediction/__init__.py` | Must stop treating ranking view as Canonical | P |
| `single_prediction_mapper.py` | Must not null Core facts as authority | P |
| `prediction_adapter.py` / `main.py` | Bundle = Product View; Mock labeled | P |
| Contracts `PredictionBundle.d.ts` | Remains Product Public View schema | P |
| Research CE scripts | Already Canonical-aligned | P |

---

## V53 — Prediction Assembly

| Module / Path | Assembly role | Track |
|---|---|---|
| `ai_platform.single.prediction.predict` | Orchestrate Core views/CE + Bet | P |
| `ai_platform.single.bet_strategy` / `bet_builder` | BettingRecommendations owner path | P |
| `ai_platform.single.models.prediction_response` | Intermediate Product DTO | P |
| `single_prediction_mapper.prediction_response_to_bundle` | Bundle assemble + RaceInfo + marks | P |
| `single_prediction_mapper._race_info` + `race_data.get_race` | RaceInfo attach | P |
| `prediction_adapter` (+ Mock/catalog) | Identity, fallback, list meta | P |
| `domains` / `functions/_lib/domain.js` | Normalize / catalog projection | P |
| GUI / Conversation / Challenge / Functions | **Consumers only** | P |

**Assembly Input Contract（freeze）**

| Input | Module |
|---|---|
| Canonical CE（target） | `evaluate_candidates` |
| Compatibility views（legacy interim） | `predict_ranking` / `predict_confidence` |
| RaceData | `get_race` / catalog race_meta |
| Bet | `build_bet_plan` / `build_bets` |
| Catalog / Mock | `data.load_races` / fixtures |
| Identity | `resolve_identity` / `resolve_core_race_id` |

---

## Cross-cutting map（who changes when）

| Module | Track W | Track P | Notes |
|---|---|---|---|
| `demo_ticket_optimizer_core` Trigger | **Primary** | No（S0–S7） | S8 may bind |
| `WorldClassifier` | Indirect（meta/world source） | Reads CE world | Align after W Soft |
| Facade `evaluate_candidates` | No | **Primary consumer path** | Already Canonical API |
| Mapper / Adapter / HTTP | No | **Primary** | Assembly |
| GUI / Functions | No | Consumer Soft | After Dual world projection |
| PE Scorer/Ranker | No | No | Out of Blueprint mandatory |
| Win5 ticket optimizer (non-trigger) | S8 only | No | Isolated |

---

## Module ownership reminder（from V53）

| Fact | Owner module family |
|---|---|
| Rank / Confidence / World / Meta | AI Core |
| RaceInfo / Catalog | RaceData / Catalog |
| BettingRecommendations | Single Bet |
| ChallengeMark | Assembly overlay |
| PredictionBundle shape | Product Assembly output |

---

*V54 Module Map — blueprint only.*
