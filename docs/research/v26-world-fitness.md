# Version26 — World Fitness Analysis

**Date:** 2026-07-27T12:25:50+00:00  
**Scope:** Predictions assigned to `midupper_world` → fitness vs all EXISTING Worlds  
**Metric:** Trigger-proximity soft fitness (NOT hit rate)  

## Guardrails

- product_mutation: `False`
- world_trigger_changed: `False`
- new_worlds_forbidden: `True`

## Sample

- midupper_assigned: `51`
- evaluated (with snapshot signals block): `51`
- NB bins available: `51`
- near-miss: `1` (margin < `0.15`)
- chaos_missing among evaluated: `51`
- NB tables degenerate (midupper-only labels): `True`

## Mean fitness to each World (midupper-assigned set)

| World | Mean trigger fitness | Mean NB fitness |
|-------|---------------------:|----------------:|
| `core_world` | 0.0196 | 0.0 |
| `midupper_world` | 0.9804 | 1.0 |
| `midhole_world` | 0.0 | 0.0 |
| `rank7_world` | 0.0 | 0.0 |
| `bug_world` | 0.0 | 0.0 |
| `mixed_world` | 0.0 | 0.0 |

### Rank by mean trigger fitness

1. `midupper_world` — 0.9804
2. `core_world` — 0.0196
3. `midhole_world` — 0.0
4. `rank7_world` — 0.0
5. `bug_world` — 0.0
6. `mixed_world` — 0.0

## Best-fit distribution (trigger proximity argmax)

| Best-fit World | N |
|----------------|--:|
| `midupper_world` | 50 |
| `core_world` | 1 |

## Method

1. Restrict to Prediction Bundle `evaluation.world == midupper_world`
2. Load V25 `payload.research_world_signals.signals`
3. Score proximity to each EXISTING World trigger (V24 matrix / `classify_world_line_type` thresholds)
4. Secondary: V22 evidence-bin NB soft membership (often 1.0 on midupper only)

## Notes

- Primary metric: trigger-proximity soft fitness from V25 research_world_signals
- NB likelihood fitness reused from V22; collapses when only midupper labels exist
- chaos missing → proximity uses 0.0 (understates rank7/bug/mixed chaos routes)
- Does not change World Trigger or Prediction assignment
