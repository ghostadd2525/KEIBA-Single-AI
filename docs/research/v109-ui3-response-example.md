# Phase UI3 — Response Example

**Date:** 2026-07-29

---

## Mapper output（base_bundle なし · 契約最小充足）

```json
{
  "schema_version": "single-prediction-bundle/2.0",
  "race_id": "2026-07-19-04-11",
  "race_info": {
    "race_id": "2026-07-19-04-11",
    "date": "unknown",
    "venue": "unknown",
    "race_no": 11
  },
  "evaluation": {
    "status": "ok",
    "world": null,
    "sub_world": null,
    "runners": [
      {
        "candidate_id": "c05",
        "horse_number": 5,
        "horse_name": null,
        "model_rank": 1,
        "win_prob": 0.3,
        "mark": "honmei",
        "mark_rank": 1
      }
    ]
  },
  "ai_confidence": {
    "schema_version": "ai-confidence/1.0",
    "status": "unknown",
    "score": null,
    "band": "unknown"
  },
  "explain": {
    "meta": { "world": null, "sub_world": null },
    "reasons": [],
    "narrative": ""
  },
  "betting_recommendations": {
    "schema_version": "betting-recommendations/1.0",
    "items": []
  }
}
```

## Live Prediction API（本番サンプル · Flag OFF）

`GET /api/predictions/2026-07-26-01-11` — `schema_version=single-prediction-bundle/2.0` · `race_info.race_no=11`（number）· `explain.narrative` string · Guard PASS（2026-07-26 全日 36/36 PASS スキャン）。

## After UI3 ensure

不完全な中間オブジェクトでも `normalizePredictionBundle` / Mapper 出口で上記必須形に揃う。
