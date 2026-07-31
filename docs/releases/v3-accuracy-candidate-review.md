# Version 3 — Accuracy Candidate Review（A-01 vs A-02）

**Date:** 2026-07-24  
**Review ID:** `v3-accuracy-candidate-review/1.0`  
**Scope:** Review only（新 Evaluation 実装なし · A-03 未着手）  
**Artifacts:** `research/v3_lab/baselines/accuracy_candidate_review/`

---

## 1. 目的

A-01（D1）と A-02（D2）を**同一条件**で比較し、Version 3 Evaluation の採用候補順位を決定する。

---

## 2. 同一条件の定義

Primary panel: `build_candidate_review_corpus()`（`rev-285-*`）

| 要素 | 内容 |
|------|------|
| N | 285R · Control Hit **218** |
| Eval 層（28） | A-01 回収形状（D1 向け） |
| Boundary（14）· Reorder（10） | A-02 回収形状（D2 向け） |
| Pool / Delete | どちらも非回収 |
| Arms | Control OFF / A-01=`F_V3_RANK_D1` / A-02=`F_V3_RANK_D2` |

Native corpus 交差確認も実施（再現用・帰属確認）。

---

## 3. 採用順位（結論）

| 順位 | 候補 | Hit（同一条件） | churn | Validation |
|------|------|-----------------|-------|------------|
| **1** | **A-01（D1 Recalibrator）** | **246** | 0 | PASS |
| **2** | A-02（D2 Listwise Reranker） | 242 | 0 | Lab PASS のみ |

### 推奨案

1. **Lab 一次採用候補 = A-01**
2. **二次候補 = A-02**（拡張・相補 miss 層向け）
3. **同時 ON / stack はしない**（単独 Flag 原則）
4. **本番配線はしない**（別承認）
5. 重複率 0 のため将来 stack は**別実験承認**が必要

---

## 4. A-01 vs A-02 比較表（同一条件）

| 指標 | Baseline | A-01 | A-02 |
|------|----------|------|------|
| Hit | 218 | **246** | 242 |
| Purchase | 218 | **246** | 242 |
| rank710 | 9 | 9 | 9 |
| rank46 | 6 | 6 | 6 |
| other | 52 | **24** | 28 |
| ROI | 1.1418 | 1.4463 | **1.4744** |
| churn | — | **0** | **0** |
| ΔHit | — | **+28** | +24 |

詳細: [`v3-a01-vs-a02-comparison.md`](./v3-a01-vs-a02-comparison.md)

---

## 5. 改善レース比較

| 項目 | 値 |
|------|-----|
| A-01 改善 | 28（すべて **Eval**） |
| A-02 改善 | 24（**Boundary** 14 + **Reorder** 10） |
| 重複（intersection） | **0** |
| 重複率（/ union） | **0.0** |
| 差集合 only A-01 | 28 |
| 差集合 only A-02 | 24 |
| union | 52 |
| 悪化 A-01 / A-02 | **0 / 0** |

→ 改善カテゴリは完全に相補。同一レースを奪い合っていない。

改善レース詳細: [`v3-a01-a02-improved-races.md`](./v3-a01-a02-improved-races.md)  
JSON: `baselines/accuracy_candidate_review/improved_race_comparison.json`

---

## 6. Native corpus 交差（帰属確認）

| Corpus | A-01 Hit | A-02 Hit | 解釈 |
|--------|----------|----------|------|
| a01 native | **246** | 218 | D2 は A-01 Eval 形状を回収しない |
| a02 native | 218 | **242** | D1 は A-02 Boundary/Reorder を回収しない |
| unified review | **246** | **242** | 同一条件の正式比較 |

---

## 7. 定性比較

| 観点 | A-01 | A-02 | 優位 |
|------|------|------|------|
| 実装複雑度 | 2/5（単一スコア校正） | 3/5（listwise + pairwise） | **A-01** |
| 保守性 | 高（Validation 済・信号少） | 中（crowding / history 依存） | **A-01** |
| 将来拡張性 | 等張校正へ自然 | rank-loss / Representation 接続 | **A-02** |

---

## 8. 判定根拠（要約）

1. 同一条件で Hit **A-01 246 > A-02 242**
2. 両者 churn=0 · 悪化レースなし
3. A-01 は Validation PASS 済
4. 複雑度・保守性は A-01 優位
5. ROI は A-02 がわずかに高いが、採用一次指標は Hit Hard Gate
6. 改善は相補 → stack は魅力的だが単独 Flag 原則により今回は非推奨

---

## 9. 変更範囲

Review harness / 文書のみ。

| 追加 | `accuracy_candidate_review.py` · tests · docs · JSON artifacts |
|------|------|
| **未変更** | Evaluation アルゴリズム · Rep/Adm/Sel/Purchase · V2 Production · API/UI/Ops/Explain |

---

## 10. 停止

**Accuracy Candidate Review 完了。ここで停止する。**  
A-03 には着手しない。
