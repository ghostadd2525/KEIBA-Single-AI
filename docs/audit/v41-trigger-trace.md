# Version41 Trigger Evaluation Trace

各Race・各Worldの PASS / FAIL / Margin / 不足条件 / Why-Not。

## `2026-06-28-函館-11` → Decision `midupper_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | PASS | — | short_field_pressure | False | — |
| `midhole_world` | FAIL | — | late_stop | False | R4_midhole: late_stop不足 (val=0.4846653333333332, thr=0.56, margin=-0.075335) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.4588934322994684, thr=0.58, margin=-0.121107) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.4588934322994684, thr=0.66, margin=-0.201107) |
| `mixed_world` | FAIL | — | phase, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midhole_world** [FAIL] fitness=0.8655
  - R4_midhole: late_stop不足 (val=0.4846653333333332, thr=0.56, margin=-0.075335)
- **rank7_world** [FAIL] fitness=0.7912
  - R5_rank7: chaos不足 (val=0.4588934322994684, thr=0.58, margin=-0.121107)
- **bug_world** [FAIL] fitness=0.6953
  - R6_bug: chaos不足 (val=0.4588934322994684, thr=0.66, margin=-0.201107)
- **mixed_world** [FAIL] fitness=0.8486
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase不足 (val=0.526136, thr=0.62, margin=-0.093864)

## `2026-06-28-小倉-10` → Decision `midupper_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | PASS | — | short_field_pressure | False | — |
| `midhole_world` | FAIL | — | late_stop | True | R4_midhole: late_stop不足 (val=0.514255, thr=0.56, margin=-0.045745) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.46247676058572496, thr=0.58, margin=-0.117523) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.46247676058572496, thr=0.66, margin=-0.197523) |
| `mixed_world` | FAIL | — | phase, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midhole_world** [FAIL] fitness=0.9183
  - R4_midhole: late_stop不足 (val=0.514255, thr=0.56, margin=-0.045745)
- **rank7_world** [FAIL] fitness=0.7974
  - R5_rank7: chaos不足 (val=0.46247676058572496, thr=0.58, margin=-0.117523)
- **bug_world** [FAIL] fitness=0.7007
  - R6_bug: chaos不足 (val=0.46247676058572496, thr=0.66, margin=-0.197523)
- **mixed_world** [FAIL] fitness=0.8013
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase不足 (val=0.496822, thr=0.62, margin=-0.123178)

## `2026-06-28-小倉-11` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.41656000000000004, thr=0.56, margin=-0.14344) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.34862892141050966, thr=0.58, margin=-0.231371) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.34862892141050966, thr=0.66, margin=-0.311371) |
| `mixed_world` | FAIL | — | chaos, phase, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.8587
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.429357, thr=0.5, margin=-0.070643)
- **midhole_world** [FAIL] fitness=0.7439
  - R4_midhole: late_stop不足 (val=0.41656000000000004, thr=0.56, margin=-0.14344)
- **rank7_world** [FAIL] fitness=0.6011
  - R5_rank7: chaos不足 (val=0.34862892141050966, thr=0.58, margin=-0.231371)
- **bug_world** [FAIL] fitness=0.5282
  - R6_bug: chaos不足 (val=0.34862892141050966, thr=0.66, margin=-0.311371)
- **mixed_world** [FAIL] fitness=0.7949
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase不足 (val=0.492831, thr=0.62, margin=-0.127169)

## `2026-06-28-福島-10` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop | False | R4_midhole: late_stop不足 (val=0.503910909090909, thr=0.56, margin=-0.056089) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.4024794875578539, thr=0.58, margin=-0.177521) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.4024794875578539, thr=0.66, margin=-0.257521) |
| `mixed_world` | FAIL | — | chaos, phase, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.8921
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.446047, thr=0.5, margin=-0.053953)
- **midhole_world** [FAIL] fitness=0.8998
  - R4_midhole: late_stop不足 (val=0.503910909090909, thr=0.56, margin=-0.056089)
- **rank7_world** [FAIL] fitness=0.6939
  - R5_rank7: chaos不足 (val=0.4024794875578539, thr=0.58, margin=-0.177521)
- **bug_world** [FAIL] fitness=0.6098
  - R6_bug: chaos不足 (val=0.4024794875578539, thr=0.66, margin=-0.257521)
- **mixed_world** [FAIL] fitness=0.8313
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase不足 (val=0.515422, thr=0.62, margin=-0.104578)

## `2026-06-28-福島-11` → Decision `midhole_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | PASS | — | short_field_pressure | False | — |
| `midhole_world` | PASS | — | — | False | — |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.5188479456819488, thr=0.58, margin=-0.061152) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.5188479456819488, thr=0.66, margin=-0.141152) |
| `mixed_world` | FAIL | — | phase, short_field_pressure | True | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midupper_world** [PASS] fitness=1.0
  - Evaluation Order: TriggerはPASSだが、より高優先度のDecision(priority≤4)が先に確定
- **rank7_world** [FAIL] fitness=0.8946
  - R5_rank7: chaos不足 (val=0.5188479456819488, thr=0.58, margin=-0.061152)
- **bug_world** [FAIL] fitness=0.7861
  - R6_bug: chaos不足 (val=0.5188479456819488, thr=0.66, margin=-0.141152)
- **mixed_world** [FAIL] fitness=0.9243
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase不足 (val=0.573066, thr=0.62, margin=-0.046934)

## `2026-07-25-01-01` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.1173388652, thr=0.52, margin=-0.402661) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.244741484116, thr=0.58, margin=-0.335259) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.244741484116, thr=0.66, margin=-0.415259) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.582
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.291, thr=0.5, margin=-0.209)
- **midhole_world** [FAIL] fitness=0.2257
  - R4_midhole: sustained不足 (val=0.1173388652, thr=0.52, margin=-0.402661)
- **rank7_world** [FAIL] fitness=0.422
  - R5_rank7: chaos不足 (val=0.244741484116, thr=0.58, margin=-0.335259)
- **bug_world** [FAIL] fitness=0.3708
  - R6_bug: chaos不足 (val=0.244741484116, thr=0.66, margin=-0.415259)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-01-02` → Decision `midupper_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | PASS | — | difficulty | False | — |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.1063077142857143, thr=0.52, margin=-0.413692) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.32613549042857143, thr=0.58, margin=-0.253865) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.32613549042857143, thr=0.66, margin=-0.333865) |
| `mixed_world` | FAIL | phase | chaos, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.6412091554738095, thr=0.7... |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midhole_world** [FAIL] fitness=0.2044
  - R4_midhole: sustained不足 (val=0.1063077142857143, thr=0.52, margin=-0.413692)
- **rank7_world** [FAIL] fitness=0.5623
  - R5_rank7: chaos不足 (val=0.32613549042857143, thr=0.58, margin=-0.253865)
- **bug_world** [FAIL] fitness=0.4941
  - R6_bug: chaos不足 (val=0.32613549042857143, thr=0.66, margin=-0.333865)
- **mixed_world** [FAIL] fitness=0.8906
  - R1_mixed_short_field: short_field_pressure不足 (val=0.6412091554738095, thr=0.72, margin=-0.078791)
  - R3_mixed_phase: phase missing

## `2026-07-25-01-03` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.11626375703125, thr=0.56, margin=-0.443736) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.19906810618749998, thr=0.58, margin=-0.380932) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.19906810618749998, thr=0.66, margin=-0.460932) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.55
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.275, thr=0.5, margin=-0.225)
- **midhole_world** [FAIL] fitness=0.1606
  - R4_midhole: late_stop不足 (val=0.11626375703125, thr=0.56, margin=-0.443736)
- **rank7_world** [FAIL] fitness=0.2396
  - R5_rank7: chaos不足 (val=0.19906810618749998, thr=0.58, margin=-0.380932)
- **bug_world** [FAIL] fitness=0.3016
  - R6_bug: chaos不足 (val=0.19906810618749998, thr=0.66, margin=-0.460932)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-01-04` → Decision `mixed_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | PASS | — | difficulty | False | — |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.38434700571733327, thr=0.52, margin=-0.135653) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.4226221114663946, thr=0.58, margin=-0.157378) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.381667, thr=0.62, margin=-0.238333) |
| `mixed_world` | PASS | phase | — | False | — |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midupper_world** [PASS] fitness=1.0
  - Evaluation Order: TriggerはPASSだが、より高優先度のDecision(priority≤1)が先に確定
- **midhole_world** [FAIL] fitness=0.7391
  - R4_midhole: sustained不足 (val=0.38434700571733327, thr=0.52, margin=-0.135653)
- **rank7_world** [FAIL] fitness=0.7287
  - R5_rank7: chaos不足 (val=0.4226221114663946, thr=0.58, margin=-0.157378)
- **bug_world** [FAIL] fitness=0.6156
  - R6_bug: difficulty不足 (val=0.381667, thr=0.62, margin=-0.238333)

## `2026-07-25-01-05` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.3590415287616666, thr=0.56, margin=-0.200958) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.3401611189829939, thr=0.58, margin=-0.239839) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.289545, thr=0.62, margin=-0.330455) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.5791
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.289545, thr=0.5, margin=-0.210455)
- **midhole_world** [FAIL] fitness=0.6411
  - R4_midhole: late_stop不足 (val=0.3590415287616666, thr=0.56, margin=-0.200958)
- **rank7_world** [FAIL] fitness=0.5865
  - R5_rank7: chaos不足 (val=0.3401611189829939, thr=0.58, margin=-0.239839)
- **bug_world** [FAIL] fitness=0.467
  - R6_bug: difficulty不足 (val=0.289545, thr=0.62, margin=-0.330455)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-01-06` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop | True | R4_midhole: late_stop不足 (val=0.5264766714836001, thr=0.56, margin=-0.033523) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.47060422380156813, thr=0.58, margin=-0.109396) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.355, thr=0.62, margin=-0.265) |
| `mixed_world` | FAIL | phase | difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.71
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.355, thr=0.5, margin=-0.145)
- **midhole_world** [FAIL] fitness=0.9401
  - R4_midhole: late_stop不足 (val=0.5264766714836001, thr=0.56, margin=-0.033523)
- **rank7_world** [FAIL] fitness=0.8114
  - R5_rank7: chaos不足 (val=0.47060422380156813, thr=0.58, margin=-0.109396)
- **bug_world** [FAIL] fitness=0.5726
  - R6_bug: difficulty不足 (val=0.355, thr=0.62, margin=-0.265)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-01-07` → Decision `mixed_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | PASS | — | difficulty | False | — |
| `midhole_world` | FAIL | — | late_stop | False | R4_midhole: late_stop不足 (val=0.4839957878482353, thr=0.56, margin=-0.076004) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.4514301602240942, thr=0.58, margin=-0.12857) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.407941, thr=0.62, margin=-0.212059) |
| `mixed_world` | PASS | phase | — | False | — |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midupper_world** [PASS] fitness=1.0
  - Evaluation Order: TriggerはPASSだが、より高優先度のDecision(priority≤1)が先に確定
- **midhole_world** [FAIL] fitness=0.8643
  - R4_midhole: late_stop不足 (val=0.4839957878482353, thr=0.56, margin=-0.076004)
- **rank7_world** [FAIL] fitness=0.7783
  - R5_rank7: chaos不足 (val=0.4514301602240942, thr=0.58, margin=-0.12857)
- **bug_world** [FAIL] fitness=0.658
  - R6_bug: difficulty不足 (val=0.407941, thr=0.62, margin=-0.212059)

## `2026-07-25-01-08` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.4003569485911538, thr=0.56, margin=-0.159643) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.36522191291406164, thr=0.58, margin=-0.214778) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.321154, thr=0.62, margin=-0.298846) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.6423
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.321154, thr=0.5, margin=-0.178846)
- **midhole_world** [FAIL] fitness=0.7149
  - R4_midhole: late_stop不足 (val=0.4003569485911538, thr=0.56, margin=-0.159643)
- **rank7_world** [FAIL] fitness=0.6297
  - R5_rank7: chaos不足 (val=0.36522191291406164, thr=0.58, margin=-0.214778)
- **bug_world** [FAIL] fitness=0.518
  - R6_bug: difficulty不足 (val=0.321154, thr=0.62, margin=-0.298846)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-01-09` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.45867859806239997, thr=0.56, margin=-0.101321) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.39585322363891196, thr=0.58, margin=-0.184147) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.2125, thr=0.62, margin=-0.4075) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.425
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.2125, thr=0.5, margin=-0.2875)
- **midhole_world** [FAIL] fitness=0.8191
  - R4_midhole: late_stop不足 (val=0.45867859806239997, thr=0.56, margin=-0.101321)
- **rank7_world** [FAIL] fitness=0.6825
  - R5_rank7: chaos不足 (val=0.39585322363891196, thr=0.58, margin=-0.184147)
- **bug_world** [FAIL] fitness=0.3427
  - R6_bug: difficulty不足 (val=0.2125, thr=0.62, margin=-0.4075)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-01-10` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.3371968524903334, thr=0.56, margin=-0.222803) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.3623725376432266, thr=0.58, margin=-0.217627) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.3623725376432266, thr=0.66, margin=-0.297627) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.8167
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.408333, thr=0.5, margin=-0.091667)
- **midhole_world** [FAIL] fitness=0.6021
  - R4_midhole: late_stop不足 (val=0.3371968524903334, thr=0.56, margin=-0.222803)
- **rank7_world** [FAIL] fitness=0.6248
  - R5_rank7: chaos不足 (val=0.3623725376432266, thr=0.58, margin=-0.217627)
- **bug_world** [FAIL] fitness=0.549
  - R6_bug: chaos不足 (val=0.3623725376432266, thr=0.66, margin=-0.297627)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-01-11` → Decision `mixed_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | PASS | — | difficulty | False | — |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.34797792782962966, thr=0.52, margin=-0.172022) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.4634635251680297, thr=0.58, margin=-0.116536) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.419444, thr=0.62, margin=-0.200556) |
| `mixed_world` | PASS | phase | — | False | — |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midupper_world** [PASS] fitness=1.0
  - Evaluation Order: TriggerはPASSだが、より高優先度のDecision(priority≤1)が先に確定
- **midhole_world** [FAIL] fitness=0.6692
  - R4_midhole: sustained不足 (val=0.34797792782962966, thr=0.52, margin=-0.172022)
- **rank7_world** [FAIL] fitness=0.7991
  - R5_rank7: chaos不足 (val=0.4634635251680297, thr=0.58, margin=-0.116536)
- **bug_world** [FAIL] fitness=0.6765
  - R6_bug: difficulty不足 (val=0.419444, thr=0.62, margin=-0.200556)

## `2026-07-25-01-12` → Decision `mixed_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | PASS | — | difficulty | False | — |
| `midhole_world` | FAIL | — | late_stop | True | R4_midhole: late_stop不足 (val=0.5479624861858651, thr=0.56, margin=-0.012038) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.48137107925062006, thr=0.58, margin=-0.098629) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.390294, thr=0.62, margin=-0.229706) |
| `mixed_world` | PASS | phase | — | False | — |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midupper_world** [PASS] fitness=1.0
  - Evaluation Order: TriggerはPASSだが、より高優先度のDecision(priority≤1)が先に確定
- **midhole_world** [FAIL] fitness=0.9785
  - R4_midhole: late_stop不足 (val=0.5479624861858651, thr=0.56, margin=-0.012038)
- **rank7_world** [FAIL] fitness=0.83
  - R5_rank7: chaos不足 (val=0.48137107925062006, thr=0.58, margin=-0.098629)
- **bug_world** [FAIL] fitness=0.6295
  - R6_bug: difficulty不足 (val=0.390294, thr=0.62, margin=-0.229706)

## `2026-07-25-02-01` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.12089000624999999, thr=0.56, margin=-0.43911) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.20183076105555556, thr=0.58, margin=-0.378169) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.20183076105555556, thr=0.66, margin=-0.458169) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.59
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.295, thr=0.5, margin=-0.205)
- **midhole_world** [FAIL] fitness=0.1595
  - R4_midhole: late_stop不足 (val=0.12089000624999999, thr=0.56, margin=-0.43911)
- **rank7_world** [FAIL] fitness=0.2563
  - R5_rank7: chaos不足 (val=0.20183076105555556, thr=0.58, margin=-0.378169)
- **bug_world** [FAIL] fitness=0.3058
  - R6_bug: chaos不足 (val=0.20183076105555556, thr=0.66, margin=-0.458169)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-02-02` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.07913615384615383, thr=0.52, margin=-0.440864) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.21225452688461535, thr=0.58, margin=-0.367745) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.21225452688461535, thr=0.66, margin=-0.447745) |
| `mixed_world` | FAIL | phase | chaos, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.848
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.424, thr=0.5, margin=-0.076)
- **midhole_world** [FAIL] fitness=0.1522
  - R4_midhole: sustained不足 (val=0.07913615384615383, thr=0.52, margin=-0.440864)
- **rank7_world** [FAIL] fitness=0.3229
  - R5_rank7: chaos不足 (val=0.21225452688461535, thr=0.58, margin=-0.367745)
- **bug_world** [FAIL] fitness=0.3216
  - R6_bug: chaos不足 (val=0.21225452688461535, thr=0.66, margin=-0.447745)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-02-03` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.41317427825291664, thr=0.56, margin=-0.146826) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.37327953446256673, thr=0.58, margin=-0.20672) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.305, thr=0.62, margin=-0.315) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.61
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.305, thr=0.5, margin=-0.195)
- **midhole_world** [FAIL] fitness=0.7378
  - R4_midhole: late_stop不足 (val=0.41317427825291664, thr=0.56, margin=-0.146826)
- **rank7_world** [FAIL] fitness=0.6436
  - R5_rank7: chaos不足 (val=0.37327953446256673, thr=0.58, margin=-0.20672)
- **bug_world** [FAIL] fitness=0.4919
  - R6_bug: difficulty不足 (val=0.305, thr=0.62, margin=-0.315)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-02-04` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.43123974179999996, thr=0.52, margin=-0.08876) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.48057229999995, thr=0.58, margin=-0.099428) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.37875, thr=0.62, margin=-0.24125) |
| `mixed_world` | FAIL | phase | difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.7575
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.37875, thr=0.5, margin=-0.12125)
- **midhole_world** [FAIL] fitness=0.8293
  - R4_midhole: sustained不足 (val=0.43123974179999996, thr=0.52, margin=-0.08876)
- **rank7_world** [FAIL] fitness=0.8286
  - R5_rank7: chaos不足 (val=0.48057229999995, thr=0.58, margin=-0.099428)
- **bug_world** [FAIL] fitness=0.6109
  - R6_bug: difficulty不足 (val=0.37875, thr=0.62, margin=-0.24125)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-02-05` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.31366097315, thr=0.52, margin=-0.206339) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.37252336440818334, thr=0.58, margin=-0.207477) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.37252336440818334, thr=0.66, margin=-0.287477) |
| `mixed_world` | FAIL | phase | chaos, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.845
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.4225, thr=0.5, margin=-0.0775)
- **midhole_world** [FAIL] fitness=0.6032
  - R4_midhole: sustained不足 (val=0.31366097315, thr=0.52, margin=-0.206339)
- **rank7_world** [FAIL] fitness=0.6423
  - R5_rank7: chaos不足 (val=0.37252336440818334, thr=0.58, margin=-0.207477)
- **bug_world** [FAIL] fitness=0.5644
  - R6_bug: chaos不足 (val=0.37252336440818334, thr=0.66, margin=-0.287477)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-02-06` → Decision `mixed_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty | True | R2_midupper_sf_diff: difficulty不足 (val=0.3725, thr=0.38, margin=-0.0075); R7_... |
| `midhole_world` | FAIL | — | late_stop | True | R4_midhole: late_stop不足 (val=0.5228261925020312, thr=0.56, margin=-0.037174) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.4673767380017875, thr=0.58, margin=-0.112623) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.3725, thr=0.62, margin=-0.2475) |
| `mixed_world` | PASS | phase | — | False | — |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midupper_world** [FAIL] fitness=0.9803
  - R2_midupper_sf_diff: difficulty不足 (val=0.3725, thr=0.38, margin=-0.0075)
  - R7_midupper_diff: difficulty不足 (val=0.3725, thr=0.5, margin=-0.1275)
- **midhole_world** [FAIL] fitness=0.9336
  - R4_midhole: late_stop不足 (val=0.5228261925020312, thr=0.56, margin=-0.037174)
- **rank7_world** [FAIL] fitness=0.8058
  - R5_rank7: chaos不足 (val=0.4673767380017875, thr=0.58, margin=-0.112623)
- **bug_world** [FAIL] fitness=0.6008
  - R6_bug: difficulty不足 (val=0.3725, thr=0.62, margin=-0.2475)

## `2026-07-25-02-07` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.28701662765196967, thr=0.56, margin=-0.272983) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.2981430366973697, thr=0.58, margin=-0.281857) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.2981430366973697, thr=0.66, margin=-0.361857) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.6155
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.307727, thr=0.5, margin=-0.192273)
- **midhole_world** [FAIL] fitness=0.5125
  - R4_midhole: late_stop不足 (val=0.28701662765196967, thr=0.56, margin=-0.272983)
- **rank7_world** [FAIL] fitness=0.514
  - R5_rank7: chaos不足 (val=0.2981430366973697, thr=0.58, margin=-0.281857)
- **bug_world** [FAIL] fitness=0.4517
  - R6_bug: chaos不足 (val=0.2981430366973697, thr=0.66, margin=-0.361857)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-02-08` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.44192804509114586, thr=0.56, margin=-0.118072) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.38172982968020824, thr=0.58, margin=-0.19827) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.2125, thr=0.62, margin=-0.4075) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.425
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.2125, thr=0.5, margin=-0.2875)
- **midhole_world** [FAIL] fitness=0.7892
  - R4_midhole: late_stop不足 (val=0.44192804509114586, thr=0.56, margin=-0.118072)
- **rank7_world** [FAIL] fitness=0.6582
  - R5_rank7: chaos不足 (val=0.38172982968020824, thr=0.58, margin=-0.19827)
- **bug_world** [FAIL] fitness=0.3427
  - R6_bug: difficulty不足 (val=0.2125, thr=0.62, margin=-0.4075)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-02-09` → Decision `mixed_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty | True | R2_midupper_sf_diff: difficulty不足 (val=0.37875, thr=0.38, margin=-0.00125); R... |
| `midhole_world` | FAIL | — | late_stop | True | R4_midhole: late_stop不足 (val=0.5306228180039844, thr=0.56, margin=-0.029377) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.47294146980350626, thr=0.58, margin=-0.107059) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.37875, thr=0.62, margin=-0.24125) |
| `mixed_world` | PASS | phase | — | False | — |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midupper_world** [FAIL] fitness=0.9967
  - R2_midupper_sf_diff: difficulty不足 (val=0.37875, thr=0.38, margin=-0.00125)
  - R7_midupper_diff: difficulty不足 (val=0.37875, thr=0.5, margin=-0.12125)
- **midhole_world** [FAIL] fitness=0.9475
  - R4_midhole: late_stop不足 (val=0.5306228180039844, thr=0.56, margin=-0.029377)
- **rank7_world** [FAIL] fitness=0.8154
  - R5_rank7: chaos不足 (val=0.47294146980350626, thr=0.58, margin=-0.107059)
- **bug_world** [FAIL] fitness=0.6109
  - R6_bug: difficulty不足 (val=0.37875, thr=0.62, margin=-0.24125)

## `2026-07-25-02-10` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.36419954212875, thr=0.56, margin=-0.1958) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.3435464173399667, thr=0.58, margin=-0.236454) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.3435464173399667, thr=0.66, margin=-0.316454) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.61
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.305, thr=0.5, margin=-0.195)
- **midhole_world** [FAIL] fitness=0.6504
  - R4_midhole: late_stop不足 (val=0.36419954212875, thr=0.56, margin=-0.1958)
- **rank7_world** [FAIL] fitness=0.5923
  - R5_rank7: chaos不足 (val=0.3435464173399667, thr=0.58, margin=-0.236454)
- **bug_world** [FAIL] fitness=0.4919
  - R6_bug: chaos不足 (val=0.3435464173399667, thr=0.66, margin=-0.316454)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-02-11` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.44343404746161463, thr=0.56, margin=-0.116566) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.38527738216622076, thr=0.58, margin=-0.194723) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.2125, thr=0.62, margin=-0.4075) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.425
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.2125, thr=0.5, margin=-0.2875)
- **midhole_world** [FAIL] fitness=0.7918
  - R4_midhole: late_stop不足 (val=0.44343404746161463, thr=0.56, margin=-0.116566)
- **rank7_world** [FAIL] fitness=0.6643
  - R5_rank7: chaos不足 (val=0.38527738216622076, thr=0.58, margin=-0.194723)
- **bug_world** [FAIL] fitness=0.3427
  - R6_bug: difficulty不足 (val=0.2125, thr=0.62, margin=-0.4075)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-02-12` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.38517903710976564, thr=0.56, margin=-0.174821) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.39220565893659376, thr=0.58, margin=-0.187794) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.39220565893659376, thr=0.66, margin=-0.267794) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.8325
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.41625, thr=0.5, margin=-0.08375)
- **midhole_world** [FAIL] fitness=0.6878
  - R4_midhole: late_stop不足 (val=0.38517903710976564, thr=0.56, margin=-0.174821)
- **rank7_world** [FAIL] fitness=0.6762
  - R5_rank7: chaos不足 (val=0.39220565893659376, thr=0.58, margin=-0.187794)
- **bug_world** [FAIL] fitness=0.5943
  - R6_bug: chaos不足 (val=0.39220565893659376, thr=0.66, margin=-0.267794)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-03-01` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.40074290718750005, thr=0.56, margin=-0.159257) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.3590782351249999, thr=0.58, margin=-0.220922) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.221, thr=0.62, margin=-0.399) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.442
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.221, thr=0.5, margin=-0.279)
- **midhole_world** [FAIL] fitness=0.7156
  - R4_midhole: late_stop不足 (val=0.40074290718750005, thr=0.56, margin=-0.159257)
- **rank7_world** [FAIL] fitness=0.6191
  - R5_rank7: chaos不足 (val=0.3590782351249999, thr=0.58, margin=-0.220922)
- **bug_world** [FAIL] fitness=0.3565
  - R6_bug: difficulty不足 (val=0.221, thr=0.62, margin=-0.399)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-03-02` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.258855581, thr=0.52, margin=-0.261144) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.36213778209409164, thr=0.58, margin=-0.217862) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.225, thr=0.62, margin=-0.395) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.45
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.225, thr=0.5, margin=-0.275)
- **midhole_world** [FAIL] fitness=0.4978
  - R4_midhole: sustained不足 (val=0.258855581, thr=0.52, margin=-0.261144)
- **rank7_world** [FAIL] fitness=0.6244
  - R5_rank7: chaos不足 (val=0.36213778209409164, thr=0.58, margin=-0.217862)
- **bug_world** [FAIL] fitness=0.3629
  - R6_bug: difficulty不足 (val=0.225, thr=0.62, margin=-0.395)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-03-03` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.4184451576899667, thr=0.56, margin=-0.141555) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.37292462043117064, thr=0.58, margin=-0.207075) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.255, thr=0.62, margin=-0.365) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.51
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.255, thr=0.5, margin=-0.245)
- **midhole_world** [FAIL] fitness=0.7472
  - R4_midhole: late_stop不足 (val=0.4184451576899667, thr=0.56, margin=-0.141555)
- **rank7_world** [FAIL] fitness=0.643
  - R5_rank7: chaos不足 (val=0.37292462043117064, thr=0.58, margin=-0.207075)
- **bug_world** [FAIL] fitness=0.4113
  - R6_bug: difficulty不足 (val=0.255, thr=0.62, margin=-0.365)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-03-04` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.42830806498681523, thr=0.5... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.42393084757142857, thr=0.52, margin=-0.096069) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.4697993949743999, thr=0.58, margin=-0.110201) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.337857, thr=0.62, margin=-0.282143) |
| `mixed_world` | FAIL | phase | difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.42830806498681523, thr=0.... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.7385
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.42830806498681523, thr=0.58, margin=-0.151692)
  - R7_midupper_diff: difficulty不足 (val=0.337857, thr=0.5, margin=-0.162143)
- **midhole_world** [FAIL] fitness=0.8153
  - R4_midhole: sustained不足 (val=0.42393084757142857, thr=0.52, margin=-0.096069)
- **rank7_world** [FAIL] fitness=0.81
  - R5_rank7: chaos不足 (val=0.4697993949743999, thr=0.58, margin=-0.110201)
- **bug_world** [FAIL] fitness=0.5449
  - R6_bug: difficulty不足 (val=0.337857, thr=0.62, margin=-0.282143)
- **mixed_world** [FAIL] fitness=0.5949
  - R1_mixed_short_field: short_field_pressure不足 (val=0.42830806498681523, thr=0.72, margin=-0.291692)
  - R3_mixed_phase: phase missing

## `2026-07-25-03-05` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.10738500937499999, thr=0.56, margin=-0.452615) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.19348414158333335, thr=0.58, margin=-0.386516) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.19348414158333335, thr=0.66, margin=-0.466516) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.55
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.275, thr=0.5, margin=-0.225)
- **midhole_world** [FAIL] fitness=0.162
  - R4_midhole: late_stop不足 (val=0.10738500937499999, thr=0.56, margin=-0.452615)
- **rank7_world** [FAIL] fitness=0.2062
  - R5_rank7: chaos不足 (val=0.19348414158333335, thr=0.58, margin=-0.386516)
- **bug_world** [FAIL] fitness=0.2932
  - R6_bug: chaos不足 (val=0.19348414158333335, thr=0.66, margin=-0.466516)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-03-06` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.46101891154761915, thr=0.56, margin=-0.098981) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.4361892673504762, thr=0.58, margin=-0.143811) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.352143, thr=0.62, margin=-0.267857) |
| `mixed_world` | FAIL | phase | difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.7043
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.352143, thr=0.5, margin=-0.147857)
- **midhole_world** [FAIL] fitness=0.8232
  - R4_midhole: late_stop不足 (val=0.46101891154761915, thr=0.56, margin=-0.098981)
- **rank7_world** [FAIL] fitness=0.7521
  - R5_rank7: chaos不足 (val=0.4361892673504762, thr=0.58, margin=-0.143811)
- **bug_world** [FAIL] fitness=0.568
  - R6_bug: difficulty不足 (val=0.352143, thr=0.62, margin=-0.267857)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-03-07` → Decision `mixed_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty | True | R2_midupper_sf_diff: difficulty不足 (val=0.335, thr=0.38, margin=-0.045); R7_mi... |
| `midhole_world` | PASS | — | — | False | — |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.50818344726576, thr=0.58, margin=-0.071817) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.335, thr=0.62, margin=-0.285) |
| `mixed_world` | PASS | phase | — | False | — |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midupper_world** [FAIL] fitness=0.8816
  - R2_midupper_sf_diff: difficulty不足 (val=0.335, thr=0.38, margin=-0.045)
  - R7_midupper_diff: difficulty不足 (val=0.335, thr=0.5, margin=-0.165)
- **midhole_world** [PASS] fitness=1.0
  - Evaluation Order: TriggerはPASSだが、より高優先度のDecision(priority≤1)が先に確定
- **rank7_world** [FAIL] fitness=0.8762
  - R5_rank7: chaos不足 (val=0.50818344726576, thr=0.58, margin=-0.071817)
- **bug_world** [FAIL] fitness=0.5403
  - R6_bug: difficulty不足 (val=0.335, thr=0.62, margin=-0.285)

## `2026-07-25-03-08` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.41317427825291664, thr=0.56, margin=-0.146826) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.3720898427292334, thr=0.58, margin=-0.20791) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.296667, thr=0.62, margin=-0.323333) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.5933
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.296667, thr=0.5, margin=-0.203333)
- **midhole_world** [FAIL] fitness=0.7378
  - R4_midhole: late_stop不足 (val=0.41317427825291664, thr=0.56, margin=-0.146826)
- **rank7_world** [FAIL] fitness=0.6415
  - R5_rank7: chaos不足 (val=0.3720898427292334, thr=0.58, margin=-0.20791)
- **bug_world** [FAIL] fitness=0.4785
  - R6_bug: difficulty不足 (val=0.296667, thr=0.62, margin=-0.323333)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-03-09` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.4709786337421, thr=0.56, margin=-0.089021) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.40070029657304806, thr=0.58, margin=-0.1793) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.235, thr=0.62, margin=-0.385) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.47
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.235, thr=0.5, margin=-0.265)
- **midhole_world** [FAIL] fitness=0.841
  - R4_midhole: late_stop不足 (val=0.4709786337421, thr=0.56, margin=-0.089021)
- **rank7_world** [FAIL] fitness=0.6909
  - R5_rank7: chaos不足 (val=0.40070029657304806, thr=0.58, margin=-0.1793)
- **bug_world** [FAIL] fitness=0.379
  - R6_bug: difficulty不足 (val=0.235, thr=0.62, margin=-0.385)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-03-10` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.4281866512731819, thr=0.56, margin=-0.131813) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.3795361870046975, thr=0.58, margin=-0.200464) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.271364, thr=0.62, margin=-0.348636) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.5427
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.271364, thr=0.5, margin=-0.228636)
- **midhole_world** [FAIL] fitness=0.7646
  - R4_midhole: late_stop不足 (val=0.4281866512731819, thr=0.56, margin=-0.131813)
- **rank7_world** [FAIL] fitness=0.6544
  - R5_rank7: chaos不足 (val=0.3795361870046975, thr=0.58, margin=-0.200464)
- **bug_world** [FAIL] fitness=0.4377
  - R6_bug: difficulty不足 (val=0.271364, thr=0.62, margin=-0.348636)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-03-11` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.435619920095, thr=0.56, margin=-0.12438) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.38255115101693327, thr=0.58, margin=-0.197449) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.288333, thr=0.62, margin=-0.331667) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.5767
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.288333, thr=0.5, margin=-0.211667)
- **midhole_world** [FAIL] fitness=0.7779
  - R4_midhole: late_stop不足 (val=0.435619920095, thr=0.56, margin=-0.12438)
- **rank7_world** [FAIL] fitness=0.6596
  - R5_rank7: chaos不足 (val=0.38255115101693327, thr=0.58, margin=-0.197449)
- **bug_world** [FAIL] fitness=0.4651
  - R6_bug: difficulty不足 (val=0.288333, thr=0.62, margin=-0.331667)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-25-03-12` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.3609429572766666, thr=0.56, margin=-0.199057) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.33988527585801215, thr=0.58, margin=-0.240115) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.289545, thr=0.62, margin=-0.330455) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.5791
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.289545, thr=0.5, margin=-0.210455)
- **midhole_world** [FAIL] fitness=0.6445
  - R4_midhole: late_stop不足 (val=0.3609429572766666, thr=0.56, margin=-0.199057)
- **rank7_world** [FAIL] fitness=0.586
  - R5_rank7: chaos不足 (val=0.33988527585801215, thr=0.58, margin=-0.240115)
- **bug_world** [FAIL] fitness=0.467
  - R6_bug: difficulty不足 (val=0.289545, thr=0.62, margin=-0.330455)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-26-01-01` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.10723640000000002, thr=0.52, margin=-0.412764) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.23858858181818177, thr=0.58, margin=-0.341411) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.23858858181818177, thr=0.66, margin=-0.421411) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.6238
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.311909, thr=0.5, margin=-0.188091)
- **midhole_world** [FAIL] fitness=0.2062
  - R4_midhole: sustained不足 (val=0.10723640000000002, thr=0.52, margin=-0.412764)
- **rank7_world** [FAIL] fitness=0.4114
  - R5_rank7: chaos不足 (val=0.23858858181818177, thr=0.58, margin=-0.341411)
- **bug_world** [FAIL] fitness=0.3615
  - R6_bug: chaos不足 (val=0.23858858181818177, thr=0.66, margin=-0.421411)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-26-01-02` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.11790000000000002, thr=0.56, margin=-0.4421) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.195324, thr=0.58, margin=-0.384676) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.195324, thr=0.66, margin=-0.464676) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.66
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.33, thr=0.5, margin=-0.17)
- **midhole_world** [FAIL] fitness=0.1502
  - R4_midhole: late_stop不足 (val=0.11790000000000002, thr=0.56, margin=-0.4421)
- **rank7_world** [FAIL] fitness=0.2563
  - R5_rank7: chaos不足 (val=0.195324, thr=0.58, margin=-0.384676)
- **bug_world** [FAIL] fitness=0.2959
  - R6_bug: chaos不足 (val=0.195324, thr=0.66, margin=-0.464676)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-26-01-03` → Decision `mixed_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty | True | R2_midupper_sf_diff: difficulty不足 (val=0.375, thr=0.38, margin=-0.005); R7_mi... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.37083820999999983, thr=0.52, margin=-0.149162) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.43091279999999993, thr=0.58, margin=-0.149087) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.375, thr=0.62, margin=-0.245) |
| `mixed_world` | PASS | phase | — | False | — |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midupper_world** [FAIL] fitness=0.9868
  - R2_midupper_sf_diff: difficulty不足 (val=0.375, thr=0.38, margin=-0.005)
  - R7_midupper_diff: difficulty不足 (val=0.375, thr=0.5, margin=-0.125)
- **midhole_world** [FAIL] fitness=0.7132
  - R4_midhole: sustained不足 (val=0.37083820999999983, thr=0.52, margin=-0.149162)
- **rank7_world** [FAIL] fitness=0.743
  - R5_rank7: chaos不足 (val=0.43091279999999993, thr=0.58, margin=-0.149087)
- **bug_world** [FAIL] fitness=0.6048
  - R6_bug: difficulty不足 (val=0.375, thr=0.62, margin=-0.245)

## `2026-07-26-01-04` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | True | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.3668488888888889, thr=0.56, margin=-0.193151) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.3696032, thr=0.58, margin=-0.210397) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.3696032, thr=0.66, margin=-0.290397) |
| `mixed_world` | FAIL | phase | chaos, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.9167
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.458333, thr=0.5, margin=-0.041667)
- **midhole_world** [FAIL] fitness=0.6551
  - R4_midhole: late_stop不足 (val=0.3668488888888889, thr=0.56, margin=-0.193151)
- **rank7_world** [FAIL] fitness=0.6372
  - R5_rank7: chaos不足 (val=0.3696032, thr=0.58, margin=-0.210397)
- **bug_world** [FAIL] fitness=0.56
  - R6_bug: chaos不足 (val=0.3696032, thr=0.66, margin=-0.290397)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-26-01-05` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty | True | R2_midupper_sf_diff: difficulty不足 (val=0.375, thr=0.38, margin=-0.005); R7_mi... |
| `midhole_world` | FAIL | — | late_stop | False | R4_midhole: late_stop不足 (val=0.445348, thr=0.56, margin=-0.114652) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.41678949333333315, thr=0.58, margin=-0.163211) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.375, thr=0.62, margin=-0.245) |
| `mixed_world` | FAIL | phase | chaos, difficulty | True | R1_mixed_short_field: phase missing; R3_mixed_phase: phase missing |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.9868
  - R2_midupper_sf_diff: difficulty不足 (val=0.375, thr=0.38, margin=-0.005)
  - R7_midupper_diff: difficulty不足 (val=0.375, thr=0.5, margin=-0.125)
- **midhole_world** [FAIL] fitness=0.7953
  - R4_midhole: late_stop不足 (val=0.445348, thr=0.56, margin=-0.114652)
- **rank7_world** [FAIL] fitness=0.7186
  - R5_rank7: chaos不足 (val=0.41678949333333315, thr=0.58, margin=-0.163211)
- **bug_world** [FAIL] fitness=0.6048
  - R6_bug: difficulty不足 (val=0.375, thr=0.62, margin=-0.245)
- **mixed_world** [FAIL] fitness=0.9924
  - R1_mixed_short_field: phase missing
  - R3_mixed_phase: phase missing

## `2026-07-26-02-01` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.11790000000000002, thr=0.56, margin=-0.4421) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.195324, thr=0.58, margin=-0.384676) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.195324, thr=0.66, margin=-0.464676) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.59
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.295, thr=0.5, margin=-0.205)
- **midhole_world** [FAIL] fitness=0.1502
  - R4_midhole: late_stop不足 (val=0.11790000000000002, thr=0.56, margin=-0.4421)
- **rank7_world** [FAIL] fitness=0.2563
  - R5_rank7: chaos不足 (val=0.195324, thr=0.58, margin=-0.384676)
- **bug_world** [FAIL] fitness=0.2959
  - R6_bug: chaos不足 (val=0.195324, thr=0.66, margin=-0.464676)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-26-02-02` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.10289999999999999, thr=0.56, margin=-0.4571) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.18721199999999996, thr=0.58, margin=-0.392788) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.18721199999999996, thr=0.66, margin=-0.472788) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.648
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.324, thr=0.5, margin=-0.176)
- **midhole_world** [FAIL] fitness=0.1564
  - R4_midhole: late_stop不足 (val=0.10289999999999999, thr=0.56, margin=-0.4571)
- **rank7_world** [FAIL] fitness=0.2062
  - R5_rank7: chaos不足 (val=0.18721199999999996, thr=0.58, margin=-0.392788)
- **bug_world** [FAIL] fitness=0.2837
  - R6_bug: chaos不足 (val=0.18721199999999996, thr=0.66, margin=-0.472788)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-26-02-03` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.32309600000000005, thr=0.56, margin=-0.236904) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.31260831999999994, thr=0.58, margin=-0.267392) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.31260831999999994, thr=0.66, margin=-0.347392) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.55
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.275, thr=0.5, margin=-0.225)
- **midhole_world** [FAIL] fitness=0.577
  - R4_midhole: late_stop不足 (val=0.32309600000000005, thr=0.56, margin=-0.236904)
- **rank7_world** [FAIL] fitness=0.539
  - R5_rank7: chaos不足 (val=0.31260831999999994, thr=0.58, margin=-0.267392)
- **bug_world** [FAIL] fitness=0.4435
  - R6_bug: chaos不足 (val=0.31260831999999994, thr=0.66, margin=-0.347392)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-26-02-04` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.3971401466666667, thr=0.52, margin=-0.12286) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.4350411200000001, thr=0.58, margin=-0.144959) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.368333, thr=0.62, margin=-0.251667) |
| `mixed_world` | FAIL | phase | difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.7367
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.368333, thr=0.5, margin=-0.131667)
- **midhole_world** [FAIL] fitness=0.7637
  - R4_midhole: sustained不足 (val=0.3971401466666667, thr=0.52, margin=-0.12286)
- **rank7_world** [FAIL] fitness=0.7501
  - R5_rank7: chaos不足 (val=0.4350411200000001, thr=0.58, margin=-0.144959)
- **bug_world** [FAIL] fitness=0.5941
  - R6_bug: difficulty不足 (val=0.368333, thr=0.62, margin=-0.251667)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-26-02-05` → Decision `mixed_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty | True | R2_midupper_sf_diff: difficulty不足 (val=0.37875, thr=0.38, margin=-0.00125); R... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.3859663125, thr=0.52, margin=-0.134034) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.4425237, thr=0.58, margin=-0.137476) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.37875, thr=0.62, margin=-0.24125) |
| `mixed_world` | PASS | phase | — | False | — |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midupper_world** [FAIL] fitness=0.9967
  - R2_midupper_sf_diff: difficulty不足 (val=0.37875, thr=0.38, margin=-0.00125)
  - R7_midupper_diff: difficulty不足 (val=0.37875, thr=0.5, margin=-0.12125)
- **midhole_world** [FAIL] fitness=0.7422
  - R4_midhole: sustained不足 (val=0.3859663125, thr=0.52, margin=-0.134034)
- **rank7_world** [FAIL] fitness=0.763
  - R5_rank7: chaos不足 (val=0.4425237, thr=0.58, margin=-0.137476)
- **bug_world** [FAIL] fitness=0.6109
  - R6_bug: difficulty不足 (val=0.37875, thr=0.62, margin=-0.24125)

## `2026-07-26-03-01` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.21126375833333333, thr=0.52, margin=-0.308736) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.3519002666666667, thr=0.58, margin=-0.2281) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.3519002666666667, thr=0.66, margin=-0.3081) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.6687
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.334333, thr=0.5, margin=-0.165667)
- **midhole_world** [FAIL] fitness=0.4063
  - R4_midhole: sustained不足 (val=0.21126375833333333, thr=0.52, margin=-0.308736)
- **rank7_world** [FAIL] fitness=0.6067
  - R5_rank7: chaos不足 (val=0.3519002666666667, thr=0.58, margin=-0.2281)
- **bug_world** [FAIL] fitness=0.5332
  - R6_bug: chaos不足 (val=0.3519002666666667, thr=0.66, margin=-0.3081)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-26-03-02` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.41598266666666667, thr=0.56, margin=-0.144017) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.36634938666666667, thr=0.58, margin=-0.213651) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.255, thr=0.62, margin=-0.365) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.51
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.255, thr=0.5, margin=-0.245)
- **midhole_world** [FAIL] fitness=0.7428
  - R4_midhole: late_stop不足 (val=0.41598266666666667, thr=0.56, margin=-0.144017)
- **rank7_world** [FAIL] fitness=0.6316
  - R5_rank7: chaos不足 (val=0.36634938666666667, thr=0.58, margin=-0.213651)
- **bug_world** [FAIL] fitness=0.4113
  - R6_bug: difficulty不足 (val=0.255, thr=0.62, margin=-0.365)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-26-03-03` → Decision `mixed_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | PASS | — | difficulty | False | — |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.45674145, thr=0.52, margin=-0.063259) |
| `rank7_world` | FAIL | — | chaos | False | R5_rank7: chaos不足 (val=0.44639399999999996, thr=0.58, margin=-0.133606) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: difficulty不足 (val=0.385, thr=0.62, margin=-0.235) |
| `mixed_world` | PASS | phase | — | False | — |

### Why-Not detail

- **core_world** [PASS] fitness=0.0
  - Evaluation Order: より高優先度の非core TriggerがPASSしたため R8_core_default に到達せず
- **midupper_world** [PASS] fitness=1.0
  - Evaluation Order: TriggerはPASSだが、より高優先度のDecision(priority≤1)が先に確定
- **midhole_world** [FAIL] fitness=0.8783
  - R4_midhole: sustained不足 (val=0.45674145, thr=0.52, margin=-0.063259)
- **rank7_world** [FAIL] fitness=0.7696
  - R5_rank7: chaos不足 (val=0.44639399999999996, thr=0.58, margin=-0.133606)
- **bug_world** [FAIL] fitness=0.621
  - R6_bug: difficulty不足 (val=0.385, thr=0.62, margin=-0.235)

## `2026-07-26-03-04` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: late_stop不足 (val=0.3230781818181817, thr=0.56, margin=-0.236922) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.3129497454545454, thr=0.58, margin=-0.26705) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.3129497454545454, thr=0.66, margin=-0.34705) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.5973
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.298636, thr=0.5, margin=-0.201364)
- **midhole_world** [FAIL] fitness=0.5769
  - R4_midhole: late_stop不足 (val=0.3230781818181817, thr=0.56, margin=-0.236922)
- **rank7_world** [FAIL] fitness=0.5396
  - R5_rank7: chaos不足 (val=0.3129497454545454, thr=0.58, margin=-0.26705)
- **bug_world** [FAIL] fitness=0.4742
  - R6_bug: chaos不足 (val=0.3129497454545454, thr=0.66, margin=-0.34705)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

## `2026-07-26-03-05` → Decision `core_world`

| World | Status | Missing | Below threshold | Near-miss | Why-Not (要約) |
|---|---|---|---|---|---|
| `core_world` | PASS | — | — | False | — |
| `midupper_world` | FAIL | — | difficulty, short_field_pressure | False | R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)... |
| `midhole_world` | FAIL | — | late_stop, sustained | False | R4_midhole: sustained不足 (val=0.07701, thr=0.52, margin=-0.44299) |
| `rank7_world` | FAIL | — | chaos, high_pace | False | R5_rank7: chaos不足 (val=0.19802799999999995, thr=0.58, margin=-0.381972) |
| `bug_world` | FAIL | — | chaos, difficulty | False | R6_bug: chaos不足 (val=0.19802799999999995, thr=0.66, margin=-0.461972) |
| `mixed_world` | FAIL | phase | chaos, difficulty, short_field_pressure | False | R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72... |

### Why-Not detail

- **midupper_world** [FAIL] fitness=0.75
  - R2_midupper_sf_diff: short_field_pressure不足 (val=0.0, thr=0.58, margin=-0.58)
  - R7_midupper_diff: difficulty不足 (val=0.375, thr=0.5, margin=-0.125)
- **midhole_world** [FAIL] fitness=0.1481
  - R4_midhole: sustained不足 (val=0.07701, thr=0.52, margin=-0.44299)
- **rank7_world** [FAIL] fitness=0.2729
  - R5_rank7: chaos不足 (val=0.19802799999999995, thr=0.58, margin=-0.381972)
- **bug_world** [FAIL] fitness=0.3
  - R6_bug: chaos不足 (val=0.19802799999999995, thr=0.66, margin=-0.461972)
- **mixed_world** [FAIL] fitness=0.0
  - R1_mixed_short_field: short_field_pressure不足 (val=0.0, thr=0.72, margin=-0.72)
  - R3_mixed_phase: phase missing

