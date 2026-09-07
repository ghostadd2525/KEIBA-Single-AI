# Version27 — Trigger Saturation

**Date:** 2026-07-27T12:50:55+00:00  

## Observed assignment

- N: `51`

| World | Assigned N | Observed share |
|-------|-----------:|---------------:|
| `core_world` | 0 | 0.0% |
| `midupper_world` | 51 | 100.0% |
| `midhole_world` | 0 | 0.0% |
| `rank7_world` | 0 | 0.0% |
| `bug_world` | 0 | 0.0% |
| `mixed_world` | 0 | 0.0% |

## First-match simulation (same priority order, frozen thresholds)

| World | Simulated share |
|-------|----------------:|
| `core_world` | 2.0% |
| `midupper_world` | 98.0% |
| `midhole_world` | 0.0% |
| `rank7_world` | 0.0% |
| `bug_world` | 0.0% |
| `mixed_world` | 0.0% |

## Why midupper saturates (observational)

Priority order (unchanged):

1. mixed (short_field≥0.72 ∧ …)
2. **midupper** (short_field≥0.58 ∧ difficulty≥0.38)
3. mixed (phase≥0.62)
4. midhole
5. rank7
6. bug
7. midupper (difficulty≥0.50)
8. core default

Saturation reading uses rule pass rates + bottleneck ranks below — no threshold changes.

## Rule pass / fail

| Rule | World | Pass | Fail | Pass rate | Mean margin | Top dropout |
|------|-------|-----:|-----:|----------:|------------:|-------------|
| `R1_mixed_short_field` | `mixed_world` | 0 | 51 | 0.0% | -0.72 | `short_field_pressure` |
| `R2_midupper_sf_diff` | `midupper_world` | 0 | 51 | 0.0% | -0.58 | `short_field_pressure` |
| `R3_mixed_phase` | `mixed_world` | 0 | 51 | 0.0% | -0.62 | `phase` |
| `R4_midhole` | `midhole_world` | 0 | 51 | 0.0% | -0.56 | `late_stop` |
| `R5_rank7` | `rank7_world` | 0 | 51 | 0.0% | None | `chaos(MISSING)` |
| `R6_bug` | `bug_world` | 0 | 51 | 0.0% | None | `chaos(MISSING)` |
| `R7_midupper_diff` | `midupper_world` | 50 | 1 | 98.0% | 0.0 | `difficulty(MISSING)` |

## Guardrails

- Trigger / thresholds / Worlds not modified
- Improvement proposals forbidden in V27
