# Version47 — PE Dependency Graph

**Date:** 2026-07-28  
**Type:** Audit only

## ③ Dependency Graph

### Runtime call graph（Production 予測経路）

```text
HTTP GET /v1/predictions/{race_id}
  └─ PredictionAdapter (AI_ENGINE=real)
       └─ ai_platform.single.api.get_prediction
            └─ single.prediction.predict
                 ├─ facade.predict_ranking
                 │    └─ evaluate_candidates
                 │         └─ CorePipeline.evaluate
                 │              ├─ FeatureLoader.load
                 │              │    └─ DB / daily CSV / global CSV
                 │              ├─ FeatureGenerator.build_feature_matrix
                 │              │    └─ enrich_stable_features / prepare_feature_matrix
                 │              ├─ Scorer.score_candidates
                 │              │    ├─ get_ranking_model / model_predict_score
                 │              │    ├─ build_base_probability_scores   [fallback]
                 │              │    ├─ attach_probability_context_columns
                 │              │    ├─ apply_grade_distance_style_adjustment
                 │              │    ├─ ensure_non_tied_scores
                 │              │    └─ _temperature_softmax → win_prob
                 │              ├─ Ranker.build_ranking
                 │              │    └─ build_probability_from_adjusted_score → model_rank
                 │              ├─ WorldClassifier.build_race_meta
                 │              │    └─ detect_race_meta (demo_ticket_optimizer_core)
                 │              ├─ ConfidenceBuilder.build_confidence
                 │              ├─ WorldClassifier.classify_world
                 │              │    ├─ classify_world_line_type
                 │              │    └─ classify_sub_world_type(..., None)
                 │              └─ CandidateEvaluationProjector.project_candidates
                 └─ predict_confidence (別投影)
            └─ single_prediction_mapper → PredictionBundle
                 └─ evaluation.world = None
```

### Module dependency（PE 狭義）

```text
                    ┌─────────────────────┐
                    │   FeatureLoader     │
                    │   FeatureGenerator  │
                    └──────────┬──────────┘
                               │ feature_matrix
                               ▼
┌──────────────────────────────────────────────────┐
│ Scorer                                           │
│  + model_registry.get_ranking_model               │
│  + demo_probability_model_logic                  │
│  + demo_probability_adjustment_logic             │
│  + demo_probability_context_logic                │
└──────────────────────┬───────────────────────────┘
                       │ score_bundle
                       ▼
                 ┌──────────┐
                 │  Ranker  │
                 └────┬─────┘
                      │ ranking (model_rank)
                      ▼
              [PE 狭義ここまで]

                      │ scored_frame
                      ▼
              ┌───────────────┐
              │ WorldClassifier│──► demo_ticket_optimizer_core
              └───────┬───────┘
                      ▼
              ConfidenceBuilder
                      ▼
                   Projector → CE rows
```

### Explicit non-dependencies（コード）

| モジュール | CorePipeline から | 根拠 |
|---|---|---|
| `build_candidate_pool` | **呼ばれない** | CE docstring L1–5 |
| Repick / Ticket / Purchase | **呼ばれない** | facade docstring |
| `classify_world_line_type` as Scorer input | **なし** | scoring grep 0 |

### Data stores

| データ | 用途 |
|---|---|
| expect feature DB / daily CSV / global CSV | FeatureLoader |
| `win5_lgbm_ranker_features.json` | 特徴スキーマ |
| ranking model artifact | ModelRegistry |
| PredictionBundle / HTTP response | 公開出力 |

### Library / legacy coupling

| PE コンポーネント | legacy 依存 |
|---|---|
| Scorer | `demo_probability_*_logic` |
| WorldClassifier | `demo_ticket_optimizer_core` |
| Feature defaults | `demo_probability_feature_utils.STABLE_FEATURE_DEFAULTS` |
