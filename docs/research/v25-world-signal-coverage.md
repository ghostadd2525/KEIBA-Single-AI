# Version25 — World Signal Coverage / NULL / Persistence

**Date:** 2026-07-27T12:03:48+00:00  

## Coverage

- Instrumentation coverage (snapshots with block): `100.0%` (57/57)
- Snapshots updated this run: `57`

## Persistence rate

- Mean persistence rate (non-null / inventory size): `76.6%`

## NULL rate

- Mean NULL rate: `23.4%`

| Signal | NULL rate |
|--------|----------:|
| `world` | 3.5% |
| `sub_world` | 3.5% |
| `chaos` | 100.0% |
| `chaos_score` | 100.0% |
| `difficulty` | 12.3% |
| `race_leg_difficulty` | 12.3% |
| `phase` | 12.3% |
| `phase_transition` | 12.3% |
| `late_stop` | 12.3% |
| `late_stop_risk_score` | 12.3% |
| `sustained` | 12.3% |
| `sustained_run_possible_score` | 12.3% |
| `high_pace` | 12.3% |
| `high_pace_score` | 12.3% |
| `pace_collapse_risk` | 12.3% |
| `world_line` | 12.3% |
| `world_line_score` | 12.3% |
| `world_score` | 12.3% |
| `world_reason` | 100.0% |
| `short_field_pressure` | 12.3% |
| `traffic_score` | 12.3% |
| `world_load_score` | 12.3% |

## Interpretation

- High NULL on chaos/difficulty/phase means Core meta copy was unavailable or Prediction Bundle never carried those fields
- world/sub_world may persist from Bundle labels even when numerics are NULL
- This run does not change World Trigger or Prediction logic
