# Phase UI4 — State Diagram

```mermaid
stateDiagram-v2
  [*] --> Loading: open race detail
  Loading --> CachedReady: prefetch Ready Bundle
  Loading --> Pending: HTTP 202 PREDICTION_PENDING
  Loading --> Ready: HTTP 200 PredictionBundle
  Loading --> Error: 4xx/5xx/timeout

  CachedReady --> Pending: network still pending
  CachedReady --> Ready: network Ready Bundle

  Pending --> Pending: retry 8s (attempt < 15)
  Pending --> Ready: HTTP 200 PredictionBundle
  Pending --> Exhausted: attempt >= 15
  Pending --> Error: transport failure

  Exhausted --> Loading: manual retry
  Ready --> [*]: prediction-bind applied
  Error --> [*]
```

| State | User-facing | validatePredictionBundle | prediction-bind |
|---|---|---|---|
| Loading | skeleton | no | no |
| Pending | AI予想を生成しています | **no** | no |
| Ready | AI 予想 UI | yes | yes |
| Exhausted | 時間超過 + 再読み込み | no | no |
| Error | 既存エラー | no | no |

詳細フロー: [v109-ui4-pending-state-flow.md](./v109-ui4-pending-state-flow.md)
