# Version 5 — Conversation Metrics Dashboard Specification

## Surface

1. **Ops UI:** `public/ops.html` → section **Conversation Metrics**
2. **API:** `GET /api/ops/conversation`（BFF）→ AI `GET /v1/ops/conversation/dashboard`

## Categories (required)

| Category | Cards / fields |
|----------|----------------|
| Conversation | requests, error_rate, p50/p95/p99, chat/review/explain counts |
| Ollama | model_name, p95 latency, timeouts, errors |
| Knowledge | search_count, hit/miss, top_k, health probe latency |
| Security | block/allow, block_reason map (table/alerts) |

## Health strip

Component OK/NG:

- Conversation API
- Ollama
- Knowledge Runtime
- Tool Manager
- Prediction Connector

## Alerts table

Shows ALT-C01 … ALT-C04 when active.

## Access

- Requires existing ops flags (`v11_ops_dashboard` / `v2_ops_dashboard`) and admin gate already used by `ops.html`.
- Product UI (`chat.html` 等) は変更しない。
