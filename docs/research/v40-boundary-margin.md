# Version40 — Boundary Margin

**N:** `56`  
**Ambiguous rate (|soft_margin| <= 0.15):** `28.6%` (16 races)

## 3. Rule margins by World

| World | n_obs | mean margin | pass rate | near-zero (|m|<=0.05) | negative rate |
|-------|------:|------------:|----------:|----------------------:|--------------:|
| core_world | 0 | nan | n/a | n/a | n/a |
| midupper_world | 56 | -0.1555 | 5.4% | 3.6% | 94.6% |
| midhole_world | 56 | -0.1912 | 3.6% | 12.5% | 96.4% |
| rank7_world | 56 | -0.2126 | 0.0% | 0.0% | 100.0% |
| bug_world | 56 | -0.3239 | 0.0% | 0.0% | 100.0% |
| mixed_world | 5 | -0.0991 | 0.0% | 20.0% | 100.0% |

- Mean soft margin (assigned vs 2nd): `-0.3479`

Positive margin means rule condition exceeded. Near-zero means ambiguous boundary.
