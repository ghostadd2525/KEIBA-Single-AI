# Version41 Decision Trace

- generated_at: `2026-07-28T01:10:34+00:00`
- n_races: **56**
- core_share: **75.0%**
- mechanism: priority first-match (`TRIGGER_RULES` → `R8_core_default`)
- signal_pack: V39 FeatureLoader restoration（V40と同一条件）

## Pipeline

```
FeatureLoader / reconstruct_leg_upset / Scorer diagnostics
  → Signals (difficulty, chaos, phase, late_stop, sustained, high_pace, sfp)
  → evaluate_all_rules (R1…R8)
  → first_match_world = Decision
  → trigger_proximity_fitness = soft Fitness
```

## Rule priority order

- P1: `R1_mixed_short_field` → `mixed_world`
- P2: `R2_midupper_sf_diff` → `midupper_world`
- P3: `R3_mixed_phase` → `mixed_world`
- P4: `R4_midhole` → `midhole_world`
- P5: `R5_rank7` → `rank7_world`
- P6: `R6_bug` → `bug_world`
- P7: `R7_midupper_diff` → `midupper_world`
- P8: `R8_core_default` → `core_world`

## Per-Race Traces

### `2026-06-28-函館-11`

- **Decision**: `midupper_world` via `R7_midupper_diff`
- **Best-fit (soft)**: `midupper_world` (agree=True)
- **Root cause**: `その他`
- **Signals**:
  - difficulty: `0.56098`
  - chaos: `0.4588934322994684`
  - phase: `0.526136`
  - late_stop: `0.4846653333333332`
  - sustained: `0.5370714086150227`
  - high_pace: `0.57908`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=-0.093864 bottleneck=phase margin=-0.093864
  - [FAIL] `R4_midhole` → midhole_world margin=-0.075335 bottleneck=late_stop margin=-0.075335
  - [FAIL] `R5_rank7` → rank7_world margin=-0.121107 bottleneck=chaos margin=-0.121107
  - [FAIL] `R6_bug` → bug_world margin=-0.201107 bottleneck=chaos margin=-0.201107
  - [PASS] `R7_midupper_diff` → midupper_world margin=0.06098
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.8486, 'midupper_world': 1.0, 'midhole_world': 0.8655, 'rank7_world': 0.7912, 'bug_world': 0.6953, 'core_world': 0.0}`

### `2026-06-28-小倉-10`

- **Decision**: `midupper_world` via `R7_midupper_diff`
- **Best-fit (soft)**: `midupper_world` (agree=True)
- **Root cause**: `Boundary`
- **Signals**:
  - difficulty: `0.522803`
  - chaos: `0.46247676058572496`
  - phase: `0.496822`
  - late_stop: `0.514255`
  - sustained: `0.5437896004152547`
  - high_pace: `0.6234500000000001`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=-0.123178 bottleneck=phase margin=-0.123178
  - [FAIL] `R4_midhole` → midhole_world margin=-0.045745 bottleneck=late_stop margin=-0.045745
  - [FAIL] `R5_rank7` → rank7_world margin=-0.117523 bottleneck=chaos margin=-0.117523
  - [FAIL] `R6_bug` → bug_world margin=-0.197523 bottleneck=chaos margin=-0.197523
  - [PASS] `R7_midupper_diff` → midupper_world margin=0.022803
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.8013, 'midupper_world': 1.0, 'midhole_world': 0.9183, 'rank7_world': 0.7974, 'bug_world': 0.7007, 'core_world': 0.0}`

### `2026-06-28-小倉-11`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.429357`
  - chaos: `0.34862892141050966`
  - phase: `0.492831`
  - late_stop: `0.41656000000000004`
  - sustained: `0.5168956991965441`
  - high_pace: `0.5184000000000001`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=-0.127169 bottleneck=phase margin=-0.127169
  - [FAIL] `R4_midhole` → midhole_world margin=-0.14344 bottleneck=late_stop margin=-0.14344
  - [FAIL] `R5_rank7` → rank7_world margin=-0.231371 bottleneck=chaos margin=-0.231371
  - [FAIL] `R6_bug` → bug_world margin=-0.311371 bottleneck=chaos margin=-0.311371
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.070643 bottleneck=difficulty margin=-0.070643
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.7949, 'midupper_world': 0.8587, 'midhole_world': 0.7439, 'rank7_world': 0.6011, 'bug_world': 0.5282, 'core_world': 0.1413}`

### `2026-06-28-福島-10`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.446047`
  - chaos: `0.4024794875578539`
  - phase: `0.515422`
  - late_stop: `0.503910909090909`
  - sustained: `0.5293022583621781`
  - high_pace: `0.634890909090909`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=-0.104578 bottleneck=phase margin=-0.104578
  - [FAIL] `R4_midhole` → midhole_world margin=-0.056089 bottleneck=late_stop margin=-0.056089
  - [FAIL] `R5_rank7` → rank7_world margin=-0.177521 bottleneck=chaos margin=-0.177521
  - [FAIL] `R6_bug` → bug_world margin=-0.257521 bottleneck=chaos margin=-0.257521
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.053953 bottleneck=difficulty margin=-0.053953
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.8313, 'midupper_world': 0.8921, 'midhole_world': 0.8998, 'rank7_world': 0.6939, 'bug_world': 0.6098, 'core_world': 0.1002}`

### `2026-06-28-福島-11`

- **Decision**: `midhole_world` via `R4_midhole`
- **Best-fit (soft)**: `midhole_world` (agree=True)
- **Root cause**: `Boundary`
- **Signals**:
  - difficulty: `0.600738`
  - chaos: `0.5188479456819488`
  - phase: `0.573066`
  - late_stop: `0.5831275`
  - sustained: `0.5698127005485996`
  - high_pace: `0.726725`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=-0.046934 bottleneck=phase margin=-0.046934
  - [PASS] `R4_midhole` → midhole_world margin=0.023127
  - [FAIL] `R5_rank7` → rank7_world margin=-0.061152 bottleneck=chaos margin=-0.061152
  - [FAIL] `R6_bug` → bug_world margin=-0.141152 bottleneck=chaos margin=-0.141152
  - [PASS] `R7_midupper_diff` → midupper_world margin=0.100738
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.9243, 'midupper_world': 1.0, 'midhole_world': 1.0, 'rank7_world': 0.8946, 'bug_world': 0.7861, 'core_world': 0.0}`

### `2026-07-25-01-01`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.291`
  - chaos: `0.244741484116`
  - phase: `None`
  - late_stop: `0.19509259995`
  - sustained: `0.1173388652`
  - high_pace: `0.22208`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.402661 bottleneck=sustained margin=-0.402661
  - [FAIL] `R5_rank7` → rank7_world margin=-0.335259 bottleneck=chaos margin=-0.335259
  - [FAIL] `R6_bug` → bug_world margin=-0.415259 bottleneck=chaos margin=-0.415259
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.209 bottleneck=difficulty margin=-0.209
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.582, 'midhole_world': 0.2257, 'rank7_world': 0.422, 'bug_world': 0.3708, 'core_world': 0.418}`

### `2026-07-25-01-02`

- **Decision**: `midupper_world` via `R2_midupper_sf_diff`
- **Best-fit (soft)**: `midupper_world` (agree=True)
- **Root cause**: `その他`
- **Signals**:
  - difficulty: `0.43`
  - chaos: `0.32613549042857143`
  - phase: `None`
  - late_stop: `0.2787878624999999`
  - sustained: `0.1063077142857143`
  - high_pace: `0.319`
  - short_field_pressure: `0.6412091554738095`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.078791 bottleneck=short_field_pressure margin=-0.078791
  - [PASS] `R2_midupper_sf_diff` → midupper_world margin=0.05
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.413692 bottleneck=sustained margin=-0.413692
  - [FAIL] `R5_rank7` → rank7_world margin=-0.253865 bottleneck=chaos margin=-0.253865
  - [FAIL] `R6_bug` → bug_world margin=-0.333865 bottleneck=chaos margin=-0.333865
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.07 bottleneck=difficulty margin=-0.07
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.8906, 'midupper_world': 1.0, 'midhole_world': 0.2044, 'rank7_world': 0.5623, 'bug_world': 0.4941, 'core_world': 0.0}`

### `2026-07-25-01-03`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.275`
  - chaos: `0.19906810618749998`
  - phase: `None`
  - late_stop: `0.11626375703125`
  - sustained: `0.08353`
  - high_pace: `0.115`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.443736 bottleneck=late_stop margin=-0.443736
  - [FAIL] `R5_rank7` → rank7_world margin=-0.380932 bottleneck=chaos margin=-0.380932
  - [FAIL] `R6_bug` → bug_world margin=-0.460932 bottleneck=chaos margin=-0.460932
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.225 bottleneck=difficulty margin=-0.225
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.55, 'midhole_world': 0.1606, 'rank7_world': 0.2396, 'bug_world': 0.3016, 'core_world': 0.45}`

### `2026-07-25-01-04`

- **Decision**: `mixed_world` via `R1_mixed_short_field`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Evaluation Order`
- **Signals**:
  - difficulty: `0.381667`
  - chaos: `0.4226221114663946`
  - phase: `None`
  - late_stop: `0.43551133965059996`
  - sustained: `0.38434700571733327`
  - high_pace: `0.5056399999999999`
  - short_field_pressure: `0.7789464389066532`
- **Trigger chain**:
  - [PASS] `R1_mixed_short_field` → mixed_world margin=0.002622
  - [PASS] `R2_midupper_sf_diff` → midupper_world margin=0.001667
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.135653 bottleneck=sustained margin=-0.135653
  - [FAIL] `R5_rank7` → rank7_world margin=-0.157378 bottleneck=chaos margin=-0.157378
  - [FAIL] `R6_bug` → bug_world margin=-0.238333 bottleneck=difficulty margin=-0.238333
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.118333 bottleneck=difficulty margin=-0.118333
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 1.0, 'midupper_world': 1.0, 'midhole_world': 0.7391, 'rank7_world': 0.7287, 'bug_world': 0.6156, 'core_world': 0.0}`

### `2026-07-25-01-05`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.289545`
  - chaos: `0.3401611189829939`
  - phase: `None`
  - late_stop: `0.3590415287616666`
  - sustained: `0.49936921709090903`
  - high_pace: `0.4346`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.200958 bottleneck=late_stop margin=-0.200958
  - [FAIL] `R5_rank7` → rank7_world margin=-0.239839 bottleneck=chaos margin=-0.239839
  - [FAIL] `R6_bug` → bug_world margin=-0.330455 bottleneck=difficulty margin=-0.330455
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.210455 bottleneck=difficulty margin=-0.210455
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.5791, 'midhole_world': 0.6411, 'rank7_world': 0.5865, 'bug_world': 0.467, 'core_world': 0.3589}`

### `2026-07-25-01-06`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Boundary`
- **Signals**:
  - difficulty: `0.355`
  - chaos: `0.47060422380156813`
  - phase: `None`
  - late_stop: `0.5264766714836001`
  - sustained: `0.5453257877866665`
  - high_pace: `0.6280400000000002`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.033523 bottleneck=late_stop margin=-0.033523
  - [FAIL] `R5_rank7` → rank7_world margin=-0.109396 bottleneck=chaos margin=-0.109396
  - [FAIL] `R6_bug` → bug_world margin=-0.265 bottleneck=difficulty margin=-0.265
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.145 bottleneck=difficulty margin=-0.145
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.71, 'midhole_world': 0.9401, 'rank7_world': 0.8114, 'bug_world': 0.5726, 'core_world': 0.0599}`

### `2026-07-25-01-07`

- **Decision**: `mixed_world` via `R1_mixed_short_field`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Evaluation Order`
- **Signals**:
  - difficulty: `0.407941`
  - chaos: `0.4514301602240942`
  - phase: `None`
  - late_stop: `0.4839957878482353`
  - sustained: `0.5408107483529411`
  - high_pace: `0.5546`
  - short_field_pressure: `0.9107720962464989`
- **Trigger chain**:
  - [PASS] `R1_mixed_short_field` → mixed_world margin=0.03143
  - [PASS] `R2_midupper_sf_diff` → midupper_world margin=0.027941
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.076004 bottleneck=late_stop margin=-0.076004
  - [FAIL] `R5_rank7` → rank7_world margin=-0.12857 bottleneck=chaos margin=-0.12857
  - [FAIL] `R6_bug` → bug_world margin=-0.212059 bottleneck=difficulty margin=-0.212059
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.092059 bottleneck=difficulty margin=-0.092059
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 1.0, 'midupper_world': 1.0, 'midhole_world': 0.8643, 'rank7_world': 0.7783, 'bug_world': 0.658, 'core_world': 0.0}`

### `2026-07-25-01-08`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.321154`
  - chaos: `0.36522191291406164`
  - phase: `None`
  - late_stop: `0.4003569485911538`
  - sustained: `0.4842972976923076`
  - high_pace: `0.4769692307692308`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.159643 bottleneck=late_stop margin=-0.159643
  - [FAIL] `R5_rank7` → rank7_world margin=-0.214778 bottleneck=chaos margin=-0.214778
  - [FAIL] `R6_bug` → bug_world margin=-0.298846 bottleneck=difficulty margin=-0.298846
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.178846 bottleneck=difficulty margin=-0.178846
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.6423, 'midhole_world': 0.7149, 'rank7_world': 0.6297, 'bug_world': 0.518, 'core_world': 0.2851}`

### `2026-07-25-01-09`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.2125`
  - chaos: `0.39585322363891196`
  - phase: `None`
  - late_stop: `0.45867859806239997`
  - sustained: `0.5038357566799999`
  - high_pace: `0.56312`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.101321 bottleneck=late_stop margin=-0.101321
  - [FAIL] `R5_rank7` → rank7_world margin=-0.184147 bottleneck=chaos margin=-0.184147
  - [FAIL] `R6_bug` → bug_world margin=-0.4075 bottleneck=difficulty margin=-0.4075
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.2875 bottleneck=difficulty margin=-0.2875
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.425, 'midhole_world': 0.8191, 'rank7_world': 0.6825, 'bug_world': 0.3427, 'core_world': 0.1809}`

### `2026-07-25-01-10`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.408333`
  - chaos: `0.3623725376432266`
  - phase: `None`
  - late_stop: `0.3371968524903334`
  - sustained: `0.4088796009813333`
  - high_pace: `0.3914799999999999`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.222803 bottleneck=late_stop margin=-0.222803
  - [FAIL] `R5_rank7` → rank7_world margin=-0.217627 bottleneck=chaos margin=-0.217627
  - [FAIL] `R6_bug` → bug_world margin=-0.297627 bottleneck=chaos margin=-0.297627
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.091667 bottleneck=difficulty margin=-0.091667
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.8167, 'midhole_world': 0.6021, 'rank7_world': 0.6248, 'bug_world': 0.549, 'core_world': 0.1833}`

### `2026-07-25-01-11`

- **Decision**: `mixed_world` via `R1_mixed_short_field`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Evaluation Order`
- **Signals**:
  - difficulty: `0.419444`
  - chaos: `0.4634635251680297`
  - phase: `None`
  - late_stop: `0.5099986144114815`
  - sustained: `0.34797792782962966`
  - high_pace: `0.6056000000000001`
  - short_field_pressure: `0.9094531762584016`
- **Trigger chain**:
  - [PASS] `R1_mixed_short_field` → mixed_world margin=0.043464
  - [PASS] `R2_midupper_sf_diff` → midupper_world margin=0.039444
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.172022 bottleneck=sustained margin=-0.172022
  - [FAIL] `R5_rank7` → rank7_world margin=-0.116536 bottleneck=chaos margin=-0.116536
  - [FAIL] `R6_bug` → bug_world margin=-0.200556 bottleneck=difficulty margin=-0.200556
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.080556 bottleneck=difficulty margin=-0.080556
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 1.0, 'midupper_world': 1.0, 'midhole_world': 0.6692, 'rank7_world': 0.7991, 'bug_world': 0.6765, 'core_world': 0.0}`

### `2026-07-25-01-12`

- **Decision**: `mixed_world` via `R1_mixed_short_field`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Evaluation Order`
- **Signals**:
  - difficulty: `0.390294`
  - chaos: `0.48137107925062006`
  - phase: `None`
  - late_stop: `0.5479624861858651`
  - sustained: `0.5377574730823529`
  - high_pace: `0.6626`
  - short_field_pressure: `0.9134338480801781`
- **Trigger chain**:
  - [PASS] `R1_mixed_short_field` → mixed_world margin=0.061371
  - [PASS] `R2_midupper_sf_diff` → midupper_world margin=0.010294
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.012038 bottleneck=late_stop margin=-0.012038
  - [FAIL] `R5_rank7` → rank7_world margin=-0.098629 bottleneck=chaos margin=-0.098629
  - [FAIL] `R6_bug` → bug_world margin=-0.229706 bottleneck=difficulty margin=-0.229706
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.109706 bottleneck=difficulty margin=-0.109706
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 1.0, 'midupper_world': 1.0, 'midhole_world': 0.9785, 'rank7_world': 0.83, 'bug_world': 0.6295, 'core_world': 0.0}`

### `2026-07-25-02-01`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.295`
  - chaos: `0.20183076105555556`
  - phase: `None`
  - late_stop: `0.12089000624999999`
  - sustained: `0.08293444444444445`
  - high_pace: `0.123`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.43911 bottleneck=late_stop margin=-0.43911
  - [FAIL] `R5_rank7` → rank7_world margin=-0.378169 bottleneck=chaos margin=-0.378169
  - [FAIL] `R6_bug` → bug_world margin=-0.458169 bottleneck=chaos margin=-0.458169
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.205 bottleneck=difficulty margin=-0.205
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.59, 'midhole_world': 0.1595, 'rank7_world': 0.2563, 'bug_world': 0.3058, 'core_world': 0.41}`

### `2026-07-25-02-02`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.424`
  - chaos: `0.21225452688461535`
  - phase: `None`
  - late_stop: `0.13997000432692314`
  - sustained: `0.07913615384615383`
  - high_pace: `0.15500000000000005`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.440864 bottleneck=sustained margin=-0.440864
  - [FAIL] `R5_rank7` → rank7_world margin=-0.367745 bottleneck=chaos margin=-0.367745
  - [FAIL] `R6_bug` → bug_world margin=-0.447745 bottleneck=chaos margin=-0.447745
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.076 bottleneck=difficulty margin=-0.076
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.848, 'midhole_world': 0.1522, 'rank7_world': 0.3229, 'bug_world': 0.3216, 'core_world': 0.152}`

### `2026-07-25-02-03`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.305`
  - chaos: `0.37327953446256673`
  - phase: `None`
  - late_stop: `0.41317427825291664`
  - sustained: `0.3963961661666666`
  - high_pace: `0.4958`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.146826 bottleneck=late_stop margin=-0.146826
  - [FAIL] `R5_rank7` → rank7_world margin=-0.20672 bottleneck=chaos margin=-0.20672
  - [FAIL] `R6_bug` → bug_world margin=-0.315 bottleneck=difficulty margin=-0.315
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.195 bottleneck=difficulty margin=-0.195
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.61, 'midhole_world': 0.7378, 'rank7_world': 0.6436, 'bug_world': 0.4919, 'core_world': 0.2622}`

### `2026-07-25-02-04`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.37875`
  - chaos: `0.48057229999995`
  - phase: `None`
  - late_stop: `0.542698643818125`
  - sustained: `0.43123974179999996`
  - high_pace: `0.6464`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.08876 bottleneck=sustained margin=-0.08876
  - [FAIL] `R5_rank7` → rank7_world margin=-0.099428 bottleneck=chaos margin=-0.099428
  - [FAIL] `R6_bug` → bug_world margin=-0.24125 bottleneck=difficulty margin=-0.24125
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.12125 bottleneck=difficulty margin=-0.12125
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.7575, 'midhole_world': 0.8293, 'rank7_world': 0.8286, 'bug_world': 0.6109, 'core_world': 0.1707}`

### `2026-07-25-02-05`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.4225`
  - chaos: `0.37252336440818334`
  - phase: `None`
  - late_stop: `0.3556104101002084`
  - sustained: `0.31366097315`
  - high_pace: `0.4169`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.206339 bottleneck=sustained margin=-0.206339
  - [FAIL] `R5_rank7` → rank7_world margin=-0.207477 bottleneck=chaos margin=-0.207477
  - [FAIL] `R6_bug` → bug_world margin=-0.287477 bottleneck=chaos margin=-0.287477
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.0775 bottleneck=difficulty margin=-0.0775
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.845, 'midhole_world': 0.6032, 'rank7_world': 0.6423, 'bug_world': 0.5644, 'core_world': 0.155}`

### `2026-07-25-02-06`

- **Decision**: `mixed_world` via `R1_mixed_short_field`
- **Best-fit (soft)**: `mixed_world` (agree=True)
- **Root cause**: `Boundary`
- **Signals**:
  - difficulty: `0.3725`
  - chaos: `0.4673767380017875`
  - phase: `None`
  - late_stop: `0.5228261925020312`
  - sustained: `0.5603929919999999`
  - high_pace: `0.6234500000000001`
  - short_field_pressure: `0.9110413369000895`
- **Trigger chain**:
  - [PASS] `R1_mixed_short_field` → mixed_world margin=0.047377
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.0075 bottleneck=difficulty margin=-0.0075
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.037174 bottleneck=late_stop margin=-0.037174
  - [FAIL] `R5_rank7` → rank7_world margin=-0.112623 bottleneck=chaos margin=-0.112623
  - [FAIL] `R6_bug` → bug_world margin=-0.2475 bottleneck=difficulty margin=-0.2475
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.1275 bottleneck=difficulty margin=-0.1275
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 1.0, 'midupper_world': 0.9803, 'midhole_world': 0.9336, 'rank7_world': 0.8058, 'bug_world': 0.6008, 'core_world': 0.0}`

### `2026-07-25-02-07`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.307727`
  - chaos: `0.2981430366973697`
  - phase: `None`
  - late_stop: `0.28701662765196967`
  - sustained: `0.5015473372727273`
  - high_pace: `0.33983636363636366`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.272983 bottleneck=late_stop margin=-0.272983
  - [FAIL] `R5_rank7` → rank7_world margin=-0.281857 bottleneck=chaos margin=-0.281857
  - [FAIL] `R6_bug` → bug_world margin=-0.361857 bottleneck=chaos margin=-0.361857
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.192273 bottleneck=difficulty margin=-0.192273
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.6155, 'midhole_world': 0.5125, 'rank7_world': 0.514, 'bug_world': 0.4517, 'core_world': 0.3845}`

### `2026-07-25-02-08`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.2125`
  - chaos: `0.38172982968020824`
  - phase: `None`
  - late_stop: `0.44192804509114586`
  - sustained: `0.5162156`
  - high_pace: `0.54935`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.118072 bottleneck=late_stop margin=-0.118072
  - [FAIL] `R5_rank7` → rank7_world margin=-0.19827 bottleneck=chaos margin=-0.19827
  - [FAIL] `R6_bug` → bug_world margin=-0.4075 bottleneck=difficulty margin=-0.4075
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.2875 bottleneck=difficulty margin=-0.2875
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.425, 'midhole_world': 0.7892, 'rank7_world': 0.6582, 'bug_world': 0.3427, 'core_world': 0.2108}`

### `2026-07-25-02-09`

- **Decision**: `mixed_world` via `R1_mixed_short_field`
- **Best-fit (soft)**: `mixed_world` (agree=True)
- **Root cause**: `Boundary`
- **Signals**:
  - difficulty: `0.37875`
  - chaos: `0.47294146980350626`
  - phase: `None`
  - late_stop: `0.5306228180039844`
  - sustained: `0.545482059325`
  - high_pace: `0.6349250000000001`
  - short_field_pressure: `0.9118933234901754`
- **Trigger chain**:
  - [PASS] `R1_mixed_short_field` → mixed_world margin=0.052941
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.00125 bottleneck=difficulty margin=-0.00125
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.029377 bottleneck=late_stop margin=-0.029377
  - [FAIL] `R5_rank7` → rank7_world margin=-0.107059 bottleneck=chaos margin=-0.107059
  - [FAIL] `R6_bug` → bug_world margin=-0.24125 bottleneck=difficulty margin=-0.24125
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.12125 bottleneck=difficulty margin=-0.12125
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 1.0, 'midupper_world': 0.9967, 'midhole_world': 0.9475, 'rank7_world': 0.8154, 'bug_world': 0.6109, 'core_world': 0.0}`

### `2026-07-25-02-10`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.305`
  - chaos: `0.3435464173399667`
  - phase: `None`
  - late_stop: `0.36419954212875`
  - sustained: `0.5115682836666666`
  - high_pace: `0.43459999999999993`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.1958 bottleneck=late_stop margin=-0.1958
  - [FAIL] `R5_rank7` → rank7_world margin=-0.236454 bottleneck=chaos margin=-0.236454
  - [FAIL] `R6_bug` → bug_world margin=-0.316454 bottleneck=chaos margin=-0.316454
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.195 bottleneck=difficulty margin=-0.195
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.61, 'midhole_world': 0.6504, 'rank7_world': 0.5923, 'bug_world': 0.4919, 'core_world': 0.3496}`

### `2026-07-25-02-11`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.2125`
  - chaos: `0.38527738216622076`
  - phase: `None`
  - late_stop: `0.44343404746161463`
  - sustained: `0.48738930049999996`
  - high_pace: `0.54935`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.116566 bottleneck=late_stop margin=-0.116566
  - [FAIL] `R5_rank7` → rank7_world margin=-0.194723 bottleneck=chaos margin=-0.194723
  - [FAIL] `R6_bug` → bug_world margin=-0.4075 bottleneck=difficulty margin=-0.4075
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.2875 bottleneck=difficulty margin=-0.2875
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.425, 'midhole_world': 0.7918, 'rank7_world': 0.6643, 'bug_world': 0.3427, 'core_world': 0.2082}`

### `2026-07-25-02-12`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.41625`
  - chaos: `0.39220565893659376`
  - phase: `None`
  - late_stop: `0.38517903710976564`
  - sustained: `0.458900935975`
  - high_pace: `0.43985`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.174821 bottleneck=late_stop margin=-0.174821
  - [FAIL] `R5_rank7` → rank7_world margin=-0.187794 bottleneck=chaos margin=-0.187794
  - [FAIL] `R6_bug` → bug_world margin=-0.267794 bottleneck=chaos margin=-0.267794
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.08375 bottleneck=difficulty margin=-0.08375
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.8325, 'midhole_world': 0.6878, 'rank7_world': 0.6762, 'bug_world': 0.5943, 'core_world': 0.1675}`

### `2026-07-25-03-01`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.221`
  - chaos: `0.3590782351249999`
  - phase: `None`
  - late_stop: `0.40074290718750005`
  - sustained: `0.46048243975`
  - high_pace: `0.49040000000000006`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.159257 bottleneck=late_stop margin=-0.159257
  - [FAIL] `R5_rank7` → rank7_world margin=-0.220922 bottleneck=chaos margin=-0.220922
  - [FAIL] `R6_bug` → bug_world margin=-0.399 bottleneck=difficulty margin=-0.399
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.279 bottleneck=difficulty margin=-0.279
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.442, 'midhole_world': 0.7156, 'rank7_world': 0.6191, 'bug_world': 0.3565, 'core_world': 0.2844}`

### `2026-07-25-03-02`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `rank7_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.225`
  - chaos: `0.36213778209409164`
  - phase: `None`
  - late_stop: `0.4015428719251042`
  - sustained: `0.258855581`
  - high_pace: `0.49145000000000005`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.261144 bottleneck=sustained margin=-0.261144
  - [FAIL] `R5_rank7` → rank7_world margin=-0.217862 bottleneck=chaos margin=-0.217862
  - [FAIL] `R6_bug` → bug_world margin=-0.395 bottleneck=difficulty margin=-0.395
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.275 bottleneck=difficulty margin=-0.275
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.45, 'midhole_world': 0.4978, 'rank7_world': 0.6244, 'bug_world': 0.3629, 'core_world': 0.3756}`

### `2026-07-25-03-03`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.255`
  - chaos: `0.37292462043117064`
  - phase: `None`
  - late_stop: `0.4184451576899667`
  - sustained: `0.47044767208000005`
  - high_pace: `0.50804`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.141555 bottleneck=late_stop margin=-0.141555
  - [FAIL] `R5_rank7` → rank7_world margin=-0.207075 bottleneck=chaos margin=-0.207075
  - [FAIL] `R6_bug` → bug_world margin=-0.365 bottleneck=difficulty margin=-0.365
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.245 bottleneck=difficulty margin=-0.245
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.51, 'midhole_world': 0.7472, 'rank7_world': 0.643, 'bug_world': 0.4113, 'core_world': 0.2528}`

### `2026-07-25-03-04`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.337857`
  - chaos: `0.4697993949743999`
  - phase: `None`
  - late_stop: `0.5211539348085713`
  - sustained: `0.42393084757142857`
  - high_pace: `0.6201714285714284`
  - short_field_pressure: `0.42830806498681523`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.291692 bottleneck=short_field_pressure margin=-0.291692
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.151692 bottleneck=short_field_pressure margin=-0.151692
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.096069 bottleneck=sustained margin=-0.096069
  - [FAIL] `R5_rank7` → rank7_world margin=-0.110201 bottleneck=chaos margin=-0.110201
  - [FAIL] `R6_bug` → bug_world margin=-0.282143 bottleneck=difficulty margin=-0.282143
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.162143 bottleneck=difficulty margin=-0.162143
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.5949, 'midupper_world': 0.7385, 'midhole_world': 0.8153, 'rank7_world': 0.81, 'bug_world': 0.5449, 'core_world': 0.1847}`

### `2026-07-25-03-05`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.275`
  - chaos: `0.19348414158333335`
  - phase: `None`
  - late_stop: `0.10738500937499999`
  - sustained: `0.08423666666666667`
  - high_pace: `0.09899999999999999`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.452615 bottleneck=late_stop margin=-0.452615
  - [FAIL] `R5_rank7` → rank7_world margin=-0.386516 bottleneck=chaos margin=-0.386516
  - [FAIL] `R6_bug` → bug_world margin=-0.466516 bottleneck=chaos margin=-0.466516
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.225 bottleneck=difficulty margin=-0.225
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.55, 'midhole_world': 0.162, 'rank7_world': 0.2062, 'bug_world': 0.2932, 'core_world': 0.45}`

### `2026-07-25-03-06`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.352143`
  - chaos: `0.4361892673504762`
  - phase: `None`
  - late_stop: `0.46101891154761915`
  - sustained: `0.5030321886285715`
  - high_pace: `0.5414857142857146`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.098981 bottleneck=late_stop margin=-0.098981
  - [FAIL] `R5_rank7` → rank7_world margin=-0.143811 bottleneck=chaos margin=-0.143811
  - [FAIL] `R6_bug` → bug_world margin=-0.267857 bottleneck=difficulty margin=-0.267857
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.147857 bottleneck=difficulty margin=-0.147857
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.7043, 'midhole_world': 0.8232, 'rank7_world': 0.7521, 'bug_world': 0.568, 'core_world': 0.1768}`

### `2026-07-25-03-07`

- **Decision**: `mixed_world` via `R1_mixed_short_field`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Evaluation Order`
- **Signals**:
  - difficulty: `0.335`
  - chaos: `0.50818344726576`
  - phase: `None`
  - late_stop: `0.6004966068019999`
  - sustained: `0.5514868249333332`
  - high_pace: `0.7382000000000003`
  - short_field_pressure: `0.7924525056966214`
- **Trigger chain**:
  - [PASS] `R1_mixed_short_field` → mixed_world margin=0.072453
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.045 bottleneck=difficulty margin=-0.045
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [PASS] `R4_midhole` → midhole_world margin=0.031487
  - [FAIL] `R5_rank7` → rank7_world margin=-0.071817 bottleneck=chaos margin=-0.071817
  - [FAIL] `R6_bug` → bug_world margin=-0.285 bottleneck=difficulty margin=-0.285
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.165 bottleneck=difficulty margin=-0.165
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 1.0, 'midupper_world': 0.8816, 'midhole_world': 1.0, 'rank7_world': 0.8762, 'bug_world': 0.5403, 'core_world': 0.0}`

### `2026-07-25-03-08`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.296667`
  - chaos: `0.3720898427292334`
  - phase: `None`
  - late_stop: `0.41317427825291664`
  - sustained: `0.5050027181666666`
  - high_pace: `0.4958`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.146826 bottleneck=late_stop margin=-0.146826
  - [FAIL] `R5_rank7` → rank7_world margin=-0.20791 bottleneck=chaos margin=-0.20791
  - [FAIL] `R6_bug` → bug_world margin=-0.323333 bottleneck=difficulty margin=-0.323333
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.203333 bottleneck=difficulty margin=-0.203333
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.5933, 'midhole_world': 0.7378, 'rank7_world': 0.6415, 'bug_world': 0.4785, 'core_world': 0.2622}`

### `2026-07-25-03-09`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.235`
  - chaos: `0.40070029657304806`
  - phase: `None`
  - late_stop: `0.4709786337421`
  - sustained: `0.48172656860000007`
  - high_pace: `0.58148`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.089021 bottleneck=late_stop margin=-0.089021
  - [FAIL] `R5_rank7` → rank7_world margin=-0.1793 bottleneck=chaos margin=-0.1793
  - [FAIL] `R6_bug` → bug_world margin=-0.385 bottleneck=difficulty margin=-0.385
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.265 bottleneck=difficulty margin=-0.265
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.47, 'midhole_world': 0.841, 'rank7_world': 0.6909, 'bug_world': 0.379, 'core_world': 0.159}`

### `2026-07-25-03-10`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.271364`
  - chaos: `0.3795361870046975`
  - phase: `None`
  - late_stop: `0.4281866512731819`
  - sustained: `0.48311684917355363`
  - high_pace: `0.5180545454545457`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.131813 bottleneck=late_stop margin=-0.131813
  - [FAIL] `R5_rank7` → rank7_world margin=-0.200464 bottleneck=chaos margin=-0.200464
  - [FAIL] `R6_bug` → bug_world margin=-0.348636 bottleneck=difficulty margin=-0.348636
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.228636 bottleneck=difficulty margin=-0.228636
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.5427, 'midhole_world': 0.7646, 'rank7_world': 0.6544, 'bug_world': 0.4377, 'core_world': 0.2354}`

### `2026-07-25-03-11`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.288333`
  - chaos: `0.38255115101693327`
  - phase: `None`
  - late_stop: `0.435619920095`
  - sustained: `0.5169399808333331`
  - high_pace: `0.5263999999999999`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.12438 bottleneck=late_stop margin=-0.12438
  - [FAIL] `R5_rank7` → rank7_world margin=-0.197449 bottleneck=chaos margin=-0.197449
  - [FAIL] `R6_bug` → bug_world margin=-0.331667 bottleneck=difficulty margin=-0.331667
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.211667 bottleneck=difficulty margin=-0.211667
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.5767, 'midhole_world': 0.7779, 'rank7_world': 0.6596, 'bug_world': 0.4651, 'core_world': 0.2221}`

### `2026-07-25-03-12`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.289545`
  - chaos: `0.33988527585801215`
  - phase: `None`
  - late_stop: `0.3609429572766666`
  - sustained: `0.5151684554545454`
  - high_pace: `0.4346`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.199057 bottleneck=late_stop margin=-0.199057
  - [FAIL] `R5_rank7` → rank7_world margin=-0.240115 bottleneck=chaos margin=-0.240115
  - [FAIL] `R6_bug` → bug_world margin=-0.330455 bottleneck=difficulty margin=-0.330455
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.210455 bottleneck=difficulty margin=-0.210455
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.5791, 'midhole_world': 0.6445, 'rank7_world': 0.586, 'bug_world': 0.467, 'core_world': 0.3555}`

### `2026-07-26-01-01`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.311909`
  - chaos: `0.23858858181818177`
  - phase: `None`
  - late_stop: `0.1937927272727272`
  - sustained: `0.10723640000000002`
  - high_pace: `0.22507272727272729`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.412764 bottleneck=sustained margin=-0.412764
  - [FAIL] `R5_rank7` → rank7_world margin=-0.341411 bottleneck=chaos margin=-0.341411
  - [FAIL] `R6_bug` → bug_world margin=-0.421411 bottleneck=chaos margin=-0.421411
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.188091 bottleneck=difficulty margin=-0.188091
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.6238, 'midhole_world': 0.2062, 'rank7_world': 0.4114, 'bug_world': 0.3615, 'core_world': 0.3762}`

### `2026-07-26-01-02`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.33`
  - chaos: `0.195324`
  - phase: `None`
  - late_stop: `0.11790000000000002`
  - sustained: `0.07809`
  - high_pace: `0.123`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.4421 bottleneck=late_stop margin=-0.4421
  - [FAIL] `R5_rank7` → rank7_world margin=-0.384676 bottleneck=chaos margin=-0.384676
  - [FAIL] `R6_bug` → bug_world margin=-0.464676 bottleneck=chaos margin=-0.464676
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.17 bottleneck=difficulty margin=-0.17
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.66, 'midhole_world': 0.1502, 'rank7_world': 0.2563, 'bug_world': 0.2959, 'core_world': 0.34}`

### `2026-07-26-01-03`

- **Decision**: `mixed_world` via `R1_mixed_short_field`
- **Best-fit (soft)**: `mixed_world` (agree=True)
- **Root cause**: `Boundary`
- **Signals**:
  - difficulty: `0.375`
  - chaos: `0.43091279999999993`
  - phase: `None`
  - late_stop: `0.4683400000000002`
  - sustained: `0.37083820999999983`
  - high_pace: `0.5546`
  - short_field_pressure: `0.7962089733333334`
- **Trigger chain**:
  - [PASS] `R1_mixed_short_field` → mixed_world margin=0.010913
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.005 bottleneck=difficulty margin=-0.005
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.149162 bottleneck=sustained margin=-0.149162
  - [FAIL] `R5_rank7` → rank7_world margin=-0.149087 bottleneck=chaos margin=-0.149087
  - [FAIL] `R6_bug` → bug_world margin=-0.245 bottleneck=difficulty margin=-0.245
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.125 bottleneck=difficulty margin=-0.125
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 1.0, 'midupper_world': 0.9868, 'midhole_world': 0.7132, 'rank7_world': 0.743, 'bug_world': 0.6048, 'core_world': 0.0}`

### `2026-07-26-01-04`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Boundary`
- **Signals**:
  - difficulty: `0.458333`
  - chaos: `0.3696032`
  - phase: `None`
  - late_stop: `0.3668488888888889`
  - sustained: `0.4074500638888889`
  - high_pace: `0.4424`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.193151 bottleneck=late_stop margin=-0.193151
  - [FAIL] `R5_rank7` → rank7_world margin=-0.210397 bottleneck=chaos margin=-0.210397
  - [FAIL] `R6_bug` → bug_world margin=-0.290397 bottleneck=chaos margin=-0.290397
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.041667 bottleneck=difficulty margin=-0.041667
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.9167, 'midhole_world': 0.6551, 'rank7_world': 0.6372, 'bug_world': 0.56, 'core_world': 0.0833}`

### `2026-07-26-01-05`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `mixed_world` (agree=False)
- **Root cause**: `Boundary`
- **Signals**:
  - difficulty: `0.375`
  - chaos: `0.41678949333333315`
  - phase: `None`
  - late_stop: `0.445348`
  - sustained: `0.5279258033333333`
  - high_pace: `0.53012`
  - short_field_pressure: `0.7942788080000001`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.003211 bottleneck=phase margin=None
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.005 bottleneck=difficulty margin=-0.005
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.114652 bottleneck=late_stop margin=-0.114652
  - [FAIL] `R5_rank7` → rank7_world margin=-0.163211 bottleneck=chaos margin=-0.163211
  - [FAIL] `R6_bug` → bug_world margin=-0.245 bottleneck=difficulty margin=-0.245
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.125 bottleneck=difficulty margin=-0.125
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.9924, 'midupper_world': 0.9868, 'midhole_world': 0.7953, 'rank7_world': 0.7186, 'bug_world': 0.6048, 'core_world': 0.0076}`

### `2026-07-26-02-01`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.295`
  - chaos: `0.195324`
  - phase: `None`
  - late_stop: `0.11790000000000002`
  - sustained: `0.07809`
  - high_pace: `0.123`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.4421 bottleneck=late_stop margin=-0.4421
  - [FAIL] `R5_rank7` → rank7_world margin=-0.384676 bottleneck=chaos margin=-0.384676
  - [FAIL] `R6_bug` → bug_world margin=-0.464676 bottleneck=chaos margin=-0.464676
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.205 bottleneck=difficulty margin=-0.205
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.59, 'midhole_world': 0.1502, 'rank7_world': 0.2563, 'bug_world': 0.2959, 'core_world': 0.41}`

### `2026-07-26-02-02`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.324`
  - chaos: `0.18721199999999996`
  - phase: `None`
  - late_stop: `0.10289999999999999`
  - sustained: `0.08133`
  - high_pace: `0.09899999999999999`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.4571 bottleneck=late_stop margin=-0.4571
  - [FAIL] `R5_rank7` → rank7_world margin=-0.392788 bottleneck=chaos margin=-0.392788
  - [FAIL] `R6_bug` → bug_world margin=-0.472788 bottleneck=chaos margin=-0.472788
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.176 bottleneck=difficulty margin=-0.176
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.648, 'midhole_world': 0.1564, 'rank7_world': 0.2062, 'bug_world': 0.2837, 'core_world': 0.352}`

### `2026-07-26-02-03`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.275`
  - chaos: `0.31260831999999994`
  - phase: `None`
  - late_stop: `0.32309600000000005`
  - sustained: `0.44564896000000004`
  - high_pace: `0.39224000000000003`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.236904 bottleneck=late_stop margin=-0.236904
  - [FAIL] `R5_rank7` → rank7_world margin=-0.267392 bottleneck=chaos margin=-0.267392
  - [FAIL] `R6_bug` → bug_world margin=-0.347392 bottleneck=chaos margin=-0.347392
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.225 bottleneck=difficulty margin=-0.225
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.55, 'midhole_world': 0.577, 'rank7_world': 0.539, 'bug_world': 0.4435, 'core_world': 0.423}`

### `2026-07-26-02-04`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.368333`
  - chaos: `0.4350411200000001`
  - phase: `None`
  - late_stop: `0.47650266666666674`
  - sustained: `0.3971401466666667`
  - high_pace: `0.5668400000000001`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.12286 bottleneck=sustained margin=-0.12286
  - [FAIL] `R5_rank7` → rank7_world margin=-0.144959 bottleneck=chaos margin=-0.144959
  - [FAIL] `R6_bug` → bug_world margin=-0.251667 bottleneck=difficulty margin=-0.251667
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.131667 bottleneck=difficulty margin=-0.131667
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.7367, 'midhole_world': 0.7637, 'rank7_world': 0.7501, 'bug_world': 0.5941, 'core_world': 0.2363}`

### `2026-07-26-02-05`

- **Decision**: `mixed_world` via `R1_mixed_short_field`
- **Best-fit (soft)**: `mixed_world` (agree=True)
- **Root cause**: `Boundary`
- **Signals**:
  - difficulty: `0.37875`
  - chaos: `0.4425237`
  - phase: `None`
  - late_stop: `0.4912975`
  - sustained: `0.3859663125`
  - high_pace: `0.589025`
  - short_field_pressure: `0.9193274350000001`
- **Trigger chain**:
  - [PASS] `R1_mixed_short_field` → mixed_world margin=0.022524
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.00125 bottleneck=difficulty margin=-0.00125
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.134034 bottleneck=sustained margin=-0.134034
  - [FAIL] `R5_rank7` → rank7_world margin=-0.137476 bottleneck=chaos margin=-0.137476
  - [FAIL] `R6_bug` → bug_world margin=-0.24125 bottleneck=difficulty margin=-0.24125
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.12125 bottleneck=difficulty margin=-0.12125
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 1.0, 'midupper_world': 0.9967, 'midhole_world': 0.7422, 'rank7_world': 0.763, 'bug_world': 0.6109, 'core_world': 0.0}`

### `2026-07-26-03-01`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.334333`
  - chaos: `0.3519002666666667`
  - phase: `None`
  - late_stop: `0.38741333333333333`
  - sustained: `0.21126375833333333`
  - high_pace: `0.46520000000000006`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.308736 bottleneck=sustained margin=-0.308736
  - [FAIL] `R5_rank7` → rank7_world margin=-0.2281 bottleneck=chaos margin=-0.2281
  - [FAIL] `R6_bug` → bug_world margin=-0.3081 bottleneck=chaos margin=-0.3081
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.165667 bottleneck=difficulty margin=-0.165667
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.6687, 'midhole_world': 0.4063, 'rank7_world': 0.6067, 'bug_world': 0.5332, 'core_world': 0.3313}`

### `2026-07-26-03-02`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midhole_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.255`
  - chaos: `0.36634938666666667`
  - phase: `None`
  - late_stop: `0.41598266666666667`
  - sustained: `0.4689765549999999`
  - high_pace: `0.50804`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.144017 bottleneck=late_stop margin=-0.144017
  - [FAIL] `R5_rank7` → rank7_world margin=-0.213651 bottleneck=chaos margin=-0.213651
  - [FAIL] `R6_bug` → bug_world margin=-0.365 bottleneck=difficulty margin=-0.365
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.245 bottleneck=difficulty margin=-0.245
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.51, 'midhole_world': 0.7428, 'rank7_world': 0.6316, 'bug_world': 0.4113, 'core_world': 0.2572}`

### `2026-07-26-03-03`

- **Decision**: `mixed_world` via `R1_mixed_short_field`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Evaluation Order`
- **Signals**:
  - difficulty: `0.385`
  - chaos: `0.44639399999999996`
  - phase: `None`
  - late_stop: `0.49895`
  - sustained: `0.45674145`
  - high_pace: `0.6005`
  - short_field_pressure: `0.9223447`
- **Trigger chain**:
  - [PASS] `R1_mixed_short_field` → mixed_world margin=0.026394
  - [PASS] `R2_midupper_sf_diff` → midupper_world margin=0.005
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.063259 bottleneck=sustained margin=-0.063259
  - [FAIL] `R5_rank7` → rank7_world margin=-0.133606 bottleneck=chaos margin=-0.133606
  - [FAIL] `R6_bug` → bug_world margin=-0.235 bottleneck=difficulty margin=-0.235
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.115 bottleneck=difficulty margin=-0.115
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 1.0, 'midupper_world': 1.0, 'midhole_world': 0.8783, 'rank7_world': 0.7696, 'bug_world': 0.621, 'core_world': 0.0}`

### `2026-07-26-03-04`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.298636`
  - chaos: `0.3129497454545454`
  - phase: `None`
  - late_stop: `0.3230781818181817`
  - sustained: `0.41716221363636363`
  - high_pace: `0.39321818181818186`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.236922 bottleneck=late_stop margin=-0.236922
  - [FAIL] `R5_rank7` → rank7_world margin=-0.26705 bottleneck=chaos margin=-0.26705
  - [FAIL] `R6_bug` → bug_world margin=-0.34705 bottleneck=chaos margin=-0.34705
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.201364 bottleneck=difficulty margin=-0.201364
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.5973, 'midhole_world': 0.5769, 'rank7_world': 0.5396, 'bug_world': 0.4742, 'core_world': 0.4027}`

### `2026-07-26-03-05`

- **Decision**: `core_world` via `R8_core_default`
- **Best-fit (soft)**: `midupper_world` (agree=False)
- **Root cause**: `Trigger不足`
- **Signals**:
  - difficulty: `0.375`
  - chaos: `0.19802799999999995`
  - phase: `None`
  - late_stop: `0.12290000000000001`
  - sustained: `0.07701`
  - high_pace: `0.131`
  - short_field_pressure: `0.0`
- **Trigger chain**:
  - [FAIL] `R1_mixed_short_field` → mixed_world margin=-0.72 bottleneck=short_field_pressure margin=-0.72
  - [FAIL] `R2_midupper_sf_diff` → midupper_world margin=-0.58 bottleneck=short_field_pressure margin=-0.58
  - [FAIL] `R3_mixed_phase` → mixed_world margin=None bottleneck=phase margin=None
  - [FAIL] `R4_midhole` → midhole_world margin=-0.44299 bottleneck=sustained margin=-0.44299
  - [FAIL] `R5_rank7` → rank7_world margin=-0.381972 bottleneck=chaos margin=-0.381972
  - [FAIL] `R6_bug` → bug_world margin=-0.461972 bottleneck=chaos margin=-0.461972
  - [FAIL] `R7_midupper_diff` → midupper_world margin=-0.125 bottleneck=difficulty margin=-0.125
  - [PASS] `R8_core_default` → core_world margin=0.0 [DEFAULT]
- **Fitness**: `{'mixed_world': 0.0, 'midupper_world': 0.75, 'midhole_world': 0.1481, 'rank7_world': 0.2729, 'bug_world': 0.3, 'core_world': 0.25}`

