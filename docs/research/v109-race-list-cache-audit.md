# Race List Cache Audit（A1 / I1 / UI1 / UI2 後）

**Date:** 2026-07-29  
**Mode:** Audit only · **実装変更なし**  
**Scope:** 既存サイト レース一覧の Race List Cache が A1–UI2 後も維持されているか

---

## 監査結論

レース一覧の Race List Cache は **維持**されている。  
A1 / I1 / UI1 / UI2 は一覧経路に Single API を接続していない。

---

## 確認項目

| # | 項目 | 判定 | 要点 |
|---|---|---|---|
| 1 | 一覧で Single API を呼んでいないか | **維持（呼んでいない）** | `races.html` に `single.js` / `ExpectApi.Single` / `/api/single` なし |
| 2 | PredictionBundle Cache が従来どおりか | **維持** | `expect_race_list_cache_v4` + prefetch `expect_pb_prefetch_v1` |
| 3 | 詳細のみ Single API か | **未配線** | 詳細も `ExpectApi.Prediction.getWithMeta`。Single はページ未接続 |
| 4 | 一覧で追加 HTTP が増えていないか | **A1–UI2 起因の追加なし** | 既存の Prediction / race-cards / prefetch のみ |
| 5 | Cache 寿命・更新方法の変更 | **変更なし** | TTL 5分 · localStorage v4 キー |

キャッシュ構造自体の変更はない。

---

## Evidence

### 1. 一覧は Single API を呼ばない

`races.html` script: Prediction / RaceCards / prefetch のみ（`single.js` なし）。

`public/{races,race,index}.html` を `ExpectApi.Single` / `/api/single` / `/api/ui/prediction` で検索 → ヒットなし。  
`predictionAdapter.js` に `/v1/site` · `/v1/ui` · SingleSite 参照 → なし。

### 2. Race List Cache

| 項目 | 値 |
|---|---|
| Key | `expect_race_list_cache_v4` |
| TTL | `RACE_LIST_CACHE_TTL_MS = 5 * 60 * 1000`（5 分） |
| v1 hit | bundles 描画して return（`Prediction.list` しない） |
| v2 hit | race_cards 描画 → 従来 enrich のみ |

Prefetch: `expect_pb_prefetch_v1` · max 20 · `ExpectApi.Prediction.getWithMeta`（Single ではない）。

### 3. 詳細も現状は Prediction

`race.html` は `prediction.js` / `prediction-bind.js` / `race-prefetch.js`。  
取得: `ExpectApi.Prediction.getWithMeta`。`single.js` 未ロード。

「詳細遷移時のみ Single API」は将来 opt-in であり、**現行ページでは Single は一覧・詳細どちらからも呼ばれない**。

### 4. A1–UI2 追加物と一覧接続

| Phase | 追加物 | 一覧への接続 |
|---|---|---|
| A1 | `/v1/single/*` | なし |
| I1 | `/api/single/*` · `single.js`（opt-in） | HTML 未配線 |
| UI1 | `/api/ui/prediction-bundle` · Mapper | HTML 未配線 |
| UI2 | Shadow 検証のみ | なし |

### 5. 寿命・更新（変更なし）

| 項目 | 値 | A1–UI2 |
|---|---|---|
| Key | `expect_race_list_cache_v4` | なし |
| TTL | 5 分 | なし |
| Write | ready cards のみ（v2） | なし |
| Prefetch SS | `expect_pb_prefetch_v1` | Single 非使用のまま |

---

## 補足

一覧の HTTP が常にゼロとは限らない（従来仕様）:

- cache miss 時の RaceCards / catalog
- enrichProgressive / viewport Prediction prefetch（`MAX_CONCURRENT=2`）

これらは A1–UI2 以前からの Prediction 経路であり、Single API ではない。

---

```
【Decision】
Action Type: Audit only
Implementation Required: No
Deployment Required: No
Production Required: No
Rollback Required: No
Risk: Low
Expected Next Action: 現状維持。詳細を Single に切る場合は別 Gate（一覧 cache 維持を必須条件）
```
