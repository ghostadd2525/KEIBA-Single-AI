# Version80 — Attribution Shadow Evaluation

**Generated:** `2026-07-28T08:53:51+00:00`  
**N:** 285  
**Mode:** Shadow only（Production / Trigger / Prediction pipeline 非変更）  
**Design:** V79 2×2（LL / LP / CL / CP）

## 方法注記

- legacy_pe: `fixture predicted_top1 / hit_at_1 / model_rank`
- pilot_pe: `research-only Shadow scorer from V75 Ready contracts`

## Full 285R

| Cell | n | Hit | Purchase | rank710 | other_1_3 | other_10_13 | rank46 | fired | Fingerprint |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **LL** | 285 | 218 | 218 | 14 | 1 | 13 | 35 | 0 | `3e28516afffa8092…` |
| **LP** | 285 | 218 | 218 | 14 | 1 | 13 | 35 | 0 | `3e28516afffa8092…` |
| **CL** | 285 | 218 | 218 | 14 | 1 | 13 | 35 | 0 | `3e28516afffa8092…` |
| **CP** | 285 | 85 | 85 | 32 | 80 | 14 | 71 | 241 | `abdec149427fe335…` |

## Ready: rank7 only（CEW=rank7）

| Cell | n | Hit | Purchase | rank710 | other_1_3 | other_10_13 | rank46 | fired | Fingerprint |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **LL** | 65 | 52 | 52 | 1 | 0 | 3 | 9 | 0 | `7d6505f4181cc1a0…` |
| **LP** | 65 | 52 | 52 | 1 | 0 | 3 | 9 | 0 | `7d6505f4181cc1a0…` |
| **CL** | 65 | 52 | 52 | 1 | 0 | 3 | 9 | 0 | `7d6505f4181cc1a0…` |
| **CP** | 65 | 11 | 11 | 12 | 21 | 4 | 17 | 65 | `4f1183ccfea7f939…` |

## Residual: unsatisfied（CEW=unsatisfied）

| Cell | n | Hit | Purchase | rank710 | other_1_3 | other_10_13 | rank46 | fired | Fingerprint |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **LL** | 176 | 128 | 128 | 13 | 1 | 8 | 24 | 0 | `7df69f292b84a3df…` |
| **LP** | 176 | 128 | 128 | 13 | 1 | 8 | 24 | 0 | `7df69f292b84a3df…` |
| **CL** | 176 | 128 | 128 | 13 | 1 | 8 | 24 | 0 | `7df69f292b84a3df…` |
| **CP** | 176 | 36 | 36 | 20 | 59 | 8 | 52 | 176 | `d5d27f81546dc885…` |

## Boundary Audit

- LP pilot_fired_n = 0 （must 0: Y）
- CP on Non-Ready pilot_fired_n = 0 （must 0: Y）

## 数値正本

`docs/research/_v80-attribution-shadow.json`
