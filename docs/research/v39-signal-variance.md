# Version39 — Signal Variance & Coverage

**N:** `56`

## Current vs Restored

| Signal | Cur cov | Cur std | Cur nunique | Res cov | Res std | Res nunique |
|--------|--------:|--------:|------------:|--------:|--------:|------------:|
| difficulty | 100.0% | 0.0000 | 1 | 100.0% | 0.0828 | 44 |
| chaos | 0.0% | 0.0000 | 0 | 100.0% | 0.0904 | 55 |
| phase | 100.0% | 0.0000 | 1 | 8.9% | 0.0288 | 5 |
| late_stop | 100.0% | 0.0000 | 1 | 100.0% | 0.1362 | 53 |
| sustained | 100.0% | 0.0000 | 1 | 100.0% | 0.1655 | 54 |
| high_pace | 100.0% | 0.0000 | 1 | 100.0% | 0.1719 | 45 |
| short_field_pressure | 100.0% | 0.0000 | 1 | 100.0% | 0.3517 | 14 |

## Reading

- Current arm collapses many L1/L2 signals to constant/null (V28-V38).
- Restored arm reconstructs difficulty from designed pace formula and pulls chaos/pace/late/sustained from Scorer diagnostics (virtual; not written back).
- `phase` may remain weak if `phase_chain_seed` is absent/low-variance.
