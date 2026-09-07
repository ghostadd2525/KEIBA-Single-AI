# Version109 Phase A1 — Deployment（Non-Production）

**Date:** 2026-07-29  
**Status:** Local / Staging 手順のみ。**Production Deploy = 別 Gate（未承認）**

---

## Local

```text
cd services/win5-ai
set AI_API_KEY=dev-key
set SINGLE_AI_HTTP_ENABLED=true
python -m app.main
```

Smoke:

```text
GET  /v1/single/health          (Header: X-AI-Key)
GET  /v1/single/openapi.json
POST /v1/single/response        body with core_payload + force=true
GET  /v1/single/metrics
```

## Staging（推奨設定）

| Setting | Value | Note |
|---|---|---|
| `SINGLE_AI_HTTP_ENABLED` | true | Facade ON |
| `W_CONSUMER_SINGLE_ENABLED` | false → shadow true | Flag Gate は C6 準拠 |
| `force` in clients | Shadow only | Production clients に載せない |
| Traffic split | **禁止** | C9 / Production Gate |

## Rollback（Application）

1. `SINGLE_AI_HTTP_ENABLED=0` → `/v1/single/response` returns 503  
2. または `W_CONSUMER_SINGLE_ENABLED=0`（library）  
3. Process restart 不要で facade 無効化可能（env 再読込はプロセス再起動前提の現状）

## Production

| Item | A1 |
|---|---|
| Deploy to Production | **禁止** |
| Canary traffic | **禁止** |
| Cutover | C9 + 明示承認後 |

Deployment artifact = 既存 `app.main` ThreadingHTTPServer プロセスにルート追加。別バイナリは作らない。
