# Version29 — World Trigger Signal Contract (Audit)

**Date:** 2026-07-27T13:34:28+00:00  
**Function:** `demo_ticket_optimizer_core.classify_world_line_type`  

## Final signals read by World Trigger

| Signal | How obtained |
|--------|--------------|
| `short_field_pressure` | calc_short_field_pressure(meta, candidate) |
| `phase_transition` | calc_world_line_score(meta)['phase_transition'] |
| `late_stop` | calc_world_line_score(meta)['late_stop'] |
| `sustained` | calc_world_line_score(meta)['sustained'] |
| `high_pace` | calc_world_line_score(meta)['high_pace'] |
| `race_leg_difficulty` | meta['race_leg_difficulty'] via nz(...,0.0) |
| `chaos_score` | meta['chaos_score'] via nz(...,0.0) |

## Live values on probe race

- race: `2026-07-26-03-05`
- difficulty (race_leg_difficulty): `0.5`
- chaos_score: `None`
- CE world output: `midupper_world`

## Not directly read by Trigger

- `leg_base_chaos`
- `leg_field_pressure` / generic `field_pressure`
- `style_entropy`
- `upset_share`
- `world_line_score` (components are read via `calc_world_line_score` outputs)
- Research-only alias key `difficulty` (Trigger uses `race_leg_difficulty`)

## Bundle contract note

- Current mapper sets `evaluation.world=None` (code), while DB may show `midupper_world` from other persistence paths
- Numeric difficulty is **not** in Prediction Bundle (contains string? `False`)

## Guardrails

- Contract documented only; Trigger unchanged
