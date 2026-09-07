# Version103 — Governance（Core Contract Surface）

**Date:** 2026-07-28  
**Parents:** ADR-009 · ADR-010 · V102 · V103 Audit

---

## Decision Gate

| Item | Value |
|---|---|
| Action Type | Core Contract Surface Audit |
| Implementation Required | **No** |
| Deployment Required | No |
| Feature / Semantic 追加 | **No** |
| Prediction / World / Trigger / Decision | **No** |
| Promote 集合の製品配線 | **Not authorized**（別 Decision） |
| Risk | Low |
| Expected Next Action | PROMOTE 4 件の Shadow emit 設計は任意の次ゲート。MS-1/MS-6 は非 promote 維持 |

---

## 硬制約

| ID | 制約 |
|---|---|
| G103-1 | 新しい意味情報を発明しない |
| G103-2 | KEEP_DERIVED / DO_NOT_EXPORT を無断で PROMOTE しない |
| G103-3 | Natural Explanation を Core に載せない |
| G103-4 | Expected Strategy を race 固有本文として新造しない |
| G103-5 | PROMOTE は serialize のみ（Logic 変更禁止） |
| G103-6 | 本フェーズでコード実装禁止 |

---

## 採択分類（固定）

| Class | Members |
|---|---|
| PROMOTE_FIRST_CLASS | Affinity, Exclusion Reasons, Explanation Confidence, Near Miss Class |
| KEEP_DERIVED | Expected Strategy（レジストリ） |
| DO_NOT_EXPORT | Natural Explanation |

---

## 成果物

| 成果物 | Path |
|---|---|
| Core Contract Surface | `v103-core-contract-surface.md` |
| Export Matrix | `v103-export-matrix.md` |
| Payload Contract | `v103-payload-contract.md` |
| Governance | `v103-governance.md` |

---

## 一文

**公開すべきは「導出済みの構造化説明」であり、「新しい予測」でも「自然文」でもない。**
