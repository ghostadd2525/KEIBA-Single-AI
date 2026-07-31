# Version 3 — Phase 2 Baseline Report（Lab Baseline v2）

**Date:** 2026-07-24  
**Baseline ID:** `v3-lab-baseline-v2-a01-a03`  
**Freeze ID:** `v3-lab-configuration-freeze/1.0`  
**Parent:** `v3-lab-baseline-p5-v1`（基盤は維持）  
**Artifact:** `research/v3_lab/baselines/lab_baseline_v2_a01_a03.json`  

> **注記:** 公式 Accuracy スタックは Phase 2 Close により  
> [`v3-phase2-baseline-v3-report.md`](./v3-phase2-baseline-v3-report.md)（Hit 279）へ更新。  
> 本 v2 は履歴として保持する。

---

## 1. 定義

Lab Baseline v2 は **採用スタック A-01（Evaluation）+ A-03（Admission）** の測定結果を固定した Accuracy 基準線である。

| 項目 | 値 |
|------|-----|
| Corpus | `build_a03_accuracy_corpus()` · 285R |
| Control | 全 Flag OFF · Hit **218** |
| Stack | D1 + A-03 Admit · Hit **255** |
| churn vs Control | **0** |
| churn vs A-01 | **0** |

---

## 2. 構成図

```text
Representation (Baseline)
        ↓
Admission (A-03 Pool Coverage)
        ↓
Selection (Baseline)
        ↓
Evaluation (A-01 D1 Recalibrator)
        ↓
Purchase (Baseline)
```

---

## 3. Metric Snapshot

| Arm | Hit | Purchase | rank710 | rank46 | other | ROI |
|-----|-----|----------|---------|--------|-------|-----|
| Control | 218 | 218 | 9 | 6 | 52 | 1.1418 |
| A-01 only | 246 | 246 | 9 | 6 | 24 | 1.4463 |
| **v2 Stack** | **255** | **255** | **0** | 6 | 24 | **2.7095** |

Δ Stack − Control: Hit **+37** · rank710 **−9**

---

## 4. Invariants（Freeze）

| 条件 | 値 |
|------|-----|
| control_hit_218 | True |
| stack_hit_255 | True |
| churn_vs_control_0 | True |
| churn_vs_a01_0 | True |
| production_wiring | False |
| algorithms_unchanged | True |

---

## 5. 非採用（本 Baseline 外）

| 項目 | 扱い |
|------|------|
| A-02 D2 | Secondary Candidate として保持 |
| P3 `F_V3_ADMISSION` (AP-V3-A) | スタック外（A-03 Flag を使用） |
| Representation / Selection ON | Baseline のまま |

---

## 6. 参照

| 文書 | パス |
|------|------|
| Configuration Report | `v3-lab-configuration-report.md` |
| A-01 Report / Validation | `v3-a01-accuracy-report.md` · `v3-a01-validation-report.md` |
| A-03 Report / Validation | `v3-a03-accuracy-report.md` · `v3-a03-validation-report.md` |
