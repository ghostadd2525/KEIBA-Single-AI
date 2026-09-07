# Version109 Phase I1 — Migration Guide（既存サイト）

**Date:** 2026-07-29  
**原則:** サイト側変更量を最小化。Prediction 経路は維持。

---

## Phase 0 — 変更なし（現状維持）

- 画面は `ExpectApi.Prediction` のまま
- `/api/predictions` / PredictionBundle 2.0 継続

---

## Phase 1 — 接続追加（本フェーズ I1）

| 変更 | 要否 |
|---|---|
| BFF `functions/api/single/*` | **追加済** |
| Python `/v1/site/*` | **追加済** |
| `public/assets/api/single.js` | **追加済（未配線）** |
| `race.html` / Prediction bind | **不要** |
| PredictionAdapter | **不要** |
| Bundle 契約 | **不要** |

Opt-in 配線（必要なページのみ）:

```html
<script src="assets/api/single.js?v=1"></script>
```

```js
ExpectApi.Single.call({
  race_id: id,
  core_payload: corePayload, // PROMOTE 前は供給元が必要
  force: true                // Shadow のみ
});
```

---

## Phase 2 — Core 供給（別 Gate）

`core_payload` をリクエスト必須にしている理由:

- I1 は Core / PROMOTE を変更しない
- Site Integration は Core を捏造しない

PROMOTE（`W_CORE_PAYLOAD_V103`）後の想定:

1. Python が race_id のみで Core read
2. Request から `core_payload` を外せる
3. そのとき初めて FE の呼び出しが `race_id` のみに縮小

---

## Phase 3 — UI 切替（任意・別承認）

Single 応答を画面に出す場合:

- **推奨:** 新セクション / Shadow パネル（Prediction を壊さない）
- **非推奨:** PredictionBundle を Consumer DTO で置換（契約破壊）

Consumer → Bundle 投影が必要なら **別 Mapper Gate**（Presentation/Contract 変更禁止のまま View 層のみ）。

---

## Rollback

1. ページから `single.js` 参照を外す（UI）
2. または `SITE_SINGLE_HTTP_ENABLED=0`（Python）
3. Prediction 経路は無影響

---

## Checklist

- [ ] `AI_BASE_URL` / `AI_API_KEY` 設定
- [ ] `GET /api/single/health` 200
- [ ] Shadow: `force=true` + sample core_payload
- [ ] Production: `force` 禁止・Flag Gate 承認後
- [ ] Prediction 回帰: `/api/predictions/:id` 変更なし
