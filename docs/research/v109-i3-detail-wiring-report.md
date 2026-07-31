# Phase I3 — Detail Wiring Report

**Date:** 2026-07-29  
**Status:** **IMPLEMENTED**（詳細のみ）· 一覧 **LOCK** · Cutover 既定 OFF  
**Parents:** I2 BLOCK · Race List Cache Product Requirement · UI1/UI2

---

## 目的達成

詳細画面のみ Feature Flag `single_ai_detail` で  
**Prediction ↔ Single AI（Bundle 供給）** を切替可能にした。  
一覧・Race List Cache は未変更。

---

## 配線

| 層 | Path | 役割 |
|---|---|---|
| Flag | `ui_features.single_ai_detail`（default **false**） | 詳細のみ |
| FE | `public/assets/api/single-detail.js` | Flag 分岐 + fallback |
| FE | `public/race.html` | `SingleDetail.getWithMeta` 呼び出し |
| Bind | `prediction-bind.js` | **描画非変更**（コメントのみ） |
| BFF | `GET/POST /api/single/detail/:raceId` | Single 試行 → Bundle / Prediction fallback |
| Adapter | `singleDetailAdapter.js` | core あり→Site+UI1 Mapper / なし→Prediction |

### Flag 挙動

```text
Flag OFF → ExpectApi.Prediction.getWithMeta  （従来）
Flag ON  → POST /api/single/detail/:id
            ├─ core_payload あり → Single → Mapper → Bundle
            └─ なし / 失敗 / Timeout → Prediction Bundle（即時フォールバック）
```

Staging で Single 本体を試す場合のみ `sessionStorage.expect_single_core_<raceId>` に core_payload を置ける（Core 捏造はしない・明示注入のみ）。

---

## 一覧 LOCK（遵守）

| 禁止 | 結果 |
|---|---|
| races.html 変更 | **なし**（single-detail 未ロード） |
| Cache key/TTL/更新 | **なし** |
| Single API on list | **なし** |

---

## Contract

- PredictionBundle 2.0 維持（UI1 sanitize）
- UI レイアウト変更なし
- Core / Consumer 変更なし
