# Version100 — Semantic Coverage

**Generated:** `2026-07-28T12:57:28+00:00`

**問い:** 各レースについて「なぜこの World になったのか」を Core が説明できるか？

- mean semantic score: **1.0000**
- semantic_complete_rate: **1.0000**
- explainable_rate: **1.0000**

## 構成要素

| Element | Coverage |
|---|---:|
| `world_label` | 1.0000 |
| `must_satisfied_known` | 1.0000 |
| `must_gaps_known` | 1.0000 |
| `exclusion_reasons_known` | 1.0000 |
| `near_miss_reasons_known` | 1.0000 |
| `expected_strategy_known` | 1.0000 |
| `transition_known` | 1.0000 |
| `trigger_path_known` | 1.0000 |

## 要素の意味

- must_satisfied_known / must_gaps_known / exclusion_reasons_known
- near_miss_reasons_known（unsatisfied 時）
- expected_strategy_known（V75 マップ解決）
- transition_known / trigger_path_known

Hit・ROI は含めない。
