# Version 2 — Architecture（最終構成図）

**Date:** 2026-07-22  
**Status:** Release Candidate  
**正本 RC:** [`v2-rc-report.md`](./v2-rc-report.md)

---

## 1. システム全体

```text
Browser (Expect Web)
  │
  ├─ races.html / race.html / chat.html / ops.html
  │     Flags: v2_race_list_ui · v2_explain · v2_ops_dashboard
  │
  ▼
Cloudflare Pages (BFF)
  ├─ GET /api/predictions*     → PI_BASE_URL  (/v1/predictions)     [v1.1]
  ├─ GET /api/races*           → PI_BASE_URL  (/v1/races)           [v1.1]
  ├─ GET /api/race-cards*      → PI + summary 投影                  [v2 · Flag]
  ├─ GET /api/health           → BFF + additive pi                  [v2 Ops]
  ├─ GET /api/ops/monitor      → probes + metrics/alerts            [v1.1+v2]
  ├─ GET /api/ops/dashboard    → admin + v2_ops_dashboard           [v2]
  ├─ Kaoba / Conversation      → explain_pick（v2_explain）         [v2]
  └─ explainBuilder            → Bundle.explain 2.1                 [v2]
        │
        ▼
Cloudflare Tunnel (ai.expect-keiba.com)
  ├─ /v1/races* · /v1/predictions* · PI /health → :8081  pi-keibanet-api
  └─ /*（admin / conversation 等）               → :8000  expect-ai (win5-ai)
        │
        ▼
EC2
  ├─ expect-pi-keibanet-api (:8081)
  │     └─ AI Core（WIN5）  PE-V2-A / Explain Flag
  ├─ expect-ai (:8000)
  ├─ cloudflared-expect-ai
  └─ expect-ops-monitor.timer → monitor-prod.mjs
        ├─ PI-H01/H02/H03 · Tunnel · Python · BFF
        ├─ pi-metrics.jsonl · incidents.jsonl
        └─ Slack SLK-N01/N02/N03（任意）
```

---

## 2. Accuracy スタック（採用構成）

```text
Phase255 Final（V1.1 Baseline）
  └─ PE-V2-A ON     ← 採用（Hit 218）
  └─ RP-V2-* OFF    ← 不採用
  └─ CE-V2-* OFF    ← 不採用
  └─ Delete Boundary 不変
```

---

## 3. Explainability データフロー

```text
AI Core explain_payload (+ product_stages)
  → PI pass-through（EXPLAIN_V2_ENABLED）
  → BFF explainBuilder → PredictionBundle.explain 2.1
  → Web race.html（v2_explain）
  → Kaoba / Conversation explain_pick（context.v2_explain）
```

---

## 4. UI Enhancement データフロー

```text
Flag OFF:  ExpectApi.Prediction.list → raceCardHtml          （v1.1）
Flag ON:   ExpectApi.RaceCards.list  → raceCardSummaryHtml
             + URL ?date= + Search + Favorites summary
```

---

## 5. Operations 監視レイヤ

```text
[Probes]  EC2 timer / BFF /ops/monitor|/dashboard /api/health
    ↓
[Metrics] expect-ops-metrics/1.0 → jsonl + Logpush
    ↓
[Dashboard] ops.html（v2_ops_dashboard）
    ↓
[Alert]   ALT-E* → Slack / incidents.jsonl / Runbook
    ↓
[Prepared] Promtail → Loki（本番接続は任意）
```

詳細: `docs/ops/v2-operations-architecture-final.md`

---

## 6. 契約境界（非破壊）

| 境界 | 方針 |
|------|------|
| PI HTTP 契約 | 変更しない |
| PredictionBundle 2.0 | 維持 · explain additive |
| RaceCardSummary | フィールド追加なし |
| Delete Boundary | Accuracy でも不変 |

---

## 7. 関連図・文書

| 文書 | パス |
|------|------|
| Ops 最終図 | `docs/ops/v2-operations-architecture-final.md` |
| Explain Final | `docs/releases/v2-explainability-final-report.md` |
| UI Final | `docs/releases/v2-ui-enhancement-final-report.md` |
| Accuracy Final | `docs/releases/v2-accuracy-final-report.md` |
