# Version64 — Confusion Matrix

**Date:** 2026-07-28  
**行列:** 行 = Semantic GT / 列 = Shadow 予測  
**n:** 285

---

## ⑤ Shadow Confusion Matrix（非ゼロセル）

| GT \\ Pred | core | midupper | midhole | rank7 | mixed | bug | unsatisfied | GT計 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| core | **6** | 1 | 0 | 0 | 0 | 0 | **73** | 80 |
| midupper | 0 | **1** | 9 | **26** | 1 | 0 | 17 | 54 |
| midhole | 0 | 2 | **4** | 15 | 0 | 0 | **61** | 82 |
| rank7 | 0 | 0 | 0 | **6** | 0 | 0 | 1 | 7 |
| mixed | 0 | 0 | 6 | 3 | **1** | 0 | 1 | 11 |
| bug | 2 | 0 | 3 | 5 | 1 | **0** | 14 | 25 |
| unsatisfied | 0 | 2 | 2 | 10 | 3 | 0 | **9** | 26 |
| **Pred計** | 8 | 6 | 24 | 65 | 6 | 0 | 176 | 285 |

---

## 主な誤分類パターン

| パターン | n | 意味 |
|---|---:|---|
| GT core → unsatisfied | **73** | 能力決着レースを Shadow が成立させない |
| GT midhole → unsatisfied | **61** | 中位帯レースの取りこぼし |
| GT midupper → rank7 | **26** | 中上位を混戦 World へ誤爆 |
| GT midhole → rank7 | 15 | midhole / rank7 境界の崩壊 |
| GT bug → unsatisfied | 14 | bug 経路が存在しない |
| GT unsatisfied → rank7 | 10 | 意味的に弱いレースを rank7 へ |

---

## 解釈（測定のみ）

1. 対角成分が極めて薄い（正解セル合計 27）。  
2. 最大質量は **GT→unsatisfied** 列。  
3. 第二質量は **→rank7**（GT midupper/midhole から流入）。  
4. bug 列は全ゼロ。

完全行列 JSON: `_v64-classification-validation.json` → `confusion_matrix.shadow_rows_gt_cols_pred`
