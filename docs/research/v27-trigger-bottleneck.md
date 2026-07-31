# Version27 — Trigger Bottleneck

**Date:** 2026-07-27T12:50:55+00:00  
**Question:** Which condition most often stops each World from firing?  

## By World

### `core_world`

_No failed-rule bottleneck counted (rule rarely evaluated as fail, or world only default)._

### `midupper_world`

| Rank | Condition | N | Share among dropouts |
|-----:|-----------|--:|---------------------:|
| 1 | `short_field_pressure` | 50 | 96.2% |
| 2 | `short_field_pressure(MISSING)` | 1 | 1.9% |
| 3 | `difficulty(MISSING)` | 1 | 1.9% |

### `midhole_world`

| Rank | Condition | N | Share among dropouts |
|-----:|-----------|--:|---------------------:|
| 1 | `late_stop` | 50 | 98.0% |
| 2 | `late_stop(MISSING)` | 1 | 2.0% |

### `rank7_world`

| Rank | Condition | N | Share among dropouts |
|-----:|-----------|--:|---------------------:|
| 1 | `chaos(MISSING)` | 51 | 100.0% |

### `bug_world`

| Rank | Condition | N | Share among dropouts |
|-----:|-----------|--:|---------------------:|
| 1 | `chaos(MISSING)` | 51 | 100.0% |

### `mixed_world`

| Rank | Condition | N | Share among dropouts |
|-----:|-----------|--:|---------------------:|
| 1 | `short_field_pressure` | 50 | 49.0% |
| 2 | `phase` | 50 | 49.0% |
| 3 | `short_field_pressure(MISSING)` | 1 | 1.0% |
| 4 | `phase(MISSING)` | 1 | 1.0% |

## By Rule

| Rule | World | #1 bottleneck | #2 | #3 |
|------|-------|---------------|----|----|
| `R1_mixed_short_field` | `mixed_world` | `short_field_pressure` | `short_field_pressure(MISSING)` | `-` |
| `R2_midupper_sf_diff` | `midupper_world` | `short_field_pressure` | `short_field_pressure(MISSING)` | `-` |
| `R3_mixed_phase` | `mixed_world` | `phase` | `phase(MISSING)` | `-` |
| `R4_midhole` | `midhole_world` | `late_stop` | `late_stop(MISSING)` | `-` |
| `R5_rank7` | `rank7_world` | `chaos(MISSING)` | `-` | `-` |
| `R6_bug` | `bug_world` | `chaos(MISSING)` | `-` | `-` |
| `R7_midupper_diff` | `midupper_world` | `difficulty(MISSING)` | `-` | `-` |

## Near Activation counts

| World | Near-N |
|-------|-------:|
| `core_world` | 0 |
| `midupper_world` | 0 |
| `midhole_world` | 0 |
| `rank7_world` | 0 |
| `bug_world` | 0 |
| `mixed_world` | 0 |

### Near Activation examples

