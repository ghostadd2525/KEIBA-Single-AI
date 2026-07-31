# Version11 Research — Prediction Corpus

**Date:** 2026-07-27T07:44:28+00:00  
**Scope:** Research only / Prediction 変更禁止 / Shadow only  

## Summary

- Prediction count: `340` / target `3000`
- Gap: `2660`
- Bundle付き: `56`
- RaceResult付き: `334`
- Evidence Snapshot付き: `55`
- Shadow Result付き: `9`

## Source Breakdown

| Source | Count |
|--------|------:|
| `live_prediction` | 56 |
| `miss_evidence` | 1 |
| `baseline_eval` | 283 |

## Breakdown

### 年齢別

| Age | Count |
|-----|------:|
| `unknown` | 295 |
| `older` | 12 |
| `2yo_maiden` | 6 |
| `2yo_newcomer` | 7 |
| `3yo_maiden` | 19 |
| `2yo_other` | 1 |

### クラス別

| Class | Count |
|-------|------:|
| `unknown` | 190 |
| `3歳未勝利` | 19 |
| `3歳以上1勝クラス` | 11 |
| `2歳新馬` | 7 |
| `2歳未勝利` | 6 |
| `福島民報杯` | 3 |
| `豊栄特別` | 1 |
| `新潟日報賞` | 1 |
| `清津峡特別` | 1 |
| `3歳以上障害OP` | 1 |
| `四日市特別` | 1 |
| `関ケ原S` | 1 |
| `香嵐渓特別` | 1 |
| `ライラック賞` | 1 |
| `TVh賞` | 1 |
| `桑園特別` | 1 |
| `紫川S` | 1 |
| `招福S` | 1 |
| `中山金杯` | 1 |
| `ジュニアC` | 1 |
| `寿S` | 1 |
| `京都金杯` | 1 |
| `ポルックスS` | 1 |
| `新春S` | 1 |
| `初咲賞` | 1 |
| `淀短距離S` | 1 |
| `フェアリーS` | 1 |
| `若潮S` | 1 |
| `ジャニュアリーS` | 1 |
| `京成杯` | 1 |
| `日経新春杯` | 1 |
| `大津特別` | 1 |
| `江戸川S` | 1 |
| `AJCC` | 1 |
| `山城S` | 1 |
| `壇之浦S` | 1 |
| `プロキオンS` | 1 |
| `シルクロードS` | 1 |
| `門司S` | 1 |
| `八坂S` | 1 |

### 芝ダート別

| Surface | Count |
|---------|------:|
| `turf` | 186 |
| `dirt` | 107 |
| `unknown` | 47 |

### 距離別

| Distance | Count |
|----------|------:|
| `middle` | 61 |
| `mile` | 124 |
| `unknown` | 47 |
| `sprint` | 91 |
| `long` | 17 |

### 開催別

| Venue | Count |
|-------|------:|
| `中山` | 71 |
| `京都` | 54 |
| `阪神` | 50 |
| `東京` | 42 |
| `中京` | 34 |
| `新潟` | 22 |
| `小倉` | 22 |
| `福島` | 19 |
| `札幌` | 18 |
| `函館` | 8 |

## Decision

```
Action Type: Prediction Corpus Expansion (Research)
Prediction Mutation: FORBIDDEN
Shadow Only: YES
Next: continue ingesting historical Prediction Bundles + RaceResults
```
