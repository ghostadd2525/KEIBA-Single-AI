# Version100 — Missing Metadata Inventory

**Generated:** `2026-07-28T12:57:28+00:00`

- races with any missing: **285** / 285
- races clean (no missing flags): **0**

## Missing counts（バケット）

| Missing key | n_races_touched |
|---|---:|
| `confidence:candidate_missing` | 285 |
| `rank_not_unique_or_incomplete` | 7 |

## Examples（最大5 race_id / key）

```json
{
  "confidence:candidate_missing": [
    "2024-01-06-中山-09",
    "2024-01-06-中山-10",
    "2024-01-06-中山-11",
    "2024-01-06-京都-10",
    "2024-01-06-京都-11"
  ],
  "rank_not_unique_or_incomplete": [
    "2024-01-06-中山-09",
    "2024-04-07-阪神-10",
    "2024-06-02-京都-11",
    "2025-12-13-中京-10",
    "2026-01-18-中山-11"
  ]
}
```

## 解釈

本 Inventory は **改善実装をしない**。欠落の所在を示すのみ。
最大ギャップが Confidence 候補付与であれば、それは Completeness 課題であり Hit 改善課題ではない。
