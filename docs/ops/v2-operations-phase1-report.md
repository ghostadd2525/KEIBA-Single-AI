# Version 2 Operations — Phase 1 実施レポート

**Date:** 2026-07-22  
**Status:** **実装完了 — 受領待ち**  
**設計正本:** [`docs/releases/v2-operations-monitoring-inventory.md`](../releases/v2-operations-monitoring-inventory.md) §8 Phase 1  
**対象:** PI Probe · Health Check · 基本 Metrics · Dashboard 基盤 · Logging  
**非対象:** Accuracy · UI Enhancement · Explainability · Prediction API · RaceCardSummary 契約  
**Final Report:** **未作成**（Phase 1 完了後停止）

---

## Feature Flag

| Flag | レイヤ | 既定 | 役割 |
|------|--------|------|------|
| `v2_ops_dashboard` | Web (`beta.json` / `ui-features.js`) | **false** | ops.html の PI Health パネル表示 |

ページ入場自体は既存 `v11_ops_dashboard` を維持。`v2_ops_dashboard` OFF ≡ PI パネル非表示（v1.1 同等）。

EC2 / Slack 側に追加 Flag はなし（env 未設定 = no-op）。

---

## 実装要点

| ID | 内容 |
|----|------|
| **PI-H01** | `monitor-prod.mjs` → `systemctl is-active`（`PI_SYSTEMD_UNIT`） |
| **PI-H02** | `GET PI_HEALTH_URL`（既定 `http://127.0.0.1:8081/health`） |
| **PI-H03** | 任意 `PI_TUNNEL_PROBE_URL`（未設定は skip） |
| **MET-J04** | `expect-ops-metrics/1.0` → `var/ops/pi-metrics.jsonl` |
| **ALT-E02 / E05** | incident に `alert_id` 付与 |
| **SLK-N01** | Critical Slack（webhook 未設定 no-op · 15 分抑制） |
| **Health** | `GET /api/health` に additive `pi` / `pi_proxy_configured` |
| **BFF Probe** | `probePiHealth`（`PI_BASE_URL/health`）· monitor 応答に `pi` ブロック |
| **Logging** | EC2 jsonl + BFF `console.log`（Logpush 向け `ops_metric`） |
| **Dashboard 基盤** | `ops.html` PI セクション（Flag ON 時） |

**原則維持:** PI API / Prediction / RaceCardSummary 契約は変更なし（外形プローブ + additive のみ）。

---

## 監視構成図

詳細: [`docs/ops/v2-operations-phase1-architecture.md`](./v2-operations-phase1-architecture.md)

```text
[Browser / Ops]
  ├─ GET /api/health        (+ additive pi)
  └─ GET /api/ops/monitor   (+ pi_health · metrics log)
         ↓
 Cloudflare Pages (BFF)
    ├─ PI_BASE_URL  → Tunnel → :8081  (PI)
    └─ AI_BASE_URL  → Tunnel → :8000  (win5-ai)
         ↓
 EC2 timer → monitor-prod.mjs
    ├─ PI-H01/H02/H03
    ├─ MET-J04  pi-metrics.jsonl
    ├─ ALT-E02/E05 → incidents.jsonl
    └─ SLK-N01 Slack（任意）
```

---

## スクリーンショット

| ファイル | 内容 |
|----------|------|
| `fixtures/ops/v2-ops-phase1-preview.html` | PI Dashboard 基盤プレビュー |
| `fixtures/ops/v2-ops-phase1-preview.png` | 提出用スクショ |

---

## テスト結果

```text
node --test tests/contract/ops-v2-phase1.test.mjs tests/contract/ops-monitor.test.mjs
→ 15 passed / 0 failed
```

| Suite | 結果 |
|-------|------|
| opsMetrics（MET-J04 行・jsonl） | PASS |
| opsSlack（SLK-N01 · 抑制） | PASS |
| BFF probePiHealth | PASS |
| 既存 OPS-Monitor / Hardening | PASS（回帰） |

---

## 変更ファイル一覧

| ファイル | 内容 |
|----------|------|
| `scripts/ops/monitor-prod.mjs` | PI probe · MET-J04 · ALT · Slack |
| `scripts/ops/opsMetrics.mjs` | **新規** expect-ops-metrics/1.0 writer |
| `scripts/ops/opsSlack.mjs` | **新規** SLK-N01 |
| `functions/_lib/opsMetrics.js` | **新規** BFF Logpush metrics |
| `functions/_lib/opsMonitor.js` | `probePiHealth` · `pi` ブロック |
| `functions/api/health.js` | additive `pi` |
| `contracts/expect-ops-metrics/1.0/schema.json` | **新規** 契約 |
| `infra/aws/systemd/ops-monitor.env.example` | PI / Slack env |
| `public/ops.html` | PI Dashboard 基盤 |
| `public/assets/v11.css` | PI セクション様式 |
| `public/assets/api/ui-features.js` | `v2_ops_dashboard` |
| `functions/_lib/betaConfig.js` | Flag 既定 |
| `config/beta.json` / `public/config/beta.json` | Flag 既定 false |
| `tests/contract/ops-v2-phase1.test.mjs` | **新規** 契約テスト |
| `fixtures/ops/v2-ops-phase1-preview.*` | プレビュー / PNG |
| `docs/ops/v2-operations-phase1-architecture.md` | 監視構成図 |
| `docs/ops/v2-operations-phase1-report.md` | 本レポート |

---

## 運用メモ（デプロイ時）

1. EC2 `/etc/expect-ai/ops-monitor.env` に `PI_HEALTH_URL` 等を追加（example 参照）
2. 任意: `OPS_SLACK_WEBHOOK_URL`（未設定でも probe / metrics は動作）
3. Pages: `PI_BASE_URL` 設定時に `/api/health.pi` と `/api/ops/monitor` の `pi_health` が有効
4. Dashboard: `v11_ops_dashboard=true` かつ `v2_ops_dashboard=true` で PI パネル表示

---

**停止点:** Operations Phase 1 完了。Phase 2（Grafana / Slack 全般 / ルート別 Latency）および Final Report は作成していません。受領をお待ちします。
