# UI Enhancement Phase 5 — お気に入り 実施レポート

**Date:** 2026-07-22  
**Scope:** お気に入り登録／解除 · RaceCardSummary 投影 · ローカル保存 · 一覧★ · 検索共存  
**設計:** `docs/releases/v2-ui-enhancement-mock.md` §3.6  
**非対象:** Accuracy / Explainability / Operations / Prediction API / RaceCardSummary 契約変更

## Feature Flag

| Flag | 既定 | 役割 |
|------|------|------|
| `v2_race_list_ui` | **false** | ON 時のみホーム fav レールへ ◎ / 信頼度% を表示 |
| `v2_race_cards` | false | 一覧 DTO（既存） |

お気に入り専用 Flag は追加していない（モック §2.3 に合わせ `v2_race_list_ui` 連動）。

## 実装要点

| 項目 | 内容 |
|------|------|
| RaceCardSummary feed | `ExpectFavorites.cacheBundles(cards)`（`races.html` renderV2 後） |
| 投影 | `summary.honmei` → ◎ / `summary.confidence` → % |
| ローカル保存 | `expect_favorites_v1` に `honmei` / `honmeiNum` / `confPct` / `confBand` |
| 一覧 ★ | `data-fav-honmei` / `data-fav-conf` 等を RaceCardSummary カードへ付与 |
| 検索共存 | Phase 4 `ExpectRaceSearch` と独立（★・fav レールは検索フィルタ外） |

## Flag OFF 恒等性

| 確認 | 結果 |
|------|------|
| Unit: Flag OFF で `cardHtml` に `fav-summary` / ◎ / % なし | PASS |
| Unit: v1 `raceCardHtml` に `data-fav-honmei` / `data-fav-conf` なし | PASS |
| `beta.json` `v2_race_list_ui: false` | PASS |
| 一覧★・localStorage・最大3件の既存挙動は維持 | PASS |

## テスト結果

```text
node --test tests/contract/favorites-v2.test.mjs tests/contract/race-search.test.mjs tests/contract/race-card-list-ui.test.mjs
→ 24 passed, 0 failed
```

## スクリーンショット

- Preview HTML: `fixtures/race-card-summary/v2-race-favorites-preview.html`
- PNG: `fixtures/race-card-summary/v2-race-favorites-preview.png`  
  （ホーム fav レールに ◎ / % · 一覧★ 同期）

## 変更ファイル一覧

| ファイル | 内容 |
|----------|------|
| `public/assets/favorites.js` | RaceCardSummary 対応 · summary 投影 · enrich · Flag ゲート |
| `public/assets/api/prediction-bind.js` | `data-fav-honmei` / conf / band |
| `public/races.html` | V2 描画後に RaceCardSummary を `cacheBundles` |
| `public/assets/styles.css` | `.fav-summary` |
| `tests/contract/favorites-v2.test.mjs` | **新規** 契約テスト |
| `fixtures/race-card-summary/v2-race-favorites-preview.html` | プレビュー |
| `fixtures/race-card-summary/v2-race-favorites-preview.png` | スクショ |
| `docs/releases/v2-ui-enhancement-mock.md` | Phase 5 チェック完了 |
| `docs/ops/v2-ui-phase5-favorites-report.md` | 本レポート |
| `docs/releases/v2-ui-enhancement-final-report.md` | UI Enhancement 最終レポート |
