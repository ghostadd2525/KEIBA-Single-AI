# Phase R1 — Live Rehearsal Report

**Date:** 2026-07-29  
**Environment:** Production `expect-keiba.com`  
**Actor:** ADMIN（Research Week bypass）  
**Target:** `race.html` only · list **out of scope**

---

## Procedure（Production と同手順）

1. Deploy I3+I4 with Flag **OFF** — baseline
2. Set `ui_features.single_ai_detail: true` + deploy — limited ON
3. Exercise detail path
4. Set Flag **false** + deploy — restore

## Results

| Check | Status | Evidence |
|---|---|---|
| Feature Flag ON（beta） | **PASS** | `config/beta.json` → true（一時） |
| FE Flag readable | **PASS**（cache-bust 後） | `ExpectUiFeatures.enabled('single_ai_detail')===true` |
| Single API 呼出 | **PASS** | `POST /api/single/detail/2026-07-26-01-11` in page resources + manual |
| Prediction Fallback | **PASS** | `fallback_reason=CORE_PAYLOAD_REQUIRED` · Bundle 表示継続 |
| UI render（detail） | **PASS** | 本命・印・説明が表示（レイアウト非変更） |
| Timeout path | **PASS**（I5 harness）· live 未強制 | 本番では Abort 未注入 |
| Rollback Flag OFF | **PASS** | 最終 beta false |
| Alert surface | **PASS** | probe present · deferred（sample 不足は Flag OFF 正常） |
| Metrics | **PARTIAL** | 記録コード有効 · Worker isolate 分散で snapshot が 0 になり得る |
| Dashboard | **PASS** | monitor に `single_detail` / `single_detail_ops` |
| List / Cache | **PASS** | races に Single なし · cache v4 |

## Issues found & mitigated

| Issue | Mitigation |
|---|---|
| `ui-features.js?v=11` CDN が旧 DEFAULTS（Flag キー欠落） | `?v=12` |
| Flag 判定が beta load 前に走り OFF 扱い | `ready()` 後判定（`single-detail.js?v=2`） |

## Residual

- Core payload なし → expected fallback（PROMOTE 前は想定内）
- Research Week 中 USER は OPS_CLOSED（ADMIN のみ rehearse）
- `/v1/site/health` probe が AI proxy Response（監視ノイズ）

## Duration Flag ON

限定デプロイ数回のみ。**最終状態は OFF。**
