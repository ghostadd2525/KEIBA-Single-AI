# Version10.6 Research — Adoption Gate

## Production採用条件

| Gate | Threshold |
|------|-----------|
| `min_tie_races` | 100 |
| `min_resolver_win_rate` | 60.0% |
| `max_resolver_lose_rate` | 5.0% |
| `min_strict_improvement_rate` | 5.0% |
| `min_roi_change` | 0.0% |
| `min_coverage` | 95.0% |
| `min_confidence_median` | 70.0% |

## Status Rules

- `eligible`: すべての Gate を満たす
- `sample_insufficient`: Tie sample が閾値未満
- `rejected`: Lose rate 超過 または ROI悪化
- `watching`: 上記以外
