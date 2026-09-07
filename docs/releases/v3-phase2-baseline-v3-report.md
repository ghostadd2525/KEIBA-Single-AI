# Version 3 — Phase 2 Baseline Report（Lab Baseline v3）

**Date:** 2026-07-24  
**Baseline ID:** `v3-lab-baseline-v3-a01-a03-a04`  
**Close ID:** `v3-accuracy-phase2-close/1.0`  
**Parent:** `v3-lab-baseline-v2-a01-a03`  
**Artifact:** `research/v3_lab/baselines/lab_baseline_v3_a01_a03_a04.json`

---

## 1. 定義

Lab Baseline v3 は **採用スタック A-01（Evaluation）+ A-03（Admission）+ A-04（Selection）** の測定結果を固定した Accuracy 基準線である。

| 項目 | 値 |
|------|-----|
| Corpus | `build_a03_accuracy_corpus()` · 285R |
| Control | 全 Flag OFF · Hit **218** |
| Baseline v2 | A-01 + A-03 · Hit **255** |
| Stack v3 | D1 + A-03 Admit + A-04 Sel · Hit **279** |
| churn vs Control | **0** |
| churn vs Baseline v2 | **0** |

---

## 2. 構成図

```text
Representation (Baseline)
        ↓
Admission (A-03 Pool Coverage)
        ↓
Selection (A-04 History Crowding)
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
| Baseline v2 | 255 | 255 | 0 | 6 | 24 | 2.7095 |
| **v3 Stack** | **279** | **279** | **0** | **6** | **0** | **3.0421** |

| Δ | Hit | other |
|---|-----|-------|
| Stack − Control | **+61** | −52 |
| Stack − Baseline v2 | **+24** | −24 |

---

## 4. Invariants（Phase 2 Close）

| 条件 | 値 |
|------|-----|
| control_hit_218 | True |
| baseline_v2_hit_255 | True |
| stack_hit_279 | True |
| churn_vs_control_0 | True |
| churn_vs_baseline_v2_0 | True |
| remaining_miss_delete_only | True |
| production_wiring | False |
| algorithms_unchanged | True |

---

## 5. 非採用（本 Baseline 外）

| 項目 | 扱い |
|------|------|
| A-02 D2 | Secondary Candidate として保持 |
| P3 `F_V3_ADMISSION` / P4 `F_V3_SELECTION` | スタック外（A-03 / A-04 Flag を使用） |
| Delete Boundary | 研究対象外 · 残 6 miss |

---

## 6. 参照

| 文書 | パス |
|------|------|
| Phase 2 Final Report | `v3-accuracy-phase2-final-report.md` |
| Configuration Registry | `v3-lab-configuration-registry.md` |
| A-04 Report | `v3-a04-accuracy-report.md` |
| Remaining Issues | `v3-remaining-issues.md` |
