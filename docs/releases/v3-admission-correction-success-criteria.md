# Version 3 — Admission Correction Success Criteria

**Date:** 2026-07-24  
**Status:** Criteria Locked for next Implementation Round · **検証実行なし**  
**Parent:** [`v3-admission-correction-design.md`](./v3-admission-correction-design.md)  
**Candidate:** A-05

---

## 1. 成功の定義（一文）

> A-05 は、Offline Real 285R において **本命（観測上の強 top-1）を破壊せず**、  
> Control より Hit を改善し、かつ A-03 ソースと既定 Flag を汚さない。

---

## 2. Must Pass（Hard）

| ID | Criteria | 閾値 |
|----|----------|------|
| H1 | Offline Treatment Hit > Control Hit | ΔHit **≥ 1**（推奨は明確な改善） |
| H2 | Offline `worsened_winner_rank1` | **= 0** |
| H3 | A-03 ソース非変更 | SHA / diff で確認 |
| H4 | Flag 既定値 | 全 Lab Flag **False** 維持 |
| H5 | A-03 ∧ A-05 同時 ON | 実験に含めない / harness 拒否 |
| H6 | Leak | 結果・払戻・確定着順を入力にしない |
| H7 | Stage isolation | Admission + Flag（+ registry/docs）以外のアルゴリズム差分なし |

**H2 は本 Correction の核心。** H1 を満たしても H2 欠落なら FAIL。

---

## 3. Should Pass（Strong Soft）

| ID | Criteria | 目安 |
|----|----------|------|
| S1 | T2（A-01+A-05+A-04）が R1（A-01+A-03+A-04）より Offline で優れる | Hit 高い ∧ worsened_rank1 低い |
| S2 | promote_precision | A-03 Offline より改善 |
| S3 | promote_rate | A-03 の ~53% から有意に低下 |
| S4 | Lab Pool 層 | 完全ゼロ回復は望ましくない（監視） |

---

## 4. Nice to Have

| ID | Criteria |
|----|----------|
| N1 | Lab Stack Hit が Baseline v3（279）に近い |
| N2 | Offline improved が A-03 の 12 に近い水準を維持 |
| N3 | favsafe_block_rate が悪化 29 相当レースで高い |

---

## 5. Fail（即不採用）

| 条件 | 理由 |
|------|------|
| worsened_rank1 > 0 | 主因未解決 |
| ΔHit ≤ 0 かつ H2 のみ | 改善なし（保護のみで価値不足の場合は要レビューだが Primary FAIL 候補） |
| A-03 改変が混入 | 独立候補方針違反 |
| 既定 Flag ON | Production リスク |
| Selection/Eval 改変で数字を作った | スコープ違反 |

---

## 6. Candidate Review への進み方

```text
A-05 Accuracy + Offline Hard (H*) PASS
        ↓
Validation PASS
        ↓
Candidate Review:
  - Baseline v3 の Admission を A-03 → A-05 に置換するか
  - PRR HOLD 解除条件の更新
        ↓
（別承認）Shadow / Production
```

Lab 279 の再現は **置換 Decision の必須条件にしない**。  
Offline 本命非破壊 + ΔHit 改善を正とする。

---

## 7. 本 Round の扱い

Success Criteria を固定したのみ。  
測定・判定・実装は行わない。PRR は HOLD のまま。
