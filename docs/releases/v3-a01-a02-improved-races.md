# Version 3 — A-01 / A-02 改善レース比較

**Date:** 2026-07-24  
**Corpus:** Unified Review `rev-285-*`（285R）  
**Artifact:** `research/v3_lab/baselines/accuracy_candidate_review/improved_race_comparison.json`

---

## 1. 集計

| 項目 | A-01 | A-02 |
|------|------|------|
| 改善レース数 | 28 | 24 |
| 悪化レース数 | 0 | 0 |
| 改善層 | Eval ×28 | Boundary ×14 + Reorder ×10 |

| 集合演算 | 件数 | 内容 |
|----------|------|------|
| 重複（A-01 ∩ A-02） | **0** | なし |
| 差集合 only A-01 | 28 | すべて Eval |
| 差集合 only A-02 | 24 | Boundary 14 + Reorder 10 |
| Union | 52 | 相補的カバー |

**重複率（intersection / union）= 0.0**

---

## 2. 悪化レース

両候補とも **なし**（churn_hit = 0）。

---

## 3. only A-01（Eval · 28R）

`rev-285-219` … `rev-285-246`（連続 28）

パターン: Control は model_rank=1 を pick、A-01 は win_prob 優勢の rank2（winner）へ再校正。A-02 は rank_prior 優勢の clear-field 経路で rank1 を維持 → 非回収。

---

## 4. only A-02（Boundary 14 + Reorder 10）

### Boundary（14）

混雑トップ3 + winner=rank3 の高 `history_score`。A-02 pairwise が回収。A-01 は rank_prior で rank1 維持 → 非回収。

### Reorder（10）

混雑トップ2 + winner=rank2 の高 `history_score`。同様に A-02 のみ回収。

レース ID のフル一覧は JSON artifact の `only_a01` / `only_a02` を参照。

---

## 5. 解釈

- 改善カテゴリが直交 → **互いに代替ではなく補完**
- ただし単独 Flag 原則により、現時点の一次採用は Hit 上位の **A-01**
- stack（D1→D2 または選択的適用）は A-03 以降の別承認事項（本 Review では実装しない）
