# Lab / Offline Root Cause Analysis

**Status:** Analysis Complete  
**Companion:** `v3-lab-offline-divergence-report.md`  
**Date:** 2026-07-24

---

## 1. Problem Statement

同一アルゴリズムスタック（Lab Baseline v3 = A-01 + A-03 + A-04）が:

- Lab Accuracy corpus では Hit **279**
- Real Offline Gate では Hit **42**（Control 59 から −17）

を示す。差分の因果を特定する。

---

## 2. Causal Chain（主経路）

```
Real field size ≥12 (86% of races)
        ↓
A-03 Admission gate OPEN
        ↓
Style-rarity promote fires (~53%)
        ↓
Deep horse win_prob / model_rank rewritten
        ↓
D1 / top-1 Selection picks promoted horse
        ↓
When true winner was rank-1 favorite:
  Control HIT → Treatment MISS  (×29)
When true winner was deep rare-style:
  Control MISS → Treatment HIT  (×12)
        ↓
Net ΔHit = −17, Churn = 29
```

---

## 3. Evidence

### 3.1 A-03 dominate on worsened set

From `divergence_a03_diag.json` / race-level analysis:

| Condition on worsened 29 | Count |
|--------------------------|-------|
| A-03 promote fired | 27 |
| Treatment pick == A-03 promoted horse | 26 |
| Promoted horse == winner | 0 |
| A-04 promote fired | 3 |

### 3.2 Lab A-03 is corpus-gated

From Lab A-03 Accuracy corpus diagnostics:

| Layer | A-03 promote |
|-------|--------------|
| Hit / Eval / Boundary / Reorder / Delete | **0** |
| Pool | **9/9** |

Lab では A-03 が「深掘り専用」に閉じている。実データでは閉じられない。

### 3.3 Input distribution mismatch

| Feature | Lab | Real |
|---------|-----|------|
| field mean | 8.13 | 14.6 |
| field≥12 | 3% | 86% |
| history_score mean | 0.10 | 0.74 |
| winner_rank=1 rate | 76.5% | 21.1% |

A-03 の `PROMOTE_FIELD_MIN=12` は Lab ではほぼ常に閉、Real ではほぼ常に開。

### 3.4 Flags / Leak ruled out

- Control = identity top-1（OFF）
- Treatment = stack 適用（ON）— sample verified
- No training on Offline labels; no winner-as-feature leak
- Lab 279 は「シナリオ設計の成功」でありリークではない

---

## 4. Alternative Hypotheses Rejected

| Hypothesis | Verdict | Why |
|------------|---------|-----|
| Metric 定義が Lab と Offline で異なる | **Rejected** | 両方 top-1 pick==winner。V2 PE Hit 218 は別定義で今回比較対象外 |
| Feature Flag 未適用 / 誤適用 | **Rejected** | Control/Treatment 差分が A-03/A-04 挙動と一致 |
| A-04 History Crowding が主因 | **Rejected as primary** | worsened の A-04 promote は 3/29 のみ |
| A-01 Evaluation が破壊 | **Rejected** | worsened の支配は Admission promote → pick 変更 |
| データリークで Lab 過大評価 | **Rejected as leak** | 合成コーパスの非代表性（評価設計問題） |
| Purchase / Pool 生存差 | **Out of scope** | Offline Gate は Lab 同一定義の top-1 |

---

## 5. Root Cause Statement

**Root Cause (Primary):**  
Admission A-03 の promote 条件が、Lab 合成コーパス（小頭数・層別シナリオ）に過適合しており、実レース（大頭数・高 style 分散）では本命破壊型の誤 promote が支配する。

**Contributing:**  
- Lab 評価コーパスが実フィールド分布を代表していない（field / history_score / favorite rate）
- A-04 は実データで稀に干渉するが、悪化 29 の説明力は弱い
- D1 は Admission が書き換えた rank を忠実に採用するため、上流誤りの増幅器として働く（D1 自体のバグではない）

---

## 6. Implications for Next Stage（提案のみ）

実装は行わない。修正対象の優先ステージは **Admission（A-03）**。

望ましい方向性（設計提案）:

1. 実データでの promote 率を大幅抑制（本命保護ゲート）
2. Lab コーパスに実フィールド分布を反映した回帰セットを追加（評価改善）
3. A-04 は A-03 安定後に副次レビュー

A-05 / Shadow / Production 配線は Divergence 解決前に進めるべきではない（PRR HOLD 継続と整合）。
