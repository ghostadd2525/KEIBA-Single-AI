# Version102 — Semantic Coverage Report

**Generated:** `2026-07-28T13:10:35+00:00`  
**n_races:** 285  
**Mode:** Shadow Observation · **実装禁止**  
**非評価:** Hit / ROI / Calibration / Decision / Prediction 改善

## Verdict

**`DERIVABLE_COMPLETE_BUT_NOT_FIRST_CLASS`**

Structured traces allow deriving a closed explanation for essentially all races, but Expected Strategy / Affinity / Exclusion reasons / Near Miss class / EC Bundle are not first-class Core emits — explanation depends on maps + derivation (no new Features).

- derivable closed rate: **1.0000**
- explainability flow closed rate: **1.0000**
- first-class payload complete: **False**

## Slot coverage（現有情報）

- mean coverage: **1.0000**
- fully closed races: **1.0000**

| Slot | Rate |
|---|---:|
| `affinity_in_race_payload` | 0.0000 |
| `affinity_vector` | 1.0000 |
| `exclusion_reasons` | 1.0000 |
| `exclusion_reasons_in_trace_payload` | 0.0000 |
| `exclusion_trace` | 1.0000 |
| `expected_strategy` | 1.0000 |
| `expected_strategy_in_race_payload` | 0.0000 |
| `explanation_confidence_ec` | 1.0000 |
| `explanation_confidence_emitted` | 0.0000 |
| `match_trace` | 1.0000 |
| `must_gaps` | 1.0000 |
| `must_trace` | 1.0000 |
| `near_miss_class` | 1.0000 |
| `near_world_or_pure` | 1.0000 |
| `prediction_bundle` | 1.0000 |
| `transition` | 1.0000 |
| `world_label` | 1.0000 |

## Missing required slots

```
{}
```

## 解釈

Coverage は『導出すれば説明が閉じるか』を測る。
first-class 未 emit（Affinity/ES/EC 等）は Missing Inventory を参照。
