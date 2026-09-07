# Version26 — World Near-Miss

**Date:** 2026-07-27T12:25:50+00:00  
**Definition:** assigned=`midupper_world` but best_fit≠midupper OR gap vs best other < `0.15` OR overall margin < threshold  

## Summary

- Near-miss N: `1` / midupper `51` (`2.0%`)

## Near-miss table

| Race | Assigned fit | Best fit | Best other | Gap | Chaos missing |
|------|-------------:|----------|------------|----:|:-------------:|
| `2026-07-26-01-01` | 0.0 | `core_world` (1.0) | `core_world` (1.0) | -1.0 | Y |

## Soft vector examples (first 15)

- `2026-07-26-01-01`: core_world=1.0, midupper_world=0.0, midhole_world=0.0, rank7_world=0.0, bug_world=0.0, mixed_world=0.0

## Interpretation

- Near-miss ≠ product mis-assignment; research proximity only
- With chaos=NULL, rank7/bug proximity is suppressed (chaos treated as 0)
- See `docs/audit/v26-chaos-trace.md` for chaos NULL root cause
- No Trigger / World / Prediction changes in this run
