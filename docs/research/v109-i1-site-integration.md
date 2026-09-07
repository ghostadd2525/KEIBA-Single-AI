# Version109 Phase I1 — Existing Site Integration

**Date:** 2026-07-29  
**Status:** **IMPLEMENTED**（Web Integration）· Production cutover = **別 Gate**  
**Parents:** Core Platform Version1 · Single AI Version1 · A1 Service Integration  
**目的:** AI 改善ではなく、既存サイトから Single AI を呼び出せること。

---

## フロー

```text
既存サイト (ExpectApi.Single)
    ↓  same-origin Bearer
BFF /api/single/*
    ↓  X-AI-Key + timeout
HTTP /v1/site/*
    ↓
Single API (build_single_response)
    ↓  read-only
Core (core_payload 供給 / CoreClient)
```

`/api/predictions`（PredictionBundle）は **非変更・並存**。

---

## REST API

### Python（AI）

| Method | Path | 説明 |
|---|---|---|
| GET | `/v1/site/health` | Health |
| GET | `/v1/site/version` | Version |
| GET | `/v1/site/openapi.json` | OpenAPI |
| POST | `/v1/site/single` | race_id + core_payload → Single |
| POST | `/v1/site/single/{race_id}` | Path routing |

### BFF（既存サイト）

| Method | Path | 説明 |
|---|---|---|
| GET | `/api/single/health` | Health |
| GET | `/api/single/version` | Version |
| POST | `/api/single` | Site call |
| POST | `/api/single/:raceId` | Race ID routing |

### 対象項目

| 項目 | 実装 |
|---|---|
| Authentication | Browser Bearer → BFF; BFF → `X-AI-Key` |
| Race ID Routing | normalize + path `/…/{race_id}` |
| Error Handling | `CORE_PAYLOAD_REQUIRED` / `TIMEOUT` / `CONSUMER_DISABLED` 等 |
| Timeout | body `timeout_ms` + header `X-Request-Timeout-Ms`（default 12s） |
| Version | `/version` + meta.api_version `i1/1.0` |

---

## 禁止（遵守）

Prediction / Core / World / Consumer / Presentation / Ticket / Contract **変更なし**。

`core_payload` は I1 では **リクエスト必須**（Core PROMOTE 別 Gate までサイト側で発明しない）。

---

## 成果物

| 成果物 | Path |
|---|---|
| REST / 概要 | 本票 |
| OpenAPI | `GET /v1/site/openapi.json` |
| Integration Guide | `v109-i1-integration-guide.md` |
| Request Example | `v109-i1-request-example.json` |
| Response Example | `v109-i1-response-example.json` |
| Migration Guide | `v109-i1-migration-guide.md` |
| Governance | `v109-i1-governance.md` |

## コード

| Path | Role |
|---|---|
| `app/site_integration/` | Python Web facade |
| `functions/_lib/adapters/singleSiteAdapter.js` | BFF adapter |
| `functions/api/single/*` | BFF routes |
| `public/assets/api/single.js` | Opt-in ExpectApi.Single |
| `tests/site_integration/` | Unit tests |
