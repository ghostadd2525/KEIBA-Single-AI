# Version90 — Decision Layer ADR（研究正本ミラー）

**Date:** 2026-07-28  
**Formal ADR:** [`../adr/ADR-008-decision-layer.md`](../adr/ADR-008-decision-layer.md)  
**Status:** Accepted（Architecture） · **実装禁止（本フェーズ）**

本文の正本は **ADR-008**。本ファイルは V90 成果物名「Decision Layer ADR」としての入口。

---

## 確定アーキテクチャ（一文）

> **Prediction は World 非依存。Confidence は Global Calibration。World は Decision Layer 専属（Ticket / Pool / Explanation / Risk）。**

```text
Prediction Engine (World-independent)
        ↓ read-only
Confidence (Global Calibration)
        ↓
World Label (input only)
        ↓
Decision Layer → Ticket · Pool · Explanation · Risk
                 (+ Confidence display policy; no re-rank)
```

## 責務 / Owner / Contract / Rollback / Flag

詳細は ADR-008 の各節を正とする。

| 項目 | 要約 |
|---|---|
| 責務 | PE=順位、Confidence=Global、World=Decision Selector、Decision=券/プール/説明/リスク |
| Owner | Decision Owner（論理）が Ticket/Pool/Explain/Risk の変更点を専有 |
| Contract | DL-C0–C7（Rank mutate 禁止、World→PE weight 禁止、Flag 既定 OFF） |
| Rollback | Flag OFF → Legacy Decision デフォルト。Prediction 不変 |
| Feature Flag | `W_DECISION_LAYER_ENABLED` + サブフラグ（全て既定 OFF） |
| Migration | `v90-migration-adr.md` |

## 関連

- `v90-responsibility-matrix.md`
- `v90-migration-adr.md`
- `v90-governance.md`
- Evidence: V43–V89 research docs
