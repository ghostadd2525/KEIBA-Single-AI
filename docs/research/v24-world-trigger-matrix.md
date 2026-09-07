# Version24 — World Trigger Matrix

**Date:** 2026-07-27T11:41:58+00:00  

Source: `classify_world_line_type` (read-only research extract).
First matching rule wins.

| Pri | World | Trigger | Required | Route | Role | Gap | Spread |
|----:|-------|---------|----------|-------|------|-----|--------|
| 1 | `mixed_world` | `short_field_pressure >= 0.72 AND (phase_transition >= 0.48 OR chaos_score >= 0.42 OR race_leg_difficulty >= 0.42)` | ['short_field_pressure', 'phase|chaos|difficulty'] | route-forward / multi-survivor | Multiple world-lines coexist; high short-field + phase/chaos/difficulty | top gaps unstable; rescue diversity needed | high — avoid single-family collapse |
| 2 | `midupper_world` | `short_field_pressure >= 0.58 AND race_leg_difficulty >= 0.38` | ['short_field_pressure', 'race_leg_difficulty'] | midupper_route vs midupper_spread | Short-field × difficulty mid-upper survival world | moderate; rank deeper than core | route vs spread split |
| 3 | `mixed_world` | `phase_transition >= 0.62` | ['phase_transition'] | phase-chain / transition | Late phase transition dominates | phase-driven, not ability-lock | high |
| 4 | `midhole_world` | `late_stop >= 0.56 AND sustained >= 0.52` | ['late_stop', 'sustained'] | sustained / outside survivor | Late-stop × sustained mid-hole survival | mid-pack hole between core and deep | sustained-family preference |
| 5 | `rank7_world` | `chaos_score >= 0.58 AND high_pace >= 0.48` | ['chaos_score', 'high_pace'] | rank7_transition / rank7_residual | Chaos × high-pace rank7–10 observation world | compressed top → hidden rank7-10 | transition vs residual |
| 6 | `bug_world` | `chaos_score >= 0.66 AND race_leg_difficulty >= 0.62` | ['chaos_score', 'race_leg_difficulty'] | deep residual / bug observation | Extreme chaos × difficulty bug residual | deep ranks (often 12+) | observation not primary purchase |
| 7 | `midupper_world` | `race_leg_difficulty >= 0.50` | ['race_leg_difficulty'] | difficulty-driven midupper | Elevated race difficulty without needing short-field | ability less decisive | mid |
| 8 | `core_world` | `DEFAULT (no prior trigger matched)` | [] | core_top / core_under (ability lock) | Default ability-settlement world | small top gaps; model_rank settles | low |

## World Trigger summary

### `core_world`
- Activation: Fires when no higher-priority survival world trigger matches
- Role: Ability-settlement default
- Route: core_top / core_under; may promote to midupper_route under compression
- Gap: tight top probability gaps
- Spread: low

### `midupper_world`
- Activation: short_field_pressure≥0.58 & difficulty≥0.38 OR difficulty≥0.50
- Role: Short-field / difficulty mid-upper survival
- Route: midupper_route | midupper_spread | midupper_corelike
- Gap: mid-upper ranks survive via route or spread
- Spread: route vs spread

### `midhole_world`
- Activation: late_stop≥0.56 AND sustained≥0.52
- Role: Late-stop × sustained mid-hole
- Route: sustained / outside (via mixed/midhole sub rules)
- Gap: hole between core lock and deep chaos
- Spread: sustained-family

### `rank7_world`
- Activation: chaos≥0.58 AND high_pace≥0.48
- Role: Chaos × high-pace rank7 observation
- Route: rank7_transition | rank7_residual
- Gap: hidden rank7–10 under top compression
- Spread: transition preference

### `bug_world`
- Activation: chaos≥0.66 AND difficulty≥0.62
- Role: Extreme chaos × difficulty residual
- Route: bug observation / deep residual
- Gap: deep (often ≥12)
- Spread: observation

### `mixed_world`
- Activation: short_field≥0.72+(phase|chaos|diff) OR phase≥0.62
- Role: Multi world-line coexistence
- Route: route-forward + multi-survivor families
- Gap: unstable; diversity required
- Spread: high
