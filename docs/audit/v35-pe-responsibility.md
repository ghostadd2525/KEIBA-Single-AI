# Version35 — PE Responsibility Audit

**Phase:** V35 PE Dependency Audit  
**Mode:** Research / Audit only（改善・実装禁止）  
**Scope lock:** Prediction / PE / CE / AI / World / SubWorld / Role / Required / Candidate Pool / Challenge / ResultAutomation / Production — 変更禁止  
**Date:** 2026-07-28

---

## 用語整理（本 Audit の定義）

| 用語 | コード上の実体 | 本 Audit での扱い |
|------|----------------|-------------------|
| **CE** | `ai_platform.core.candidate_evaluation.CorePipeline` / `CandidateEvaluationProjector` | Feature→Score→Rank→Confidence→World label→CE rows |
| **PE（狭義・ops）** | 「Prediction Engine」として単レース予測の top pick / ranking を指す語 | 実際の ranking 生成は **CE/Core の Ranker+Scorer**。World 非依存 |
| **PE（Win5・Pool/Entry）** | `demo_ticket_optimizer_core.build_candidate_pool` 以降の購入・再ピック経路 | World/SubWorld を **購入側ガード**で参照。Hit 用 model_rank / win_prob は変更しない |
| **Prediction** | Single `predict_ranking` + mapper 経由の公開予測 | World を **出力から落とす** |

本 Audit の問い「PE は World をどう使うか」に対し、ops が Hit/rank を見る **Prediction top pick** の経路は **CE Core ranking** であり、World はその後段ラベルである。

---

## ① PE（= Prediction ranking 経路）の責務

### 設計上の責務（コードコメント・モジュール境界）

`CorePipeline`（`ai_platform/core/candidate_evaluation/__init__.py`）:

> Feature-to-CE orchestration with **no Product or Win5 selection stages**.

`CandidateEvaluationProjector`:

> Project frozen Rank/Confidence values into CE rows.  
> **No Candidate Pool or Repick** is imported or called.

→ Core CE は「全出走馬をスコアし、順位・信頼度を投影する」。World は **順位確定後のメタ付与**。

### 入力

| 入力 | 経路 | World 依存 |
|------|------|------------|
| `race_id` | `FeatureLoader.load` | なし |
| runner feature frame | DB / daily CSV / global CSV | なし（特徴量そのものに World ラベルは不要） |
| `feature_matrix` | `FeatureGenerator.build_feature_matrix` | なし |
| scores | `Scorer.score_candidates` | **なし**（scoring パッケージに world 参照なし） |
| ranking | `Ranker.build_ranking(scores)` | **なし** |

### 出力

| 出力キー | 内容 | World の役割 |
|----------|------|--------------|
| `candidates[]` | Rank / Confidence / WorldMeta / SubWorldMeta | **メタのみ**（Rank は world 前に確定） |
| `world` / `sub_world` | レースラベル | 分類結果 |
| `meta` | `detect_race_meta` 由来 | World 分類の入力 |
| `overall_confidence` | ConfidenceBuilder | meta を受け取るが score 本体は scores 由来 |
| Facade `predict_ranking` | `ranking` + `feature_source` のみ | **world キーごと欠落** |

### World を参照する責務があるか

| 層 | 責務として World を読むか | 実装 |
|----|---------------------------|------|
| Scorer / Ranker | **No** | world 参照なし |
| ConfidenceBuilder | meta 経由の間接 | score 後 |
| WorldClassifier | **Yes（ラベル生成）** | ranking/confidence **の後** |
| Projector | World を CE row に **添付** | Rank は変更しない |
| `predict_ranking` | **No** | world を伝播しない |
| Single mapper | **明示的に None** | `evaluation.world = None` |

**結論（責務）:** Prediction に効く PE/CE ranking の責務は **特徴量→スコア→順位** であり、**World を入力として順位を変える責務はない**。World は **事後ラベル / 説明メタ** である。

---

## 実行順序（証明）

```
FeatureLoader
  → FeatureGenerator
  → Scorer.score_candidates          # World なし
  → Ranker.build_ranking             # World なし
  → WorldClassifier.build_race_meta  # score 後
  → ConfidenceBuilder
  → WorldClassifier.classify_world   # rank 後ラベル
  → CandidateEvaluationProjector     # WorldMeta 添付のみ
```

出典: `CorePipeline.evaluate` L64–93。

---

## 最終メモ

「PE が World を正しく消費している」設計意図（V32/V33 WIC）と、現行 PE/CE ranking 実装は **一致していない**。詳細は `v35-pe-dependency.md` / `v35-frozen-point.md`。
