# Version 2 Operations — 監視構成図（最終版）

**Status:** CLOSED（Phase 1–3）  
**Flag:** `v2_ops_dashboard`（既定 false · OFF ≡ v1.1）

```text
[Browser · ops.html]
  │  v11_ops_dashboard → 入場
  │  v2_ops_dashboard  → Overview / PI / Probes / Metrics /
  │                      Alerts(+Runbook) / Incidents /
  │                      Inventory / Slack status
  ├─ GET /api/health                 (+ additive pi)
  └─ GET /api/ops/dashboard ★        auth + admin + Flag
         │
         ├─ runAllProbes()
         ├─ buildDashboardPayload()  expect-ops-dashboard/1.0
         │     metrics · alerts · incidents · inventory · overview
         └─ dispatchAlerts()         SLK-N01/N02（Secrets 任意）

GET /api/ops/monitor（OPS_MONITOR_KEY）
  └─ 同一 probe + 集約 JSON + Slack dispatch

Cloudflare Pages (BFF)
  ├─ PI_BASE_URL  → Tunnel → :8081  pi-keibanet-api
  └─ AI_BASE_URL  → Tunnel → :8000  expect-ai

EC2 expect-ops-monitor.timer
  └─ monitor-prod.mjs (phase v2-ops-phase3)
        ├─ PI-H01/H02/H03 · TUN · Python · BFF
        ├─ MET-J04 → pi-metrics.jsonl
        ├─ incidents.jsonl (+ alert_id)
        └─ Slack Critical/Warning/Recovery

[Observability prepared]
  Promtail example → Loki（GRF-D01）
  infra/observability/promtail-ops-metrics.example.yml
```

**非対象（継承）:** Prediction API / RaceCardSummary / Accuracy / UI Enhancement / Explainability

**Addendum:** Race Refresh / Shadow / Production 切替ゲートは  
[`v2-operations-race-refresh-addendum.md`](./v2-operations-race-refresh-addendum.md) を正とする。
