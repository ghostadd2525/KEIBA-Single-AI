# Version47 — PE Responsibility Decomposition

**Date:** 2026-07-28  
**Type:** Research / Audit only（改善・実装・Production 変更禁止）  
**Question:** PE は何を入力し、どう順位を決め、何を出力するか — 責務単位で分解する。

## 用語（コード正本）

コード上に `PredictionEngine` クラスは **存在しない**。

| 本 Audit の用語 | コード実体 | 根拠 |
|---|---|---|
| **PE（狭義）** | `Scorer` + `Ranker` + `FeatureLoader`/`FeatureGenerator` | 順位（`model_rank` / `win_prob`）を生成する層 |
| **CE** | `CorePipeline` + `CandidateEvaluationProjector` | Feature→Score→Rank→Confidence→World ラベル→CE rows。Candidate Evaluation |
| **Facade Prediction** | `predict_ranking` / Single `predict` / HTTP `/v1/predictions` | CE から ranking を投影。World を落とす場合あり |
| **World 分類** | `WorldClassifier` → `classify_world_line_type` | **順位確定後**のラベル生成 |
| **購入 PE（広義・非本対象の主経路）** | `build_candidate_pool` 等 | CorePipeline から **未呼出**（CE docstring） |

Causal Engine というモジュール名は Core に無い（`causal_race_type` は meta 列）。

出典: `ai_platform/core/candidate_evaluation/__init__.py` L1–5, L48–58。

---

## ① PE Responsibility（責務列挙）

### A. PE 狭義（順位生成）が持つ責務

| 責務 ID | 責務 | 実装 | 出力 |
|---|---|---|---|
| R1 Feature Load | レース特徴の読込 | `FeatureLoader.load` | runner frame |
| R2 Feature Matrix | 行列化・欠損処理 | `FeatureGenerator.build_feature_matrix` | `X`, `_source_frame` |
| R3 Base Scoring | モデル or fallback 基礎点 | `Scorer` → `model_predict_score` / `build_base_probability_scores` | `base_model_score` |
| R4 Score Adjustment | グレード距離脚質等の補正 | `apply_grade_distance_style_adjustment` | `adjusted_model_score` |
| R5 Tie Break | 同点解消 | `ensure_non_tied_scores` | 非タイ scores |
| R6 Softmax | レース内確率化 | `_temperature_softmax` / `race_softmax` | `win_prob` |
| R7 Ranking | 確率→順位 | `Ranker.build_ranking` | `model_rank` / ranking rows |
| R8 Top-pick 投影 | rank1 を本命扱い | Single mapper `_MARK_BY_RANK` | honmei 等 |

### B. CorePipeline が同一 `evaluate` に同梱するが、狭義 PE（順位）とは別責務

| 責務 ID | 責務 | 実装 | 順位への影響 |
|---|---|---|---|
| R9 Race Meta | スコア後 meta 構築 | `WorldClassifier.build_race_meta` → `detect_race_meta` | **なし**（後段） |
| R10 Confidence | 信頼度バンド | `ConfidenceBuilder.build_confidence` | **なし**（順位後） |
| R11 World Label | World/SubWorld 分類 | `classify_world` | **なし**（順位後・添付のみ） |
| R12 CE Project | CE 行投影 | `CandidateEvaluationProjector` | Rank 変更なし |

### C. PE / Core が持たない責務（コード証明）

| 責務 | 所在 | 証明 |
|---|---|---|
| Candidate Selection (Pool) | `build_candidate_pool` | CE: “No Candidate Pool or Repick” |
| Role / Required 購入ガード | optimizer | CorePipeline 未呼出 |
| Winner 特殊決定（rank 以外） | なし | top pick ≡ `model_rank==1` |
| World による再ランク | なし | scoring/ranking に world 参照 **0件** |

---

## ⑤ World Consumption（要約・証明）

| 入力概念 | Scorer | Ranker | Confidence | WorldClassifier | Projector | `predict_ranking` |
|---|---|---|---|---|---|---|
| World | **不使用** | **不使用** | 不使用（meta は受けるが World ラベルではない） | **生成** | **添付のみ** | **キー欠落** |
| SubWorld | 不使用 | 不使用 | 不使用 | **生成**（candidate=None） | 添付のみ | 欠落 |
| Required | 不使用 | 不使用 | — | meta 観測列として読みうる | 不使用 | 不使用 |
| Candidate Pool | 不使用 | 不使用 | 不使用 | 不使用 | 不使用 | 不使用 |
| Role | 不使用 | 不使用 | 不使用 | 不使用 | 不使用 | 不使用 |

**証明:** `ai_platform/core/scoring` および `ranking` 配下に `world_line` / `classify_world` / `candidate_pool` / `sub_world` の参照は **マッチ 0**。  
`CorePipeline.evaluate` は `score`→`rank` の **後** に `build_race_meta` / `classify_world`（L71–93）。

詳細: `v47-pe-input-contract.md` / `v47-pe-boundary.md`。

---

## Governance 予告

責務が **CorePipeline 一式に Feature〜World ラベルまで同梱**され、かつ **World は順位に効かない**一方でパイプライン名上は同一 evaluate にある → 構造的混在。  
最終判定は `v47-governance.md`（**C**）。

## Artifacts

- `v47-pe-responsibility.md`（本ファイル）
- `v47-pe-input-contract.md`
- `v47-pe-dependency.md`
- `v47-pe-decision-pipeline.md`
- `v47-pe-boundary.md`
- `v47-governance.md`
