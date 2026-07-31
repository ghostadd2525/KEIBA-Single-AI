# Version 3 — Lab Configuration Registry

**Date:** 2026-07-24  
**Configuration ID:** `v3-lab-config-a01-a03-a04/1.0`  
**Close ID:** `v3-accuracy-phase2-close/1.0`  
**Prior:** `v3-lab-config-a01-a03/1.0`（Baseline v2 · 履歴）  
**Code:** `research/v3_lab/phase2_close.py` · `LAB_CONFIGURATION_V3`  
**Artifact:** `research/v3_lab/baselines/accuracy_phase2_close/lab_configuration_registry_v3.json`

---

## Official Stack（Baseline v3）

| Order | Stage | Mode | Policy / ID | Flag | Stack |
|-------|-------|------|-------------|------|-------|
| 1 | Representation | Baseline | identity | `F_V3_REPRESENTATION` | OFF |
| 2 | Admission | **A-03** | `AP-V3-A03-pool-coverage` | `F_V3_A03_POOL_ADMIT_ENABLED` | **ON** |
| 3 | Selection | **A-04** | `SEL-V3-A04-history-crowding` | `F_V3_A04_SEL_HISTORY_ENABLED` | **ON** |
| 4 | Evaluation | **A-01** | `D1-Recalibrator` | `F_V3_RANK_D1_ENABLED` | **ON** |
| 5 | Purchase | Baseline | identity mapper | `F_V3_PURCHASE_ENABLED` | OFF |

## Explicitly OFF in stack

`F_V3_REPRESENTATION` · `F_V3_ADMISSION`（P3）· `F_V3_SELECTION`（P4）· `F_V3_RANK_D2_ENABLED` · `F_V3_PURCHASE_ENABLED`

## Diagram

```text
Representation (Baseline)
        ↓
Admission (A-03)
        ↓
Selection (A-04)
        ↓
Evaluation (A-01)
        ↓
Purchase (Baseline)
```

## Notes

- ランタイム既定は引き続き全 Flag OFF（本番配線なし）。
- 本 Registry は Lab 採用意図と Baseline v3 測定の正本。
- Delete Boundary は研究対象外。
