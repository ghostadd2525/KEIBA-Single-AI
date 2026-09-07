# Version11 Research — Young Horse Corpus

**Date:** 2026-07-27T07:43:14+00:00  
- Young Horse count: `33` / target `300`
- Gap: `267`

## Age Group

| Age | Count |
|-----|------:|
| `2yo_maiden` | 6 |
| `2yo_newcomer` | 7 |
| `3yo_maiden` | 19 |
| `2yo_other` | 1 |

## Class

| Class | Count |
|-------|------:|
| `3歳未勝利` | 19 |
| `2歳新馬` | 7 |
| `2歳未勝利` | 6 |
| `ジュニアC` | 1 |

## Note

Young Horse 判定は `class_label` / race_name のヒューリスティック。
現状は class_label 欠損が多く、`young_horse_count` が過小になる。
次フェーズで race meta の補完と過去 Prediction Bundle の取り込みが必要。
