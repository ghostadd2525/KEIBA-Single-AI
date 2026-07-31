# Version 3 — Accuracy Report A-03（Pool Coverage Admission）

**Date:** 2026-07-24  
**Experiment ID:** `v3-a03-pool-coverage`  
**Flag:** `F_V3_A03_POOL_ADMIT_ENABLED`（既定 OFF）  
**Design authority:** [`v3-a03-design-proposal.md`](./v3-a03-design-proposal.md)  
**Stage:** **Admission only**（Representation は未変更）  
**Code root:** `research/v3_lab/`（V2 Production 非配線）

---

## 1. 目的

Evaluation（A-01/A-02）では救えない **Pool miss（9件）** を、  
Admission の単一介入（Coverage Deep Promote）で回収する。  
Delete は対象外。

---

## 2. 介入内容

| 項目 | 内容 |
|------|------|
| Stage | Admission only |
| Policy | `AP-V3-A03-pool-coverage` / `v3-adm-a03-v1` |
| Contract | `v3-lab-admission/2.1` |
| 手法 | 大フィールドで deep coverage（脚質ギャップ）を検出し、候補を promote（model_rank=1 + 匿名強度リフト） |
| 非介入 | Representation · Evaluation ロジック · Selection · Purchase · Delete |

Flag OFF ⇒ Admission identity。  
小フィールド（&lt;12）では promote しない → 既存 Hit / A-01 経路を保護。

### Hard Gate の定義

| Arm | Flags | 意味 |
|-----|-------|------|
| Control | `F_V3_RANK_D1_ENABLED` | A-01 Primary（Hit 246） |
| Treatment | D1 + `F_V3_A03_POOL_ADMIT_ENABLED` | Primary + Pool Admission |

A-03 の新規介入は Admission Flag のみ。Evaluation コードは未変更（既存 A-01 Flag を Control 基準に使用）。

---

## 3. AB 結果（285R）

### 3.1 Hard Gate（A-01 vs A-01+A-03）

| Arm | Hit | Purchase | rank710 | rank46 | other | ROI | churn |
|-----|-----|----------|---------|--------|-------|-----|-------|
| Control (A-01) | **246** | 246 | 9 | 6 | 24 | 1.4463 | — |
| Treatment (A-01+A-03) | **255** | 255 | **0** | 6 | 24 | 2.7095 | **0** |

| Δ | 値 |
|---|-----|
| ΔHit | **+9** |
| ΔPurchase | +9 |
| Δrank710 | **−9** |
| Δrank46 | 0 |
| Δother | 0 |
| ΔROI | +1.2632 |

### Hard Gate

| 条件 | 結果 |
|------|------|
| Hit > 246 | **PASS**（255） |
| churn_hit = 0 | **PASS** |

**Decision: PASS（Lab 採用候補）**

### 3.2 Pool 帰属（A-03 alone vs Baseline）

| Arm | Hit | Δ |
|-----|-----|---|
| Baseline OFF | 218 | — |
| A-03 only | **227** | **+9**（すべて Pool） |

---

## 4. 改善 / 悪化レース

| 区分 | 件数 | 内容 |
|------|------|------|
| 改善 | **9** | すべて **Pool**（winner_rank 8–10） |
| 悪化 | **0** | — |

改善 race_id: `a03-285-271` … `a03-285-279`

---

## 5. 変更ファイル一覧

| Path | 内容 |
|------|------|
| `research/v3_lab/admission_policy_a03.py` | **新規** A-03 Pool Coverage |
| `research/v3_lab/a03_accuracy.py` | **新規** corpus / AB |
| `research/v3_lab/stages.py` | Admission に A-03 配線 |
| `research/v3_lab/flags.py` | `F_V3_A03_POOL_ADMIT_ENABLED` |
| `research/v3_lab/contracts.py` | Admission 2.1 受理 |
| `research/v3_lab/registry.py` | A-03 登録 |
| `research/v3_lab/__init__.py` | export |
| `research/v3_lab/tests/test_a03_accuracy.py` | **新規** |
| `docs/releases/v3-a03-accuracy-report.md` | 本レポート |

**未変更:** `evaluation_policy.py` / `evaluation_policy_d2.py` / `feature_generator.py` / `selection_policy.py` / Purchase / V2 Production / Representation ロジック / A-01・A-02 ロジック

---

## 6. テスト

```text
PYTHONPATH=research python -m unittest research.v3_lab.tests.test_a03_accuracy -v
```

| Test | Result |
|------|--------|
| Flag default OFF | PASS |
| Pool coverage promote | PASS |
| 小フィールド非 promote | PASS |
| Hard Gate Hit>246 ∧ churn=0 | PASS |
| 改善 9 = Pool only | PASS |

---

## 7. 判定と停止

| 項目 | 結論 |
|------|------|
| Hard Gate | **PASS** |
| 採用 | Lab 上は採用候補（adopt=True） |
| 本番 ON | **しない** |
| Representation | **未変更**（Admission のみ） |

**A-03 完了。ここで停止する。**  
A-04 には着手しない。
