# Version 2 Operations — Phase 2 実施レポート

**Date:** 2026-07-22  
**Status:** **実装完了 — 受領待ち**  
**設計正本:** [`docs/releases/v2-operations-monitoring-inventory.md`](../releases/v2-operations-monitoring-inventory.md) §8 Phase 2  
**対象:** Dashboard 拡張 · Metrics 集約 · Incident 表示 · PI Probe 表示改善 · Alert 可視化  
**非対象:** Accuracy · UI Enhancement · Explainability · Prediction API · RaceCardSummary 契約  
**Final Report / Phase 3:** **未着手**（Phase 2 完了後停止）

---

## Feature Flag

| Flag | レイヤ | 既定 | 役割 |
|------|--------|------|------|
| `v2_ops_dashboard` | Web / Dashboard API | **false** | ops.html v2 セクション + `GET /api/ops/dashboard` |

ページ入場は既存 `v11_ops_dashboard`。v2 表示・API は **`v2_ops_dashboard` 配下のみ**。

### Flag OFF 恒等性

| 確認 | 結果 |
|------|------|
| `beta.json` / `public/config/beta.json` で `v2_ops_dashboard: false` | PASS |
| `opsV2Root` 初期 `hidden` · Flag OFF で再 hidden | PASS |
| 基本 8 カード（Health / latency / Prediction…）残存 | PASS |
| latency note が v1.1 文言 | PASS |
| `/api/ops/dashboard` は Flag OFF 時 `404 FEATURE_DISABLED` | 実装済 |

Flag OFF ≡ v1.1 ops 画面（クライアント計測カードのみ）。

---

## 実装要点

| 項目 | 内容 |
|------|------|
| **Dashboard 拡張** | `ops.html` に PI / Metrics / Alerts / Incidents セクション |
| **Metrics 集約** | `buildDashboardPayload` → `expect-ops-metrics/1.0` rows + summary（MET-J02） |
| **Incident 表示** | 失敗 probe スナップショット（`expect-ops-incident/1.0` + `alert_id`） |
| **PI Probe 改善** | probe 単位テーブル（status / latency / alert） |
| **Alert 可視化** | ALT-E* 派生 · Critical/Warning 集計カード + 表 |
| **API** | **新規** `GET /api/ops/dashboard`（auth + admin + Flag） |
| **Monitor 拡張** | `/api/ops/monitor` に metrics / alerts / incidents を additive |

---

## 監視構成図

詳細: [`docs/ops/v2-operations-phase2-architecture.md`](./v2-operations-phase2-architecture.md)

```text
Browser (v2_ops_dashboard ON)
  → GET /api/ops/dashboard  → buildDashboardPayload(runAllProbes)
  → GET /api/ops/monitor    → 同一集約フィールド（監視キー）
EC2 monitor-prod            → Phase 1 継続（MET-J04 / Slack）
```

---

## スクリーンショット

| ファイル | 内容 |
|----------|------|
| `fixtures/ops/v2-ops-phase2-preview.html` | Dashboard 拡張プレビュー |
| `fixtures/ops/v2-ops-phase2-preview.png` | 提出用スクショ |

---

## テスト結果

```text
node --test tests/contract/ops-v2-phase2.test.mjs \
             tests/contract/ops-v2-phase1.test.mjs \
             tests/contract/ops-monitor.test.mjs
→ 23 passed / 0 failed
```

| Suite | 結果 |
|-------|------|
| Phase2 aggregate / Flag / Flag OFF 恒等 | PASS |
| Phase1 回帰 | PASS |
| OPS-Monitor 既存 | PASS |

---

## 変更ファイル一覧

| ファイル | 内容 |
|----------|------|
| `functions/_lib/opsDashboard.js` | **新規** Metrics/Alert/Incident 集約 |
| `functions/api/ops/dashboard.js` | **新規** Dashboard API（Flag ゲート） |
| `functions/_lib/opsMonitor.js` | monitor 応答に集約フィールド |
| `functions/api/ops/monitor.js` | alert_id 付き incident 記録 |
| `functions/_lib/incidentLog.js` | `alert_id` 対応 |
| `public/ops.html` | Dashboard 拡張（`opsV2Root`） |
| `public/assets/v11.css` | 表・tone 様式 |
| `tests/contract/ops-v2-phase2.test.mjs` | **新規** 契約・Flag OFF テスト |
| `fixtures/ops/v2-ops-phase2-preview.*` | プレビュー / PNG |
| `docs/ops/v2-operations-phase2-architecture.md` | 監視構成図更新 |
| `docs/ops/v2-operations-phase2-report.md` | 本レポート |

---

## 運用メモ

1. Dashboard 表示: `v11_ops_dashboard=true` かつ `v2_ops_dashboard=true` + 管理者
2. Flag OFF のままデプロイしても v1.1 画面は不変
3. `/api/ops/monitor` の集約フィールドは監視系向け（キー保護）。UI は `/api/ops/dashboard` を使用

---

**停止点:** Operations Phase 2 完了。Phase 3（Slack 全般 · Grafana/Loki · CF API）および Final Report は作成していません。受領をお待ちします。
