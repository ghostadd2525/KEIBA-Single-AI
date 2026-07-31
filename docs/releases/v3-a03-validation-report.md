# Version 3 — A-03 Validation Report（Admission Pool Coverage）

**Date:** 2026-07-24  
**Validation ID:** `v3-a03-validation/1.0`  
**Experiment ID:** `v3-a03-pool-coverage`  
**Flag:** `F_V3_A03_POOL_ADMIT_ENABLED`（既定 OFF）  
**Lab Accuracy Report:** [`v3-a03-accuracy-report.md`](./v3-a03-accuracy-report.md)  
**Artifacts:** `research/v3_lab/baselines/a03_validation/`

---

## 1. 目的

A-03（Admission Pool Coverage）が Lab PASS だけでなく、  
**正式採用候補として再現可能**であることを検証する。

対象: **A-03 単独** および **A-01 + A-03**。  
新しい Accuracy アルゴリズムは追加しない。

---

## 2. Decision

| 項目 | 結果 |
|------|------|
| **採用可否** | **PASS** |
| Lab 採用候補 | Yes |
| Production wiring | **False** |

| Gate | Solo | A-01+A-03 |
|------|------|-----------|
| Hit 改善 | 218→**227** | 246→**255**（>246） |
| churn | **0** | **0** |
| Pool 改善 9 件 | **再現** | **再現** |
| 悪化 | 0 | 0 |

---

## 3. Metric Summary

### 3.1 A-03 単独（Baseline OFF → A-03 ON）

| 指標 | Control | Treatment | Δ |
|------|---------|-----------|---|
| Hit | 218 | **227** | **+9** |
| Purchase | 218 | 227 | +9 |
| rank710 | 9 | **0** | −9 |
| rank46 | 6 | 6 | 0 |
| other | 52 | 52 | 0 |
| ROI | 1.1418 | 2.4049 | +1.2631 |
| churn | — | **0** | — |

### 3.2 A-01 + A-03（Hard Gate）

| 指標 | Control (A-01) | Treatment (A-01+A-03) | Δ |
|------|----------------|------------------------|---|
| Hit | 246 | **255** | **+9** |
| Purchase | 246 | 255 | +9 |
| rank710 | 9 | **0** | −9 |
| rank46 | 6 | 6 | 0 |
| other | 24 | 24 | 0 |
| ROI | 1.4463 | 2.7095 | +1.2632 |
| churn | — | **0** | — |

詳細 JSON: `baselines/a03_validation/a03_metric_summary.json`

---

## 4. 再現性確認

| 項目 | 結果 |
|------|------|
| ラウンド数 | **2**（独立フル `run_a03_ab`） |
| 指標完全一致 | **PASS** |
| 期待値一致（solo 227 / stack 255 / Pool+9 / churn0） | **PASS** |

---

## 5. 入力一致・Flag 比較

| 項目 | 結果 |
|------|------|
| Corpus N | 285（`a03-285-*`） |
| Corpus fingerprint | （artifact 参照） |
| race_id 集合一致 | **PASS** |
| Solo OFF/ON | 218 / 227 |
| Stack A-01 / A-01+A-03 | 246 / 255 |

---

## 6. Stage 隔離・SHA

### A-03 単独 ON

| Stage | 期待 | 結果 |
|-------|------|------|
| Representation | OFF | PASS |
| Admission | AP-V3-A03 | PASS |
| Selection | identity | PASS |
| Evaluation | OFF | PASS |
| Purchase | identity | PASS |

### A-01 + A-03

| Stage | 期待 | 結果 |
|-------|------|------|
| Representation | OFF | PASS |
| Admission | AP-V3-A03 | PASS |
| Selection | identity | PASS |
| Evaluation | D1 | PASS |
| Purchase | identity | PASS |

### Frozen SHA16

| Module | Match |
|--------|-------|
| `feature_generator.py` | ✓ |
| `evaluation_policy.py` | ✓ |
| `evaluation_policy_d2.py` | ✓ |
| `selection_policy.py` | ✓ |
| `admission_policy.py`（P3） | ✓ |
| `admission_policy_a03.py` | ✓（Validation スナップショット） |

---

## 7. Race Diff（要約）

| Panel | Improved | Worsened | Pool |
|-------|----------|----------|------|
| A-03 solo | 9 | 0 | **9** |
| A-01+A-03 | 9 | 0 | **9** |

詳細: [`v3-a03-race-diff-report.md`](./v3-a03-race-diff-report.md)

---

## 8. 提出物

| 提出物 | 場所 |
|--------|------|
| Validation Report | 本ドキュメント |
| Race Diff Report | `v3-a03-race-diff-report.md` |
| Metric Summary | §3 + JSON |
| 再現性 | §4 |
| 採用可否 | **PASS** |

Harness: `research/v3_lab/a03_validation.py`  
Tests: `research/v3_lab/tests/test_a03_validation.py`

---

## 9. 停止

**A-03 Validation 完了。ここで停止する。**  
A-04 には着手しない。本番 Flag ON は別承認。
