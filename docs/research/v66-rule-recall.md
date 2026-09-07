# Version66 — Rule Recall / FP / FN

**Date:** 2026-07-28  
**Recall 定義:** Intent GT == Rule.world のレースのうち、当該 Rule が first-match した割合  
**FP:** first-match したが Intent GT ≠ Rule.world  
**FN:** Intent GT == Rule.world だが当該 Rule が first-match しなかった

---

## ④ Rule Recall

| Rule | World | GT support | Recall | FN |
|---|---|---:|---:|---:|
| R1_mixed_short_field | mixed | 40 | **15.0%** | 34 |
| R2_midupper_sf_diff | midupper | 92 | **0.0%** | 92* |
| R3_mixed_phase | mixed | 40 | 0.0% | 40 |
| R4_midhole | midhole | 50 | **2.0%** | 49 |
| R5_rank7 | rank7 | 7 | **0.0%** | 7 |
| R6_bug | bug | 25 | **0.0%** | 25 |
| R7_midupper_diff | midupper | 92 | **39.1%** | 56 |
| R8_core_default | core | 45 | **44.4%** | 25 |

\*midupper の GT 92 に対し R2 はほぼ関与せず、R7 が主経路。

### midupper 合算（参考）

R2∨R7 が first-match した GT midupper = R7 の 36（R2 の TP=0）→ 合算 Recall **39.1%**（R7 のみ）。

---

## ⑤ False Positive（過剰発火）

| Rule | FP | 主な Intent 被害先（Trigger 誤分類内） |
|---|---:|---|
| R7 | **72**（全コーパス） / 57（Trigger誤分類） | midhole, core, bug |
| R8 | **84** / 46 | midupper, mixed, midhole |
| R1 | **50** / 50 | midupper, midhole, bug |
| R4 | 14 / 2 | unsatisfied |
| R2 | 2 / 2 | core |

---

## ⑥ False Negative（未発火）

| 現象 | 測定 |
|---|---|
| R5_rank7 が GT rank7 を拾えない | Recall 0、fires 0 |
| R6_bug が GT bug を拾えない | Recall 0、fires 0 |
| R4 が GT midhole をほぼ拾えない | Recall 2.0% |
| R3 が mixed を拾えない | fires 0（R1 が先行） |

FN の本体は「正しい Rule が通らない」か「より優先の誤 Rule が先に通る」の両方。first-match 監査では後者は上位 Rule の FP として計上される。
