# Phase UI4 — Production Verification Report

**Date:** 2026-07-29 JST  
**Environment:** **Production** (`https://expect-keiba.com`)  
**Deploy:** `npm run deploy:pages`（Uploaded **1 file** = `public/race.html`）  
**Deployment ID:** `4f6ece3a-3b4f-4e14-9b0e-e96f98ea26ee`  
**pages.dev:** `https://4f6ece3a.keiba-single-ai.pages.dev`  
**Source label:** `c6b3171` + dirty (`--commit-dirty=true`)

---

## Verdict

| Check | Result |
|---|---|
| PENDING → 契約エラーが出ない | **PASS** |
| PENDING → 「AI予想を生成しています」 | **PASS** |
| Skeleton 維持 | **PASS** |
| Retry（≈8s 再取得） | **PASS** |
| READY → prediction-bind | **PASS** |
| 一覧 / Race List Cache / Prefetch 非破壊 | **PASS** |
| Console error | **PASS**（なし） |

**UI4 Production: GO**  
**Single AI V1 UI 系不具合（PENDING 契約誤検知）: CLOSED**

---

## Checklist

| Item | Evidence |
|---|---|
| HTTP 202 | `GET /api/predictions/2026-08-01-01-02` → **202** `PREDICTION_PENDING` |
| HTTP 200 | `GET /api/predictions/2026-07-26-01-11` → **200** Bundle |
| Retry | Performance resource delta +1 / 9s on PENDING page |
| Timeout | 既存 14s `withTimeout` 維持（本検証で強制発火なし） |
| Manual Reload | Exhausted 時 UI に「再読み込み」ボタンあり（コード確認） |
| Rollback | 直前 Deployment `ff8b2de6-…` へ Pages rollback 可能 |
| Console Error | 検証中 `console.error/warn` 捕捉なし |
| Network | `artifacts/ui4/network-capture.json` |

---

## PENDING race `2026-08-01-01-02`

| Expectation | Observed |
|---|---|
| 契約エラーカード無し | `contract_error_present: false` |
| Pending 文言 | `AI予想を生成しています` / `準備ができ次第、自動で更新します。` |
| `data-pending-state=1` | present |
| Skeleton | marks loading / honmei `is-loading` / pace「読み込んでいます」 |
| Screenshot | `artifacts/ui4/after-pending-2026-08-01-01-02.png` |

## READY race `2026-07-26-01-11`

| Expectation | Observed |
|---|---|
| 本命描画 | ルブリアン |
| 印・対抗穴 | 表示あり |
| Pending / Contract error | なし |
| Screenshot | `artifacts/ui4/after-ready-2026-07-26-01-11.png` |

## List / Cache / Prefetch

| Surface | Observed |
|---|---|
| `races.html` に UI4 Pending コード混入 | **false** |
| `/api/race-cards?date=2026-07-26` | HTTP 200 |
| `/api/predictions?date=2026-07-26` | HTTP 200 |
| 一覧 DOM race items | **36** 件（例: `2026-07-26-01-01`…） |

---

## Before / After

| | Before UI4 | After UI4（本番） |
|---|---|---|
| HTTP 202 | 「PredictionBundle が契約と一致しません」 | 「AI予想を生成しています」 |
| Guard | envelope を validate | **pending では実行しない** |
| READY 200 | 正常 | 正常（回帰なし） |

Before 根拠: Production Reflection Audit（同 race で契約エラーカード確認済み）  
After 根拠: 本レポート + screenshots

---

## Artifacts

- `docs/research/artifacts/ui4/after-pending-2026-08-01-01-02.png`
- `docs/research/artifacts/ui4/after-ready-2026-07-26-01-11.png`
- `docs/research/artifacts/ui4/list-races-2026-07-26.png`
- `docs/research/artifacts/ui4/network-capture.json`
- `docs/research/artifacts/ui4/console-log.json`
