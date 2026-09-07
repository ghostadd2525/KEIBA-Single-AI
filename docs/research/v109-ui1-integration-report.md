# Version109 Phase UI1 — Existing UI Integration Report

**Date:** 2026-07-29  
**Status:** COMPLETE（View Mapper）· UI レイアウト変更 **なし**

---

## 目的達成

既存サイトの画面構成を維持したまま、Single AI 結果を **PredictionBundle 形**で供給可能にした。

## 実装

| 項目 | 結果 |
|---|---|
| View Mapper | `map_single_to_prediction_bundle` |
| HTTP | `POST /v1/ui/prediction-bundle` · `POST /api/ui/prediction-bundle` |
| prediction-bind.js | **未変更** |
| race.html / デザイン | **未変更** |
| Consumer / Core / Contract | **未変更** |

## 対象画面カバレッジ

| 画面 | 供給可否 | 備考 |
|---|---|---|
| レース一覧 | Yes | Bundle→既存 summary bind |
| レース詳細 | Yes | applyRaceDetail |
| AI予想タブ | Yes | 同上 |
| 評価内訳 | Yes* | ability_scores は base_bundle 必要 |
| このレースの自信度 | Yes* | ai_confidence は base_bundle / 既存 Product |

\* Single Presentation から評価内訳・自信度を新造しない（既存 Product View を合成）。

## 推奨運用

1. 既存 `/api/predictions` で base Bundle を取得（または PI）
2. Single 結果 + `base_bundle` を `POST /api/ui/prediction-bundle`
3. 返却 Bundle を既存 `ExpectPredictionBind` に渡す（レイアウト同一）

Shadow 時のみ。Production 切替は別 Gate。
