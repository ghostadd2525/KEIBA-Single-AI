# Version28 — Difficulty Saturation

**Date:** 2026-07-27T13:20:11+00:00  
**Context:** V27 observed R7 `difficulty >= 0.50` pass ≈ 98%  

## Pass rates

| Threshold | Pass N | Pass rate | Bar |
|----------:|-------:|----------:|-----|
| `>=0.50` | 50 | 100.0% | `########################################` |
| `>=0.60` | 0 | 0.0% | `` |
| `>=0.70` | 0 | 0.0% | `` |
| `>=0.80` | 0 | 0.0% | `` |
| `>=0.90` | 0 | 0.0% | `` |

## Link to World assignment (observational)

- R7 midupper trigger uses `difficulty >= 0.50` only
- If pass_rate(>=0.50) is near 100% and unique values collapse to 0.5, first-match simulation yields midupper saturation after earlier rules fail
- Thresholds are not modified in this audit
