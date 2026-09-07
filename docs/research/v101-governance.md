# Version101 — Governance（Explanation Confidence）

**Date:** 2026-07-28  
**ADR:** ADR-010 Accepted（Definition）

---

## Decision Gate

| Item | Value |
|---|---|
| Action Type | Confidence Definition ADR |
| Implementation Required | **No** |
| Deployment Required | No |
| Shadow Observation | Taxonomy 写像のみ（V100 再利用） |
| Prediction/Ranking/Score Change | **No** |
| Trigger/World/Near Miss/Decision Change | **No** |
| ADR-009 | **維持** |
| Risk | Low |
| Expected Next Action | EC 数値 Shadow は別 Decision。Prediction Confidence を Core に追加しない |

---

## 硬制約

| ID | 制約 |
|---|---|
| G101-1 | Core Confidence = Explanation Confidence のみ |
| G101-2 | Prediction Probability / オッズ / Calibration を Core Confidence と呼んではならない |
| G101-3 | Core は Prediction Confidence を返さない（欠落としない） |
| G101-4 | EC を Rank/Score にフィードバックしてはならない |
| G101-5 | 本フェーズで製品実装・Flag 追加禁止 |
| G101-6 | V100 `confidence:candidate_missing` を Core Completeness 必須欠落に再掲しない |

---

## 成果物

| 成果物 | Path |
|---|---|
| ADR | `docs/adr/ADR-010-explanation-confidence.md` |
| Contract | `docs/research/v101-confidence-contract.md` |
| Taxonomy | `docs/research/v101-confidence-taxonomy.md` |
| Governance | `docs/research/v101-governance.md` |
| Observation | `docs/research/v101-confidence-observation.md` |

---

## 一文

**Core の Confidence は「どれだけ正しく説明できているか」であり、「どれだけ勝ちそうか」ではない。**
