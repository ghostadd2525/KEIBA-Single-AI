# Version109 Phase A1 — Monitoring

**Date:** 2026-07-29  
**Scope:** Application-layer observability only. Production alert wiring = 別 Gate.

---

## Endpoints

| Path | Content |
|---|---|
| `GET /v1/single/health` | `status`, `http_enabled`, Consumer flags, version refs |
| `GET /v1/single/metrics` | `requests_total/ok/error`, `latency_ms_avg`, `by_path`, `uptime_sec` |

## Logging

Structured stdout lines prefixed `[single-ai-http]`:

- `response_ok` / `response_error` / `response_validation_error`
- `response_unauthorized` / `response_disabled` / `response_consumer_disabled`
- Includes flag snapshot + composer version info

## Existing platform metrics

`main.py` `_send` continues to call `record_timing("api", path, …)` for all routes including `/v1/single/*`.

## Out of scope (A1)

- Prometheus / Datadog exporters
- Alert rules / paging
- Traffic-split dashboards
- Production SLO burn alerts
