# Version64 — Root Cause（誤分類）

**Date:** 2026-07-28  
**対象:** Shadow ≠ Semantic GT の 258 / 285 件  
**分類枠:** Signal / Trigger / Exclusion / Must不足 / Data不足  
**根拠:** dual-eval `decision_trace` / `restored_ok` / match・exclude フラグ（推測で新仮説を作らない）

---

## ⑦ 集計

| Root Cause | n | 定義（本フェーズ） |
|---|---:|---|
| **Exclusion** | **117** | GT World の Must は成立しうるが Shadow trace で Exclude が真、または Exclude 起因で別 World/unsatisfied へ |
| **Must不足** | **89** | GT World の Must が Shadow 上 True でない（must_gaps） |
| **Data不足** | **36** | `restored_ok=False`（Signal 復元失敗） |
| **Trigger** | **16** | 上記以外の割当不一致（優先・競合解決・GT unsatisfied への過剰割当等） |
| **Signal** | 0* | 単独カテゴリ残差（本集計では Must/Data に吸収） |

\*明示 `Signal` 残差は 0。欠損・極性失敗は Must不足 / Data不足 に計上。

---

## Top 誤分類ペア × 原因

| GT | Shadow Pred | Cause | n |
|---|---|---|---:|
| core | unsatisfied | **Exclusion** | 45 |
| midhole | unsatisfied | **Must不足** | 45 |
| midupper | rank7 | **Exclusion** | 25 |
| core | unsatisfied | Must不足 | 19 |
| midhole | rank7 | Exclusion | 14 |
| bug | unsatisfied | Must不足 | 12 |
| unsatisfied | rank7 | Trigger | 10 |
| midhole | unsatisfied | Data不足 | 10 |
| core | unsatisfied | Data不足 | 9 |
| midupper | unsatisfied | Must不足 | 8 |

---

## 原因別の設計含意（記述のみ・改修禁止）

### Exclusion（117）

V44 Forbidden-as-positive / Exclude が Shadow で発火し、Semantic 上の core/midupper/midhole を落とす、または rank7 へ流す。  
W-S3 Exclusion Shadow（False Exclusion 51）と方向が一致。

### Must不足（89）

V44 Must（例: midhole の mid_band∧top_monopoly↓、bug の exception_flag、midupper の aptitude）が 285R 上で揃わない。  
V45 Compliance / V59 Ledger（Missing signals）と整合。

### Data不足（36）

285R 中 Signal 復元失敗。分類以前に観測が欠ける。

### Trigger（16）

GT が unsatisfied なのに rank7 等へ割当、など Logic Form の競合解決・過剰 Match。

---

## Signal カテゴリについて

「Signal」単体ラベルの残差は 0 だが、**Must不足の実質は Signal 供給・極性観測の不足**を含む。  
V44 契約上の Must 概念がデータに無い場合は Must不足へ分類した（推測で新 Signal を捏造しない）。

---

## 改善はしない

本ドキュメントは原因の **分類** のみ。Exclusion 緩和・Must 追加・Trigger 改修・Production 変更は **禁止のまま**。
