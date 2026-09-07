# Version96 — Near Miss Attribution

**Generated:** `2026-07-28T12:22:33+00:00`

## Near Miss Distribution（primary）

| near_world | n |
|---|---:|
| `core_world` | 81 |
| `midhole_world` | 13 |
| `midupper_world` | 9 |
| `rank7_world` | 1 |

class_distribution: `{'PURE_RESIDUAL': 72, 'NEAR_MISS': 104}`

## Must Gap Attribution（unsatisfied 全体・出現レース数）

### `core_world`

| must_gap | n |
|---|---:|
| `ability_separation↑` | 71 |
| `top_gap↑` | 43 |

### `midupper_world`

| must_gap | n |
|---|---:|
| `aptitude_fit↑` | 85 |
| `upper_ability_band↑` | 74 |
| `development_pressure↑` | 31 |

### `midhole_world`

| must_gap | n |
|---|---:|
| `top_monopoly↓` | 116 |
| `mid_eval_band_open↑` | 77 |

### `rank7_world`

| must_gap | n |
|---|---:|
| `ability_subordinate↑` | 132 |
| `chaos↑` | 127 |
| `pace_conflict↑` | 31 |

## Exclusion Reason Attribution（exclude=True のレースで発火）

### `core_world`

| exclusion_reason | n |
|---|---:|
| `excl:short_field_pressure↑` | 145 |
| `excl:mid_eval_band_open↑` | 99 |
| `excl:chaos↑` | 49 |
| `excl:late∧sustained` | 38 |

### `midupper_world`

| exclusion_reason | n |
|---|---:|
| `excl:mid_eval_band_open↑` | 99 |
| `excl:chaos↑∧high_pace↑` | 43 |
| `excl:top_gap↑_without_dev/apt` | 6 |

### `midhole_world`

| exclusion_reason | n |
|---|---:|
| `excl:top_gap↑` | 133 |
| `excl:chaos↑∧difficulty↑` | 39 |

### `rank7_world`

| exclusion_reason | n |
|---|---:|
| `excl:top_gap↑` | 133 |
| `excl:difficulty↑_without_chaos` | 16 |

## 保持契約

- Near Miss レコードは **Must Gap** と **Exclusion Reason** を両方保持する。
- Affinity スコアは Must 近さ。Exclusion はブロック理由であり、近さの減点ではない。
