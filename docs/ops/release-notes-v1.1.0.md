# Release Notes — Version 1.1.0

**Tag:** `v1.1.0`  
**Merge commit:** `7fcdc47`（`feature/v1.1-ui-ops` → `main`）  
**RC tip:** `e5d1121`（Canary docs 含む）/ 実装本体 `238fd28` + `eaab497`  
**Date:** 2026-07-21  
**Baseline Freeze:** `v1.0.0-stable`（`08c7986`）は **変更しない**

---

## Summary

Version 1.1 は **UI / Ops 表示改善**と **開催日自動メンテナンス（Feature Flag 配下）**を追加するリリースです。  
本番既定では Canary 対象 Flag はすべて **OFF** のため、merge 直後の挙動は Version 1.0 と同等パスです。

---

## Included

- Feature Flag 基盤（`ui_features` / `ExpectUiFeatures`）
- UI Improvements（loading/errors 既定 ON、他は既定 OFF）
- Explain / Confidence / Collector HOLD 表示 / System Health / Ops Dashboard（Flag ON 時）
- Auto Maintenance: `CalendarProvider` + `WeekendCalendarProvider`、`maintenance.html`、`GET /api/ops/public-status`
- Canary Report（GO）・証拠・Merge Plan

## Explicitly unchanged / HOLD

| 項目 | 状態 |
|------|------|
| Prediction Core | 変更なし |
| RePick V2 | Flag OFF / research のみ |
| Real KeibaNet | **HOLD** |
| `v1.0.0-stable` tag | 移動なし |

## Feature Flag defaults（本番）

| Flag | Default |
|------|---------|
| `v11_loading_errors` | true |
| `v11_mobile` … `v11_ops_dashboard` | **false** |
| `v11_auto_maintenance` | **false** |

## Rollback

1. `ui_features.v11_auto_maintenance`（および他 Canary Flag）を `false` → Pages 再デプロイ  
2. 強制公開: `ops_mode: "PUBLIC"`  
3. 強制クローズ: `maintenance_mode: true`  
4. 最終: merge revert（`v1.0.0-stable` は触らない）

## Canary

詳細: [`v1.1-canary-report.md`](./v1.1-canary-report.md) — **GO**
