# V53 — Prediction Assembly Boundary Audit

**Date:** 2026-07-28  
**Scope:** Research / Architecture Audit only  
**Question:** Is **Prediction Assembly** the correct responsibility boundary between AI Core and Product?  
**Locks:** Prediction / PE / CE / AI / CorePublicBundle / PredictionBundle / World / Trigger / Signal / Production — **変更・実装禁止**

**Inputs:** ADR-050 (V50), Adapter feasibility (V52), live modules below

---

## Definition under audit

**Prediction Assembly**（本監査の作業定義 — 現行に同名モジュールは無い）:

> AI Core の Canonical / Compatibility 出力と、RaceData / Catalog / BetBuilder 等の **非 Core ソース** を合成し、Product Public DTO（主に `PredictionBundle`）および中間 `prediction_response` を生成する責務帯。

**現行の実体（分散）:**

| Step | Module | Role |
|---|---|---|
| 1 | `ai_platform.single.prediction.predict` | Ranking/Confidence view + Bet plan/build |
| 2 | `single.models.prediction_response` | Product intermediate envelope |
| 3 | `prediction_response_to_bundle` | Expect Bundle DTO + race_info + marks + explain |
| 4 | `diagnose_inference` / `prediction_adapter` | identity, Real/Mock, catalog meta, HTTP 供給 |
| 5 | Mock / `catalog_to_prediction_bundle` | Core 非経由の並列 Assembly |

---

## Verdict (summary)

**Assembly は AI Core と Product の正しい境界“種”である。**  
ただし現行実装は単一境界モジュールではなく、**一部責務混在**がある。

**Governance: B**

→ 詳細: `v53-assembly-responsibility.md`, `v53-contract-boundary.md`, `v53-governance.md`

根拠（硬）:

1. Facade が Product-stage 禁止（Core に Assembly を置けない）  
2. V52: Bundle は CE 単純 View ではない（RaceData + Bet 必須）  
3. BetBuilder が CE 非参照・Plan のみ入力（Product 側合成）  
4. Presentation（GUI）は Bundle Consumer であり合成しない  
5. 一方で Mapper が `world=None`（Core 所有事実の破壊）、Canonical CE 未入力、Mock 並列など **混在**

---

## ①–⑦ Index

| # | Topic | Doc |
|---|---|---|
| ① Assembly Responsibility | 持つべき責務 | `v53-assembly-responsibility.md` |
| ② Ownership | Rank…ChallengeMark | 同上 |
| ③ Boundary Validation | 層図 | `v53-contract-boundary.md` |
| ④ Input Contract | 入力元一覧 | 同上 |
| ⑤ Output Contract | 出力先 | 同上 |
| ⑥ Responsibility Leak | 漏洩監査 | `v53-assembly-responsibility.md` + governance |
| ⑦ Governance | A/B/C | `v53-governance.md` |

---

## Boundary diagram (compact)

```text
[ AI Core ]
  evaluate_candidates → CorePublicBundle   ← Canonical (ADR-050)
  predict_ranking / predict_confidence     ← Compatibility views
  (Rank, Confidence, World, SubWorld, meta)
           │
           │  MUST NOT: race_info invent / bets / Bundle schema / marks product rules
           ▼
[ Prediction Assembly ]  ← boundary under audit (conceptual)
  inputs: Core views|CE, RaceData, Catalog, BetStrategy/Builder, identity, Mock
  duties: DTO assemble, RaceInfo attach, Bet integrate, marks overlay, Product View
  outputs: prediction_response, PredictionBundle (+ provenance meta)
           │
           ▼
[ Product surfaces ]
  HTTP Adapter, Single API/CLI, Conversation, Challenge fetch, Functions proxy
           │
           ▼
[ Presentation ]
  GUI bind / ContractGuard  （合成しない・表示する）
```

---

## Decision Gate（参照）

```
【Decision】※分析のみ
Action Type: Prediction Assembly Boundary Audit
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: Treating scattered Mapper+Single+Adapter as “done Assembly” without fixing ownership leaks
Expected Next Action: Optional Assembly charter / ownership freeze (design) — no code
```

---

*V53 Boundary Audit — research only. No code changes.*
