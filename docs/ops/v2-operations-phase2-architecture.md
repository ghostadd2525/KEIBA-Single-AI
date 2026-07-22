# Version 2 Operations — Phase 2 監視構成図

Phase 1 構成を拡張。Dashboard 集約・Metrics / Alert / Incident 可視化を追加。

```text
[Browser / Ops · Flag v2_ops_dashboard]
      │
      ├─ GET /api/health                 (+ additive pi)     … Phase 1
      ├─ GET /api/ops/dashboard          ★ Phase 2
      │     auth + admin + Flag ON
      │     → metrics / alerts / incidents / pi probes
      └─ GET /api/ops/monitor            (+ metrics/alerts/incidents JSON 統一)
              │
     Cloudflare Pages (BFF)
              │
     ┌────────┴────────┐
     │ PI_BASE_URL     │ AI_BASE_URL
     ▼                 ▼
 Cloudflare Tunnel
     ├─ → :8081  expect-pi-keibanet-api
     └─ → :8000  expect-ai

EC2 timer: monitor-prod.mjs（Phase 1）
  ├─ PI-H01/H02/H03
  ├─ MET-J04  pi-metrics.jsonl
  ├─ ALT-E02/E05 → incidents.jsonl
  └─ SLK-N01 Slack（任意）

[Phase 2 データフロー]
  runAllProbes()
       ↓
  buildDashboardPayload()
       ├─ metrics   expect-ops-metrics/1.0 集約（MET-J02）
       ├─ alerts    ALT-E* 可視化
       ├─ incidents expect-ops-incident/1.0 スナップショット
       └─ pi        probe 単位表示改善
```

**Flag OFF:** `opsV2Root` 非表示 · `/api/ops/dashboard` → 404 `FEATURE_DISABLED` · 基本 8 カードのみ（v1.1 恒等）。

Grafana / Loki / Slack 全般は **Phase 3**。
