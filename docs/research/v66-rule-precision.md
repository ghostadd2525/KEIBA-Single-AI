# Version66 — Rule Precision

**Date:** 2026-07-28  
**定義:** Rule が **first-match（実決定）** したレースのうち、Intent GT == Rule.world の割合  
**n fires:** 下表

---

## ③ Rule Precision（全 285R）

| Rule | World | Fires | TP | FP | Precision | Intent一致率* |
|---|---|---:|---:|---:|---:|---:|
| R1_mixed_short_field | mixed | 56 | 6 | 50 | **10.7%** | 10.7% |
| R2_midupper_sf_diff | midupper | 2 | 0 | 2 | **0.0%** | 0.0% |
| R3_mixed_phase | mixed | 0 | — | — | n/a | n/a |
| R4_midhole | midhole | 15 | 1 | 14 | **6.7%** | 6.7% |
| R5_rank7 | rank7 | 0 | — | — | n/a | n/a |
| R6_bug | bug | 0 | — | — | n/a | n/a |
| R7_midupper_diff | midupper | 108 | 36 | 72 | **33.3%** | 33.3% |
| R8_core_default | core | 104 | 20 | 84 | **19.2%** | 19.2% |

\*本データでは Intent GT == world ⇔ agree（AI world = firing world）。

### 読み（測定）

- **R7** は発火最多だが Precision 33% — difficulty≥0.50 単独の過剰。  
- **R1** Precision 10.7% — mixed への過剰発火。  
- **R8** Precision 19.2% — DEFAULT core の Intent 外押し込み（FP 84）。  
- **R5/R6/R3** は発火ゼロのため Precision 未定義（未使用 Rule）。
