# Version27 — Trigger Margin Analysis

**Date:** 2026-07-27T12:50:55+00:00  
**Scope:** Research only / Trigger unchanged / No improvements  

## Definition

`margin = signal_value - threshold`

- `margin >= 0` → condition passes
- `margin < 0` → dropped by |margin|
- `margin = NULL` → signal missing (dropout)

- Near-activation epsilon: `0.05`
- Sample N: `51`

## Rule-level margin summary

| Rule | World | Pass rate | Mean margin | Median | P95 | Top dropout |
|------|-------|----------:|------------:|-------:|----:|-------------|
| `R1_mixed_short_field` | `mixed_world` | 0.0% | -0.72 | -0.72 | -0.72 | `short_field_pressure` |
| `R2_midupper_sf_diff` | `midupper_world` | 0.0% | -0.58 | -0.58 | -0.58 | `short_field_pressure` |
| `R3_mixed_phase` | `mixed_world` | 0.0% | -0.62 | -0.62 | -0.62 | `phase` |
| `R4_midhole` | `midhole_world` | 0.0% | -0.56 | -0.56 | -0.56 | `late_stop` |
| `R5_rank7` | `rank7_world` | 0.0% | None | None | None | `chaos(MISSING)` |
| `R6_bug` | `bug_world` | 0.0% | None | None | None | `chaos(MISSING)` |
| `R7_midupper_diff` | `midupper_world` | 98.0% | 0.0 | 0.0 | 0.0 | `difficulty(MISSING)` |

## Atom-level margins (rule.signal)

| Atom | N | Mean | Median | P05 | P95 | ≈Pass rate |
|------|--:|-----:|-------:|----:|----:|-----------:|
| `R1_mixed_short_field.difficulty` | 50 | 0.08 | 0.08 | 0.08 | 0.08 | 100.0% |
| `R1_mixed_short_field.phase` | 50 | -0.48 | -0.48 | -0.48 | -0.48 | 0.0% |
| `R1_mixed_short_field.short_field_pressure` | 50 | -0.72 | -0.72 | -0.72 | -0.72 | 0.0% |
| `R2_midupper_sf_diff.difficulty` | 50 | 0.12 | 0.12 | 0.12 | 0.12 | 100.0% |
| `R2_midupper_sf_diff.short_field_pressure` | 50 | -0.58 | -0.58 | -0.58 | -0.58 | 0.0% |
| `R3_mixed_phase.phase` | 50 | -0.62 | -0.62 | -0.62 | -0.62 | 0.0% |
| `R4_midhole.late_stop` | 50 | -0.56 | -0.56 | -0.56 | -0.56 | 0.0% |
| `R4_midhole.sustained` | 50 | -0.52 | -0.52 | -0.52 | -0.52 | 0.0% |
| `R5_rank7.high_pace` | 50 | -0.48 | -0.48 | -0.48 | -0.48 | 0.0% |
| `R6_bug.difficulty` | 50 | -0.12 | -0.12 | -0.12 | -0.12 | 0.0% |
| `R7_midupper_diff.difficulty` | 50 | 0.0 | 0.0 | 0.0 | 0.0 | 100.0% |

## Example interpretation

If `R5_rank7.chaos` mean margin is largely negative or NULL, rank7 drops on chaos before high_pace is decisive.

## Guardrails

- product_mutation: `False`
- world_trigger_changed: `False`
- improvement_forbidden: `True`
