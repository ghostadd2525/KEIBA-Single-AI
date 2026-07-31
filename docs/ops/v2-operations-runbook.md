# Version 2 Operations — Runbook（アラート運用）

**Status:** Phase 3 確定  
**正本設計:** `docs/releases/v2-operations-monitoring-inventory.md` §2.5 / §2.6  
**Dashboard:** Flag `v2_ops_dashboard` ON 時に Runbook パスを表示  
**Addendum（Race Refresh / Shadow）:** [`v2-operations-race-refresh-addendum.md`](./v2-operations-race-refresh-addendum.md)

---

## 0. 運用原則

| 原則 | 内容 |
|------|------|
| PI API 契約非変更 | 外形プローブ + additive metrics のみ |
| Flag OFF ≡ v1.1 | UI / Dashboard API は `v2_ops_dashboard` 配下 |
| Webhook 任意 | 未設定時 Slack は **no-op**（probe / metrics は継続） |
| 抑制 | 同一 Alert ID × severity で **15 分** |
| Features 正本 | **現行 shutuba**（詳細は Race Refresh Addendum） |

---

## 1. アラート一覧と初動

### ALT-E01 — BFF / Python 障害

1. `GET /api/health` と `GET /api/ops/monitor` を確認  
2. Pages Functions デプロイ / `AI_BASE_URL` Secrets  
3. EC2 `expect-ai` が active か

### ALT-E02 — PI 到達不可 {#alt-e02}

1. EC2: `systemctl status expect-pi-keibanet-api`  
2. `curl -sS http://127.0.0.1:8081/health`  
3. Tunnel: `PI_TUNNEL_PROBE_URL` / Access Token  
4. BFF `PI_BASE_URL` 設定

### ALT-E03 — Tunnel 切断 {#alt-e03}

1. `systemctl status cloudflared-expect-ai`  
2. local PI/win5 OK で Tunnel のみ NG → cloudflared / ingress  
3. Cloudflare Zero Trust connector

### ALT-E04 — Prediction 全失敗 {#alt-e04}

1. 開催日か確認（非開催はスキップ可）  
2. `GET /v1/predictions`（PI）と BFF `/api/predictions`  
3. FeatureLoader / features_unavailable は Warning 系（ALT-E07 は後続）  
4. daily features / Shadow 切替が絡む場合は [`v2-operations-race-refresh-addendum.md`](./v2-operations-race-refresh-addendum.md) のゲート（頭数減少で切替禁止）を確認

### ALT-E05 — PI systemd down {#alt-e05}

1. `systemctl status expect-pi-keibanet-api`  
2. `journalctl -u expect-pi-keibanet-api -n 100`  
3. 再起動後 `NRestarts` と incidents.jsonl

### ALT-E08 — Result Automation {#alt-e08}

1. `/v1/admin/results/status`  
2. `docs/ops/ops-hardening-runbook.md`  
3. Slack は **Warning**（SLK-N02）

### ALT-E09 — ETL 失敗 {#alt-e09}

1. `/v1/admin/etl/status`  
2. 最新 run の error_reason  
3. Slack は **Warning**（SLK-N02）

---

## 2. Slack チャンネル（設計）

| ID | 用途 | Env |
|----|------|-----|
| SLK-N01 | Critical | `OPS_SLACK_WEBHOOK_CRITICAL` or `OPS_SLACK_WEBHOOK_URL` |
| SLK-N02 | Warning | `OPS_SLACK_WEBHOOK_WARNING` or shared URL |
| SLK-N03 | Recovery | Warning と同じ webhook |

EC2: `/etc/expect-ai/ops-monitor.env`  
Pages: Secrets（Dashboard / Monitor 呼び出し時に dispatch）

---

## 3. 最終確認チェックリスト

- [x] Critical（ALT-E02/E05）→ SLK-N01  
- [x] Warning（ALT-E08/E09）→ SLK-N02  
- [x] Recovery → SLK-N03（EC2 monitor-prod）  
- [x] Dashboard に Runbook / Slack configured 表示  
- [x] Webhook 未設定でも probe・metrics・UI が動作  
- [x] Flag OFF で Dashboard API 404 · UI 非表示  

---

## 4. Grafana / Loki（prepared）

本番 Loki 接続は **設定例のみ**（Phase 3 では SaaS 契約不要）:

- `infra/observability/promtail-ops-metrics.example.yml`  
- 入力: `var/ops/pi-metrics.jsonl` / `incidents.jsonl`  
- パネル設計 ID: GRF-D01（prepared）
