# Version 3 — A-05 Validation Report（Favorite-Safe Coverage）

**Date:** 2026-07-24  
**Validation ID:** `v3-a05-validation/1.0`  
**Experiment ID:** `v3-a05-favorite-safe-coverage`  
**Flag:** `F_V3_A05_ADM_FAVSAFE_ENABLED`（既定 OFF · 未変更）  
**Accuracy Report:** [`v3-a05-accuracy-report.md`](./v3-a05-accuracy-report.md)  
**Artifacts:** `research/v3_lab/baselines/a05_validation/`  
**Harness:** `research/v3_lab/a05_validation.py`

---

## 1. 目的

A-05（Favorite-Safe Coverage）が Offline Hard Gate を **再現可能**であることを検証する。

対象: **Control（Flag OFF）** vs **A-05 ON**。  
新しいアルゴリズム・Flag 既定値変更・Production 配線は行わない。

---

## 2. Decision

| 項目 | 結果 |
|------|------|
| **Decision** | **PASS** |
| Lab 採用候補 | Yes（`adopt_lab=true`） |
| Production wiring | **False**（未配線） |
| PRR | **HOLD** 継続 |

| Gate | 結果 |
|------|------|
| Offline Hit 59→66（Δ+7） | **再現** |
| worsened_winner_rank1 = 0 | **再現** |
| worsened = 0 | **再現** |
| improved = 7（同一 race_id） | **再現** |
| churn_hit = 0 | **再現** |
| 2 ラウンド指標一致 | **PASS** |
| SHA / 入力一致 / 隔離 | **PASS** |

---

## 3. Metric Summary

### 3.1 Offline（主判定 · Control vs A-05）

| 指標 | Control (OFF) | Treatment (A-05) | Δ |
|------|---------------|------------------|---|
| Hit | **59** | **66** | **+7** |
| Purchase | 59 | 66 | +7 |
| rank710 | 37 | 32 | −5 |
| rank46 | 101 | 101 | 0 |
| other | 88 | 86 | −2 |
| ROI | 0.0246 | **0.5235** | +0.4989 |
| churn_hit | — | **0** | — |
| pick_churn | — | 46 | — |
| worsened_winner_rank1 | — | **0** | — |

### 3.2 Lab（参考 · Control vs A-05）

| 指標 | Control | A-05 | Δ |
|------|---------|------|---|
| Hit | 218 | 218 | 0 |
| Purchase | 218 | 218 | 0 |
| ROI | 1.1418 | 1.1418 | 0 |
| churn_hit | — | 0 | — |

詳細: `baselines/a05_validation/a05_metric_summary.json`

---

## 4. 再現性確認結果

| 項目 | 結果 |
|------|------|
| ラウンド数 | **2**（独立フル Offline Control/A-05） |
| 指標完全一致 | **PASS** |
| 期待値一致（59→66 · +7 · wr1=0 · improved7 · churn0 · ROI） | **PASS** |
| Corpus fingerprint | `c9ae4f172c5565cd0674c37b` |

---

## 5. 入力一致・Feature Flag ON/OFF

| 項目 | 結果 |
|------|------|
| Offline N | 285 |
| Control / Treatment race_id 集合一致 | **PASS** |
| Flag OFF Hit | 59 |
| Flag ON Hit | 66 |
| Flag 既定 `F_V3_A05_ADM_FAVSAFE_ENABLED` | **OFF**（確認） |
| A-03∧A-05 同時 ON | 拒否（mutex） |

---

## 6. Race Diff

詳細: [`v3-a05-validation-race-diff-report.md`](./v3-a05-validation-race-diff-report.md)

| | Offline |
|--|---------|
| Improved | **7**（Accuracy と同一 race_id） |
| Worsened | **0** |
| worsened_winner_rank1 | **0** |

---

## 7. Stage 隔離・SHA

### A-05 のみ ON

| Stage | 期待 | 結果 |
|-------|------|------|
| Representation | OFF | PASS |
| Admission | A-05 | PASS |
| Selection | identity | PASS |
| Evaluation | OFF | PASS |
| Purchase | identity | PASS |

### Frozen module SHA（16 hex）

| Module | Match |
|--------|-------|
| `admission_policy_a05.py` | PASS |
| `admission_policy_a03.py`（凍結） | PASS |
| Representation / Evaluation / Selection | PASS |

---

## 8. 変更範囲（本 Validation）

| 追加 | Validation harness · artifacts · 文書 |
|------|------|
| **未変更** | A-05/A-03 ロジック · Feature Flag 既定 · Production · API · UI · Ops · Explain |

---

## 9. 停止

**A-05 Validation 完了。Decision = PASS。**  
Shadow · Production · Phase 3 には着手しない。
