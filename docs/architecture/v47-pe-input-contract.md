# Version47 — PE Input Contract

**Date:** 2026-07-28  
**Type:** Audit only  
**Scope:** PE 狭義（Feature→Score→Rank）および CorePipeline.evaluate が実際に読む入力

## ② Input Contract — 全入力一覧

### I1. Race identity

| 入力 | 型 | 到来層 | 消費者 |
|---|---|---|---|
| `race_id` | str | HTTP / Adapter / Single API | `FeatureLoader.load`, Facade |

### I2. Feature（主入力）

| 入力 | 到来層 | 消費者 | World 依存 |
|---|---|---|---|
| runner feature frame | DB → daily CSV → global CSV（`FeatureLoader`） | FeatureGenerator, Scorer | **なし** |
| `feature_matrix["X"]` | FeatureGenerator + schema | Scorer `model_predict_score` | なし |
| `_source_frame` | 同一 | Scorer adjustment / Ranker | なし |
| 欠損埋め | `prepare_feature_matrix` → 0.0 / `STABLE_FEATURE_DEFAULTS` | Feature/Scorer | difficulty 既定 0.5 等（Signal 契約の DEFAULT 問題と接続するが World ラベルではない） |

### I3. Model

| 入力 | 到来層 | 消費者 |
|---|---|---|
| ranking model | `get_ranking_model()` | Scorer |
| （欠落時）fallback 重み | `build_base_probability_scores` / `DEFAULT_FALLBACK_WEIGHTS` | Scorer |

### I4. Score 内部中間（PE 内産）

| 入力 | 産出元 | 消費者 |
|---|---|---|
| `base_model_score` | Scorer | Adjustment |
| context columns | `attach_probability_context_columns` | Adjustment |
| `adjusted_model_score` | Adjustment | Softmax / Ranker |
| `win_prob` | Softmax | Ranker / Confidence / Bundle |

### I5. Meta（スコア **後** — 狭義 PE の順位入力ではない）

| 入力 | 到来層 | 消費者 | 備考 |
|---|---|---|---|
| scored_frame + probs | Rank/Score 後 | `detect_race_meta` | `top*_prob`, gap, entropy, `race_leg_difficulty`, `race_required_pick` 等 |
| `race_meta` | WorldClassifier.build_race_meta | Confidence, classify_world | |

### I6. World / SubWorld / Required / Pool / Role / Signal（契約観点）

| 概念 | PE 狭義への入力か | 実際の経路 | 根拠 |
|---|---|---|---|
| **World** | **No**（順位入力として） | 順位後に **生成**され CE に添付。PredictionBundle では `world=None` | evaluate 順序; mapper |
| **SubWorld** | **No** | 同上。`classify_sub_world_type(meta, None)` | world/__init__.py L29–30 |
| **Required** | **No**（Scorer/Ranker） | meta に `race_required_pick` 等が載りうるが **分類後段** | detect_race_meta |
| **Candidate Pool** | **No** | CorePipeline 非呼出 | CE module docstring |
| **Role** | **No** | optimizer / pool 内 | build_candidate_pool |
| **Signal（WIC）** | Feature 列として間接 | difficulty/chaos 等が frame にあれば Scorer は特徴として読みうる。**World Trigger としては読まない** | scoring に classify なし |
| **Score** | 内部 | PE が自ら産出 | — |

---

## Input by Responsibility

| 責務 | 必須入力 | 任意/内部 | 禁止（コード上未接続） |
|---|---|---|---|
| Feature Load | race_id | feature_source 経路 | World ラベル |
| Scoring | X, frame | model | World, Pool, Role |
| Ranking | adjusted scores / win_prob | — | World, Pool |
| Confidence | scores, meta | — | Pool（meta はスコア後） |
| World Label | meta, confidence_result | — | （これは生成側） |
| Prediction facade | CE candidates | — | World 伝播なし |

---

## Contract Statement

```text
PE Ranking Input Contract (as implemented):
  REQUIRED: race_id → feature frame / matrix → (optional) ranking model
  NOT IN CONTRACT: world_line_type, sub_world, candidate_pool, assigned_role
  PRODUCED LATER (not inputs to rank): world, sub_world, confidence bands
```

これは設計意図（V32/V36「World が勝ち筋を決め PE が従う」）とは **不一致**（V35 と同結論）。本 Audit は実装事実のみを固定する。
