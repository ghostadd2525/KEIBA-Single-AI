# Version65 — Root Cause

**Date:** 2026-07-28  
**対象:** Intent GT ≠ AI Legacy（222 / 285）  
**枠:** Signal / Trigger / Exclusion / Must / Data  
**根拠:** V42/V45 既証パターン + dual-eval `decision_trace` / `restored_ok`（新仮説の創作禁止）

---

## ⑧ 集計（AI Legacy）

| Cause | n | 定義 |
|---|---:|---|
| **Trigger** | **157** | Legacy ルール経路が意図と不一致（DEFAULT core、difficulty/sfp/phase 本体化、rank7/bug 非出力等） |
| **Data** | **38** | `restored_ok=False` |
| **Exclusion** | **15** | Shadow trace 上 GT World が Exclude（参照情報） |
| **Must** | **12** | GT World の Must が Shadow 上も未充足（供給欠落） |
| **Signal** | 0 | 残差なし（Must/Data に吸収） |

---

## Top ペア

| Intent GT | AI Legacy | Cause | n |
|---|---|---|---:|
| midupper | mixed | Trigger | 21 |
| midhole | midupper | Trigger | 20 |
| core | midupper | Trigger | 17 |
| midupper | core | Trigger | 16 |
| midupper | core | Data | 15 |
| mixed | core | Trigger | 14 |
| unsatisfied | midupper | Trigger | 11 |
| midhole | core | Data | 11 |
| mixed | midupper | Must | 10 |
| midhole | core | Trigger | 9 |

---

## V42 / V45 との整合（記述）

| 既証 | 本集計での現れ |
|---|---|
| V42: core = DEFAULT 残余 | Intent 外への AI core 割当が大量（over-assignment 84） |
| V45: rank7 以外 Compliance 低 / bug Must 欠 | AI の rank7・bug **0 件** |
| V45: midupper difficulty 本体化 | midhole/core 意図 → midupper への流入 |
| W-S1 restored 失敗 | Data 38 |

---

## Shadow 対照（参考）

Shadow 誤分類原因: JSON `root_cause.shadow_counts`（Exclusion/Must が主）。主 Governance は Legacy AI。

---

## 改修禁止

原因分類のみ。Trigger/Signal/Exclusion/Must/Data の実装変更は行わない。
