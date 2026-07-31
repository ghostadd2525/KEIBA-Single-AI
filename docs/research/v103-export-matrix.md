# Version103 — Export Matrix

**Date:** 2026-07-28  
**Parent:** `v103-core-contract-surface.md`  
**Mode:** Shadow Audit · 実装禁止

---

## Matrix

| ID | Semantic | 公開価値 | 重複性 | 導出コスト | Contract安定 | Single | Win5 | **Class** |
|---|---|---|---|---|---|---|---|---|
| MS-1 | Expected Strategy | L | H | L | M | M | L | **KEEP_DERIVED** |
| MS-2 | Affinity | H | M | L–M | H | H | M | **PROMOTE_FIRST_CLASS** |
| MS-3 | Exclusion Reasons | H | L | M | H | H | M | **PROMOTE_FIRST_CLASS** |
| MS-4 | Explanation Confidence | H | M | L–M | H | H | M | **PROMOTE_FIRST_CLASS** |
| MS-5 | Near Miss Class | H | M | L | H | H | H | **PROMOTE_FIRST_CLASS** |
| MS-6 | Natural Explanation | M | H | M–H | L | H* | M* | **DO_NOT_EXPORT** |

\* Presentation 層での利用は可。Core Export は不可。

---

## Class 定義

| Class | 意味 |
|---|---|
| **KEEP_DERIVED** | 意味は維持。race first-class にはしない。消費者または共有レジストリで導出 |
| **PROMOTE_FIRST_CLASS** | 既存導出結果を Core payload に載せる候補（意味新造禁止・実装は別 Decision） |
| **DO_NOT_EXPORT** | Core Contract Surface に載せない。他層の責務 |

---

## Promote 集合（実装候補・未承認）

```text
PROMOTE = {
  NearMissTaxonomyMeta,   # MS-5
  AffinityVector,         # MS-2  (unsatisfied)
  ExclusionReasons,       # MS-3
  ExplanationConfidenceBundle  # MS-4
}
```

```text
KEEP_DERIVED = {
  ExpectedStrategyRegistry  # MS-1  (world_id → text/policy id)
}
```

```text
DO_NOT_EXPORT = {
  NaturalLanguageWhy  # MS-6
}
```

---

## 既に first-class（本監査の前提・変更なし）

| 既出 | 備考 |
|---|---|
| Prediction Rank/Score | ADR-003 / ADR-009 |
| World label (CEW) | Trigger 契約 |
| decision_trace (must/gaps/exclude/match) | W-S1 / V44 |
| transition / trigger_path | dual-eval |

本監査はこれらを改変しない。
