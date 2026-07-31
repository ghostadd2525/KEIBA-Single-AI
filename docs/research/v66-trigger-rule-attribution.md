# Version66 — Trigger Rule Attribution Audit

**Date:** 2026-07-28  
**Subject:** V65 Trigger 起因誤分類 157 件の Rule 単位責任分解  
**Locks:** Trigger Logic / Signal / Threshold / Polarity / Exclusion / PE / Prediction / World / Production — **変更・実装禁止**  
**根拠:** `demo_ticket_optimizer_core.classify_world_line_type` と同型の research mirror `TRIGGER_RULES` R1–R8（`world_trigger_saturation.py`）+ 285R 実 Signal 復元

---

## 結論（1行）

157 件すべてを発火 Rule に帰属できた。主因は **R7_midupper_diff（57）・R1_mixed_short_field（50）・R8_core_default（46）**。R3/R5/R6 は 285R で **発火 0**。Governance **A**。

---

## Rule 定義（実コード mirror・変更なし）

| Rule | World | 条件（製品コードと同型） |
|---|---|---|
| R1_mixed_short_field | mixed | sfp≥0.72 ∧ (phase≥0.48 ∨ chaos≥0.42 ∨ difficulty≥0.42) |
| R2_midupper_sf_diff | midupper | sfp≥0.58 ∧ difficulty≥0.38 |
| R3_mixed_phase | mixed | phase≥0.62 |
| R4_midhole | midhole | late_stop≥0.56 ∧ sustained≥0.52 |
| R5_rank7 | rank7 | chaos≥0.58 ∧ high_pace≥0.48 |
| R6_bug | bug | chaos≥0.66 ∧ difficulty≥0.62 |
| R7_midupper_diff | midupper | difficulty≥0.50 |
| R8_core_default | core | DEFAULT（R1–R7 全 FAIL） |

整合確認: `first_match_world` ≡ `classify_world_line_type` 不一致 **0/285**。

---

## ① Rule Attribution（Trigger 誤分類 157）

| Rule | 誤分類 n | シェア |
|---|---:|---:|
| **R7_midupper_diff** | **57** | 36.3% |
| **R1_mixed_short_field** | **50** | 31.8% |
| **R8_core_default** | **46** | 29.3% |
| R4_midhole | 2 | 1.3% |
| R2_midupper_sf_diff | 2 | 1.3% |
| R3_mixed_phase | 0 | 0% |
| R5_rank7 | 0 | 0% |
| R6_bug | 0 | 0% |
| **合計** | **157** | 100% |

---

## ② World別 Rule Impact（Rule 発火 × Intent GT）

Trigger 誤分類のみ:

| Firing Rule | → Intent 被害（件数） |
|---|---|
| R7 | midhole 20, core 15, unsatisfied 11, bug 9, rank7 2 |
| R1 | midupper 21, midhole 9, bug 7, core 5, unsatisfied 4, rank7 4 |
| R8 | midupper 16, mixed 14, midhole 9, unsatisfied 6, bug 1 |
| R4 | unsatisfied 2 |
| R2 | core 2 |

---

## 方法

1. V65 `_v65-intent-validation.json` から `root_cause_ai=Trigger` かつ不一致 157 件を抽出  
2. 各レースで W-S1 同型 Signal 復元 → `evaluate_all_rules` → **first-match Rule** を責任 Rule とする  
3. Intent GT は V65 保存値を使用  

数値正本: `docs/research/_v66-rule-attribution.json`
