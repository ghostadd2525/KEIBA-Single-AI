# Version 3 — Remaining Issues（Phase 2 Close）

**Date:** 2026-07-24  
**Issues ID:** `v3-accuracy-remaining-issues/phase2-close`  
**Baseline:** `v3-lab-baseline-v3-a01-a03-a04` · Hit **279** / Miss **6**  
**Artifact:** `research/v3_lab/baselines/accuracy_phase2_close/remaining_issues.json`

---

## 1. 要約

Accuracy 研究スコープ内の残 miss は **0**。  
残る 6 件はすべて **Delete** であり、製品方針により研究対象外。

| 区分 | n | 扱い |
|------|---|------|
| 研究対象内 | **0** | — |
| Delete（対象外） | **6** | 変更しない |

---

## 2. Out of Scope — Delete（6）

| race_id | 層 | 発生ステージ |
|---------|-----|--------------|
| a03-285-280 | Delete | Delete |
| a03-285-281 | Delete | Delete |
| a03-285-282 | Delete | Delete |
| a03-285-283 | Delete | Delete |
| a03-285-284 | Delete | Delete |
| a03-285-285 | Delete | Delete |

| 項目 | 内容 |
|------|------|
| 理由 | Purchase / Delete Boundary |
| アクション | **なし**（Accuracy 非介入） |
| 指標上の見え方 | rank46 = 6 · other = 0 |

---

## 3. 回収済（Baseline v3）

| 層 | Phase 2 での扱い |
|----|------------------|
| Eval | A-01 で回収 |
| Pool | A-03 で回収 |
| Boundary | A-04 で回収 |
| Reorder | A-04 で回収 |

---

## 4. Phase 3

Phase 3 研究は **未着手**。本文書は残課題の棚卸しのみ。
