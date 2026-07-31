# Version41 Fitness Mismatch

- fitness_agree_rate: **14.3%** （V40 agree best-fit = 14.3% と同一系）
- mismatch_n: **48** / 56

## Pair counts (best-fit → decision)

- `midhole_world->core_world`: 22
- `midupper_world->core_world`: 18
- `midupper_world->mixed_world`: 5
- `rank7_world->core_world`: 1
- `midhole_world->mixed_world`: 1
- `mixed_world->core_world`: 1

## Reason buckets

- `DEFAULT_core_vs_bestfit_trigger_fail`: 42
- `first_match_priority_over_bestfit`: 6

## Per-race mismatch

| race_id | best_fit | decision | fitness_gap | reason |
|---|---|---|---|---|
| `2026-06-28-小倉-11` | `midupper_world` | `core_world` | 0.7174 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-06-28-福島-10` | `midhole_world` | `core_world` | 0.7996 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.503910909090909, ... |
| `2026-07-25-01-01` | `midupper_world` | `core_world` | 0.164 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-25-01-03` | `midupper_world` | `core_world` | 0.1 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-25-01-04` | `midupper_world` | `mixed_world` | 0.0 | first-match=mixed_world(R1_mixed_short_field) が best-fit=midupper_world より高優先で確定 |
| `2026-07-25-01-05` | `midhole_world` | `core_world` | 0.2822 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.3590415287616666,... |
| `2026-07-25-01-06` | `midhole_world` | `core_world` | 0.8802 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.5264766714836001,... |
| `2026-07-25-01-07` | `midupper_world` | `mixed_world` | 0.0 | first-match=mixed_world(R1_mixed_short_field) が best-fit=midupper_world より高優先で確定 |
| `2026-07-25-01-08` | `midhole_world` | `core_world` | 0.4298 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.4003569485911538,... |
| `2026-07-25-01-09` | `midhole_world` | `core_world` | 0.6382 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.45867859806239997... |
| `2026-07-25-01-10` | `midupper_world` | `core_world` | 0.6334 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-25-01-11` | `midupper_world` | `mixed_world` | 0.0 | first-match=mixed_world(R1_mixed_short_field) が best-fit=midupper_world より高優先で確定 |
| `2026-07-25-01-12` | `midupper_world` | `mixed_world` | 0.0 | first-match=mixed_world(R1_mixed_short_field) が best-fit=midupper_world より高優先で確定 |
| `2026-07-25-02-01` | `midupper_world` | `core_world` | 0.18 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-25-02-02` | `midupper_world` | `core_world` | 0.696 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-25-02-03` | `midhole_world` | `core_world` | 0.4756 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.41317427825291664... |
| `2026-07-25-02-04` | `midhole_world` | `core_world` | 0.6586 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: sustained不足 (val=0.43123974179999996... |
| `2026-07-25-02-05` | `midupper_world` | `core_world` | 0.69 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-25-02-07` | `midupper_world` | `core_world` | 0.231 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-25-02-08` | `midhole_world` | `core_world` | 0.5784 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.44192804509114586... |
| `2026-07-25-02-10` | `midhole_world` | `core_world` | 0.3008 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.36419954212875, t... |
| `2026-07-25-02-11` | `midhole_world` | `core_world` | 0.5836 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.44343404746161463... |
| `2026-07-25-02-12` | `midupper_world` | `core_world` | 0.665 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-25-03-01` | `midhole_world` | `core_world` | 0.4312 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.40074290718750005... |
| `2026-07-25-03-02` | `rank7_world` | `core_world` | 0.2488 | DEFAULT→core / best-fit rank7_world Trigger未達: R5_rank7: chaos不足 (val=0.36213778209409164, thr=0.... |
| `2026-07-25-03-03` | `midhole_world` | `core_world` | 0.4944 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.4184451576899667,... |
| `2026-07-25-03-04` | `midhole_world` | `core_world` | 0.6306 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: sustained不足 (val=0.42393084757142857... |
| `2026-07-25-03-05` | `midupper_world` | `core_world` | 0.1 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-25-03-06` | `midhole_world` | `core_world` | 0.6464 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.46101891154761915... |
| `2026-07-25-03-07` | `midhole_world` | `mixed_world` | 0.0 | first-match=mixed_world(R1_mixed_short_field) が best-fit=midhole_world より高優先で確定 |
| `2026-07-25-03-08` | `midhole_world` | `core_world` | 0.4756 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.41317427825291664... |
| `2026-07-25-03-09` | `midhole_world` | `core_world` | 0.682 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.4709786337421, th... |
| `2026-07-25-03-10` | `midhole_world` | `core_world` | 0.5292 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.4281866512731819,... |
| `2026-07-25-03-11` | `midhole_world` | `core_world` | 0.5558 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.435619920095, thr... |
| `2026-07-25-03-12` | `midhole_world` | `core_world` | 0.289 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.3609429572766666,... |
| `2026-07-26-01-01` | `midupper_world` | `core_world` | 0.2476 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-26-01-02` | `midupper_world` | `core_world` | 0.32 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-26-01-04` | `midupper_world` | `core_world` | 0.8334 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-26-01-05` | `mixed_world` | `core_world` | 0.9848 | DEFAULT→core / best-fit mixed_world Trigger未達: R1_mixed_short_field: phase missing |
| `2026-07-26-02-01` | `midupper_world` | `core_world` | 0.18 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-26-02-02` | `midupper_world` | `core_world` | 0.296 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-26-02-03` | `midhole_world` | `core_world` | 0.154 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.32309600000000005... |
| `2026-07-26-02-04` | `midhole_world` | `core_world` | 0.5274 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: sustained不足 (val=0.3971401466666667,... |
| `2026-07-26-03-01` | `midupper_world` | `core_world` | 0.3374 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-26-03-02` | `midhole_world` | `core_world` | 0.4856 | DEFAULT→core / best-fit midhole_world Trigger未達: R4_midhole: late_stop不足 (val=0.41598266666666667... |
| `2026-07-26-03-03` | `midupper_world` | `mixed_world` | 0.0 | first-match=mixed_world(R1_mixed_short_field) が best-fit=midupper_world より高優先で確定 |
| `2026-07-26-03-04` | `midupper_world` | `core_world` | 0.1946 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |
| `2026-07-26-03-05` | `midupper_world` | `core_world` | 0.5 | DEFAULT→core / best-fit midupper_world Trigger未達: R2_midupper_sf_diff: short_field_pressure不足 (va... |

