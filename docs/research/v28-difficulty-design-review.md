# Version28 — Difficulty Design Consistency Review

**Date:** 2026-07-27T13:20:11+00:00  
**Design claim:** difficulty should disperse Worlds (informative World-line signal)  

## Evaluation flags (observational)

- Sufficient discriminability: `False`
- Sufficient information: `False`
- Saturated at 0.50: `True`
- Collapsed to constant: `True`
- Dominated by stable default 0.5: `True`

### Observed facts

- unique_n=1
- std=0.0
- pass_rate(>=0.50)=1.0
- share_exactly_0.5=1.0

## Sensitivity (designed formula, held-other-constant sweeps)

| Factor | Difficulty delta span |
|--------|----------------------:|
| horse_count / field pressure | 0.2 |
| pace_collapse_risk | 0.2 |
| style_entropy | 0.15 |
| upset_share (weight 0.10) | 0.1 |
| win5_leg / leg_base_chaos | 0.063 |

- distance in designed formula: `False`
- field note: horse_count drives leg_field_pressure; distance not a direct input

### horse_count sweep (excerpt)

| horse_count | field_pressure | difficulty |
|------------:|---------------:|-----------:|
| 8 | 0.0 | 0.175 |
| 10 | 0.2 | 0.215 |
| 12 | 0.4 | 0.255 |
| 14 | 0.6 | 0.295 |
| 16 | 0.8 | 0.335 |
| 18 | 1.0 | 0.375 |

## Consistency statement (no improvements)

Under the design claim that difficulty should disperse Worlds, the measured research signal is evaluated only by the flags above. This document does **not** propose Trigger, threshold, World, or AI changes.

- improvement_forbidden: `True`
- world_trigger_changed: `False`
