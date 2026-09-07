# Single Detail — Dashboard Design (I4)

**Product UI unchanged.** Ops surfaces only.

---

## Primary panel: Single Detail Ops

**Data:** `GET /api/ops/single-detail`  
**Also embedded:** `GET /api/ops/dashboard` → `data.single_detail` + check `single_detail_ops`

### Layout（logical）

```
┌─ Single Detail Ops ─────────────────────────────┐
│ Status: ok | deferred | degraded                 │
│ Flag path hits | Single success | Error FB       │
│ p50 / p95 latency                                │
│ Timeout % | HTTP error % | 5xx count             │
│ Fallback reasons (top)                           │
│ Active alerts: ALT-SD*                           │
│ Site health: /v1/site/health latency             │
└──────────────────────────────────────────────────┘
```

### KPI tiles

1. `requests_total`
2. `latency_ms_p95`
3. `rates.timeout`
4. `error_fallback` / `single_attempted`
5. `prediction_fallback`（件数）
6. `status_5xx`

### Alert strip

| Color | Meaning |
|---|---|
| Grey | deferred（sample不足） |
| Green | no alerts |
| Amber | warning only（SD01/04/05） |
| Red | critical（SD02/03） |

## Secondary: Live Monitor tab

Existing Operations Console **Live Monitor** continues to call `/api/ops/dashboard`.  
I4 adds `checks[].name === "single_detail_ops"` and merges SD alerts into `alerts[]`.

No change required to `race.html` / Prediction bind UI.

## Future（out of I4）

- Persist metrics to R2/KV for multi-isolate history
- FE beacon for true Flag ON page-view rate
- Dedicated ops.html panel widget（optional; design only here）
