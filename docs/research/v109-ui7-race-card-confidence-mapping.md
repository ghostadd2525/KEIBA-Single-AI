# Phase UI7 — Race Card Confidence Mapping

**Date:** 2026-07-30  
**Deploy:** Cloudflare Pages `keiba-single-ai`（Functions + `prediction-bind.js?v=37`）

## Mapping（ai_confidence.score → 表示）

| 表示意図 | score | ★ | 文言 | band |
|---|---|---|---|---|
| Normal | ≥ 0.75 | ★★★★★ | 高い | `high` |
| Near Miss | ≥ 0.60 | ★★★★☆ | やや高い | `rather_high` |
| Affinity | ≥ 0.35 | ★★★☆☆ | ふつう | `medium` |
| Pure Residual | < 0.35 | ★★☆☆☆ | 低い | `low` |

※ Bundle に Near Miss / Affinity フィールドは無い。スコア帯の表示エンコーディング。

## Changes

- [`public/assets/api/prediction-bind.js`](../../public/assets/api/prediction-bind.js) — 4段階 ★/文言
- [`functions/_lib/confidenceBands.js`](../../functions/_lib/confidenceBands.js) — 閾値
- [`functions/_lib/raceCardSummary.js`](../../functions/_lib/raceCardSummary.js) — export
- [`functions/_lib/piPredictionMapper.js`](../../functions/_lib/piPredictionMapper.js) — 共通 band
- [`contracts/expect-race-card-summary/1.0/schema.json`](../../contracts/expect-race-card-summary/1.0/schema.json) — `rather_high` 追加（値域拡張）
- cache-bust: races/race/index `prediction-bind.js?v=37`

## Verification

| Check | Result |
|---|---|
| Unit mapping (`verify-mapping.mjs`) | PASS 8 cases |
| Contract tests (`race-card-summary.test.mjs`) | PASS 12 |
| `/api/race-cards?date=2026-07-26` | 36 ready, band=`medium`（score≈0.48–0.55） |
| UI 一覧 2026-07-26 | 36件すべて ★★★☆☆ / ふつう |
| starsFromBand 4段階 | high/rather_high/medium/low PASS |
| Layout / Race List Cache / 追加HTTP | 非変更 |

Screenshot: `docs/research/artifacts/ui7/races-list-affinity-band.png`
