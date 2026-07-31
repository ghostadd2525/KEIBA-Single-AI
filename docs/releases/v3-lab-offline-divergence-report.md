# Lab / Offline Divergence Report

**Status:** Analysis Complete  
**Scope:** Lab Baseline v3 (Hit 279) vs Offline Gate Treatment (Hit 42)  
**Algorithm / Flag / Production:** unchanged (analysis only)  
**PRR:** HOLD 継続  
**Date:** 2026-07-24

---

## 1. Executive Verdict

| Surface | Hit | Notes |
|---------|-----|-------|
| Lab Baseline v3 (A-01+A-03+A-04) | **279** | Synthetic Accuracy corpus |
| Offline Gate Control (flags OFF) | **59** | Real labeled_test 285R |
| Offline Gate Treatment (Baseline v3) | **42** | Real labeled_test 285R |
| Δ (Treatment − Control) | **−17** | Churn 29 / Improved 12 / Worsened 29 |

**結論:** Lab 279 と Offline 42 の差は、**同一スタックが異なる入力分布に当たった結果**である。  
主因は **Admission A-03 の過剰発火（実データで field≥12 × style rarity）** であり、明確本命（`winner_rank=1`）を破壊している。  
A-04 History Crowding は副次。データリーク・Flag 誤適用は確認されなかった。

---

## 2. Deliverables Index

| Artifact | Path |
|----------|------|
| Divergence Report | 本文書 |
| Root Cause Analysis | `v3-lab-offline-rca.md` |
| Lab vs Offline Diff | `v3-lab-vs-offline-diff.md` |
| 原因ランキング | `v3-divergence-cause-ranking.md` |
| Metrics JSON | `research/v3_lab/baselines/offline_gate/divergence_analysis.json` |
| A-03 diag | `.../divergence_a03_diag.json` |
| Input compare | `.../divergence_input_compare.json` |

---

## 3. What Matched / What Diverged

### Matched（同一）

- Stack 定義: Representation → A-03 → A-04 → A-01 → Purchase Baseline
- Feature Flag 配線・default OFF（Production 未適用）
- Lab Metric 定義（top-1 pick == winner）は Offline Gate Control/Treatment と一致
- リーク検査: Lab 合成ラベル依存の学習なし / Offline は race 内特徴のみで stack 適用

### Diverged（本質差）

| Axis | Lab Accuracy | Offline Real 285R |
|------|--------------|-------------------|
| Field size mean | **8.13** | **14.6** |
| Field ≥12 | **9/285 (3%)** | **246/285 (86%)** |
| A-03 promote rate | **9/285 (3%)** — Pool のみ | **151/285 (53%)** |
| history_score mean | **0.10** | **0.74** |
| winner_rank=1 rate | **76.5%** | **21.1%** |
| Baseline Hit (flags OFF) | 218 | 59 |
| Stack Hit (v3 ON) | **279** | **42** |

---

## 4. Worsened 29（winner_rank=1）共通像

全 29 件で:

- Control pick = winner（本命正解）
- Treatment pick ≠ winner
- `winner_rank == 1`

発火内訳（Treatment）:

| Signal | Count / 29 |
|--------|------------|
| A-03 promote | **27** |
| Treatment pick == A-03 promoted | **26** |
| A-04 promote | **3** |
| A-04 delete | **1** |

**共通メカニズム:**  
大頭数レースで A-03 が深い「希少スタイル」馬を promote → `win_prob`/`model_rank` を書き換え → D1 が本命を捨て非本命を選ぶ。

---

## 5. Improved 12 との対比

| | Improved 12 | Worsened 29 |
|--|-------------|-------------|
| A-03 promote | 11 | 27 |
| Promoted == winner | **11** | **0** |
| A-04 promote | 1 | 3 |
| 典型 | 深い本命を正しく昇格 | 本命正解を破壊 |

A-03 は **正しい深掘り回復**と**誤った本命破壊**の両刃。実データでは誤発火が勝る。

---

## 6. History Crowding（A-04）発火

| Surface | A-04 promote 件数 |
|---------|-------------------|
| Lab Accuracy（Boundary+Reorder 設計） | 意図どおり回復に寄与 |
| Offline worsened | **3/29** |
| Offline improved | **1/12** |

A-04 は Offline 悪化の主因ではない。実データの `history_score` スケール差（mean 0.74 vs Lab 0.10）はあるが、悪化 29 の支配因子は A-03。

---

## 7. Feature Flag 適用確認

サンプル検証（Offline Gate harness）:

| Mode | Flags | Behavior |
|------|-------|----------|
| Control | 全 OFF | identity（top-1 = model_rank 最小） |
| Treatment | A-01/A-03/A-04 ON | Admission/Selection/Eval 適用 |

誤配線・default 勝手 ON・Production 経路汚染はなし。

---

## 8. データリーク有無

| Check | Result |
|-------|--------|
| Lab 合成が Offline 評価に混入 | **No**（corpus 分離） |
| Offline が Lab 合成ラベルで学習 | **No**（学習なし・policy 決定論） |
| winner / finish を特徴に直接使用 | **No**（stack 入力は runners 特徴） |
| Lab 279 の「答え合わせ設計」 | **Yes（意図的）** — Accuracy corpus は層別シナリオ。リークではなく **評価コーパスの非代表性** |

---

## 9. Why Lab 279 / Why Offline 42

### Lab 279 が成立した理由

1. Hit/Eval/Boundary/Reorder/Delete は **field=8** → A-03 `field≥12` 不発火
2. A-03 は **Pool×9 のみ**発火（設計どおり）
3. A-01 が Eval×28 を回復
4. A-04 が Boundary+Reorder×24 を回復（A-03 干渉なし）
5. 本命層（Hit 218）は stack で壊れない

### Offline 42 になった理由

1. 実フィールドの **86% が field≥12** → A-03 ゲート常時開放気味
2. Style rarity が **53%** で発火
3. 誤 promote → D1 が非本命を購入相当の top-1 に採用
4. Control で取れていた `winner_rank=1` を **29 件破壊**
5. 正しい深掘り **+12** では足りず **net −17**

---

## 10. Proposed Fix Stage（実装しない・提案のみ）

**第一候補ステージ: Admission（A-03）**

- 実データ向け promote 条件の再設計（field 閾値・style rarity・本命保護）
- Selection（A-04）は副次レビュー
- A-05 / Shadow / Production / Phase3 は今回対象外

---

## 11. Stop Condition

本 Divergence Analysis 完了をもって停止。  
A-05 / Shadow / Production / Phase3 には着手しない。
