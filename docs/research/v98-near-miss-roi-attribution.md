# Version98 — Near Miss ROI Attribution

**Generated:** `2026-07-28T12:34:07+00:00`  
**Population:** Near Miss n=104  
**Policy:** `baseline unsatisfied BUY Top1 UNIT (V97 Affinity rejected)`  
**Locks:** Prediction / World / Trigger · **実装禁止**  
**Frame:** Affinity ではなく **ROI Pattern**

## Overall

- Pooled Ticket ROI: **0.3981**
- Purchase Hit: **0.2596**
- Mean odds(Top1): 7.6587 / field=13.2019 / top_gap=0.0504

## ROI Bands

| Band | n | Hit | Pooled ROI | mean odds | field | top_gap |
|---|---:|---:|---:|---:|---:|---:|
| `LOSS` | 77 | 0.0000 | -1.0000 | 8.4558 | 13.0779 | 0.0452 |
| `WIN_LOW` | 5 | 1.0000 | 0.6400 | 1.6400 | 12.2000 | 0.0693 |
| `WIN_MID` | 8 | 1.0000 | 2.0625 | 3.0625 | 11.8750 | 0.0686 |
| `WIN_HIGH` | 14 | 1.0000 | 7.0500 | 8.0500 | 15.0000 | 0.0620 |

## HIT vs MISS 対比

| | HIT | MISS | Δ |
|---|---:|---:|---:|
| n | 27 | 77 | — |
| mean odds | 5.3852 | 8.4558 | -3.0707 |
| field_size | 13.5556 | 13.0779 | 0.4776 |
| top_gap | 0.0653 | 0.0452 | 0.0201 |

- HIT exclusion top: `{'excl:short_field_pressure↑': 25, 'excl:mid_eval_band_open↑': 18, 'excl:chaos↑': 9, 'excl:late∧sustained': 3, 'excl:top_gap↑': 1, 'excl:chaos↑∧difficulty↑': 1}`
- MISS exclusion top: `{'excl:short_field_pressure↑': 52, 'excl:mid_eval_band_open↑': 46, 'excl:chaos↑': 15, 'excl:top_gap↑': 13, 'excl:late∧sustained': 10, 'excl:chaos↑∧difficulty↑': 5}`

## 利益になる条件（rule lift）

| Rule | n | ROI | Hit | ROI Δ |
|---|---:|---:|---:|---:|
| `has_exclusion:excl:chaos↑` | 24 | 1.8958 | 0.3750 | 1.4978 |
| `top_gap >= 0.0568` | 36 | 1.3194 | 0.4444 | 0.9214 |
| `field_size >= 15` | 37 | 1.2973 | 0.2973 | 0.8992 |
| `odds>7.194 AND top_gap<=0.0358` | 14 | 1.2357 | 0.2143 | 0.8376 |
| `odds_top1 > 7.194` | 36 | 1.1750 | 0.1944 | 0.7769 |
| `has_exclusion:excl:late∧sustained` | 13 | 0.8769 | 0.2308 | 0.4788 |
| `has_exclusion:excl:short_field_pressure↑` | 77 | 0.6429 | 0.3247 | 0.2448 |
| `near_world == core_world` | 81 | 0.5617 | 0.3086 | 0.1637 |
| `has_exclusion:excl:mid_eval_band_open↑` | 64 | 0.4313 | 0.2812 | 0.0332 |
| `odds<=4.550 AND top_gap>=0.0443` | 29 | 0.2517 | 0.4483 | -0.1464 |

## 利益にならない条件

| Rule | n | ROI | Hit | ROI Δ |
|---|---:|---:|---:|---:|
| `has_exclusion:excl:top_gap↑` | 14 | -0.4500 | 0.0714 | -0.8481 |
| `near_world == midhole_world` | 13 | -0.4077 | 0.0769 | -0.8058 |
| `odds_top1 <= 3.100` | 36 | -0.3972 | 0.2778 | -0.7953 |
| `field_size <= 12` | 40 | -0.3550 | 0.1750 | -0.7531 |
| `odds_top1 <= 4.550` | 52 | -0.0462 | 0.3269 | -0.4442 |

## Exclusion / Near World（overall）

- near_world: `{'core_world': 81, 'midhole_world': 13, 'midupper_world': 9, 'rank7_world': 1}`
- exclusion: `{'excl:short_field_pressure↑': 77, 'excl:mid_eval_band_open↑': 64, 'excl:chaos↑': 24, 'excl:top_gap↑': 14, 'excl:late∧sustained': 13, 'excl:chaos↑∧difficulty↑': 6}`

## Hit stump (depth≤3)

```
|--- top_gap <= 0.070
|   |--- odds_top1 <= 2.000
|   |   |--- class: 0
|   |--- odds_top1 >  2.000
|   |   |--- field_size <= 12.500
|   |   |   |--- class: 0
|   |   |--- field_size >  12.500
|   |   |   |--- class: 0
|--- top_gap >  0.070
|   |--- odds_top1 <= 3.050
|   |   |--- class: 0
|   |--- odds_top1 >  3.050
|   |   |--- class: 1

```

importance: `{'odds_top1': 0.16656951698439793, 'field_size': 0.07506272846975487, 'top_gap': 0.7583677545458473}`

## Synthesis

Near Miss の利益は Affinity ではなく、Top1 単勝の的中×オッズ構造（ROI band）で分解できる。 利益条件 / 損失条件は rule lift と ROI cluster を参照。

- best profit rule: `{'rule': 'has_exclusion:excl:chaos↑', 'n': 24, 'share': 0.23076923076923078, 'purchase_hit_rate': 0.375, 'ticket_roi_pooled': 1.8958333333333333, 'hit_lift': 1.4444444444444444, 'roi_delta': 1.4977564102564103, 'mean_odds': 7.004166666666666, 'mean_field_size': 15.875, 'mean_top_gap': 0.050556492817375336, 'exclusion_top': {'excl:chaos↑': 24, 'excl:short_field_pressure↑': 24, 'excl:late∧sustained': 10, 'excl:mid_eval_band_open↑': 4}, 'near_world_dist': {'core_world': 24}}`
- worst loss rule: `{'rule': 'has_exclusion:excl:top_gap↑', 'n': 14, 'share': 0.1346153846153846, 'purchase_hit_rate': 0.07142857142857142, 'ticket_roi_pooled': -0.45, 'hit_lift': 0.2751322751322751, 'roi_delta': -0.8480769230769231, 'mean_odds': 8.542857142857143, 'mean_field_size': 14.642857142857142, 'mean_top_gap': 0.032855600094939486, 'exclusion_top': {'excl:top_gap↑': 14, 'excl:chaos↑∧difficulty↑': 6}, 'near_world_dist': {'midhole_world': 13, 'rank7_world': 1}}`
