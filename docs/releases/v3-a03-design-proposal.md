# Version 3 — A-03 Design Proposal（Research Only）

**Date:** 2026-07-24  
**Status:** Design Proposal · **A-03 Lab implemented**（[`v3-a03-accuracy-report.md`](./v3-a03-accuracy-report.md)）  
**Parent:** [`v3-accuracy-phase2-research-report.md`](./v3-accuracy-phase2-research-report.md)

---

## 1. 解くべき問題（Problem Statement）

Phase 1 の Evaluation 介入（A-01 D1 / A-02 D2）は、  
**Eval / Boundary / Reorder** を回収したが **Pool（遠位）miss は 0 件**だった。

残差（Lab）:

| 層 | n | Evaluation 到達性 |
|----|---|-------------------|
| Pool | 9 | 不可（winner_rank 8–10 · 弱信号） |
| Delete | 6 | 対象外 |

**A-03 の問題定義:**

> 候補場に入っていない／表現上区別できない遠位勝者を、  
> **単一の新介入**で拾い上げ、**Hit > 246** かつ **churn_hit = 0** を達成する。  
> Delete・A-01/A-02 同時 ON・V2 Production 変更は行わない。

---

## 2. 非目標（Non-Goals）

| 非目標 | 理由 |
|--------|------|
| A-01/A-02 ロジック改変 | Phase 1 凍結 |
| D1+D2 同時 ON | Phase 1 Decision |
| Delete 緩和 | 製品境界 |
| Softmax 温度（CE 再来） | 禁止戦略 |
| 本番配線 | 別承認 |
| 本 Round での実装 | Research Design のみ |

---

## 3. 仮説オプション（実装はしない · 選定用）

| ID | 仮説 | 想定ステージ | 期待カテゴリ |
|----|------|--------------|--------------|
| H-A | 大フィールドで Deep Admit を文脈可変に増やす | Admission | I-Pool |
| H-B | 遠位馬の表現特徴（相対安定性・脚質距離）を追加し Evaluation 前に区別可能にする | Representation | I-Pool / 残余 Eval |
| H-C | Pool 内に入れた後の軽量 rerank（A-02 系の遠位版） | Evaluation（新 Flag） | I-Pool ※前提で admit 必要 |
| H-D | Coverage Admit（脚質/世界ギャップ埋め） | Admission | I-Pool |

**推奨研究順（Design）:** H-A または H-D（Admission）を一次、H-B（Representation）を並行 ROI 調査。  
H-C 単独は Pool 外勝者には無効なため、Admit 後段としてのみ検討。

---

## 4. Hard Gate（提案）

| ゲート | 条件 |
|--------|------|
| Primary | Hit **> 246**（A-01 Primary を超える） ∧ churn_hit = 0 |
| Control 再現 | Flag OFF で Hit = 218 |
| Secondary | Purchase 非悪化 · rank710 減少（Pool 仮説の証拠） |
| Leak | 結果・払戻・確定着順を入力にしない |
| Isolation | A-01/A-02 Flag は OFF のまま（単独実験） |

※ Gate 数値は Lab 合成前提。実 285R では再設定可。

---

## 5. 実験スケッチ（ID 予約のみ）

| 項目 | 案 |
|------|-----|
| Experiment ID | `v3-a03-…`（承認後に確定） |
| Flag | 新 Flag（**未追加** · Phase 2 実装承認後） |
| Control | Baseline 218 または A-01 参照比較 |
| Corpus | 実 285R + Pool 層別 |
| 比較 | vs Baseline · vs A-01 · vs A-02（単独） |

---

## 6. 成功 / 失敗の読み方

| 結果 | 解釈 | 次アクション |
|------|------|--------------|
| Hit↑ · rank710↓ · churn=0 | Pool 仮説支持 | Validation → Candidate Review |
| Pool 入るが Hit 不変 | Evaluation 後段不足 | H-C 接続を別実験 |
| Hit 不変 · Purchase のみ悪化 | 容量過剰 | 仮説破棄 |
| churn>0 | 不採用 | 即停止 |

---

## 7. 依存関係

```text
Phase 1 CLOSE (A-01 Primary, A-02 Secondary)
        ↓
Phase 2 Research Design（本提案）
        ↓
実 285R Miss 再凍結
        ↓
A-03 実装承認（別 Round）← ここでは停止
```

---

## 8. 停止

本文書は **Design Proposal** まで。A-03 コード・Flag・Contract 実装は行わない。
