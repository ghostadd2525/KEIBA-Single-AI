# Version49 — Prediction Information Loss（Root Cause）

**Date:** 2026-07-28  
**Type:** Audit only  
**Focus:** World / SubWorld / Meta がどこで・なぜ失われるか

## ⑥ Root Cause Chain（コード証明）

### Loss Point 1 — Facade 投影（一次原因）

**どこ:** `ai_platform/core/facade/core_facade.py` `predict_ranking`

**何が失われる:** `world`, `sub_world`, `meta`, 行 `WorldMeta`/`SubWorldMeta`

**なぜ:** 関数が返す dict リテラルにそれらのキーが含まれない。Compatibility Ranking view として Rank/score のみを投影する実装。

```text
ce = evaluate_candidates(...)   # CE には world あり
return { race_id, ranking, core_version, feature_source }  # world 無し
```

**Prediction との関係:** Single `predict` がこの戻りだけを ranking 源にする。

---

### Loss Point 2 — Single 応答組み立て（二次・非存在）

**どこ:** `ai_platform/single/models/prediction_response`

**何が失われる:** World フィールド自体がスキーマに無い

**なぜ:** S-04 応答が ranking/confidence/items 中心。CE Bundle を受け取らない。

---

### Loss Point 3 — Expect Mapper（三次・明示 Null）

**どこ:** `prediction_response_to_bundle` L408–412

**何が失われる:** `evaluation.world` / `sub_world` が **常に None**

**なぜ:** ハードコード代入。上流に World が無い場合も、仮に将来付いてもこの行で潰す。

```text
"evaluation": {
    "status": "ok",
    "world": None,
    "sub_world": None,
    "runners": runners,
}
```

---

### Loss Point 4 — Meta

| Meta 種別 | 喪失点 |
|---|---|
| CE `meta`（detect_race_meta） | Loss Point 1 で RankingResult から除外 |
| Bundle `race_info` | catalog / resolver meta から **再構成**（CE meta のコピーではない） |
| explain.meta | Mapper が core_race_id / band / feature_source を新規作成 |

→ 「Meta が失われる」= CE 分類 meta は Prediction に流れない。別系統の race_info が載る。

---

## Why（設計実装上の理由・コード根拠のみ）

| 理由コード | 根拠 |
|---|---|
| R-COMPAT | facade: “Compatibility views are projections from CE” — 全文 CE ではない |
| R-SINGLE-SCHEMA | prediction_response に world キーが無い |
| R-BUNDLE-SCHEMA | Mapper が Expect Bundle 形へ投影時に world=None を明示 |
| R-NO-EVAL-CALL | Prediction 経路が `evaluate_candidates` を公開利用しない |

推測（意図の心理）は置かず、**実装がそう書かれている**ことのみを Root Cause とする。

---

## End-to-end proof sequence

```text
1. CorePipeline.evaluate → result["world"] = <label>     # 存在
2. predict_ranking(ce) → "world" not in return            # 喪失①
3. prediction_response.has no world                       # 喪失②（非存在）
4. prediction_response_to_bundle → world: None            # 喪失③（固定）
5. GET /v1/predictions/{id} → evaluation.world is null    # 公開結果
```

V48 の「CE 保持 / Prediction None」は、本 V49 により **喪失点 1+3 が主因**とコード位置まで固定される。

---

## Non-loss（対照）

| 情報 | Prediction での扱い |
|---|---|
| Rank | model_rank として公開 |
| Confidence 値 | win_prob / ai_confidence として公開（ラベルは変換） |
| feature_source | Bundle / envelope に残る場合あり |
| betting slips | recommendations へ変換 |
