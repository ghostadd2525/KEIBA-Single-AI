# Version109 Phase A1 — Service Integration

**Date:** 2026-07-29  
**Status:** **IMPLEMENTED**（Application facade）· Production Deploy = **別 Gate**  
**Parents:** Core Platform Version1 · Single AI Version1 · C1–C7 · ADR-011  
**Assumption:** AI Library（Consumer）完成済み。本フェーズは Application 化のみ。

---

## 目的

Single AI Version1 を **HTTP Application** として利用可能にする。

| 対象 | 対象外 |
|---|---|
| HTTP API / Validation / Serialization | Prediction |
| OpenAPI / Health / Metrics | Core |
| Logging / Error Handling / Config | Consumer ロジック変更 |
| Deployment 文書（非 Production） | Presentation / Ticket / Decision / Contract |

---

## REST API

| Method | Path | 説明 |
|---|---|---|
| GET | `/v1/single/health` | Service health + flags + version |
| GET | `/v1/single/metrics` | In-process request counters |
| GET | `/v1/single/openapi.json` | OpenAPI 3.0.3（raw JSON） |
| POST | `/v1/single/response` | Consumer response 組立（library 呼出） |

### POST `/v1/single/response`

```json
{
  "core_payload": { "...CoreRaceSemanticPayload..." },
  "options": {
    "include_tickets": false,
    "include_presentation": false,
    "locale": "ja"
  },
  "force": true
}
```

- `force` は Shadow harness 専用。Production 既定にしない。
- Flag OFF かつ `force=false` → `503 CONSUMER_DISABLED`
- Core / Prediction は変更しない。`core_payload` は request 供給（InMemoryCoreClient）

### Auth

既存 `X-AI-Key`（`AI_API_KEY`）。Application 側 `SINGLE_AI_REQUIRE_API_KEY`（default true）。

### Env

| Var | Default | 意味 |
|---|---|---|
| `SINGLE_AI_HTTP_ENABLED` | true | HTTP facade ON/OFF |
| `SINGLE_AI_REQUIRE_API_KEY` | true | API key 要求 |
| `SINGLE_AI_DEFAULT_LOCALE` | ja | locale 既定 |
| `SINGLE_AI_MAX_BODY_BYTES` | 1048576 | body 上限 |
| `SINGLE_AI_SERVICE_VERSION` | a1/1.0 | OpenAPI/meta version |

Consumer flags（`W_CONSUMER_*`）は従来どおり。Application は書き換えない。

---

## コード

| Path | Role |
|---|---|
| `app/service_integration/` | Application layer |
| `app/main.py` | Route wiring only |
| `tests/service_integration/test_a1_service_integration.py` | A1 tests |

---

## 成果物マップ

| 成果物 | 文書 / 実装 |
|---|---|
| REST API | 本票 + handlers |
| OpenAPI | `GET /v1/single/openapi.json` · `openapi.py` |
| Health | `GET /v1/single/health` |
| Monitoring | `v109-a1-monitoring.md` · `/v1/single/metrics` |
| Deployment | `v109-a1-deployment.md`（Staging/Local） |
| Governance | `v109-a1-governance.md` |

---

## C7 Gap との関係

| C7 Blocker | A1 |
|---|---|
| HTTP route | **解消**（`/v1/single/*`） |
| Metrics | **部分解消**（in-process）。Alert / traffic-split は未 |
| Production Canary | **未実施**（別 Gate） |
