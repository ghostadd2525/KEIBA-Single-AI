# Version11.1 - Corpus Growth

**Date:** 2026-07-27  

| Metric | Before (V11) | After (V11.1) | Delta | Target |
|--------|-------------:|--------------:|------:|-------:|
| Prediction | 340 | 340 | 0 | 3000 |
| Tie | 9 | 15 | +6 | 300 |
| Young Horse | 33 | 33 | 0 | 300 |

## Coverage after rebuild

- with Prediction Bundle: 339 (was 56)
- with RaceResult: 334
- with Evidence Snapshot: 55

## Gap remaining

- Prediction gap: 2660
- Tie gap: 285
- Young Horse gap: 267

## Note

- Prediction count stays flat: baseline_eval rows were replaced by Bundle-bearing historical rows.
- Tie 9->15 from 285r shared model_rank races (+6).
- Young Horse barely moves without class/race_name meta.
- Targets still require additional Historical Bundle supply.
