# Version 2 Operations — Phase 1 監視構成図

```text
[Browser / Ops]
      │
      ├─ GET /api/health          (+ additive pi)
      └─ GET /api/ops/monitor     (+ pi_health probe · metrics log)
              │
     Cloudflare Pages (BFF)
              │
     ┌────────┴────────┐
     │ PI_BASE_URL     │ AI_BASE_URL
     ▼                 ▼
 Cloudflare Tunnel (ai.expect-keiba.com)
     │                 │
     ├─ /health,/v1/* → :8081  expect-pi-keibanet-api   ← PI-H02/H03
     └─ /*            → :8000  expect-ai (win5-ai)

EC2 timer: expect-ops-monitor.timer
  └─ scripts/ops/monitor-prod.mjs
        ├─ PI-H01 systemctl  expect-pi-keibanet-api
        ├─ PI-H02 GET :8081/health
        ├─ PI-H03 GET PI_TUNNEL_PROBE_URL (optional)
        ├─ MET-J04 → var/ops/pi-metrics.jsonl  (expect-ops-metrics/1.0)
        ├─ ALT-E02 / ALT-E05 → incidents.jsonl (+ alert_id)
        └─ SLK-N01 Slack Critical (webhook 任意 · 15min 抑制)
```

Grafana / Loki 接続は Phase 1 では **JSONL 出力まで**（Promtail 接続は後続）。
