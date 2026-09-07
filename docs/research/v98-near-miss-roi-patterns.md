# Version98 — Near Miss ROI Patterns

**Generated:** `2026-07-28T12:34:07+00:00`

## ROI Clusters

k=4

| Cluster | tag | n | ROI | Hit | odds | field | top_gap | excl top |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `roi_cluster_2` | **PROFIT_HIGH** | 10 | 8.5800 | 1.0000 | 9.5800 | 15.0000 | 0.0580 | `['excl:short_field_pressure↑', 'excl:mid_eval_band_open↑']` |
| `roi_cluster_3` | **PROFIT_LOW** | 21 | 0.4476 | 0.5238 | 2.8619 | 10.5714 | 0.0815 | `['excl:mid_eval_band_open↑', 'excl:short_field_pressure↑']` |
| `roi_cluster_0` | **LOSS_MIXED** | 40 | -0.5200 | 0.1500 | 3.3375 | 13.7750 | 0.0387 | `['excl:short_field_pressure↑', 'excl:mid_eval_band_open↑']` |
| `roi_cluster_1` | **LOSS_MASS** | 33 | -1.0000 | 0.0000 | 15.3667 | 13.6364 | 0.0425 | `['excl:short_field_pressure↑', 'excl:mid_eval_band_open↑']` |

## Pattern 解釈

1. **LOSS_MASS** — 未的中が支配。ROI≈−1。Field/Odds/Gap の損失側プロファイル。
2. **PROFIT_*** — 的中帯。オッズ水準で LOW/HIGH に分かれる。
3. Affinity / near_world 単独では利益条件を説明しきれない（V97 と整合）。
4. Decision に使うなら Affinity ではなく **ROI 条件（odds×gap×field×exclusion）** を候補に（別 Shadow）。

## k search

```
[
  {
    "k": 2,
    "inertia": 320.93439175158176,
    "sizes": {
      "1": 77,
      "0": 27
    },
    "roi_mean_span": 0.04742664742664743
  },
  {
    "k": 3,
    "inertia": 233.73541319600946,
    "sizes": {
      "2": 10,
      "1": 26,
      "0": 68
    },
    "roi_mean_span": 9.297647058823529
  },
  {
    "k": 4,
    "inertia": 187.3889007602041,
    "sizes": {
      "2": 10,
      "3": 21,
      "1": 33,
      "0": 40
    },
    "roi_mean_span": 9.58
  },
  {
    "k": 5,
    "inertia": 153.74248943595813,
    "sizes": {
      "1": 10,
      "2": 18,
      "0": 29,
      "3": 24,
      "4": 23
    },
    "roi_mean_span": 9.58
  }
]
```
