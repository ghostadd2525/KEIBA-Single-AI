# Version 3 — Accuracy Report A-05（Favorite-Safe Coverage Admission）

**Date:** 2026-07-24  
**Experiment ID:** `v3-a05-favorite-safe-coverage`  
**Flag:** `F_V3_A05_ADM_FAVSAFE_ENABLED`（既定 **OFF**）  
**Stage:** Admission のみ  
**Design:** [`v3-admission-correction-design.md`](./v3-admission-correction-design.md) · [`v3-admission-correction-spec.md`](./v3-admission-correction-spec.md)  
**Decision:** **PASS**（Offline Hard Gate）  
**PRR:** HOLD 継続  
**Artifacts:** `research/v3_lab/baselines/a05_accuracy/`

---

## 1. 目的

A-03 過剰 promote による Offline 本命破壊を、**A-03 を変更せず**独立候補 A-05 で改善する。

---

## 2. 変更ファイル一覧

| ファイル | 変更 |
|----------|------|
| `research/v3_lab/admission_policy_a05.py` | **新規** A-05 Favorite-Safe Coverage |
| `research/v3_lab/flags.py` | `F_V3_A05_ADM_FAVSAFE_ENABLED` 追加（既定 False）· A-03 同時 ON 禁止 |
| `research/v3_lab/stages.py` | Admission に A-05 分岐（A-03 分岐は残置） |
| `research/v3_lab/a05_accuracy.py` | **新規** Lab + Offline AB harness |
| `research/v3_lab/registry.py` | A-05 実験登録 |
| `docs/releases/v3-a05-accuracy-report.md` | 本文書 |
| `docs/releases/v3-a05-race-diff-report.md` | 改善/悪化レース |
| `research/v3_lab/baselines/a05_accuracy/*` | AB JSON |

**未変更（凍結）:** `admission_policy_a03.py` · Representation · Selection · Evaluation · Purchase · Production · Flag 既定（他 Flag）· A-03 既定 OFF 維持

---

## 3. AB 設計

| Arm | Flags |
|-----|-------|
| Control | 全 OFF（identity top-1） |
| A-03 | `F_V3_A03_POOL_ADMIT_ENABLED=ON` |
| A-05 | `F_V3_A05_ADM_FAVSAFE_ENABLED=ON` |

評価面: **Lab Accuracy 285R** と **Offline Real 285R**。  
A-03∧A-05 同時 ON → `ValueError`（mutex 確認済み）。

---

## 4. Hard Gate（Offline 主判定）

| 条件 | 結果 |
|------|------|
| `worsened_winner_rank1 = 0` | **0** ✓ |
| `ΔHit > 0`（vs Control） | **+7** ✓ |
| churn_hit（報告） | **0** |
| Lab 279 再現 | 非必須（A-05 Lab Hit=218） |

**Decision: PASS**

---

## 5. Lab 結果

| Arm | Hit | Purchase | ROI | churn_hit | worsened_rank1 | ΔHit |
|-----|-----|----------|-----|-----------|----------------|------|
| Control | **218** | 218 | 1.1418 | — | — | — |
| A-03 | **227** | 227 | 2.4049 | 0 | 0 | +9 |
| A-05 | **218** | 218 | 1.1418 | 0 | 0 | **0** |

A-05 は Lab 合成（小頭数・低 odds 本命・低 history スケール）では promote せず Control と一致。  
Lab Pool×9 の A-03 加点は意図的に再現しない（Design: Lab279 非必須 · Offline 優先）。

---

## 6. Offline 結果（主判定）

| Arm | Hit | Purchase | ROI | churn_hit | pick_churn | worsened_rank1 | ΔHit |
|-----|-----|----------|-----|-----------|------------|----------------|------|
| Control | **59** | 59 | 0.0246 | — | — | — | — |
| A-03 | **42** | 42 | 0.2021 | 28 | 151 | **28** | **−17** |
| A-05 | **66** | 66 | 0.5235 | **0** | 46 | **0** | **+7** |

| 比較 | 値 |
|------|-----|
| A-05 − Control Hit | +7 |
| A-05 − A-03 Hit | +24 |
| A-05 improved | **7** |
| A-05 worsened | **0** |

---

## 7. A-05 政策要約

Conditional Hard Promote（すべて必須）:

1. `field_size >= 12` かつ deep 候補  
2. 複合 Coverage: style rarity ∧ hist ≥ deep median ∧ `cand_rank <= 11`  
3. Favorite-Safe: `margin < 0.04` ∧ `top_odds >= 4.5` ∧ `top_wp < 0.20`  

結果列（winner / finish）は入力に使用しない。

---

## 8. 改善 / 悪化レース

詳細: [`v3-a05-race-diff-report.md`](./v3-a05-race-diff-report.md) · `baselines/a05_accuracy/a05_race_diff.json`

| Surface | A-05 improved | A-05 worsened |
|---------|---------------|---------------|
| Lab | 0 | 0 |
| Offline | 7 | 0 |

---

## 9. 解釈

- Offline で A-03 の本命破壊を封じ、net Hit を Control 超へ改善。  
- Lab では A-03 の Pool 加点を捨てる（分布差 · 設計どおり）。  
- Baseline v3（A-01+A-03+A-04）の置換は **未実施**（Candidate Review / Validation は次 Round）。

---

## 10. 停止

**A-05 Accuracy 実装・AB 完了。ここで停止する。**  
Validation · Shadow · Production · Phase 3 には着手しない。
