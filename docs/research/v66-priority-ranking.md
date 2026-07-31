# Version66 — Priority Ranking

**Date:** 2026-07-28  
**並び:** Trigger 誤分類への帰属件数 ↓ → FP ↓ → Fires ↓  
**注意:** 改善・実装は禁止。影響の大きさの観測のみ。

---

## ⑧ 影響件数順

| Rank | Rule | Target World | Trigger誤分類 n | FP (285) | Fires | Precision | Recall |
|---:|---|---|---:|---:|---:|---:|---:|
| **1** | **R7_midupper_diff** | midupper | **57** | 72 | 108 | 33.3% | 39.1% |
| **2** | **R1_mixed_short_field** | mixed | **50** | 50 | 56 | 10.7% | 15.0% |
| **3** | **R8_core_default** | core | **46** | 84 | 104 | 19.2% | 44.4% |
| 4 | R4_midhole | midhole | 2 | 14 | 15 | 6.7% | 2.0% |
| 5 | R2_midupper_sf_diff | midupper | 2 | 2 | 2 | 0.0% | 0.0% |
| 6 | R3_mixed_phase | mixed | 0 | 0 | 0 | n/a | 0.0% |
| 7 | R5_rank7 | rank7 | 0 | 0 | 0 | n/a | 0.0% |
| 8 | R6_bug | bug | 0 | 0 | 0 | n/a | 0.0% |

---

## 観測メモ（改修指示ではない）

1. **Top3（R7+R1+R8）で 153/157（97.5%）** を説明。  
2. R5/R6 は誤分類「原因 Rule」としては 0 件だが、**未発火により rank7/bug Intent を回収できない**構造ギャップ（Recall 0）として別記録。  
3. R8 は V42 DEFAULT 問題の Rule 実体。  
4. R7 は V45「difficulty のみ → midupper」の Rule 実体。

**本フェーズは並べただけ。触らない。**
