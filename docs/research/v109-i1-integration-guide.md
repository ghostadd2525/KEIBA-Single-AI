# Version109 Phase I1 — Integration Guide

**Audience:** 既存サイト / BFF 実装者  
**Goal:** サイト側変更量を最小化して Single AI を呼ぶ

---

## 1. 推奨接続（最小変更）

1. **Prediction 画面はそのまま**（`ExpectApi.Prediction` → `/api/predictions`）
2. Single AI が必要な箇所だけ **opt-in**:
   - script: `assets/api/single.js`
   - `ExpectApi.Single.call({ race_id, core_payload, force })`
3. Secrets: 既存 `AI_BASE_URL` / `AI_API_KEY` を再利用（新規必須シークレットなし）

ブラウザは `X-AI-Key` を持たない。BFF が付与する。

---

## 2. Authentication

| 区間 | 認証 |
|---|---|
| Browser → BFF | `Authorization: Bearer`（既存 `expect_access_token_v1`） |
| BFF → Python | `X-AI-Key: $AI_API_KEY` |
| Optional | CF Access Service Token（既存 Tunnel 設定） |

---

## 3. Race ID Routing

サイトの `race_id`（例: `20260719_hanshin_11`）をそのまま使う。

- BFF: `normalizeRaceIdYear`（既存）
- Python: path `/v1/site/single/{race_id}` + body.race_id 一致検証

---

## 4. Request 必須フィールド

| Field | Required | Note |
|---|---|---|
| `race_id` | Yes | path または body |
| `core_payload` | Yes（I1） | Core PROMOTE まで必須。サイトは Core を捏造しない |
| `options.include_*` | No | Consumer flags と併用 |
| `force` | Shadow only | Production 既定禁止 |
| `timeout_ms` | No | default 12000 |

---

## 5. Timeout

- BFF `aiFetch` default 12s
- Override: body.timeout_ms または `X-Request-Timeout-Ms`
- 超過: HTTP **504** `TIMEOUT`

---

## 6. Errors（主要）

| code | HTTP | 意味 |
|---|---|---|
| `CORE_PAYLOAD_REQUIRED` | 400 | core 未供給 |
| `BAD_RACE_ID` | 400 | race_id 不正 |
| `RACE_ID_MISMATCH` | 400 | path/body/core 不一致 |
| `UNAUTHORIZED` | 401 | API key |
| `CONSUMER_DISABLED` | 503 | Flag OFF（`force` 未指定） |
| `TIMEOUT` | 504 | 時間超過 |
| `AI_BASE_URL_MISSING` | 503 | BFF 未設定 |

---

## 7. Version

- `GET /api/single/version` → `api_version: i1/1.0`
- Response `data.schema`: `site-integration/single/v1`
- Nested: `data.single.schema` = `consumer-api/single/v1`
