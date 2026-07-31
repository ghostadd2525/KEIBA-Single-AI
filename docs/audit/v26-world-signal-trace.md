# Version26 — World Signal Trace (Audit)

**Date:** 2026-07-27T12:25:50+00:00  
**Scope:** World-line signals path Prediction → Research (audit)  

## Signal families

| Signal | Generated in | On diagnostic | On meta via detect_race_meta | On Bundle | V25 persisted |
|--------|--------------|:-------------:|:----------------------------:|:---------:|:-------------:|
| chaos_score | pace features | Yes | No | No | No (NULL 100%) |
| race_leg_difficulty | probability/frame | often | Yes (copied) | No | Yes (~87.7%) |
| pace_collapse_risk | frame | — | Yes | No | Yes (via meta / line score) |
| late_stop / high_pace / phase | calc_world_line_score(meta) | derived | derived scores | No | Yes (often 0.0) |
| short_field_pressure | calc_short_field_pressure(meta) | — | computed at V25 copy | No | Yes |
| world / sub_world | classify_world_line_type | — | CE world fields | evaluation.* | Yes (~96.5%) |
| world_reason | (not a stable Core field) | — | No | No | No (NULL 100%) |

## Drop taxonomy

1. **Diagnostic-only drop** (chaos): computed in adjustment diagnostic, never joined to meta
2. **Bundle strip**: Prediction Bundle contract does not carry world-line numerics
3. **Instrumentation miss**: V25 reads meta/frame/bundle, not `_diagnostic`
4. **Default-at-judgment**: classify treats missing chaos as 0.0 — product still runs

## Relation to V25

- V25 correctly persisted signals that reached meta or were recomputed by `calc_world_line_score` / `calc_short_field_pressure`
- V25 could not persist chaos because the value never entered those inputs
- Mean persistence 76.6% with chaos/world_reason as structural NULLs

## Live probe summary

- race: `2026-07-26-03-05`
- diagnostic chaos: `{'mean': 0.19802799999999995, 'max': 0.19802799999999998, 'min': 0.19802799999999998}`
- null_from_here: `['_source_frame', 'meta', 'bundle', 'research_world_signals']`

## Forbidden actions (this version)

- No AI change
- No Prediction change
- No World / Trigger change
- No new Feature
- Audit documentation only
