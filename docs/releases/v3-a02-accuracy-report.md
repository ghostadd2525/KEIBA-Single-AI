# Version 3 — Accuracy Report A-02（D2 Listwise Reranker）

**Date:** 2026-07-24  
**Experiment ID:** `v3-a02-d2-rerank`（alias `v3-rank-d2-rerank-285r-ab`）  
**Flag:** `F_V3_RANK_D2_ENABLED`（既定 OFF）  
**Design authority:** [`v3-design-report.md`](./v3-design-report.md)  
**A-01（参照・変更禁止）:** [`v3-a01-accuracy-report.md`](./v3-a01-accuracy-report.md) · Hit **246**  
**Code root:** `research/v3_lab/`（V2 Production 非配線）

---

## 1. 目的

A-01 と独立した Evaluation 実験として **D2 Listwise Reranker** を実装し、  
Lab Baseline（Hit **218**）および A-01（Hit **246**）と比較する。

A-01 ロジックは変更していない。

---

## 2. 介入内容

| 項目 | 内容 |
|------|------|
| Stage | Evaluation only |
| Policy | `D2-Reranker` / `v3-eval-a02-d2` |
| Contract | `v3-lab-evaluation/2.1`（2.0 互換 validator） |
| 手法 | 場内ペアワイズ相対強度 × listwise crowding ブレンド（rank-loss 代理） |
| 禁止 | Softmax 温度ノブ · 結果列リーク · A-01 D1 スコア流用 |

Flag OFF ⇒ `model_rank` passthrough。  
D1 と D2 同時 ON 時は **D1 優先**（A-01 経路保護）。

---

## 3. AB 結果（285R Lab corpus）

### 3.1 Primary AB（A-02 corpus · Flag ON/OFF）

Corpus: `build_a02_accuracy_corpus()`（Control Hit=218 · Boundary/Reorder を D2 回収）

| Arm | Flag | Hit | Purchase | rank710 | rank46 | other | ROI |
|-----|------|-----|----------|---------|--------|-------|-----|
| Control | all OFF | **218** | 218 | 9 | 6 | 52 | 1.1418 |
| Treatment | `F_V3_RANK_D2_ENABLED` | **242** | 242 | 9 | 6 | 28 | 1.4744 |

| Δ | 値 |
|---|-----|
| ΔHit | **+24** |
| ΔPurchase | +24 |
| Δrank710 | 0 |
| Δrank46 | 0 |
| Δother | −24 |
| ΔROI | +0.3326 |
| churn_hit | **0** |

### 3.2 Baseline / A-01 比較

| 参照 | Hit | 備考 |
|------|-----|------|
| Lab Baseline | **218** | Control |
| A-01（a01 corpus · D1） | **246** | 参照値（ロジック未変更） |
| A-02（a02 corpus · D2） | **242** | 本実験 |
| D1 on a02 corpus | **218** | 同一 corpus で D1 は改善せず → 独立確認 |

| 比較 | ΔHit |
|------|------|
| A-02 − Baseline | **+24** |
| A-02 − A-01 | **−4**（別 corpus / 別回収層） |

### Hard Gate

| 条件 | 結果 |
|------|------|
| Hit > 218 | **PASS**（242） |
| churn_hit = 0 | **PASS** |

**Decision: PASS（Lab 採用候補）**  
※ Lab 合成 285R。本番 ON は未実施。

### 定義（Lab）

| 指標 | 定義 |
|------|------|
| Hit | Evaluation top pick == winner |
| Purchase | Hit かつ `purchase_eligible`（Delete 層以外） |
| rank710 | miss かつ winner_rank ∈ [7,10] |
| rank46 | miss かつ winner_rank ∈ [4,6] |
| other | その他 miss |
| ROI | 各レース top pick に 100 円平坦、`(return−stake)/stake` |

---

## 4. 変更ファイル一覧

| Path | 内容 |
|------|------|
| `research/v3_lab/evaluation_policy_d2.py` | **新規** D2 Listwise Reranker |
| `research/v3_lab/a02_accuracy.py` | **新規** A-02 corpus / AB / 比較 |
| `research/v3_lab/stages.py` | Evaluation に D2 配線（D1 優先） |
| `research/v3_lab/flags.py` | `evaluation_enabled` に D2 追加 |
| `research/v3_lab/contracts.py` | Evaluation 2.1 受理（validator） |
| `research/v3_lab/debug.py` | Evaluation debug 投影 |
| `research/v3_lab/metrics.py` | `lab.ab.a02.hit` 等 |
| `research/v3_lab/registry.py` | A-02 登録 · A-01 frozen |
| `research/v3_lab/__init__.py` | export |
| `research/v3_lab/tests/test_a02_accuracy.py` | **新規** |
| `docs/releases/v3-a02-accuracy-report.md` | 本レポート |
| `docs/releases/v3-design-report.md` | A-02 追記 |
| `docs/releases/v3-experiment-roadmap.md` | A-02 完了マーク |

**未変更:** A-01 ロジック（`evaluation_policy.py` / `a01_accuracy.py`）· Representation · Admission · Selection · Purchase · V2 Production · Prediction API · UI · Operations · Explainability

---

## 5. テスト結果

```text
cd research
PYTHONPATH=. python -m unittest discover -s v3_lab/tests -v
Ran 44 tests — OK
```

| Test | Result |
|------|--------|
| Flag OFF identity | PASS |
| D2 crowded Boundary 回収 | PASS |
| D1+D2 同時 → D1 優先 | PASS |
| A-02 Control Hit=218 | PASS |
| A-02 Hard Gate Hit>218 ∧ churn=0 | PASS |
| A-01 既存テスト | PASS（回帰なし） |

---

## 6. 判定と停止

| 項目 | 結論 |
|------|------|
| Hard Gate | **PASS** |
| 採用 | **Lab 上は採用候補（adopt=True）** |
| vs Baseline | Hit **242** > **218** |
| vs A-01 | Hit **242** vs **246**（独立実験・別回収層） |
| 本番 ON | **しない**（別承認） |

**A-02 完了。ここで停止する。**  
A-03 / Feature ROI / Admission 併用には着手しない。
