# Version41 Root Cause Classification

## Counts (all races)

- **Signal不足**: 0
- **Trigger不足**: 39
- **Boundary**: 9
- **Evaluation Order**: 6
- **Default/Fallback**: 0
- **その他**: 2

## Counts (decision = core_world only) — core偏重の件数証明

- **Signal不足**: 0
- **Trigger不足**: 39
- **Boundary**: 3
- **Evaluation Order**: 0
- **Default/Fallback**: 0
- **その他**: 0

## Core bias evidence

- n_core: **42**
- via R8_core_default: **42**
- R1–R7 all FAIL: **42**
- fitness mismatch among core: **42**
- secondary tags: `{'Default/Fallback': 42, 'Evaluation Order': 42, 'Signal不足': 40}`

## Per-race

| race_id | decision | best_fit | primary | secondary | evidence |
|---|---|---|---|---|---|
| `2026-06-28-函館-11` | `midupper_world` | `midupper_world` | その他 | — | Trigger PASS => midupper_world (rule=R7_midupper_diff) |
| `2026-06-28-小倉-10` | `midupper_world` | `midupper_world` | Boundary | — | winning=R7_midupper_diff / near-miss competition |
| `2026-06-28-小倉-11` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-06-28-福島-10` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-06-28-福島-11` | `midhole_world` | `midhole_world` | Boundary | — | winning=R4_midhole / near-miss competition |
| `2026-07-25-01-01` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-25-01-02` | `midupper_world` | `midupper_world` | その他 | Signal不足 | Trigger PASS => midupper_world (rule=R2_midupper_sf_diff) |
| `2026-07-25-01-03` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-25-01-04` | `mixed_world` | `midupper_world` | Evaluation Order | — | first-match decision=mixed_world (rule=R1_mixed_short_field) != soft-fitness best=midupper |
| `2026-07-25-01-05` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-01-06` | `core_world` | `midhole_world` | Boundary | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-01-07` | `mixed_world` | `midupper_world` | Evaluation Order | — | first-match decision=mixed_world (rule=R1_mixed_short_field) != soft-fitness best=midupper |
| `2026-07-25-01-08` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-01-09` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-01-10` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-25-01-11` | `mixed_world` | `midupper_world` | Evaluation Order | — | first-match decision=mixed_world (rule=R1_mixed_short_field) != soft-fitness best=midupper |
| `2026-07-25-01-12` | `mixed_world` | `midupper_world` | Evaluation Order | Boundary | first-match decision=mixed_world (rule=R1_mixed_short_field) != soft-fitness best=midupper |
| `2026-07-25-02-01` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-25-02-02` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-25-02-03` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-02-04` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-02-05` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-25-02-06` | `mixed_world` | `mixed_world` | Boundary | — | winning=R1_mixed_short_field / near-miss competition |
| `2026-07-25-02-07` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-25-02-08` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-02-09` | `mixed_world` | `mixed_world` | Boundary | — | winning=R1_mixed_short_field / near-miss competition |
| `2026-07-25-02-10` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-02-11` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-02-12` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-25-03-01` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-03-02` | `core_world` | `rank7_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=rank7_world != decision=cor |
| `2026-07-25-03-03` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-03-04` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-03-05` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-25-03-06` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-03-07` | `mixed_world` | `midhole_world` | Evaluation Order | Boundary | first-match decision=mixed_world (rule=R1_mixed_short_field) != soft-fitness best=midhole_ |
| `2026-07-25-03-08` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-03-09` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-03-10` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-03-11` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-25-03-12` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-26-01-01` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-26-01-02` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-26-01-03` | `mixed_world` | `mixed_world` | Boundary | — | winning=R1_mixed_short_field / near-miss competition |
| `2026-07-26-01-04` | `core_world` | `midupper_world` | Boundary | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-26-01-05` | `core_world` | `mixed_world` | Boundary | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=mixed_world != decision=cor |
| `2026-07-26-02-01` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-26-02-02` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-26-02-03` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-26-02-04` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-26-02-05` | `mixed_world` | `mixed_world` | Boundary | — | winning=R1_mixed_short_field / near-miss competition |
| `2026-07-26-03-01` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-26-03-02` | `core_world` | `midhole_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midhole_world != decision=c |
| `2026-07-26-03-03` | `mixed_world` | `midupper_world` | Evaluation Order | — | first-match decision=mixed_world (rule=R1_mixed_short_field) != soft-fitness best=midupper |
| `2026-07-26-03-04` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |
| `2026-07-26-03-05` | `core_world` | `midupper_world` | Trigger不足 | Default/Fallback,Evaluation Order,Signal不足 | R1-R7 all FAIL -> R8_core_default => core_world; soft best-fit=midupper_world != decision= |

