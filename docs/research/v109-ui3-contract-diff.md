# Phase UI3 — Contract Diff

**Date:** 2026-07-29  
**Guard:** `public/assets/api/contract-guard.js` → `validatePredictionBundle`  
**Consumers:** `race.html` / `ExpectPredictionBind`（UI 非変更）

---

## Required by ExpectContractGuard

| Field | Rule |
|---|---|
| `schema_version` | exactly `single-prediction-bundle/2.0` |
| `race_id` | non-empty string |
| `race_info` | object |
| `race_info.venue` | string |
| `race_info.date` | string |
| `race_info.race_no` | **number**（string/null 不可） |
| `evaluation.runners` | array |
| `ai_confidence.score` | present（number \| null） |
| `explain.narrative` | **string**（欠落不可） |
| `betting_recommendations.items` | array |

## Diff（Before → After）

| Source | Before | After |
|---|---|---|
| UI1 Mapper（base なし） | `explain` に `narrative` **欠落** | `narrative: ""` |
| UI1 Mapper / overlay | `race_no` が string/null のまま通過し得る | **int に正規化**（失敗時 1 / race_id から推定） |
| UI1 Mapper / overlay | `venue`/`date` が null になり得る | **非空 string**（`unknown` または race_id） |
| Mapper / bets | `items` 欠落し得る | **必ず array** |
| BFF `normalizePredictionBundle` | 一部フィールドが Guard 未満 | `ensurePredictionBundleContract` で最終保証 |

## Root cause（UI3）

UI1 Mapper の default `explain` が `reasons` のみで **`narrative` 未設定**。  
加えて `race_info.race_no` の型ゆれ（string/null）が Guard の `typeof === "number"` で落ちる。

Prediction エンジン自体は非変更。応答整形（Mapper + BFF normalize）で解消。
