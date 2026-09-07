# Version27 — Design Gap (Observational)

**Date:** 2026-07-27T12:50:55+00:00  
**Design reference mix (research intent, not a product knob):** core 30% / midupper 35% / rank7 15% / mixed 10% / bug 5% / midhole 5%  

## Quantitative gap

- Total variation distance: `0.65`
- L1 absolute gap: `1.3`
- Max |gap| world: `midupper_world`

| World | Design | Observed | Sim first-match | Gap (pp) | Obs/Design |
|-------|-------:|---------:|----------------:|---------:|-----------:|
| `core_world` | 30.0% | 0.0% | 2.0% | -30.0 | 0.0 |
| `midupper_world` | 35.0% | 100.0% | 98.0% | 65.0 | 2.8571 |
| `midhole_world` | 5.0% | 0.0% | 0.0% | -5.0 | 0.0 |
| `rank7_world` | 15.0% | 0.0% | 0.0% | -15.0 | 0.0 |
| `bug_world` | 5.0% | 0.0% | 0.0% | -5.0 | 0.0 |
| `mixed_world` | 10.0% | 0.0% | 0.0% | -10.0 | 0.0 |

## Reading (facts only)

- Positive gap_pp ⇒ over-represented vs design intent
- Negative gap_pp ⇒ under-represented vs design intent
- This document does **not** propose Trigger changes

## Guardrails

- improvement_forbidden: `True`
- world_trigger_changed: `False`
