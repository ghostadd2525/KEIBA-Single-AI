# Version 3 — A-01 Validation Report（Evaluation D1）

**Date:** 2026-07-24  
**Validation ID:** `v3-a01-validation/1.0`  
**Experiment ID:** `v3-a01-d1-recal`  
**Flag:** `F_V3_RANK_D1_ENABLED`（既定 OFF）  
**Lab Accuracy Report:** [`v3-a01-accuracy-report.md`](./v3-a01-accuracy-report.md)  
**Artifacts:** `research/v3_lab/baselines/a01_validation/`

---

## 1. 目的

A-01（Evaluation D1）が Lab PASS だけでなく、**正式採用候補として十分な再現性・隔離性・差分品質**を持つことを検証する。

本 Validation では **新しい Accuracy アルゴリズムは追加しない**。

---

## 2. 実施範囲

| 実施 | 内容 |
|------|------|
| ✓ | 285R 再評価（再現性） |
| ✓ | Control / Treatment 入力一致 |
| ✓ | Feature Flag ON/OFF 比較 |
| ✓ | Race 単位差分 / 改善・悪化一覧 |
| ✓ | rank710 / rank46 / other 詳細 |
| ✓ | ROI 再計算 / churn 詳細 |
| ✓ | Evaluation 以外の非変更確認 |
| ✓ | Decision Report |

| 禁止（遵守） | Representation · Admission · Selection · Purchase · Prediction API · UI · Operations · Explainability · V2 Production |

---

## 3. Decision

| 項目 | 結果 |
|------|------|
| **採用可否** | **PASS** |
| Lab 採用候補 | Yes（`adopt_lab=true`） |
| Production wiring | **False**（未配線） |

Hard Gate（再確認）: Hit **246** > 218 ∧ churn_hit **0** → PASS

---

## 4. Metric Summary

| Arm | Flag | Hit | Purchase | rank710 | rank46 | other | ROI |
|-----|------|-----|----------|---------|--------|-------|-----|
| Control | OFF | **218** | 218 | 9 | 6 | 52 | 1.1418 |
| Treatment | ON | **246** | 246 | 9 | 6 | 24 | 1.4463 |

| Δ | 値 |
|---|-----|
| ΔHit | **+28** |
| ΔPurchase | +28 |
| Δrank710 | 0 |
| Δrank46 | 0 |
| Δother | −28 |
| ΔROI | +0.3045 |
| churn_hit | **0**（悪化レースなし） |

ROI 定義: 各レース top pick に 100 円平坦、`(return − stake) / stake`  
詳細 JSON: `baselines/a01_validation/a01_metric_summary.json`

---

## 5. 再現性確認

| 項目 | 結果 |
|------|------|
| ラウンド数 | 2（独立フル AB） |
| 指標完全一致 | **PASS** |
| 期待値一致（218→246, churn=0, ΔHit=28） | **PASS** |

---

## 6. 入力一致・Flag 比較

| 項目 | 結果 |
|------|------|
| Corpus N | 285 |
| Corpus fingerprint | `1bd7dc9902871671345f552a` |
| Control/Treatment race_id 集合一致 | **PASS** |
| Flag OFF | Hit 218（identity） |
| Flag ON | Hit 246（D1 のみ） |

---

## 7. Stage 隔離・凍結モジュール

D1 Flag のみ ON 時:

| Stage | 期待 | 結果 |
|-------|------|------|
| Representation | disabled | PASS |
| Admission | identity | PASS |
| Selection | identity | PASS |
| Evaluation | enabled | PASS |
| Purchase | identity mapper | PASS |

凍結 SHA16（A-01 完了時スナップショット維持）:

| Module | SHA16 | Match |
|--------|-------|-------|
| `feature_generator.py` | `32a71445b03ddb65` | ✓ |
| `admission_policy.py` | `78a79ebce7786dea` | ✓ |
| `selection_policy.py` | `cea5a9befae0b1a6` | ✓ |

---

## 8. Race Diff（要約）

| 区分 | 件数 |
|------|------|
| Improved（miss→hit） | **28**（すべて Eval 層） |
| Worsened / churn | **0** |
| Unchanged hit | 218 |
| Unchanged miss | 39 |

バケット: rank710 / rank46 は Control・Treatment とも不変（9 / 6）。改善 28 はすべて `other` miss の解消。

Race Diff Report: [`v3-a01-race-diff-report.md`](./v3-a01-race-diff-report.md)  
フル一覧: `baselines/a01_validation/a01_race_diff.json`

---

## 9. 提出物チェック

| 提出物 | 場所 |
|--------|------|
| Validation Report | 本ドキュメント |
| Race Diff Report | `v3-a01-race-diff-report.md` |
| Metric Summary | `a01_metric_summary.json` + §4 |
| 再現性確認結果 | §5 |
| 採用可否 | **PASS** |

フル結果: `baselines/a01_validation/a01_validation_full.json`  
Harness: `research/v3_lab/a01_validation.py`  
Tests: `research/v3_lab/tests/test_a01_validation.py`

---

## 10. 停止条件

**A-01 Validation 完了。ここで停止する。**  
A-02 および新規 Accuracy 施策には着手しない。本番 Flag ON は別承認。
