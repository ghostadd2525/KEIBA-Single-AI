# Version24 — World Condition Coverage

**Date:** 2026-07-27T11:41:58+00:00  

- Corpus races: `335`
- Distance ≤1600: `163` (48.7%)
- Field ≥14: `225` (67.2%)

## Proxy short_field_pressure (distance×field only)

- Known: `334`
- ≥0.58: `83` (24.9%)
- ≥0.72: `64` (19.2%)

## World-line signal coverage in corpus bundles

| Signal | N | Rate |
|--------|--:|-----:|
| `chaos_score` | 0 | 0.0% |
| `race_leg_difficulty` | 0 | 0.0% |
| `late_stop_risk_score` | 0 | 0.0% |
| `sustained_run_possible_score` | 0 | 0.0% |
| `high_pace_score` | 0 | 0.0% |
| `pace_collapse_risk` | 0 | 0.0% |
| `world_load_score` | 0 | 0.0% |
| `traffic_score` | 0 | 0.0% |
| `phase_transition` | 0 | 0.0% |
| `short_field_pressure` | 0 | 0.0% |

_chaos / difficulty / late_stop / sustained / phase are usually ABSENT from research PredictionBundles — activation cannot be re-simulated without those meta signals._

## Labeled-bundle signal hits

`{}`

## Coverage interpretation

- Partial short-field proxy can exist from race distance/field_size
- Full World activation still requires chaos / difficulty / late_stop / sustained / high_pace / phase — currently near-zero coverage in research store
- This explains why non-midupper Worlds show 0 labeled activations
