# Phase UI4 — Compatibility Report

**Date:** 2026-07-29  
**Change surface:** `public/race.html` only  
**Frozen:** Core / Consumer / Prediction engine / Contracts / Race List Cache

---

## Compatibility Matrix

| Consumer | Impact | Notes |
|---|---|---|
| `ExpectApi.Prediction.getWithMeta` | None | 既に `{ pending:true, bundle:null }` を返却 |
| `ExpectApi.SingleDetail.getWithMeta` | None | 同上（202 経路） |
| `ExpectContractGuard` | Safer | Pending では呼ばれない |
| `ExpectPredictionBind` | None | Ready Bundle のみ従来どおり |
| `ExpectRacePrefetch` | None | pending は put しない（既存） |
| Race List Cache | **None** | 非接触 |
| Contract schema | **None** | 変更なし |
| Prediction / Core / Consumer | **None** | 変更なし |

---

## Behavior Compatibility

| Scenario | Before | After |
|---|---|---|
| 200 Ready Bundle | bind | bind（同一） |
| 202 PENDING | Guard エラー（誤検知） | Pending UI + 8s retry |
| Prefetch Ready + network Pending | cache 表示後に Guard エラーになり得た | cache 維持 + Pending 表示 + retry |
| 401 | 再ログイン | 同一 |
| Timeout / 5xx | エラーカード | 同一 |
| Exhausted retries | （即 Guard 失敗） | 手動再読み込み |

---

## API Compatibility

- Request/Response schema: unchanged  
- HTTP 202 meaning: unchanged（client 解釈のみ修正）  
- Flag `single_ai_detail`: unchanged（OFF=Prediction / ON=SingleDetail）

---

## Regression Risks

| Risk | Mitigation |
|---|---|
| Infinite retry | Max 15 attempts |
| Timer leak | `pagehide` で clear |
| Double bind | Ready 時のみ `applyPredictionResult`；`aiApplied` 既存ガード |

---

## Verdict

**Compatible.** UI4 はクライアントの Pending 解釈修正のみ。  
本番で観測された「202 なのに契約不一致」は本修正の対象であり、Contract/API 変更は不要。
