# Phase UI4 — Retry Flow

**Parent:** [v109-ui4-pending-state-flow.md](./v109-ui4-pending-state-flow.md)

## Parameters

| Name | Value | Rationale |
|---|---|---|
| `PENDING_RETRY_MS` | 8000 | Align with `ExpectRealtimeSync` active tick |
| `PENDING_MAX_ATTEMPTS` | 15 | ≈120s wall clock before Exhausted |
| Fetch timeout | 14000 | Existing `withTimeout` |

## Sequence

```
attempt = 0
on Pending:
  show 「AI予想を生成しています」
  if attempt >= 15 → Exhausted (manual retry)
  else:
    attempt += 1
    sleep 8s
    fetch getWithMeta(race_id)
      Pending → loop
      Ready   → clear timer → Contract Guard → prediction-bind
      Error   → clear timer → Error State
```

## Cleanup

- `pagehide` → `clearPendingRetry()`
- Ready / Error / Exhausted → clear timer + pending card
