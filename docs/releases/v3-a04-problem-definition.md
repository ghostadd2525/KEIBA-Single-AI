# Version 3 — A-04 Problem Definition

**Date:** 2026-07-24（**実装完了注記**）  
**Status:** Problem Definition · **Lab 実装 PASS**（[`v3-a04-accuracy-report.md`](./v3-a04-accuracy-report.md)）  
**Parent:** [`v3-accuracy-gap-analysis-v2.md`](./v3-accuracy-gap-analysis-v2.md)  
**Baseline:** Lab Baseline v2（A-01 + A-03）· Hit **255** → Treatment Hit **279**  
**Taxonomy:** [`v3-miss-taxonomy-gap-v2.md`](./v3-miss-taxonomy-gap-v2.md)

---

## 1. 一文定義

> **Lab Baseline v2（Admission A-03 + Evaluation A-01）を維持したまま、Selection ステージのみを変更し、残存する Boundary（14）+ Reorder（10）miss を churn=0 で回収する。**

Delete（6）は対象外。Evaluation D2（A-02）のスタック再投入は A-04 の解法にしない。

**実装結果（2026-07-24）:** Flag `F_V3_A04_SEL_HISTORY_ENABLED` · Policy `SEL-V3-A04-history-crowding` · Hit **279** / churn **0** · Decision **PASS**。
---

## 2. 解く問題 / 解かない問題

| 解く | 解かない |
|------|----------|
| L-Reorder（10）— 発生ステージ Selection | L-Eval（回収済） |
| L-Boundary（14）— 候補場内の並べ替えで到達可能な隣接 miss | L-Pool（回収済） |
| Baseline v2 Hit を超えること（目標 Hit > 255） | L-Delete（製品境界） |
| churn vs Baseline v2 = 0 | A-01 / A-03 ロジック改変 |
| 単独 Flag の新介入（将来） | D1+D2 同時 ON |
| | Representation / Admission / Evaluation / Purchase 変更 |
| | V2 Production / API / UI / Ops / Explain |

---

## 3. なぜ Selection か（単一ステージ提案）

| 根拠 | 内容 |
|------|------|
| Freeze | Adm=A-03 · Eval=A-01 は公式スタック固定 |
|  empirically | A-02+A-03 は残 24 を回収するが Eval 28 を破壊（Hit 251 < 255） |
| empirically | A-01+A-02+A-03 は Hit 255 のまま（Evaluation 重ね打ち増分なし） |
| スタック隙間 | Selection のみ Baseline identity |
| 層整合 | Reorder は Selection 発生 · Boundary は Selection 転用余地 |

**提案ステージ（1 つだけ）: Selection**

---

## 4. 成功条件（設計ゲート · 未実装）

| Gate | 条件 |
|------|------|
| Hard Gate | Hit > **255** ∧ churn_hit vs Baseline v2 = **0** |
| 層 | Boundary/Reorder 改善 · Eval/Pool/Delete 非悪化 |
| 介入 | Selection のみ · 単独 Flag |
| 天井参考 | 理論上最大 Hit **279**（+24） |

---

## 5. 非ゴール

- A-02 の Primary 昇格や D1 置換
- Admission / Evaluation の再チューニング
- Delete Boundary 緩和
- 本番 Flag ON / Production 配線

---

## 6. 次ステップ

1. ~~A-04 Lab 実装 / AB / Report~~ → **PASS**（本実験）  
2. Validation / Candidate Review（別承認）  
3. A-05（**未着手**）

本番 Flag ON / Production 配線は別承認。