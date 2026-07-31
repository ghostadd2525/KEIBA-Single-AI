# Version66 — Confusion Matrix（Rule → Intent World）

**Date:** 2026-07-28  
**行:** 発火 Rule（first-match）  
**列:** Intent GT World

---

## ⑦ Trigger 誤分類 157 件のみ

| Rule \\ Intent GT | core | midupper | midhole | rank7 | mixed | bug | unsatisfied | 計 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R7_midupper_diff | 15 | 0* | 20 | 2 | 0 | 9 | 11 | **57** |
| R1_mixed_short_field | 5 | 21 | 9 | 4 | 0* | 7 | 4 | **50** |
| R8_core_default | 0* | 16 | 9 | 0 | 14 | 1 | 6 | **46** |
| R4_midhole | 0 | 0 | 0* | 0 | 0 | 0 | 2 | 2 |
| R2_midupper_sf_diff | 2 | 0* | 0 | 0 | 0 | 0 | 0 | 2 |
| R3/R5/R6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

\*対角が 0 なのは「Trigger 誤分類」集合から一致ケースを除外しているため（一致は root_cause≠Trigger）。

---

## 全 285R（参考・発火 Rule × Intent GT）

主要セル（JSON 正本より）:

| Rule | Fires | Intent一致 TP | 主な FP 先 |
|---|---:|---:|---|
| R7 | 108 | 36 (midupper) | midhole/core/bug/unsatisfied |
| R8 | 104 | 20 (core) | midupper/mixed/midhole |
| R1 | 56 | 6 (mixed) | midupper/midhole/bug |
| R4 | 15 | 1 | ほぼ非 midhole |
| R2 | 2 | 0 | core |
| R3/R5/R6 | 0 | 0 | — |

完全行列: `_v66-rule-attribution.json` → `confusion_rule_to_intent_gt_full`
