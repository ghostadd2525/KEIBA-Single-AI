# Version 2 — Operations 監視対象一覧

**Date:** 2026-07-21  
**Status:** **監視対象一覧提出**（コード変更前）  
**Baseline:** Version 1.1 本番（PI API + BFF + Tunnel + EC2）  
**正本:** v1.0 監視設計を拡張（[`v1.0-ops-monitoring-design.md`](../ops/v1.0-ops-monitoring-design.md)）

---

## 0. エグゼクティブサマリー

Version 2 Operations は **運用品質向上** を目的とし、ユーザー指定の 8 カテゴリを監視対象として体系化する。

| 追加候補 | v2 監視カテゴリ | 現状 | v2 ギャップ |
|----------|----------------|------|-------------|
| PI API Health Dashboard | **PI** | `/health` 手動のみ | 統合ダッシュボード・自動プローブ未配線 |
| Prediction Latency | **Latency** | probe `latency_ms` 部分 | PI/BFF 分離計測・p95 アラート未整備 |
| Tunnel 監視 | **Tunnel** | 間接 probe | ingress ルート別・CF API 未監視 |
| Cloudflare 監視 | **Cloudflare** | 手動 Dashboard | Pages/Workers/Tunnel 自動集約なし |
| Error Alert | **Alert** | incidents.jsonl | 閾値自動判定・エスカレーション弱い |
| Slack 通知 | **Notification** | **なし** | webhook 未実装 |
| JSON Metrics | **Metrics** | `metrics.jsonl`（win5-ai のみ） | 統一スキーマ・BFF/PI 未出力 |
| Grafana 対応 | **Observability** | **なし** | Prometheus/Loki 未接続 |

**原則:** PI API 契約（`/v1/races` / `/v1/predictions` / `/health`）は **変更しない**。監視は **外形プローブ + メトリクス出力追加（additive）** で実現する。

---

## 1. 監視アーキテクチャ（v1.1 本番）

```text
Browser
  ↓
Cloudflare Pages (expect-keiba.com)
  ├─ GET /api/health
  ├─ GET /api/ops/monitor
  ├─ GET /api/races        → PI /v1/races      (Tunnel → :8081)
  └─ GET /api/predictions  → PI /v1/predictions (Tunnel → :8081)
        ↓
Cloudflare Tunnel (ai.expect-keiba.com)
  ├─ /v1/races*       → 127.0.0.1:8081  (expect-pi-keibanet-api)
  ├─ /v1/predictions* → 127.0.0.1:8081
  └─ /*               → 127.0.0.1:8000  (expect-ai / win5-ai)
        ↓
EC2 (ubuntu@13.231.5.5)
  ├─ cloudflared-expect-ai.service
  ├─ expect-pi-keibanet-api.service (:8081)
  ├─ expect-ai.service (:8000)
  └─ expect-ops-monitor.timer → monitor-prod.mjs
```

**v2 監視レイヤ:**

```text
[Probes]  EC2 timer / BFF /ops/monitor / 外形 SaaS
    ↓
[Metrics] JSON (expect-ops-metrics/1.0) → metrics.jsonl / scrape endpoint
    ↓
[Dashboard] ops.html 拡張 / PI Health Dashboard / Grafana
    ↓
[Alert]   Error rules → Slack / incident jsonl
```

---

## 2. 監視対象マスタ一覧

### 凡例

| 列 | 意味 |
|----|------|
| **状態** | `已有` = 実装済み / `部分` = 手動・限定 / `未` = v2 新規 |
| **Critical** | C=即時対応 / W=警告 / I=情報 |
| **v2** | P0=最優先 / P1=次 / P2=後続 |

---

### 2.1 PI API Health Dashboard

| ID | 監視対象 | チェック方法 | 正常判定 | 間隔 | メトリクス | Alert | 状態 | v2 |
|----|----------|--------------|----------|------|------------|-------|------|-----|
| **PI-H01** | PI プロセス | EC2 `systemctl is-active expect-pi-keibanet-api` | `active` | 1 min | `pi.systemd.active` | C | 部分 | **P0** |
| **PI-H02** | PI Liveness | `GET http://127.0.0.1:8081/health` | `status=ok`, `service=pi-keibanet-api` | 1 min | `pi.health.latency_ms` | C | 已有（手動） | **P0** |
| **PI-H03** | PI Tunnel 経由 | `GET https://ai.expect-keiba.com/v1/races?date={today}` 先 `/health` 相当 | 200 + ok | 1–5 min | `pi.tunnel.health.latency_ms` | C | 未 | **P0** |
| **PI-H04** | Race Catalog | `GET /v1/races?date=YYYY-MM-DD` | 200, `races.length > 0`（開催日） | 5–15 min | `pi.races.count`, `pi.races.venues` | W | 部分 | **P0** |
| **PI-H05** | Prediction 到達 | `GET /v1/predictions/{sample_race_id}` | `prediction_available=true` | 5–15 min | `pi.prediction.available_rate` | W | 部分 | **P0** |
| **PI-H06** | FeatureLoader | prediction 404 `features_unavailable` 率 | 開催日 < 10% | 15 min | `pi.prediction.error.features_unavailable` | W | 未 | **P1** |
| **PI-H07** | CorePipeline | prediction 500 / runtime error 率 | エラー 0（窓 15 min） | 5 min | `pi.prediction.error.runtime` | C | 未 | **P0** |
| **PI-H08** | Collector 静的 API | `GET /v1/static/race_meta`（サンプル） | Validator OK | 60 min | `pi.collector.static.ok` | W | 部分 | **P1** |
| **PI-H09** | netkeiba fetch | PI ログ / 内部 rate limit | 429/timeout 急増なし | 15 min | `pi.netkeiba.fetch.errors` | W | 未 | **P2** |
| **PI-H10** | AI Platform Root | `PI_AI_PLATFORM_ROOT` 存在 | path readable | デプロイ後 | `pi.platform.root_ok` | C | 部分 | **P1** |

**Dashboard 表示項目（設計）:**

| パネル | ソース |
|--------|--------|
| Overall PI | PI-H01〜H03 合成 |
| Catalog | PI-H04（件数・会場数） |
| Prediction | PI-H05〜H07（成功率・latency） |
| Errors | features_unavailable / race_not_found 内訳 |

---

### 2.2 Prediction Latency

| ID | 監視対象 | チェック方法 | SLO（設計） | メトリクス | Alert | 状態 | v2 |
|----|----------|--------------|-------------|------------|-------|------|-----|
| **LAT-P01** | PI Prediction（local） | EC2 `curl -w time_total` → `:8081/v1/predictions/{id}` | p95 < **8 s** | `latency.pi.prediction.local.p95_ms` | W | 未 | **P0** |
| **LAT-P02** | PI Prediction（Tunnel） | BFF/外形 → `ai.expect-keiba.com/v1/predictions/{id}` | p95 < **10 s** | `latency.pi.prediction.tunnel.p95_ms` | W | 未 | **P0** |
| **LAT-P03** | BFF Prediction 一覧 | `GET /api/predictions?date=` | p95 < **15 s** | `latency.bff.predictions.list.p95_ms` | W | 未 | **P0** |
| **LAT-P04** | BFF Prediction 詳細 | `GET /api/predictions/{id}` | p95 < **10 s** | `latency.bff.predictions.get.p95_ms` | W | 部分 | **P0** |
| **LAT-P05** | BFF Race Catalog | `GET /api/races?date=` | p95 < **5 s** | `latency.bff.races.list.p95_ms` | W | 未 | **P1** |
| **LAT-P06** | win5-ai Prediction（legacy） | `:8000/v1/predictions`（Conversation 等） | p95 < 8 s | `latency.win5.prediction.p95_ms` | I | 部分 | **P2** |
| **LAT-P07** | 一覧 N+1（v2 UI） | `/api/race-cards`（将来） | p95 < **20 s** | `latency.bff.race_cards.p95_ms` | W | 未 | **P2** |

**既存資産:**

| 資産 | 内容 | ギャップ |
|------|------|----------|
| `opsMonitor.js` | 各 probe `latency_ms` | PI 経路未分離 |
| `monitor-prod.mjs` | `latency_ms` in report | PI :8081 未プローブ |
| `performance.py` | `var/ops/metrics.jsonl` | win5-ai :8000 のみ |

---

### 2.3 Tunnel 監視

| ID | 監視対象 | チェック方法 | 正常判定 | メトリクス | Alert | 状態 | v2 |
|----|----------|--------------|----------|------------|-------|------|-----|
| **TUN-H01** | cloudflared プロセス | `systemctl is-active cloudflared-expect-ai` | `active` | `tunnel.systemd.active` | C | 已有 | **P0** |
| **TUN-H02** | Tunnel 到達（health） | 公開 `https://ai.expect-keiba.com/health` | 200 ok | `tunnel.reachability.health` | C | 部分 | **P0** |
| **TUN-H03** | Ingress `/v1/races` | Tunnel 経由 races 200 | 200 | `tunnel.route.races.ok` | C | 未 | **P0** |
| **TUN-H04** | Ingress `/v1/predictions` | Tunnel 経由 predictions 200 | 200 | `tunnel.route.predictions.ok` | C | 未 | **P0** |
| **TUN-H05** | Ingress default → :8000 | `/v1/admin/*` または health | 200 | `tunnel.route.win5.ok` | W | 部分 | **P1** |
| **TUN-H06** | connectTimeout | ingress `connectTimeout: 10` 超過率 | timeout < 1% | `tunnel.errors.connect_timeout` | W | 未 | **P1** |
| **TUN-H07** | cloudflared 再起動 | `NRestarts` | 1h 内 +3 → W | `tunnel.systemd.restarts` | W | 已有 | **P0** |
| **TUN-H08** | Tunnel config drift | CF API config version vs `tunnel-ai-ingress.json` | 一致 | `tunnel.config.version` | W | 未 | **P1** |
| **TUN-H09** | Access Service Token | BFF → AI プロキシ成功 | probe 成功 | `tunnel.access.token_ok` | C | 部分 | **P1** |

**正本 ingress:** `infra/cloudflare/tunnel-ai-ingress.json`（v1.1: races/predictions → :8081）

---

### 2.4 Cloudflare 監視

| ID | 監視対象 | チェック方法 | 正常判定 | メトリクス | Alert | 状態 | v2 |
|----|----------|--------------|----------|------------|-------|------|-----|
| **CF-H01** | Pages 静的 | `GET https://expect-keiba.com/` | 200 | `cf.pages.static.ok` | C | 部分 | **P0** |
| **CF-H02** | Pages Functions | `GET /api/health` | `ok=true` | `cf.pages.functions.ok` | C | 已有 | **P0** |
| **CF-H03** | Deployment SHA | wrangler / Dashboard API | 意図 tag/commit | `cf.pages.deploy.sha` | W | 手動 | **P1** |
| **CF-H04** | Workers 5xx 率 | Logpush / Analytics | < 1%（15 min） | `cf.workers.error_rate` | C | 未 | **P1** |
| **CF-H05** | Workers p95 | Analytics | < 3 s（health） | `cf.workers.latency.p95_ms` | W | 未 | **P2** |
| **CF-H06** | Tunnel コネクタ | CF Zero Trust Dashboard / API | connected | `cf.tunnel.connector.connected` | C | 未 | **P0** |
| **CF-H07** | DNS | `ai.expect-keiba.com` CNAME | resolve OK | `cf.dns.ai.ok` | C | 手動 | **P1** |
| **CF-H08** | Secrets 存在 | `PI_BASE_URL`, `OPS_MONITOR_KEY` 等 | 設定済 | `cf.pages.secrets.configured` | C | 手動 | **P1** |
| **CF-H09** | Rate limit / WAF | CF Security Events | 異常スパイクなし | `cf.security.blocked` | I | 未 | **P2** |

---

### 2.5 Error Alert

| ID | 監視対象 | 条件（設計） | 深刻度 | 通知 | 状態 | v2 |
|----|----------|--------------|--------|------|------|-----|
| **ALT-E01** | BFF 5xx | `/api/*` 5xx 3回/5min | Critical | Slack | 未 | **P0** |
| **ALT-E02** | PI 到達不可 | PI-H02/H03 連続失敗 3min | Critical | Slack | 未 | **P0** |
| **ALT-E03** | Tunnel 切断 | TUN-H02 失敗 + local OK | Critical | Slack | 部分 | **P0** |
| **ALT-E04** | Prediction 全失敗 | 開催日 `prediction_available=false` 100% | Critical | Slack | 未 | **P0** |
| **ALT-E05** | PI systemd down | PI-H01 inactive | Critical | Slack | 未 | **P0** |
| **ALT-E06** | Latency 劣化 | LAT-P02 p95 > 10s が 15min | Warning | Slack | 未 | **P1** |
| **ALT-E07** | features_unavailable 急増 | PI-H06 +20pt | Warning | Slack | 未 | **P1** |
| **ALT-E08** | Result Automation | RA issues 非空 | Warning | Slack | 部分 | **P1** |
| **ALT-E09** | ETL 失敗率 | > 20% | Warning | Slack | 部分 | **P2** |
| **ALT-E10** | 計画メンテ | `OPS_CLOSED` 意図 ON | Info | Slack | 部分 | **P1** |

**既存:**

| 資産 | パス |
|------|------|
| Incident ログ | `var/ops/incidents.jsonl`（`expect-ops-incident/1.0`） |
| Monitor レポート | `var/ops/monitor-latest.json` |
| Alert 定義（win5-ai） | `/v1/admin/monitoring` alerts[] |

**v2 統合:** Alert ID を `expect-ops-alert/1.0` スキーマに統一。

---

### 2.6 Slack 通知

| ID | イベント | チャンネル（設計） | ペイロード | 状態 | v2 |
|----|----------|-------------------|------------|------|-----|
| **SLK-N01** | Critical Alert | `#expect-ops-critical` | Alert ID + 要約 + Runbook link | 未 | **P0** |
| **SLK-N02** | Warning Alert | `#expect-ops-warning` | 同上 | 未 | **P0** |
| **SLK-N03** | Recovery | `#expect-ops-warning` | 「復旧」+ 継続時間 | 未 | **P1** |
| **SLK-N04** | 日次ダイジェスト | `#expect-ops-daily` | 可用性・latency・PI 成功率 | 未 | **P1** |
| **SLK-N05** | デプロイ通知 | `#expect-ops-info` | Pages/EC2 SHA | 未 | **P2** |

**設計方針:**

- Webhook URL は **Secrets のみ**（Pages / EC2 env）
- 15 min 抑制（同一 Alert ID）
- メンテ中は SLK-N01/N02 抑制（v1.0 §3.5 継承）

---

### 2.7 JSON Metrics

| ID | メトリクスストリーム | 出力元 | スキーマ | ローテーション | 状態 | v2 |
|----|---------------------|--------|----------|----------------|------|-----|
| **MET-J01** | API latency | win5-ai `performance.py` | ad-hoc | `metrics.jsonl` | 部分 | **P0** |
| **MET-J02** | BFF probe | `/api/ops/monitor` 拡張 | `expect-ops-metrics/1.0` | Workers Logpush | 未 | **P0** |
| **MET-J03** | EC2 monitor | `monitor-prod.mjs` → `monitor-latest.json` | 部分 | 上書き | 部分 | **P0** |
| **MET-J04** | PI health | 新規 PI probe script | `expect-ops-metrics/1.0` | `pi-metrics.jsonl` | 未 | **P0** |
| **MET-J05** | Prediction quality | BFF meta `engine_source` 集計 | `expect-ops-metrics/1.0` | 日次 | 未 | **P1** |
| **MET-J06** | Tunnel route | per-route latency/error | `expect-ops-metrics/1.0` | jsonl | 未 | **P1** |
| **MET-J07** | Incident | `incidents.jsonl` | `expect-ops-incident/1.0` | append | 已有 | **P0** |

**統一 JSON 行スキーマ（設計）:**

```json
{
  "schema_version": "expect-ops-metrics/1.0",
  "ts": "2026-07-21T13:00:00.000Z",
  "source": "ec2-monitor|bff-probe|pi-probe",
  "metric": "latency.pi.prediction.tunnel.p95_ms",
  "value": 8420,
  "unit": "ms",
  "labels": {
    "env": "production",
    "route": "/v1/predictions",
    "race_id": "2026-07-25-01-06"
  },
  "status": "ok"
}
```

---

### 2.8 Grafana 対応

| ID | 対象 | データ源 | Grafana パネル | 状態 | v2 |
|----|------|----------|----------------|------|-----|
| **GRF-D01** | PI Health Overview | MET-J04 + PI-H* | Stat + Time series | 未 | **P1** |
| **GRF-D02** | Prediction Latency | LAT-P* | Heatmap / p95 graph | 未 | **P1** |
| **GRF-D03** | Tunnel Routes | TUN-H03/H04 + MET-J06 | Status map | 未 | **P1** |
| **GRF-D04** | Cloudflare Edge | CF-H* / CF Analytics | Table | 未 | **P2** |
| **GRF-D05** | BFF / Pages | CF Workers + MET-J02 | RED metrics | 未 | **P2** |
| **GRF-D06** | Incidents | MET-J07 | Annotation + table | 未 | **P1** |
| **GRF-D07** | SLO Burn | LAT-P02 + ALT-E06 | SLO dashboard | 未 | **P2** |

**Grafana 接続方式（設計・PI 非変更）:**

| 方式 | 説明 | 推奨 |
|------|------|------|
| **A. JSONL + Promtail/Loki** | EC2 `metrics.jsonl` tail | Phase 1 |
| **B. Prometheus scrape** | 新規 `GET /v1/admin/ops/metrics`（win5-ai）| Phase 2 |
| **C. Cloudflare Logpush → S3 → Grafana** | Workers ログ | Phase 2 |

---

## 3. レイヤ別 監視対象サマリー

| レイヤ | コンポーネント | 監視 ID 数 | P0 | 既存 probe |
|--------|----------------|-----------|-----|------------|
| **PI API** | `:8081` pi-keibanet-api | 10 | 6 | 手動 smoke |
| **BFF** | Pages Functions | 8 | 4 | `/api/health`, `/api/ops/monitor` |
| **Tunnel** | cloudflared + ingress | 9 | 5 | 間接 health |
| **Cloudflare** | Pages / DNS / Tunnel CF | 9 | 3 | 部分 |
| **EC2 win5-ai** | `:8000` expect-ai | 12 | 2 | monitor-prod |
| **Latency** | 横断 | 7 | 4 | latency_ms 部分 |
| **Alert** | 横断 | 10 | 5 | incidents.jsonl |
| **Notification** | Slack | 5 | 2 | なし |
| **Metrics** | JSON | 7 | 4 | metrics.jsonl |
| **Grafana** | Dashboard | 7 | 0 | なし |

**合計監視項目: 84**（うち P0: **31**）

---

## 4. ユーザー追加候補 × 監視 ID マッピング

| 追加候補 | 主要監視 ID | Dashboard |
|----------|-------------|-----------|
| **PI API Health Dashboard** | PI-H01〜H10 | GRF-D01, ops.html PI パネル |
| **Prediction Latency** | LAT-P01〜P07 | GRF-D02 |
| **Tunnel 監視** | TUN-H01〜H09 | GRF-D03 |
| **Cloudflare 監視** | CF-H01〜H09 | GRF-D04, GRF-D05 |
| **Error Alert** | ALT-E01〜E10 | GRF-D06 annotations |
| **Slack 通知** | SLK-N01〜N05 | — |
| **JSON Metrics** | MET-J01〜J07 | 全 Grafana の入力 |
| **Grafana 対応** | GRF-D01〜D07 | Grafana Cloud / 自前 |

---

## 5. プローブ順序（v2 障害切り分け）

```text
1. CF-H01 Pages 静的          → CDN / DNS
2. CF-H02 BFF /api/health     → Functions
3. TUN-H02 Tunnel health      → cloudflared
4. PI-H02 PI local health     → expect-pi-keibanet-api
5. PI-H03 PI tunnel health    → ingress :8081 ルート
6. TUN-H03/H04 route 個別     → path ルーティング
7. LAT-P02 Prediction latency → CE / FeatureLoader
8. PI-H05 prediction_available → 業務品質
9. win5-ai /health            → legacy 経路
10. ALT → Slack
```

---

## 6. SLO 草案（v2）

| SLO | 対象 | 目標 | 測定 |
|-----|------|------|------|
| **Availability — PI** | PI-H02 + PI-H03 | 99.5% / 30d | probe 成功率 |
| **Availability — BFF** | CF-H02 | 99.9% / 30d | /api/health |
| **Latency — Prediction** | LAT-P02 | p95 < 10 s | 5 min 窓 |
| **Latency — Catalog** | LAT-P05 | p95 < 5 s | 5 min 窓 |
| **Quality — Prediction** | PI-H05 | 開催日 available ≥ 90% | 日次 |

---

## 7. v1.0 → v2 差分（監視拡張）

| 領域 | v1.0 | v2 追加 |
|------|------|---------|
| Prediction 経路 | win5-ai :8000 中心 | **PI :8081 明示監視** |
| Race Catalog | 間接 | **PI /v1/races 専用 probe** |
| Tunnel | health 間接 | **ingress ルート別** |
| Cloudflare | 手動 | **CF API / Analytics 自動** |
| Metrics | win5-ai jsonl | **統一スキーマ + BFF + PI** |
| Alert | 手動 + jsonl | **自動閾値 + Slack** |
| Dashboard | ops.html 簡易 | **PI Health + Grafana** |

**変更禁止（継承）:**

- PI API レスポンス契約
- v1.1 Baseline 挙動（Flag OFF = 現行）
- KI-01: mock_fallback 絶対値での Critical 禁止（v1.1 は PI 経路で mock 廃止済み → **`engine_source=pi` 監視に置換**）

---

## 8. 実装フェーズ（設計のみ）

| Phase | 内容 | コード |
|-------|------|--------|
| **Phase 1** | PI probe 追加（monitor-prod）、MET-J04、ALT-E02/E05、SLK-N01 | 要承認 |
| **Phase 2** | BFF /api/ops/monitor PI 拡張、ops.html PI Dashboard、JSON 統一 | 要承認 |
| **Phase 3** | Slack 全般、Grafana Loki 接続、CF API | 要承認 |
| **Phase 4** | SLO dashboard、日次ダイジェスト、自動 Runbook link | 要承認 |

---

## 9. 関連文書・既存資産

| 文書 / 資産 | パス |
|-------------|------|
| v1.0 監視設計 | `docs/ops/v1.0-ops-monitoring-design.md` |
| OPS Monitor | `docs/ops/ops-monitor.md` |
| Monitoring 項目 | `docs/ops/monitoring.md` |
| PI 本番レポート | `docs/ops/pi-keibanet-api-v1-production-report-2026-07-21.md` |
| Tunnel ingress | `infra/cloudflare/tunnel-ai-ingress.json` |
| monitor-prod | `scripts/ops/monitor-prod.mjs` |
| opsMonitor | `functions/_lib/opsMonitor.js` |
| metrics.jsonl | `services/win5-ai/app/ops/performance.py` |
| v1.1 Release | `docs/releases/v1.1.md` |

---

## 10. 実装前チェックリスト

- [x] 本監視対象一覧承認（Operations Phase 1 着手）
- [x] P0 項目のうち Phase 1 範囲（PI-H01/H02/H03 · MET-J04 · ALT-E02/E05 · SLK-N01）実装
- [x] Phase 2（Dashboard 拡張 · Metrics 集約 · Incident/Alert 可視化 · JSON 統一）実装
- [x] Phase 3（Dashboard 最終 · Inventory · Slack N01/N02/N03 · Docs · Final Report）実装
- [x] Slack webhook 設計 / 任意 Secrets（未設定 no-op）
- [x] Grafana / Loki 接続レシピ（prepared · Promtail example）
- [ ] PI probe サンプル race_id 固定（開催日カレンダー連動）— 任意後続
- [ ] SLO 閾値合意 / Phase 4 SLO Burn — 任意後続

---

**Status:** **Version 2 Operations 正式クローズ**  
**Final Report:** [`docs/releases/v2-operations-final-report.md`](./v2-operations-final-report.md)  
**Phase 1:** [`docs/ops/v2-operations-phase1-report.md`](../ops/v2-operations-phase1-report.md)  
**Phase 2:** [`docs/ops/v2-operations-phase2-report.md`](../ops/v2-operations-phase2-report.md)  
**Phase 3:** [`docs/ops/v2-operations-phase3-report.md`](../ops/v2-operations-phase3-report.md)  
**構成図最終:** [`docs/ops/v2-operations-architecture-final.md`](../ops/v2-operations-architecture-final.md)

