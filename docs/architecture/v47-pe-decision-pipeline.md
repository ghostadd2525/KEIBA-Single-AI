# Version47 — PE Decision Pipeline

**Date:** 2026-07-28  
**Type:** Audit only  
**Source:** `CorePipeline.evaluate` L64–93 + Scorer/Ranker/Facade/Mapper

## ④ Decision Pipeline（処理順）

```text
[1] Feature
      FeatureLoader.load(race_id)
      FeatureGenerator.build_feature_matrix(runners)
        └─ enrich / style counts / prepare (0-fill)

[2] Score (base)
      model_predict_score(X)  OR  build_base_probability_scores(frame)

[3] Score (adjust)     ← Hidden Policy 層
      attach_probability_context_columns
      apply_grade_distance_style_adjustment
      ensure_non_tied_scores

[4] Score (probability)
      field-size temperature softmax → win_prob

[5] Ranking
      Ranker.build_ranking ← adjusted → model_rank (desc win_prob)

[6] Meta (post-rank input build)
      WorldClassifier.build_race_meta(scored_frame)
      detect_race_meta  ※順位は変更しない

[7] Confidence
      ConfidenceBuilder.build_confidence(scores, meta)

[8] World Label (post-rank)
      classify_world_line_type(meta)
      classify_sub_world_type(meta, None)

[9] CE Projection
      Rank + Confidence + WorldMeta/SubWorldMeta 添付
      （Rank 再計算なし）

[10] Prediction Facade / Bundle
      predict_ranking: ranking rows only（world キーなし）
      mapper: evaluation.world = None
      top pick ≡ model_rank == 1 → honmei
```

---

## Stage ownership

| Stage | Owner | 順位決定に関与 |
|---|---|---|
| 1 Feature | Feature* | 間接（入力） |
| 2–4 Score | Scorer | **Yes** |
| 5 Ranking | Ranker | **Yes（確定）** |
| 6 Meta | WorldClassifier | No |
| 7 Confidence | ConfidenceBuilder | No |
| 8 World | WorldClassifier | No |
| 9 CE | Projector | No（添付） |
| 10 Prediction | Facade/Mapper | 投影のみ |

**順位の凍結点:** Stage 5 完了時点。以降は説明・信頼度・ラベル。

---

## ⑥ Hidden Policies（監査）

| ID | 種別 | 場所 | 内容（コード事実） |
|---|---|---|---|
| H1 | フォールバック | Scorer | model None → `build_base_probability_scores` |
| H2 | 特徴 DEFAULT | feature utils | `race_leg_difficulty: 0.5` 等 |
| H3 | 欠損埋め | prepare_feature_matrix | 数値欠損 → 0.0 |
| H4 | 暗黙補正 | `apply_grade_distance_style_adjustment` | grade/distance/style、outer_closer、pace/frame、rank46 push 等のハードコード加点 |
| H5 | タイ解消 | `ensure_non_tied_scores` | fallback 重み + secondary + horse_number ε |
| H6 | Softmax 温度 | `_field_size_temperature` | 頭数連動 / CE_V2 固定温度 / env override |
| H7 | Confidence 帯 | ConfidenceBuilder | 閾値バンド（high/medium/low）と overall 合成 |
| H8 | Winner 暗黙 | Mapper | rank1=honmei（別 Winner 関数なし） |
| H9 | World 後付け | CorePipeline | 順位後ラベル。順位非消費 |
| H10 | World 削除 | single_prediction_mapper | 公開 Prediction から world=None |
| H11 | HTTP fallback | PredictionAdapter | Core 失敗時 mock_fallback |

**Hidden Policy と World:** H4–H6 は **World 非依存の順位補正**。World Trigger（V44）とは別系統の暗黙順位政策である。

---

## Pipeline vs V44/V36 設計意図（事実対比のみ）

| 設計意図（先行文書） | 実装パイプライン |
|---|---|
| World → PE が勝ち筋に従う（V36 I3） | World は Stage 8。Stage 5 で順位確定済み |
| World Positive Match（V44） | PE は World を入力に使わない |

本対比は改善提案ではなく、責務位置の証明である。
