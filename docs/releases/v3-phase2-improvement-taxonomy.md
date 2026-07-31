# Version 3 — Phase 2 Improvement Taxonomy

**Date:** 2026-07-24  
**Scope:** Research Design（改善カテゴリ体系 · 実装なし）

---

## 1. 改善カテゴリ一覧

| カテゴリ ID | 名称 | 定義 | Phase 1 回収 | 主レバー |
|-------------|------|------|--------------|----------|
| I-Eval | Evaluation | 校正不足による top 誤選択 | A-01 **+28** | D1 Recalibrator |
| I-Boundary | Boundary | 混雑場での境界入れ替わり | A-02 **+14** | D2 Reranker |
| I-Reorder | Reorder | 順序/枠配分副作用 | A-02 **+10** | D2（将来 SEL） |
| I-Pool | Pool | 候補場外の遠位勝者 | **0** | A-03 候補 |
| I-Other | その他 | 未分類 | 0 | 調査 |
| I-Delete | Delete | 購入境界 | 非改善 | 禁止 |

---

## 2. カテゴリ診断サイン

### I-Eval（A-01）

- winner_rank が近い（典型 2）
- winner win_prob ≫ model_rank1 win_prob
- 場の混雑が低い（top gap 大）
- history 相対に依存しなくても校正で足りる

### I-Boundary（A-02）

- top-3 win_prob がほぼ同点
- winner_rank ∈ {2,3} だが wp だけでは区別困難
- history_score（または相対 form）が勝者で突出

### I-Reorder（A-02）

- Boundary に近い混雑
- winner は枠内想定だが model_rank 上位が誤る
- 相対 strength で 1↔2 入替が必要

### I-Pool（未解決）

- winner_rank ≥ 7（本 Lab では 8–10）
- winner win_prob・hist とも弱い
- 大フィールド
- Evaluation 再ランクだけでは到達不能

### I-Other

- 上記サインに当てはまらない
- データ欠測・異常オッズ・特殊条件

### I-Delete

- purchase_eligible = false
- 実験対象外

---

## 3. Phase 1 改善の排他性

| 関係 | 結果 |
|------|------|
| I-Eval ∩ (I-Boundary ∪ I-Reorder) | **空**（重複率 0%） |
| 含意 | カテゴリは代替ではなく**補完** |
| 運用 | 同時 ON は禁止のため、stack は Phase 2 以降の**別実験設計**が必要 |

---

## 4. Phase 2 でのカテゴリ優先度

| 優先 | カテゴリ | 理由 |
|------|----------|------|
| P0 | ~~**I-Pool**~~ → **回収済（A-03）** | Baseline v2 で Pool 残差 0 |
| **P0'（Gap v2）** | **I-Reorder / I-Boundary** | Baseline v2 残 24 · **Selection（A-04）** |
| P1 | I-Eval / I-Boundary 実データ検証 | 合成形状の外挿確認 |
| P2 | I-Reorder × Selection | **A-04 問題定義済 · 実装は別承認** |
| — | I-Delete | 実施しない |

詳細: [`v3-miss-taxonomy-gap-v2.md`](./v3-miss-taxonomy-gap-v2.md) · [`v3-a04-problem-definition.md`](./v3-a04-problem-definition.md)

---

## 5. 測定への写像

| 指標 | カテゴリとの関係 |
|------|------------------|
| Hit | 全 I-* の合計 |
| rank710 | 主に I-Pool 失敗の観測 |
| rank46 | Boundary / mid miss |
| other | Eval 近傍や未分類 |
| Purchase | Delete 除外後の Hit |
| churn | 既存 Hit カテゴリの破壊 |
