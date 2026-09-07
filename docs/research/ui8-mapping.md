# UI8 — Mapping Table

**Date:** 2026-07-30

## World → 内部ラベル

| world（例） | 内部ラベル |
|---|---|
| `core_world` | normal |
| `midupper_world` | near_miss |
| `midhole_world` / `mixed_world` | affinity_residual |
| `rank7_world` / `unsatisfied` / `bug_world` | pure_residual |
| `near_miss` オブジェクトあり | near_miss（優先） |
| `affinity` オブジェクトあり | affinity_residual（優先） |
| 上記以外・欠落 | score 帯フォールバック |

## Score → score band（UI7 同一）

| score | score band |
|---|---|
| ≥ 0.75 | high |
| ≥ 0.60 | rather_high |
| ≥ 0.35 | medium |
| < 0.35 | low |

## ラベル天井

| 内部ラベル | 天井 band |
|---|---|
| normal | high |
| near_miss | rather_high |
| affinity_residual | medium |
| pure_residual | low |

## 最終表示 = min(天井, score band)

| 例 | 結果 ★ / 文言 |
|---|---|
| normal + 0.80 | ★★★★★ 高い |
| near_miss + 0.80 | ★★★★☆ やや高い |
| near_miss + 0.50 | ★★★☆☆ ふつう |
| affinity_residual + 0.90 | ★★★☆☆ ふつう |
| pure_residual + 0.95 | ★★☆☆☆ 低い |
| （world 無し）score 0.48 | ★★★☆☆ ふつう（フォールバック） |

## ユーザー向け（内部名なし）

| band | ★ | 文言 |
|---|---|---|
| high | ★★★★★ | 高い |
| rather_high | ★★★★☆ | やや高い |
| medium | ★★★☆☆ | ふつう |
| low | ★★☆☆☆ | 低い |
