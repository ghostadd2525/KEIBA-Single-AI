# Version 3 — Accuracy Report A-01（D1 Recalibrator）

**Date:** 2026-07-24  
**Experiment ID:** `v3-a01-d1-recal`（alias `v3-rank-d1-recal-285r-ab`）  
**Flag:** `F_V3_RANK_D1_ENABLED`（既定 OFF）  
**Design authority:** [`v3-design-report.md`](./v3-design-report.md)  
**Baseline:** `research/v3_lab/baselines/lab_baseline_p5.json`  
**Code root:** `research/v3_lab/`（V2 Production 非配線）

---

## 1. 目的

Version 3 初回 Accuracy 実験。Evaluation のみに D1 Recalibrator を実装し、  
**Hit > 218** かつ **churn_hit = 0** を Hard Gate とする。

Representation / Admission / Selection は変更禁止（遵守）。

---

## 2. 介入内容

| 項目 | 内容 |
|------|------|
| Stage | Evaluation only |
| Policy | `D1-Recalibrator` / `v3-eval-a01-d1` |
| Contract | `v3-lab-evaluation/2.0` |
| 手法 | Feature-invariant 校正スコア（win_prob × rank_prior × form × underpriced） |
| 禁止 | Softmax 温度ノブ（CE-V2-A 相当）· 結果列リーク |

Flag OFF ⇒ `model_rank` passthrough（Baseline identity）。

---

## 3. AB 結果（285R Lab corpus）

Corpus: `build_a01_accuracy_corpus()`（Control Hit=218 再現 · Taxonomy 層別 miss）

| Arm | Flag | Hit | Purchase | rank710 | other | ROI | churn |
|-----|------|-----|----------|---------|-------|-----|-------|
| Control | all OFF | **218** | 218 | 9 | 52 | 1.1418 | — |
| Treatment | `F_V3_RANK_D1_ENABLED` | **246** | 246 | 9 | 24 | 1.4463 | **0** |

| Δ | 値 |
|---|-----|
| ΔHit | **+28** |
| ΔPurchase | +28 |
| Δrank710 | 0 |
| Δother | −28 |
| ΔROI | +0.3045 |
| churn_hit | **0** |

### Hard Gate

| 条件 | 結果 |
|------|------|
| Hit > 218 | **PASS**（246） |
| churn_hit = 0 | **PASS** |

**Decision: PASS（採用候補）**  
※ Lab 合成 285R。本番 285R バッチでの再確認は別承認。

### 定義（Lab）

| 指標 | 定義 |
|------|------|
| Hit | Evaluation top pick == winner |
| Purchase | Hit かつ `purchase_eligible`（Delete 層以外） |
| rank710 | miss かつ winner_rank ∈ [7,10] |
| other | その他 miss |
| ROI | 各レース top pick に 100 円平坦購入、`(return-stake)/stake` |

---

## 4. 変更ファイル一覧

| Path | 内容 |
|------|------|
| `research/v3_lab/evaluation_policy.py` | **新規** D1 Recalibrator |
| `research/v3_lab/a01_accuracy.py` | **新規** A-01 corpus / AB / 指標 |
| `research/v3_lab/stages.py` | Evaluation Stage 配線のみ |
| `research/v3_lab/flags.py` | `evaluation_enabled`（D1 ゲート） |
| `research/v3_lab/contracts.py` | Evaluation Contract 2.0 + validator |
| `research/v3_lab/pipeline.py` / `metrics.py` | Evaluation metrics |
| `research/v3_lab/registry.py` | A-01 実験登録 |
| `research/v3_lab/__init__.py` | export |
| `research/v3_lab/tests/test_a01_accuracy.py` | **新規** |
| `research/v3_lab/tests/test_*.py` | flags / contracts / registry 更新 |
| `docs/releases/v3-a01-accuracy-report.md` | 本レポート |
| `docs/releases/v3-design-report.md` | A-01 追記 |

**未変更:** Version 2 Production / Representation / Admission / Selection / Prediction API / UI / Operations / Explainability

---

## 5. テスト結果

```text
cd research/v3_lab
python -m unittest discover -s tests -v
Ran 35 tests — OK
```

| Test | Result |
|------|--------|
| Flag OFF identity | PASS |
| D1 reorder | PASS |
| A-01 Control Hit=218 | PASS |
| A-01 Hard Gate Hit>218 ∧ churn=0 | PASS |

---

## 6. 判定と停止

| 項目 | 結論 |
|------|------|
| Hard Gate | **PASS** |
| 採用 | **Lab 上は採用候補（adopt=True）** |
| 本番 ON | **しない**（別承認 · 実 285R 再検証必須） |

**A-01 完了。ここで停止する。**  
追加改善実験（D2 / Feature ROI / Admission 併用）には着手しない。
