# Version47 — PE Boundary Audit

**Date:** 2026-07-28  
**Type:** Audit only

## ⑦ Responsibility Matrix

| 責務 | 入力 | 処理 | 出力 |
|---|---|---|---|
| Feature Load | race_id | DB/CSV 解決 | frame, feature_source |
| Feature Matrix | frame | enrich / 行列化 / 欠損埋め | X, _source_frame |
| Base Score | X or frame, model? | LGBM or fallback weights | base_model_score |
| Adjust Score | frame+context, base | grade/distance/style 等補正 | adjusted_model_score, diagnostic |
| Softmax | adjusted, field_size | temperature softmax | win_prob |
| Ranking | score_bundle | win_prob 降順 rank | model_rank, ranking[] |
| Confidence | scores, meta | per-horse / overall / band | confidence dict |
| World Label | meta, confidence | classify_world_line_type / sub_world | world, sub_world |
| CE Project | ranking, confidence, world | 行合成 | CE candidates |
| Prediction Project | CE | ranking 抽出、world drop | PredictionBundle / ranking result |
| Candidate Pool | （PE外） | — | — |
| Role/Required 購入 | （PE外） | — | — |

---

## ⑧ Boundary — 持つべき / 持つべきでない

### コードが示す「現に持っている」境界

| 領域 | Core/PE が行う | 根拠 |
|---|---|---|
| 全出走スコア・順位 | Yes | Scorer+Ranker; 全 runner 投影 |
| 信頼度 | Yes（同パイプライン） | ConfidenceBuilder |
| World ラベル生成 | Yes（同パイプライン・後段） | WorldClassifier |
| Pool / Repick / Ticket | **No** | docstring 明示 |
| World で順位変更 | **No** | scoring/ranking 参照 0 |

### 設計文書上の境界（V32/V36）との差分（監査）

| 本来（設計意図） | 実装 | 分類 |
|---|---|---|
| PE が World（勝ち筋）を **入力消費**して順位政策を変える | World は出力メタのみ | **欠落責務** |
| World 分類は最上流 | World は Rank 後 | **順序逆転** |
| PE = 順位エンジン | CorePipeline に Confidence+World 同梱 | **責務混在** |
| 暗黙 adjustment は説明可能政策として分離 | Scorer 内ハードコード補正 | **隠れた順位政策** |
| Prediction が World を伝える | mapper が world=None | **出力切断** |

### PE が持つべき（設計意図・V36）※実装変更はしない

- Ranking / Scoring（明示）
- （設計）World-conditioned policy の **消費**（現状欠落）

### PE が持つべきでない（設計意図）※現状の混在点

- World **生成**を Ranking と同一 evaluate に暗黙同梱しつつ順位非消費（説明メタと決定の混線）
- Candidate Pool / 購入 Role（現状は未接続で境界は守られている）
- Prediction 公開契約からの World 削除は「Facade 責務」だが、勝ち筋伝播を断つ

### 現状の境界評価（一文）

> **順位決定（PE 狭義）と World ラベル生成と Confidence が同一 CorePipeline に同居し、かつ World は順位に効かない**ため、責務分離は構造的に不十分。一方 Pool/Ticket 非呼出は明示的に守られている。

---

## World Consumption Proof Table（再掲）

| 消費対象 | 責務での消費 | コード証明 |
|---|---|---|
| World | 順位: No / ラベル生成: Yes / 公開予測: Dropped | evaluate 順序; scoring grep 0; mapper world=None |
| SubWorld | 同上（candidate=None） | world/__init__.py |
| Required | 順位: No | Scorer 非参照 |
| Candidate Pool | No | CE docstring |
| Role | No | Core 非参照 |
