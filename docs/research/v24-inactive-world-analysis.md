# Version24 — Inactive World Analysis

**Date:** 2026-07-27T11:41:58+00:00  

Focus: Worlds with **0 activations** or **activation rate < 1%**.
Question answered: **あと何が足りないか** (what is still missing).

## `core_world`

- Activation N / Rate: `0` / `0.0%`
- Activation Condition: Fires when no higher-priority survival world trigger matches
- Required: `[]`
- Missing Condition (signals absent in Evidence): `[]`
- Route: core_top / core_under; may promote to midupper_route under compression
- Role: Ability-settlement default
- Gap: tight top probability gaps
- Spread: low
- World Trigger: `['DEFAULT (no prior trigger matched)']`

### なぜ発火しないのか

- Zero labeled activations in current Prediction Bundle sample
- Sample is dominated by midupper_world; default core path never observed in labeled bundles (classifier may still default to core elsewhere)

### あと何が足りないか

- Persist world_line meta on PredictionBundle evaluation (chaos_score, race_leg_difficulty, late_stop, sustained, high_pace, phase_transition, short_field_pressure)
- Accumulate labeled bundles for non-midupper Worlds (not create new Worlds)
- Do NOT change product classifier; research needs observable activation of `core_world`

## `midhole_world`

- Activation N / Rate: `0` / `0.0%`
- Activation Condition: late_stop≥0.56 AND sustained≥0.52
- Required: `['late_stop', 'sustained']`
- Missing Condition (signals absent in Evidence): `['late_stop_risk_score', 'sustained_run_possible_score']`
- Route: sustained / outside (via mixed/midhole sub rules)
- Role: Late-stop × sustained mid-hole
- Gap: hole between core lock and deep chaos
- Spread: sustained-family
- World Trigger: `['late_stop >= 0.56 AND sustained >= 0.52']`

### なぜ発火しないのか

- Zero labeled activations in current Prediction Bundle sample
- Required trigger signals for `midhole_world` are not present in research bundles (missing: ['late_stop_risk_score', 'sustained_run_possible_score'])
- Needs late_stop≥0.56 AND sustained≥0.52 — both meta fields absent from Evidence JSON

### あと何が足りないか

- Persist world_line meta on PredictionBundle evaluation (chaos_score, race_leg_difficulty, late_stop, sustained, high_pace, phase_transition, short_field_pressure)
- Accumulate labeled bundles for non-midupper Worlds (not create new Worlds)
- Do NOT change product classifier; research needs observable activation of `midhole_world`

## `rank7_world`

- Activation N / Rate: `0` / `0.0%`
- Activation Condition: chaos≥0.58 AND high_pace≥0.48
- Required: `['high_pace', 'chaos_score']`
- Missing Condition (signals absent in Evidence): `['chaos_score', 'high_pace_score']`
- Route: rank7_transition | rank7_residual
- Role: Chaos × high-pace rank7 observation
- Gap: hidden rank7–10 under top compression
- Spread: transition preference
- World Trigger: `['chaos_score >= 0.58 AND high_pace >= 0.48']`

### なぜ発火しないのか

- Zero labeled activations in current Prediction Bundle sample
- Required trigger signals for `rank7_world` are not present in research bundles (missing: ['chaos_score', 'high_pace_score'])
- Needs chaos≥0.58 AND high_pace≥0.48 — both meta fields absent from Evidence JSON

### あと何が足りないか

- Persist world_line meta on PredictionBundle evaluation (chaos_score, race_leg_difficulty, late_stop, sustained, high_pace, phase_transition, short_field_pressure)
- Accumulate labeled bundles for non-midupper Worlds (not create new Worlds)
- Do NOT change product classifier; research needs observable activation of `rank7_world`

## `bug_world`

- Activation N / Rate: `0` / `0.0%`
- Activation Condition: chaos≥0.66 AND difficulty≥0.62
- Required: `['race_leg_difficulty', 'chaos_score']`
- Missing Condition (signals absent in Evidence): `['chaos_score', 'race_leg_difficulty']`
- Route: bug observation / deep residual
- Role: Extreme chaos × difficulty residual
- Gap: deep (often ≥12)
- Spread: observation
- World Trigger: `['chaos_score >= 0.66 AND race_leg_difficulty >= 0.62']`

### なぜ発火しないのか

- Zero labeled activations in current Prediction Bundle sample
- Required trigger signals for `bug_world` are not present in research bundles (missing: ['chaos_score', 'race_leg_difficulty'])
- Needs chaos≥0.66 AND difficulty≥0.62 — both meta fields absent from Evidence JSON

### あと何が足りないか

- Persist world_line meta on PredictionBundle evaluation (chaos_score, race_leg_difficulty, late_stop, sustained, high_pace, phase_transition, short_field_pressure)
- Accumulate labeled bundles for non-midupper Worlds (not create new Worlds)
- Do NOT change product classifier; research needs observable activation of `bug_world`

## `mixed_world`

- Activation N / Rate: `0` / `0.0%`
- Activation Condition: short_field≥0.72+(phase|chaos|diff) OR phase≥0.62
- Required: `['phase_transition', 'short_field_pressure', 'phase|chaos|difficulty']`
- Missing Condition (signals absent in Evidence): `['chaos_score', 'chaos_score(for_full_short_field)', 'phase_transition', 'race_leg_difficulty']`
- Route: route-forward + multi-survivor families
- Role: Multi world-line coexistence
- Gap: unstable; diversity required
- Spread: high
- World Trigger: `['short_field_pressure >= 0.72 AND (phase_transition >= 0.48 OR chaos_score >= 0.42 OR race_leg_difficulty >= 0.42)', 'phase_transition >= 0.62']`

### なぜ発火しないのか

- Zero labeled activations in current Prediction Bundle sample
- Required trigger signals for `mixed_world` are not present in research bundles (missing: ['chaos_score', 'chaos_score(for_full_short_field)', 'phase_transition', 'race_leg_difficulty'])
- Needs short_field_pressure≥0.72 with phase/chaos/difficulty OR phase≥0.62 — proxy short_field≥0.72 corpus rate=0.19161676646706588

### あと何が足りないか

- Persist world_line meta on PredictionBundle evaluation (chaos_score, race_leg_difficulty, late_stop, sustained, high_pace, phase_transition, short_field_pressure)
- Accumulate labeled bundles for non-midupper Worlds (not create new Worlds)
- Do NOT change product classifier; research needs observable activation of `mixed_world`

## Guardrails

- Do **not** create new Worlds to fill inactive slots
- Do **not** change Prediction / PE / CE / AI
- Mature Evidence so existing triggers become observable
