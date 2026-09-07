# Version50 — Contract Boundary

**Date:** 2026-07-28  
**Parent ADR:** `v50-canonical-contract-adr.md`  
**Type:** Design only

## ⑤ Boundary Definitions

### AI Core

| Owns | Does not own |
|---|---|
| Canonical Prediction Contract = **CorePublicBundle** | Expect HTTP envelope branding |
| `evaluate_candidates` entry | GUI layout |
| Rank / Confidence / World / SubWorld / meta truth | Ticket / Pool / Purchase |
| Compatibility projections（C2/C3/C4）の **定義** | Product が投影を正本扱いすること |

### Product（Single + Expect Adapter）

| Owns | Does not own |
|---|---|
| Product Intermediate DTO（C5） | Core 事実の再定義 |
| Product Public View（C6 PredictionBundle）の **形** | Canonical からのサイレント事実削除を「仕様」と呼ぶこと |
| Mapper / Mock fallback UX | AI Core 内部 Scorer 式 |

### API（HTTP `/v1/predictions`）

| Owns | Does not own |
|---|---|
| Transport of Product View + envelope meta | Choosing a second Canonical |
| Auth / listing filters | World 真理 |

設計規則: API が返す Bundle は **View**。権威ある予測事実が必要なら Canonical（C1）を読むか、View が C1 の明示投影であることを文書で保証する（実装は将来）。

### GUI

| Owns | Does not own |
|---|---|
| Presentation of Product View | Inventing World when Bundle says None |
| UX copy | Core 契約変更 |

### Explain

| Owns | Does not own |
|---|---|
| Narrative / reasons views（C9/C10） | Overriding Rank/World truth |
| Flagged Core explain_payload attachment | Replacing Canonical |

設計規則: Explain は Canonical の **注釈**であり、別予測契約ではない。

---

## Boundary Diagram

```text
┌─────────────────────────────────────────────────────────┐
│ AI CORE                                                 │
│  Canonical Prediction Contract = CorePublicBundle (C1)  │
│  Entry: evaluate_candidates                             │
│  Contains: Rank, Confidence, World, SubWorld, meta      │
│       │                                                 │
│       ├── Compatibility Projections (C2/C3/C4)          │
│       └── optional explain_payload (C9)                 │
└───────────────────────┬─────────────────────────────────┘
                        │ (design: authoritative facts)
                        ▼
┌─────────────────────────────────────────────────────────┐
│ PRODUCT                                                 │
│  Intermediate: prediction_response (C5)                 │
│  Public View: PredictionBundle 2.0 (C6)                 │
│  Fallback View: Mock (C8)                               │
│  Mapper explain (C10)                                   │
└───────────────────────┬─────────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
        API           GUI         Ops/Challenge
   (/v1/predictions)  (display)   (read View)
```

---

## Current vs ADR Boundary（事実対比）

| 境界 | 現行実装（V49） | ADR-050 設計 |
|---|---|---|
| Core Canonical | 宣言あり、Prediction 未使用 | **唯一の正本** |
| Product Bundle | HTTP 共通契約として運用 | **Public View**（非正本） |
| world=None | 公開結果 | View 欠陥；Core 真理ではない |
| Mock | 同 Bundle 名で併存 | Fallback View；権威なし |

---

## Allowed / Forbidden（設計）

| Action | Design |
|---|---|
| Cite C1 as Prediction truth | Allowed |
| Cite C6 world=None as Core World truth | **Forbidden** |
| Add another parallel “canonical prediction” DTO | **Forbidden** |
| Keep C2 as thin compatibility helper | Allowed（非正本） |
| Implement lineage fix | Out of V50（要別承認） |
