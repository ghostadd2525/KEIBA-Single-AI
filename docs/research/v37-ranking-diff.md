# Version37 — Ranking Diff

**Weight focus:** 50%（中間感度）  
**N:** `51`

## Prediction / Candidate 順位変化

| Metric | Value |
|--------|------:|
| Races with any candidate rank change | 51 |
| Top1 changed | 49 (96.1%) |
| Top3 set changed | 49 (96.1%) |
| Mean horses with rank change / race | 5.96 |
| Mean abs candidate rank move | 1.094 |

## Hit / miss layer Δ @ 50%

| Layer | Δ |
|-------|--:|
| Hit | -2 |
| Purchase | -2 |
| rank46 | +5 |
| rank710 | +0 |
| other_1_3 | +2 |
| other_10_13 | -1 |
| other_miss | -3 |

## Full weight sweep

| Weight | Hit | ΔHit | Purchase | ΔPurch | rank710 | Δ710 | other_miss | Δother | Top1 change | mean |rank| move |
|-------:|----:|-----:|---------:|-------:|--------:|-----:|-----------:|-------:|------------:|------------------:|
| 0% | 8 (15.7%) | +0 | 8 | +0 | 9 | +0 | 19 | +0 | 0 (0.0%) | 0.000 |
| 25% | 7 (13.7%) | -1 | 7 | -1 | 9 | +0 | 17 | -2 | 47 (92.2%) | 1.002 |
| 50% | 6 (11.8%) | -2 | 6 | -2 | 9 | +0 | 16 | -3 | 49 (96.1%) | 1.094 |
| 75% | 6 (11.8%) | -2 | 6 | -2 | 9 | +0 | 17 | -2 | 50 (98.0%) | 1.100 |
| 100% | 7 (13.7%) | -1 | 7 | -1 | 11 | +2 | 15 | -4 | 50 (98.0%) | 1.335 |

## Note

Baseline ranks are frozen Production `model_rank`. Policy ranks are simulation-only.
