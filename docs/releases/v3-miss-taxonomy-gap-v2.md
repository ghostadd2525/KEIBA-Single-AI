# Version 3 — Miss Taxonomy（Gap Analysis v2 更新）

**Date:** 2026-07-24  
**Status:** Taxonomy UPDATE（分析のみ · 実装なし）  
**Parent:** [`v3-phase2-miss-taxonomy.md`](./v3-phase2-miss-taxonomy.md)  
**根拠:** Lab Baseline v2（A-01 + A-03）· Hit **255** / Miss **30**  
**Gap Report:** [`v3-accuracy-gap-analysis-v2.md`](./v3-accuracy-gap-analysis-v2.md)

本表は Phase 2 Miss Taxonomy を **Baseline v2 採用後**に再凍結した版である。  
Phase 2 時点の「残 Pool 9」は A-03 により回収済み。

---

## 1. Baseline v2 後の残 miss 全体図

```text
Baseline v2 miss 30
├── Boundary …… 14   ← 発生: Evaluation · A-04 介入候補（Selection 経由）
├── Reorder ……… 10   ← 発生: Selection · A-04 主対象
└── Delete ……… 6    ← 不変 · Accuracy 非対象

回収済（本コーパス）
├── Eval ……… 28     ← A-01
└── Pool ……… 9      ← A-03
```

理論天井（Delete 除外）: Hit **279**（255 + 24）。

---

## 2. 層定義（Gap v2 版）

| 層 ID | 名称 | 定義（操作的） | Baseline v2 状態 | A-04 |
|-------|------|----------------|------------------|------|
| L-Eval | Evaluation | 場内勝者 · 校正不足で top 外れ | **回収済（0）** | 非対象 |
| L-Boundary | Boundary | トップ近傍混雑 · survivor≈境界 | **残 14** | 対象（Selection で回収を試す） |
| L-Reorder | Reorder | 枠内だが順序/圧縮副作用で外れ | **残 10** | **主対象** |
| L-Pool | Pool | 勝者が候補場の外側 | **回収済（0）** | 非対象 |
| L-Delete | Delete | 購入/削除境界 | **残 6 · 不変** | **非対象** |
| L-Other | その他 | 未分類 | 0（本 Lab） | — |

---

## 3. 発生ステージ写像

| 層 | 発生ステージ | 原因カテゴリ | 改善余地 |
|----|--------------|--------------|----------|
| L-Boundary | **Evaluation** | I-Boundary（混雑相対） | 高（Evaluation 再スタックは不可 · Selection 転用） |
| L-Reorder | **Selection** | I-Reorder（順序副作用） | 高 |
| L-Delete | **Delete** | purchase_delete_boundary | なし |

| ステージ | 残件数 | 備考 |
|----------|--------|------|
| Representation | 0 | — |
| Admission | 0 | A-03 飽和 |
| Selection | 10（+Boundary 転用） | **次レバー** |
| Evaluation | 14 | A-01 済 · A-02 はスタック不可 |
| Purchase | 0 | — |
| Delete | 6 | 不変 |

---

## 4. Improvement Taxonomy 更新（要約）

| カテゴリ | Phase 1/2 回収 | Baseline v2 残 | 次レバー |
|----------|----------------|----------------|----------|
| I-Eval | A-01 +28 | 0 | — |
| I-Pool | A-03 +9 | 0 | — |
| I-Boundary | A-02 単独 +14（スタック不可） | **14** | **Selection（A-04）** |
| I-Reorder | A-02 単独 +10（スタック不可） | **10** | **Selection（A-04）** |
| I-Delete | — | 6 | 禁止 |

詳細 Gap: [`v3-accuracy-gap-analysis-v2.md`](./v3-accuracy-gap-analysis-v2.md)  
A-04 定義: [`v3-a04-problem-definition.md`](./v3-a04-problem-definition.md)

---

## 5. 成功指標との接続

| 目標 | Taxonomy 含意 |
|------|----------------|
| Hit > 255 | Boundary/Reorder を動かす必要 |
| churn = 0 | Eval/Pool 既存 Hit を壊さない |
| Delete 不変 | L-Delete 除外 |
| 単一ステージ | **Selection のみ**変更 |
