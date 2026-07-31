# Phase I3 — Rollback Verification

**Date:** 2026-07-29

---

## Immediate Rollback

| Step | Action | 効果 |
|---|---|---|
| 1 | `single_ai_detail: false`（beta.json） | 詳細が即 Prediction のみ |
| 2 | （任意）`W_CONSUMER_SINGLE_ENABLED=0` | Server Single 組立停止 |
| 3 | （任意）`SITE_SINGLE_HTTP_ENABLED=0` | Site HTTP 503 |

一覧 Cache 操作は不要・禁止。

## 検証観点

| 観点 | 期待 |
|---|---|
| Flag OFF 後の詳細 | Prediction Bundle 表示 |
| Flag ON 時の Single 障害 | Prediction fallback（画面継続） |
| 一覧 | 変化なし · Cache 維持 |
| 戻る / Race switch | 既存挙動（詳細のみデータ源差） |

## Evidence

- `single-detail.js` catch → `_predictionFallback`
- BFF: Single 失敗時も `ok: true` + Prediction bundle（表示維持）
- Audit test: list に single 非接続
