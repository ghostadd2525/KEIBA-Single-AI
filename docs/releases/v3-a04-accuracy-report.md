# Version 3 — Accuracy Report A-04（Selection History Crowding）

**Date:** 2026-07-24  
**Experiment ID:** `v3-a04-sel-history`  
**Flag:** `F_V3_A04_SEL_HISTORY_ENABLED`（既定 OFF）  
**Design authority:** [`v3-a04-problem-definition.md`](./v3-a04-problem-definition.md)  
**Stage:** **Selection only**  
**Code root:** `research/v3_lab/`（V2 Production 非配線）  
**Artifacts:** `research/v3_lab/baselines/a04_accuracy/`

---

## 1. 目的

Lab Baseline v2（Hit **255**）で残る **Boundary（14）+ Reorder（10）** を、  
Selection の単一介入で回収する。Delete は対象外。

---

## 2. 介入内容

| 項目 | 内容 |
|------|------|
| Stage | Selection only |
| Policy | `SEL-V3-A04-history-crowding` / `v3-sel-a04-v1` |
| Contract | `v3-lab-selection/2.0` |
| 手法 | トップ近傍混雑（crowding≥0.40）かつ history 優位（gap≥0.15）の枠内馬を promote（model_rank=1 + 匿名強度リフト） |
| 非介入 | Representation · Admission · Evaluation ロジック · Purchase · Delete |

Flag OFF ⇒ Selection identity。  
Clear field（Eval / Control / Pool 後）では promote しない → Baseline v2 Hit を保護。

### Hard Gate の定義

| Arm | Flags | 意味 |
|-----|-------|------|
| Control | `F_V3_RANK_D1_ENABLED` + `F_V3_A03_POOL_ADMIT_ENABLED` | Lab Baseline v2（Hit 255） |
| Treatment | Baseline v2 + `F_V3_A04_SEL_HISTORY_ENABLED` | + Selection A-04 |

A-04 の新規介入は Selection Flag のみ。Evaluation / Admission コードは未変更。

---

## 3. AB 結果（285R · `a03-285-*`）

### 3.1 Hard Gate（Baseline v2 vs +A-04）

| Arm | Hit | Purchase | rank710 | rank46 | other | ROI | churn |
|-----|-----|----------|---------|--------|-------|-----|-------|
| Control (A-01+A-03) | **255** | 255 | 0 | 6 | 24 | 2.7095 | — |
| Treatment (+A-04) | **279** | 279 | 0 | 6 | **0** | 3.0421 | **0** |

| Δ | 値 |
|---|-----|
| ΔHit | **+24** |
| ΔPurchase | +24 |
| Δrank710 | 0 |
| Δrank46 | 0 |
| Δother | **−24** |
| ΔROI | +0.3326 |

### Hard Gate

| 条件 | 結果 |
|------|------|
| Hit > 255 | **PASS**（279） |
| churn_hit = 0 | **PASS** |

**Decision: PASS（Lab）**

### 3.2 層帰属

| 層 | 改善 | 期待 |
|----|------|------|
| Boundary | **14** | 14 |
| Reorder | **10** | 10 |
| Delete | 0 | 対象外 |
| Eval / Pool | 0（非悪化） | — |

悪化レース: **0**

---

## 4. 改善 / 悪化レース

| 区分 | n | race_id |
|------|---|---------|
| 改善 Boundary | 14 | `a03-285-247` … `260` |
| 改善 Reorder | 10 | `a03-285-261` … `270` |
| 悪化 | 0 | — |

詳細 JSON: `research/v3_lab/baselines/a04_accuracy/a04_race_diff.json`

---

## 5. 変更ファイル一覧

| パス | 内容 |
|------|------|
| `research/v3_lab/selection_policy_a04.py` | **新設** A-04 Selection Policy |
| `research/v3_lab/a04_accuracy.py` | **新設** AB / race diff |
| `research/v3_lab/flags.py` | `F_V3_A04_SEL_HISTORY_ENABLED`（既定 OFF） |
| `research/v3_lab/stages.py` | A-04 経路配線（P4 非破壊） |
| `research/v3_lab/baselines/a04_accuracy/*` | AB 成果物 |
| `docs/releases/v3-a04-accuracy-report.md` | 本報告 |
| `docs/releases/v3-a04-race-diff-report.md` | 改善/悪化一覧 |
| `docs/releases/v3-feature-flag-inventory.md` | Flag 追記 |
| `docs/releases/v3-experiment-status.md` | 状態更新 |
| `docs/releases/v3-a04-problem-definition.md` | 実装完了注記 |
| `docs/releases/v3-design-report.md` | 追記 |
| `docs/releases/v3-experiment-roadmap.md` | 追記 |

**未変更:** `evaluation_policy.py` · `evaluation_policy_d2.py` · `admission_policy*.py` · `selection_policy.py`（P4）· `feature_generator.py` · Purchase · V2 Production · API · UI

---

## 6. 制約遵守

| 制約 | 結果 |
|------|------|
| Selection のみ変更 | **PASS** |
| Representation / Admission / Evaluation / Purchase 非変更 | **PASS** |
| 新規 Flag 既定 OFF | **PASS** |
| Delete 非対象 | **PASS**（rank46=6 残存） |
| 本番配線なし | **PASS** |

---

## 7. 停止

**A-04 完了。ここで停止する。**  
A-05 には着手しない。本番 Flag ON は別承認。
