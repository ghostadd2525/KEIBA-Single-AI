# Version 3 — A-04 Validation Report（Selection History Crowding）

**Date:** 2026-07-24  
**Validation ID:** `v3-a04-validation/1.0`  
**Experiment ID:** `v3-a04-sel-history`  
**Flag:** `F_V3_A04_SEL_HISTORY_ENABLED`（既定 OFF）  
**Lab Accuracy Report:** [`v3-a04-accuracy-report.md`](./v3-a04-accuracy-report.md)  
**Artifacts:** `research/v3_lab/baselines/a04_validation/`

---

## 1. 目的

A-04（Selection History Crowding）が Lab PASS だけでなく、  
**正式採用候補として再現可能**であることを検証する。

対象: **A-04 単独** および **Lab Baseline v2（A-01+A-03）→ +A-04**。  
新しい Accuracy アルゴリズムは追加しない。

---

## 2. Decision

| 項目 | 結果 |
|------|------|
| **採用可否** | **PASS** |
| Lab 採用候補 | Yes（`adopt_lab=true`） |
| Production wiring | **False**（未配線） |

| Gate | Solo | Baseline v2 → +A-04 |
|------|------|---------------------|
| Hit 改善 | 218→**242** | 255→**279**（>255） |
| churn | **0** | **0** |
| Boundary 14 | **再現** | **再現** |
| Reorder 10 | **再現** | **再現** |
| 悪化 | 0 | 0 |

---

## 3. Metric Summary

### 3.1 A-04 単独（Baseline OFF → A-04 ON）

| 指標 | Control | Treatment | Δ |
|------|---------|-----------|---|
| Hit | 218 | **242** | **+24** |
| Purchase | 218 | 242 | +24 |
| rank710 | 9 | 9 | 0 |
| rank46 | 6 | 6 | 0 |
| other | 52 | 28 | −24 |
| ROI | 1.1418 | 1.4744 | +0.3326 |
| churn | — | **0** | — |

### 3.2 Baseline v2 + A-04（Hard Gate）

| 指標 | Control (A-01+A-03) | Treatment (+A-04) | Δ |
|------|---------------------|-------------------|---|
| Hit | **255** | **279** | **+24** |
| Purchase | 255 | 279 | +24 |
| rank710 | 0 | 0 | 0 |
| rank46 | 6 | 6 | 0 |
| other | 24 | **0** | −24 |
| ROI | 2.7095 | **3.0421** | +0.3326 |
| churn | — | **0** | — |

詳細 JSON: `baselines/a04_validation/a04_metric_summary.json`

---

## 4. 再現性確認

| 項目 | 結果 |
|------|------|
| ラウンド数 | **2**（独立フル `run_a04_ab`） |
| 指標完全一致 | **PASS** |
| 期待値一致（stack 255→279 · Boundary14 · Reorder10 · churn0） | **PASS** |
| Corpus fingerprint | `442afd28877be24ad4d36022` |

---

## 5. 入力一致・Flag 比較

| 項目 | 結果 |
|------|------|
| Corpus N | 285（`a03-285-*`） |
| Control / Treatment race_id 集合一致 | **PASS** |
| Solo OFF/ON | 218 / 242 |
| Stack Baseline v2 / +A-04 | 255 / 279 |
| Flag 既定 | `F_V3_A04_SEL_HISTORY_ENABLED` = **OFF** |

---

## 6. Stage 隔離・SHA

### A-04 単独 ON

| Stage | 期待 | 結果 |
|-------|------|------|
| Representation | OFF | PASS |
| Admission | identity | PASS |
| Selection | SEL-V3-A04 | PASS |
| Evaluation | OFF | PASS |
| Purchase | identity | PASS |

### Baseline v2 + A-04

| Stage | 期待 | 結果 |
|-------|------|------|
| Representation | OFF | PASS |
| Admission | AP-V3-A03 | PASS |
| Selection | SEL-V3-A04 | PASS |
| Evaluation | D1 | PASS |
| Purchase | identity | PASS |
| D2 / P3 / P4 Flag | OFF | PASS |

### Frozen SHA16

| Module | Match |
|--------|-------|
| `feature_generator.py` | ✓ |
| `admission_policy.py`（P3） | ✓ |
| `admission_policy_a03.py` | ✓ |
| `evaluation_policy.py` | ✓ |
| `evaluation_policy_d2.py` | ✓ |
| `selection_policy.py`（P4） | ✓ |
| `selection_policy_a04.py` | ✓（Validation スナップショット） |

---

## 7. Race Diff（要約）

| Panel | Improved | Worsened | Boundary | Reorder |
|-------|----------|----------|----------|---------|
| A-04 solo | 24 | 0 | **14** | **10** |
| Baseline v2 + A-04 | 24 | 0 | **14** | **10** |

詳細: [`v3-a04-validation-race-diff-report.md`](./v3-a04-validation-race-diff-report.md)

---

## 8. 提出物

| 提出物 | 場所 |
|--------|------|
| Validation Report | 本ドキュメント |
| Race Diff Report | `v3-a04-validation-race-diff-report.md` |
| Metric Summary | §3 + JSON |
| 再現性 | §4 |
| 採用可否 | **PASS** |

Harness: `research/v3_lab/a04_validation.py`  
Tests: `research/v3_lab/tests/test_a04_validation.py`

---

## 9. 停止

**A-04 Validation 完了。ここで停止する。**  
Offline Gate · Shadow · Phase 3 · 本番 Flag ON には着手しない。
