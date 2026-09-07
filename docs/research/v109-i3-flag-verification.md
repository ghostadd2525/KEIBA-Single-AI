# Phase I3 — Flag Verification

**Date:** 2026-07-29

---

## Matrix

| Flag `single_ai_detail` | 詳細取得経路 | 期待 |
|---|---|---|
| **false**（default） | `Prediction.getWithMeta` のみ | 従来と同一 |
| **true** · core なし | `/api/single/detail` → Prediction fallback | 表示継続 · `detail_source=prediction_fallback` |
| **true** · core 注入 | Single → UI1 Mapper → Bundle | `detail_source=single` |
| **true** · Timeout/Error | catch → Prediction | Rollback 相当 |

## Evidence（静的）

- DEFAULTS / beta.json: `single_ai_detail: false`
- `single-detail.js`: `flagOn()` で分岐
- unittest `test_i3_detail_wiring_audit.py`

## Ops 切替

`public/config/beta.json`（および配信先 beta）で `"single_ai_detail": true`。  
一覧用 beta キーは新設しない。
