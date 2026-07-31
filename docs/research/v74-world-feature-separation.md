# Version74 — World Feature Separation

**Generated:** `2026-07-28T08:10:46+00:00`  
**Metric:** oriented effect = winner−loser（odds/popularity は低値有利に向き付け）

## ② World別特徴量重要度

### `core_world`（n=8）

| Rank | Feature | Effect | FieldHit |
|---:|---|---:|---:|
| 1 | `win_prob_z` | 1.1095 | 0.2500 |
| 2 | `odds_z` | 0.7100 | 0.2500 |
| 3 | `history_z` | 0.4960 | 0.2500 |
| 4 | `odds_pct_low` | 0.3262 | 0.2500 |
| 5 | `win_prob_pct` | 0.2274 | 0.2500 |
| 6 | `history_pct` | 0.1695 | 0.2500 |

### `midupper_world`（n=6）

| Rank | Feature | Effect | FieldHit |
|---:|---|---:|---:|
| 1 | `win_prob_z` | 0.8803 | 0.3333 |
| 2 | `odds_z` | 0.8542 | 0.1667 |
| 3 | `history_z` | 0.7303 | 0.3333 |
| 4 | `odds_pct_low` | 0.4364 | 0.1667 |
| 5 | `win_prob_pct` | 0.3609 | 0.3333 |
| 6 | `history_pct` | 0.2423 | 0.3333 |

### `midhole_world`（n=24）

| Rank | Feature | Effect | FieldHit |
|---:|---|---:|---:|
| 1 | `history_z` | 0.7075 | 0.2083 |
| 2 | `odds_z` | 0.5193 | 0.1667 |
| 3 | `win_prob_z` | 0.2866 | 0.0833 |
| 4 | `history_pct` | 0.2244 | 0.2083 |
| 5 | `odds_pct_low` | 0.1788 | 0.1667 |
| 6 | `win_prob_pct` | 0.1766 | 0.0833 |

### `rank7_world`（n=65）

| Rank | Feature | Effect | FieldHit |
|---:|---|---:|---:|
| 1 | `history_z` | 0.7074 | 0.2000 |
| 2 | `win_prob_z` | 0.6902 | 0.1538 |
| 3 | `odds_z` | 0.6808 | 0.3077 |
| 4 | `odds_pct_low` | 0.3381 | 0.3077 |
| 5 | `win_prob_pct` | 0.2727 | 0.1538 |
| 6 | `history_pct` | 0.2147 | 0.2000 |

### `mixed_world`（n=6）

| Rank | Feature | Effect | FieldHit |
|---:|---|---:|---:|
| 1 | `win_prob_z` | 1.6482 | 0.5000 |
| 2 | `odds_z` | 0.7388 | 0.3333 |
| 3 | `odds_pct_low` | 0.3128 | 0.3333 |
| 4 | `win_prob_pct` | 0.2359 | 0.5000 |
| 5 | `history_pct` | 0.0339 | 0.0000 |
| 6 | `history_z` | -0.0028 | 0.0000 |

### `bug_world`（n=0）

サンプル 0。

### `unsatisfied`（n=176）

| Rank | Feature | Effect | FieldHit |
|---:|---|---:|---:|
| 1 | `popularity_z` | 1.0631 | 0.3000 |
| 2 | `win_prob_z` | 0.8310 | 0.2273 |
| 3 | `odds_z` | 0.6905 | 0.2670 |
| 4 | `history_z` | 0.5952 | 0.1648 |
| 5 | `popularity_pct_low` | 0.3278 | 0.3000 |
| 6 | `odds_pct_low` | 0.3167 | 0.2670 |
| 7 | `win_prob_pct` | 0.2471 | 0.2273 |
| 8 | `history_pct` | 0.1891 | 0.1648 |

## ⑤ Feature Interaction（Context × Winner）

安定 World を中心に、レース文脈と勝ち馬強度の Pearson r（n≥5 のみ算出）。

### `midhole_world`

| Context | Winner feature | r | n |
|---|---|---:|---:|
| `top_gap` | `win_prob_pct` | -0.1350 | 24 |
| `top_gap` | `history_pct` | 0.2083 | 24 |
| `ability_subordinate` | `win_prob_pct` | 0.1350 | 24 |
| `ability_subordinate` | `history_pct` | -0.2083 | 24 |
| `field_size` | `win_prob_pct` | 0.1585 | 24 |
| `field_size` | `history_pct` | 0.1627 | 24 |
| `mid_eval_band_open` | `win_prob_pct` | -0.1165 | 24 |
| `upper_ability_band` | `win_prob_pct` | -0.2337 | 24 |

### `rank7_world`

| Context | Winner feature | r | n |
|---|---|---:|---:|
| `top_gap` | `win_prob_pct` | 0.0224 | 65 |
| `top_gap` | `history_pct` | 0.0563 | 65 |
| `ability_subordinate` | `win_prob_pct` | -0.0224 | 65 |
| `ability_subordinate` | `history_pct` | -0.0563 | 65 |
| `field_size` | `win_prob_pct` | -0.1131 | 65 |
| `field_size` | `history_pct` | -0.0706 | 65 |
| `mid_eval_band_open` | `win_prob_pct` | -0.1593 | 65 |
| `upper_ability_band` | `win_prob_pct` | 0.2583 | 65 |

### `core_world`

| Context | Winner feature | r | n |
|---|---|---:|---:|
| `top_gap` | `win_prob_pct` | 0.0291 | 8 |
| `top_gap` | `history_pct` | 0.3272 | 8 |
| `ability_subordinate` | `win_prob_pct` | -0.0291 | 8 |
| `ability_subordinate` | `history_pct` | -0.3272 | 8 |
| `field_size` | `win_prob_pct` | 0.2573 | 8 |
| `field_size` | `history_pct` | 0.2108 | 8 |
| `mid_eval_band_open` | `win_prob_pct` | -0.2220 | 8 |
| `upper_ability_band` | `win_prob_pct` | -0.3067 | 8 |

### `midupper_world`

| Context | Winner feature | r | n |
|---|---|---:|---:|
| — | — | — | — |

### `mixed_world`

| Context | Winner feature | r | n |
|---|---|---:|---:|
| — | — | — | — |

### `unsatisfied`

| Context | Winner feature | r | n |
|---|---|---:|---:|
| `top_gap` | `win_prob_pct` | -0.0153 | 176 |
| `top_gap` | `history_pct` | -0.0135 | 176 |
| `ability_subordinate` | `win_prob_pct` | 0.0153 | 176 |
| `ability_subordinate` | `history_pct` | 0.0135 | 176 |
| `field_size` | `win_prob_pct` | 0.1447 | 176 |
| `field_size` | `history_pct` | -0.0065 | 176 |
| `mid_eval_band_open` | `win_prob_pct` | -0.1633 | 176 |
| `upper_ability_band` | `win_prob_pct` | -0.0805 | 176 |

## 符号逆転（安定 World 間）

| Context | Winner feat | + Worlds | − Worlds |
|---|---|---|---|
| `field_size` | `win_prob_pct` | midhole_world | rank7_world |
| `upper_ability_band` | `win_prob_pct` | rank7_world | midhole_world |
