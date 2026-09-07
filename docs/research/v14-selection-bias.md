# Version14 Research - Selection Bias & Leak Risk

**Date:** 2026-07-27T08:36:40+00:00  

| Feature | SelBias | LeakRisk | ASOF rate | Obs>Pred rate | Missing reasons | Detail |
|---------|--------:|---------:|----------:|--------------:|-----------------|--------|
| `Popularity` | 0.0 | 0.7 | 100.0% | 0.0% |  | `{"mode": "always_present", "fav_share_p1_3": 0.242}` |
| `Breeder` | 0.0 | 0.7 | 100.0% | 0.0% |  | `{"mode": "always_present_or_insufficient"}` |
| `Damsire` | 0.0 | 0.7 | 100.0% | 0.0% |  | `{"mode": "always_present_or_insufficient"}` |
| `Sire` | 0.0 | 0.7 | 100.0% | 0.0% |  | `{"mode": "always_present_or_insufficient"}` |
| `Owner` | 0.0 | 0.7 | 100.0% | 0.0% |  | `{"mode": "always_present_or_insufficient"}` |
| `Trainer` | 0.0 | 0.7 | 100.0% | 0.0% |  | `{"mode": "always_present_or_insufficient"}` |
| `Odds` | 0.4639 | 0.7 | 100.0% | 0.0% |  | `{"mode": "value_vs_popularity_strata", "mean_val_fav": 4.129, "mean_val_long": 111.529}` |
| `SalePrice` | 0.1345 | 0.7 | 100.0% | 0.0% | not_listed:421 | `{"mean_pop_filled": 7.838, "mean_pop_missing": 6.762, "mode": "missingness_vs_popularity"}` |
| `WorkoutTime` | 0.11 | 0.7 | 100.0% | 0.0% | not_published:513 | `{"mean_pop_filled": 6.377, "mean_pop_missing": 7.257, "mode": "missingness_vs_popularity"}` |
| `WorkoutRating` | 0.11 | 0.7 | 100.0% | 0.0% | not_published:513 | `{"mean_pop_filled": 6.377, "mean_pop_missing": 7.257, "mode": "missingness_vs_popularity"}` |

## Reading

- **SelectionBias**: missingness or value distribution skewed by popularity strata.
- **LeakRisk**: dominated by `asof_clamped` (observation clock forced to prediction time).
- High ASOF rate means Evidence may be temporally softened for harvest; treat cautiously in research.
