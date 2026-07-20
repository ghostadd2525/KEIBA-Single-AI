# PredictionService · Envelope Meta（運用 provenance）

**Status:** Phase7-08  
**Scope:** HTTP envelope `meta` のみ。`PredictionBundle`（`single-prediction-bundle/2.0`）は変更しない。

---

## 共通（list / get）

| キー | 型 | 説明 |
|---|---|---|
| `generated_at` | string | BFF 応答生成時刻（`jsonOk`） |
| `service` | `"PredictionService"` | 固定 |
| `adapter` | `"PredictionAdapter"` | 固定 |
| `provider` | `"python"` \| `"mock"` | 輸送経路（Python 到達 / BFF ASSETS） |
| `source` | `"single-ai"` \| `"mock"` | 既存ラベル |
| `engine` | `"real"` \| `"mock"` \| `"n/a"` | Python `AI_ENGINE`。BFF 純 mock 時は `n/a` |
| `contract` / `schema_version` / `contract_*` | — | 既存の契約検証メタ |

---

## GET `/api/predictions`（一覧）

`meta.items[]` に race_id 単位の provenance:

| キー | 説明 |
|---|---|
| `race_id` | Bundle の race_id |
| `engine_source` | `real_ai` \| `mock_fallback` \| `mock` \| `bff_mock` |
| `model_version` | Bundle.`model_version` のエコー |
| `inference_generated_at` | Bundle.`generated_at` のエコー |
| `core_race_id` | 任意。実推論時の Core ID |

```json
{
  "ok": true,
  "meta": {
    "generated_at": "2026-07-20T01:40:00.000Z",
    "service": "PredictionService",
    "adapter": "PredictionAdapter",
    "provider": "python",
    "source": "single-ai",
    "engine": "real",
    "items": [
      {
        "race_id": "20260719_fukushima_11",
        "engine_source": "real_ai",
        "model_version": "core-delegated",
        "inference_generated_at": "2026-07-20T10:37:13",
        "core_race_id": "2026-07-19-04-11"
      },
      {
        "race_id": "20260719_hanshin_11",
        "engine_source": "mock_fallback",
        "model_version": "dummy-model-0.0.0",
        "inference_generated_at": "2026-07-19T12:00:00+09:00"
      }
    ]
  },
  "data": [/* PredictionBundle[] */]
}
```

---

## GET `/api/predictions/:id`（詳細）

フラット:

| キー | 説明 |
|---|---|
| `engine` | 上記と同じ |
| `engine_source` | 上記と同じ |
| `model_version` | エコー |
| `inference_generated_at` | エコー |
| `race_id` | 対象 |
| `core_race_id` | 任意 |

---

## `engine_source` 判別

| 値 | 意味 |
|---|---|
| `real_ai` | `AI_ENGINE=real` かつ Single AI 推論成功 |
| `mock_fallback` | `AI_ENGINE=real` だが Core 未解決などで Python Mock へフォールバック |
| `mock` | Python `AI_ENGINE=mock` |
| `bff_mock` | BFF が ASSETS mock を直接読んだ（`AI_BASE_URL` なし等） |

---

## Python `/v1/predictions*`

```json
{ "ok": true, "data": <bundle|bundles>, "meta": { ...provenance } }
```

BFF は `payload.meta` を envelope にマージする。
