# Version25 — World Signal Inventory

**Date:** 2026-07-27T12:03:48+00:00  
**Scope:** Persist only / No World Trigger change / No Prediction change  

## Guardrails

- product_mutation: `False`
- world_trigger_changed: `False`
- judgment_changed: `False`

## Signal Inventory

| Signal | Non-null | Coverage | NULL rate |
|--------|---------:|---------:|----------:|
| `world` | 55 | 96.5% | 3.5% |
| `sub_world` | 55 | 96.5% | 3.5% |
| `chaos` | 0 | 0.0% | 100.0% |
| `chaos_score` | 0 | 0.0% | 100.0% |
| `difficulty` | 50 | 87.7% | 12.3% |
| `race_leg_difficulty` | 50 | 87.7% | 12.3% |
| `phase` | 50 | 87.7% | 12.3% |
| `phase_transition` | 50 | 87.7% | 12.3% |
| `late_stop` | 50 | 87.7% | 12.3% |
| `late_stop_risk_score` | 50 | 87.7% | 12.3% |
| `sustained` | 50 | 87.7% | 12.3% |
| `sustained_run_possible_score` | 50 | 87.7% | 12.3% |
| `high_pace` | 50 | 87.7% | 12.3% |
| `high_pace_score` | 50 | 87.7% | 12.3% |
| `pace_collapse_risk` | 50 | 87.7% | 12.3% |
| `world_line` | 50 | 87.7% | 12.3% |
| `world_line_score` | 50 | 87.7% | 12.3% |
| `world_score` | 50 | 87.7% | 12.3% |
| `world_reason` | 0 | 0.0% | 100.0% |
| `short_field_pressure` | 50 | 87.7% | 12.3% |
| `traffic_score` | 50 | 87.7% | 12.3% |
| `world_load_score` | 50 | 87.7% | 12.3% |

## Run summary

- Snapshots seen: `57`
- Snapshots updated: `57`
- Instrumented (coverage scan): `57` / `57`
- Mean persistence rate: `76.6%`
- Mean NULL rate: `23.4%`

## Notes

- Signals are copied into `payload.research_world_signals` on Research Snapshots
- Prediction Bundle product JSON is not rewritten
- Core meta numerics may be copied read-only at harvest; classify outcome is not used to change product
