# Version100 — Core Completeness Report

**Generated:** `2026-07-28T12:57:28+00:00`  
**ADR:** ADR-009  
**n_races:** 285  
**Mode:** Shadow Observation · **実装禁止**  
**非評価:** ROI / Hit / 券種 / Skip / 資金配分

## Status

| Axis | Grade |
|---|---|
| `prediction_completeness` | **MED** |
| `prediction_with_confidence` | **LOW** |
| `world_completeness` | **HIGH** |
| `near_miss_completeness` | **HIGH** |
| `semantic_completeness` | **HIGH** |
| `semantic_explainable` | **HIGH** |

## ① Prediction Completeness

| Metric | Rate |
|---|---:|
| rank_coverage (mean) | 1.0000 |
| score_coverage (mean) | 1.0000 |
| confidence_coverage (mean) | 0.0000 |
| top1_defined | 1.0000 |
| ranks_unique_complete | 0.9754 |
| field_alignment | 1.0000 |
| fingerprint_stable | 1.0000 |
| prediction_complete (rank/score) | 0.9754 |
| prediction_complete_with_confidence | 0.0000 |

## ② World Completeness

| Metric | Rate |
|---|---:|
| label_present | 1.0000 |
| trace_present | 1.0000 |
| must_trace_complete | 1.0000 |
| exclusion_trace_complete | 1.0000 |
| match_trace_complete | 1.0000 |
| match_consistent | 1.0000 |
| transition_present | 1.0000 |
| decision_tree_trace_present | 1.0000 |
| expected_strategy_present | 1.0000 |
| world_complete | 1.0000 |
| positive_world_rate (obs) | 0.3825 |

## ③ Near Miss Completeness（unsatisfied のみ）

n_unsatisfied=176

| Metric | Rate |
|---|---:|
| class_present | 1.0000 |
| near_world_present | 1.0000 |
| affinity_present | 1.0000 |
| must_gaps_present | 1.0000 |
| exclusion_reasons_present | 1.0000 |
| transition_present | 1.0000 |
| near_miss_complete | 1.0000 |
| residual_class_dist | `{'PURE_RESIDUAL': 72, 'NEAR_MISS': 104}` |

## ④ Semantic Completeness

- mean semantic score: **1.0000**
- semantic_complete_rate: **1.0000**
- explainable_rate (≥0.8): **1.0000**

### Part coverage

| Part | Rate |
|---|---:|
| `world_label` | 1.0000 |
| `must_satisfied_known` | 1.0000 |
| `must_gaps_known` | 1.0000 |
| `exclusion_reasons_known` | 1.0000 |
| `near_miss_reasons_known` | 1.0000 |
| `expected_strategy_known` | 1.0000 |
| `transition_known` | 1.0000 |
| `trigger_path_known` | 1.0000 |

## Notes

- Confidence per-candidate is often absent in corpus runners — reported as Completeness gap, not fixed here.
- Expected Strategy is resolved via V75 design map (observation), not PE mutation.
- ROI / Hit / Skip are excluded from this report.

## 関連

- `v100-missing-metadata-inventory.md`
- `v100-trace-completeness.md`
- `v100-semantic-coverage.md`
- `v100-governance.md`
- ADR-009
