# UI Enhancement Phase 4 — 検索 実施レポート

**Date:** 2026-07-22  
**Scope:** Race Catalog 検索（`data-race-honmei` + summary 対象）  
**設計:** `docs/releases/v2-ui-enhancement-mock.md` §3.5  
**非対象:** お気に入り / Explainability / Operations / Accuracy

## Feature Flag

| Flag | 既定 | 役割 |
|------|------|------|
| `v2_race_list_ui` | **false** | ON 時に本命・信頼度・band を検索対象に含める |
| `v2_race_cards` | false | 一覧 DTO（既存） |

検索専用 Flag は追加していない（モック §2.3 に合わせ `v2_race_list_ui` 連動）。

## Flag OFF 恒等性

| 確認 | 結果 |
|------|------|
| Unit: v2Enhanced=false で honmei/conf を haystack に含めない | PASS |
| Unit: v1 `raceCardHtml` に `data-race-honmei` / `data-prediction-status` なし | PASS |
| Unit: v1 カード相当で「コルドン」「42」はマッチしない、「豊栄」はマッチ | PASS |
| `beta.json` `v2_race_list_ui: false` | PASS |

## テスト結果

```text
node --test tests/contract/race-search.test.mjs tests/contract/race-card-list-ui.test.mjs
→ 16 passed, 0 failed
```

## スクリーンショット

- Preview HTML: `fixtures/race-card-summary/v2-race-search-preview.html`
- PNG: `fixtures/race-card-summary/v2-race-search-preview.png`  
  （クエリ「コルドン」→ 本命マッチ 1/3 件）

## 変更ファイル一覧

| ファイル | 内容 |
|----------|------|
| `public/assets/api/race-search.js` | **新規** `ExpectRaceSearch` |
| `public/assets/api/prediction-bind.js` | `data-race-honmei` + aria-label |
| `public/races.html` | race-search 読込・placeholder・match 連携 |
| `tests/contract/race-search.test.mjs` | **新規** 契約テスト |
| `fixtures/race-card-summary/v2-race-search-preview.html` | プレビュー |
| `fixtures/race-card-summary/v2-race-search-preview.png` | スクショ |
| `docs/releases/v2-ui-enhancement-mock.md` | Phase 4 チェック完了 |
