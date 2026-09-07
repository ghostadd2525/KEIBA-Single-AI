# Version 3 — Accuracy Phase 2 Research Report

**Date:** 2026-07-24（**Phase 2 Close 追記**）  
**Status:** Phase 2 **CLOSED** · Baseline v3 Hit **279** · Phase 3 未着手  
**Phase 1 Close:** [`v3-accuracy-phase1-final-report.md`](./v3-accuracy-phase1-final-report.md)  
**Phase 2 Final:** [`v3-accuracy-phase2-final-report.md`](./v3-accuracy-phase2-final-report.md)  
**Gap Analysis v2:** [`v3-accuracy-gap-analysis-v2.md`](./v3-accuracy-gap-analysis-v2.md)  
**Analysis artifact:** `research/v3_lab/baselines/accuracy_phase2_research/phase2_feature_analysis.json` · `research/v3_lab/baselines/lab_baseline_v3_a01_a03_a04.json`

---

## 1. 目的

Phase 1 の結果を分析し、**Phase 2 で解くべき問題**と研究テーマを定義する。  
（事後: A-03 / Gap v2 / A-04 / Phase 2 Close まで完了。）

---

## 2. 前提（Phase 1 固定）

| 項目 | 値 |
|------|-----|
| Baseline | Hit **218** |
| Primary A-01 | Hit **246**（Δ+28） |
| Secondary A-02 | Hit **242**（Δ+24） |
| 改善重複率 | **0%** |
| 同時 ON | 禁止 |
| 本番配線 | なし |

分析コーパス: Candidate Review 同一条件 `rev-285-*`（285R）

---

## 3. A-01 が改善した 28 レースの共通特徴

| 特徴 | 値（全 28R 同一） |
|------|-------------------|
| 層 | **Eval** のみ |
| winner_rank | **2** |
| field_size | 8 |
| top（model_rank1）win_prob | 0.15 |
| winner win_prob | **0.40** |
| wp_gap (top − winner) | **−0.25**（勝者の方が高い） |
| wp_gap (1st−2nd in wp) | 0.25（明確な較差） |
| top odds / winner odds | 4.8 / 3.1 |

**シグネチャ:**  
「model_rank=1 の本命が誤り、rank2 が win_prob で明確に優位」な **校正（calibration）ミス**。  
絶対スコア再校正（D1）向き。場内混雑は低い（clear field）。

---

## 4. A-02 が改善した 24 レースの共通特徴

| 特徴 | 値 |
|------|-----|
| 層 | **Boundary 14** + **Reorder 10** |
| winner_rank | 3（14R）/ 2（10R） |
| field_size | 8 |
| top win_prob（平均） | ≈0.198 |
| winner win_prob（平均） | ≈0.190 |
| wp_gap (top − winner) | ≈**0.008**（ほぼ同点） |
| wp_gap 1–2 | ≈**0.005**（混雑） |
| winner history_score（平均） | ≈**0.47** |
| top history_score（平均） | ≈**0.13** |
| hist_gap (winner − top) | ≈**+0.34** |

**シグネチャ:**  
「win_prob はトップ近傍で混雑し、勝者は **history_score の相対優位**で区別される」  
**境界・並べ替え副作用**ミス。listwise / pairwise（D2）向き。D1 の rank_prior では回収不能。

---

## 5. 改善できなかったレースの分類（残 miss 15）

Control miss 67 − union 改善 52 = **残 15**。

| 分類 | n | winner_rank | 主な特徴 | Phase 2 扱い |
|------|---|-------------|----------|--------------|
| **Pool** | 9 | 8–10 | field=12 · winner_wp≈0.04 · odds≈45 · hist も弱い | **A-03 主対象候補** |
| **Delete** | 6 | 5 | purchase_eligible=false | **非対象（不変）** |

Pool 残差は Evaluation 単独（D1/D2）では届かない。勝者は遠位・薄支持で、候補場への取り込み（Admission）または表現不足が疑われる。

---

## 6. 改善カテゴリの体系化（要約）

| カテゴリ | Phase 1 回収 | レバー | 残課題 |
|----------|--------------|--------|--------|
| Evaluation（Eval） | A-01 +28 | D1 Recalibrator | 飽和気味（本 corpus） |
| Boundary | A-02 +14 | D2 Reranker | 同型の一般化検証 |
| Reorder | A-02 +10 | D2 / 将来 Selection | Selection 併用は別承認 |
| Pool | 0 | **未解決** | Phase 2 / A-03 |
| Delete | 0 | 触らない | 製品境界 |
| その他 | — | — | 実 285R での再ラベル |

詳細: [`v3-phase2-improvement-taxonomy.md`](./v3-phase2-improvement-taxonomy.md) · [`v3-phase2-miss-taxonomy.md`](./v3-phase2-miss-taxonomy.md)

---

## 7. A-03 が解くべき問題（定義）— 履歴

> **Evaluation 校正・場内 rerank では届かない遠位（Pool 層）miss を、候補場の不足または表現の区別不能として解き、Hit>246 かつ churn=0 を狙う。**  
> Delete は対象外。A-01/A-02 同時 ON は禁止のまま、**単一 Flag の新介入**とする。

詳細: [`v3-a03-design-proposal.md`](./v3-a03-design-proposal.md)  
**結果（事後）:** A-03 Lab+Validation PASS · Lab Stack 採用 · Hit **255**。

---

## 8. Gap Analysis v2（追記 · 2026-07-24）

Lab Baseline v2（A-01+A-03 · Hit 255）の残 miss **30**:

| 層 | n | 発生ステージ | Accuracy 対象 |
|----|---|--------------|---------------|
| Boundary | 14 | Evaluation | 対象（A-04 · Selection 経由） |
| Reorder | 10 | Selection | **主対象** |
| Delete | 6 | Delete | 非対象 |

Eval / Pool 残差は **0**。A-02 単独スタックは残 24 を回収できるが Eval を破壊し、D1 同時 ON でも増分なし。

**変更すべきステージ（1 つ）: Selection**  
**A-04 問題定義:** [`v3-a04-problem-definition.md`](./v3-a04-problem-definition.md)  
**Updated Taxonomy:** [`v3-miss-taxonomy-gap-v2.md`](./v3-miss-taxonomy-gap-v2.md)

---

## 9. Phase 2 Research Roadmap（要約）

1. ~~実 285R で Pool/Eval/Boundary ラベル再凍結~~（保留 · 合成先行）  
2. ~~A-03 仮説選定~~ → ~~実装 / Hard Gate / Validation~~ → **Lab Freeze v2**  
3. ~~Gap Analysis v2~~ → ~~A-04 Lab~~ → **Phase 2 Close / Baseline v3**  
4. Phase 3（**未着手**）  

詳細: [`v3-accuracy-phase2-research-roadmap.md`](./v3-accuracy-phase2-research-roadmap.md) · [`v3-accuracy-phase2-final-report.md`](./v3-accuracy-phase2-final-report.md)

---

## 10. 制約（Phase 2 Close 遵守）

未変更（Close Round）: A-01 / A-02 / A-03 / A-04 ロジック · Representation / Admission / Selection / Evaluation / Purchase · V2 Production · API / UI / Ops / Explain

---

## 11. 停止

**Accuracy Phase 2 Close 完了。ここで停止する。**  
Phase 3 の研究には着手しない。
