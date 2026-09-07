# UI8 — Compatibility

**Date:** 2026-07-30

## UI1 / UI7 との関係

| 項目 | 状態 |
|---|---|
| World / NM / Affinity を画面に出さない（G109-UI1-5） | **維持** |
| 一覧カード DOM（`.race-conf-stars` / `.race-conf-label`） | **維持**（★・文言の中身のみ） |
| UI7 の score 閾値 0.75 / 0.60 / 0.35 | **維持**（score 側） |
| UI7 の score のみ再計算 | **廃止** → BFF/UI とも label+score |
| RaceCardSummary `confidence.{score,band}` キー | **維持**（値の意味が label+score に更新） |
| 新規 API / Cache スキーマ | **なし** |

## 本番データ前提

- PI Bundle に Consumer の `near_miss` / `affinity` オブジェクトは通常 **無い**
- 使える内部信号: `prediction.world` / `evaluation.world` + `ai_confidence.score`
- world が CEW 以外（例 fixture `turf`）のときは score フォールバック（UI7 相当）

## 後方互換

- `band` enum: `high` / `rather_high` / `medium` / `low`（UI7 schema のまま）
- ホームキャッシュ `expect_home_honmei_v1` → **v2**（旧キーは読まない・自然失効）
- `pickTopByConfidence` は残置（他用途）。ホームは `pickHomeTodaysHonmei`

## 回帰リスク

| リスク | 緩和 |
|---|---|
| midupper + 高 score が ★5 にならない | 仕様（Near Miss 天井）。docs/mapping に明示 |
| ★★★★☆ 以上が無い日は本命空 | 空状態 UI で明示 |
| Client が score のみ再計算 | list は BFF band 優先に変更済み |

## 検証

- `tests/contract/race-card-summary.test.mjs`（UI8 label+score ケース含む）
- Production Required: **No**（本フェーズはデプロイしない）
