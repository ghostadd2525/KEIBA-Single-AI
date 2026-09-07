# Phase R1 — Deployment Report

**Date:** 2026-07-29  
**Command:** `npm run deploy:pages`（`check:auth:prod` + `wrangler pages deploy public --project-name=keiba-single-ai --branch=main --commit-dirty=true`）  
**Auth check:** `EXPECT_ENV=production` · `AUTH_MODE=stub` · `ALLOW_STUB_AUTH=1` → **OK**

---

## Pre-deploy

| Check | Result |
|---|---|
| `single_ai_detail` local default | false |
| `race.html` SingleDetail wiring | present |
| `races.html` Single なし / cache v4 | present |
| I4 ops modules | present |

## Deploy sequence

1. **Flag OFF** initial — Success (`44885c02.keiba-single-ai.pages.dev`)
2. **Flag ON** limited rehearse — Success（一時）
3. Cache-bust + ready() fix — Success
4. **Flag OFF** final — Success（custom domain 確認 `single_ai_detail: false`）

## Post-deploy smoke（custom domain）

| Probe | Result |
|---|---|
| `GET /api/health` | 200 · `expect_env=production` · `allow_stub_auth=true` · status **degraded** |
| `GET /config/beta.json` | `single_ai_detail: false`（最終） |
| `race.html` | `single-detail.js?v=2` · `ui-features.js?v=12` |
| `races.html` | Single なし · `expect_race_list_cache_v4` |
| `GET /api/ops/monitor` | `single_detail_ops` **ok**（deferred / sample 0） |
| `GET /api/ops/single-detail`（ADMIN） | 200 · schema `expect-single-detail-ops/1.0` |

## Non-Single degraded（pre-existing / out of R1 freeze）

| Check | Note |
|---|---|
| result_automation | unhealthy（failed_latest） |
| prediction_api probe | AI proxy Response |
| conversation_api probe | timeout |
| ALT-E10 horse number | NOT_FOUND path |
| site_health（via SD probe） | AI proxy Response |

→ Single Detail 経路のリリース可否とは分離して記録。恒久 Flag ON 前に別途健全化推奨。

## Rollback

Flag OFF 再デプロイで製品経路は Prediction のみ（実施済み）。
