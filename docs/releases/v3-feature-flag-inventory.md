# Version 3 — Feature Flag Inventory（Phase 2 Close）

**Date:** 2026-07-24  
**Inventory ID:** `v3-feature-flag-inventory/phase2-close`  
**Artifact:** `research/v3_lab/baselines/accuracy_phase2_close/feature_flag_inventory_v3.json`  
**原則:** コード上の既定は全 **OFF** · 本番配線なし · 下表「Stack」は Lab 採用意図（Baseline v3）

---

## Adopted Stack Flags（Baseline v3）

| Flag | Env alias | 既定 | Lab Stack | 役割 |
|------|-----------|------|-----------|------|
| `F_V3_A03_POOL_ADMIT_ENABLED` | `WIN5_V3_A03_POOL_ADMIT_ENABLED` | OFF | **ON** | Admission A-03 |
| `F_V3_A04_SEL_HISTORY_ENABLED` | `WIN5_V3_A04_SEL_HISTORY_ENABLED` | OFF | **ON** | Selection A-04 |
| `F_V3_RANK_D1_ENABLED` | `WIN5_V3_RANK_D1_ENABLED` | OFF | **ON** | Evaluation A-01 |

---

## Held / Baseline

| Flag | 既定 | Lab Stack | 役割 |
|------|------|-----------|------|
| `F_V3_RANK_D2_ENABLED` | OFF | OFF | A-02 Secondary（保持） |
| `F_V3_REPRESENTATION` | OFF | OFF | Representation Baseline |
| `F_V3_SELECTION` | OFF | OFF | P4 SEL-V3-RO（スタック外） |
| `F_V3_ADMISSION` | OFF | OFF | P3 AP-V3-A（スタック外） |
| `F_V3_PURCHASE_ENABLED` | OFF | OFF | Purchase Baseline |
| `F_V3_EVALUATION_ENABLED` | OFF | OFF | legacy alias |
| `F_V3_LAB_ENABLED` | OFF | OFF | legacy reserved |

---

## Production

V3 Accuracy Flag の本番配線は **行わない**（Phase 2 Close 時点）。
