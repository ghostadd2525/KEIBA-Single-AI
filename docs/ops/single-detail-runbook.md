# Single Detail — Runbook (I4)

Parent: [Operation Guide](./single-detail-operation-guide.md)

## Quick checks

```bash
# Ops metrics + alerts (admin session cookie OR monitor key)
curl -sf -H "X-Ops-Monitor-Key: $OPS_MONITOR_KEY" \
  "https://<host>/api/ops/single-detail" | jq '.data.metrics,.data.alerts,.data.alert_eval'

# Embedded in full dashboard
curl -sf -H "X-Ops-Monitor-Key: $OPS_MONITOR_KEY" \
  "https://<host>/api/ops/monitor" | jq '.data.single_detail,.data.alerts'

# Site integration health (via AI base)
curl -sf "$AI_BASE_URL/v1/site/health" | jq .
```

Logs: filter Cloudflare / Pages logs for `[single-detail-ops]`.

Product rollback: set `single_ai_detail` **false**（I3）.

---

## ALT-SD01 — Latency p95 high

1. Confirm sample not dominated by cold starts（`requests_total`, `uptime_sec`）.
2. Check `/v1/site/health` and Python API load.
3. Inspect recent logs for high `latency_ms` with `detail_source=single`.
4. If Mapper slow: check `/v1/ui/prediction-bundle` separately.
5. Do **not** change Core/Consumer; ops restart / capacity only.

## ALT-SD02 — Timeout rate high

1. Confirm `fallback_reason=TIMEOUT` in logs / `by_fallback_reason`.
2. Verify tunnel / `AI_BASE_URL` / Access token.
3. Check EC2 `expect-ai` CPU and request queue.
4. Temporary mitigation: keep Flag **OFF** if production ON; users stay on Prediction.
5. Raise timeout only with explicit ops approval（default 12s BFF）.

## ALT-SD03 — 5xx observed

1. Count `status_5xx` and correlate log `http_status`.
2. Probe `/health`, `/v1/site/health`, Prediction API.
3. If BFF-only 5xx: check Pages Function errors.
4. Rollback Flag OFF if user-facing failures spike.

## ALT-SD04 — Error fallback rate high

1. Confirm `single_attempted` ≥ threshold（ignore expected no-core）.
2. Top reasons in `by_fallback_reason`（exclude `CORE_PAYLOAD_REQUIRED`）.
3. If `MAP_FAILED`: UI1 mapper / Bundle schema mismatch — investigate without UI layout change.
4. If `SINGLE_SITE_ERROR`: site assembly / Consumer path health.
5. Staging without core will show high **expected** fallback — not this alert.

## ALT-SD05 — HTTP error rate high

1. Compare `http_errors` vs `error_fallback`.
2. Follow ALT-SD02/SD03 if timeout/5xx dominate.
3. Ensure Prediction fallback still succeeds（user safety）.

## Incident severity → action

| Severity | Action |
|---|---|
| warning | Investigate within business hours; no Cutover |
| critical | Page on-call; consider Flag OFF; block Cutover |

## Cutover note

I2 remains **CUTOVER BLOCKED** until staging rehearse + alerts green under Flag ON with real core path. I4 wires alerts; Cutover is a **separate** re-evaluation.
