# Version48 — CE Input Contract

**Date:** 2026-07-28  
**Type:** Audit only  
**Producer:** `CorePipeline.evaluate` 内部ステージ → Projector / Bundle

## ② Input Contract — CE へ入る情報

CE の「入力」は外部 API 引数ではなく、**パイプラインが Bundle へ渡す直前の内部産物**として定義する（外部引数は実質 `race_id` のみ）。

### External entry

| 入力 | 必須 | 備考 |
|---|---|---|
| `race_id` | Yes | `evaluate_candidates(race_id)` |
| `**opts` | No | evaluate に渡るが必須 CE フィールド定義には未使用 |

### Internal inputs to Projector / Bundle（実コード）

| 入力カテゴリ | 具体 | 到来層 | CE での使用 |
|---|---|---|---|
| **Rank** | `ranking["ranking"]` rows | Ranker | 行 `Rank` |
| **Score→Confidence** | `confidence["per_horse"]` / row score | ConfidenceBuilder（scores+meta） | 行 `Confidence` |
| **World** | `world["world"]` | WorldClassifier（順位後） | Bundle `world` + 行 `WorldMeta` |
| **SubWorld** | `world["sub_world"]` | 同上（candidate=None） | Bundle `sub_world` + 行 `SubWorldMeta` |
| **Meta** | `detect_race_meta` dict | WorldClassifier.build_race_meta | Bundle `meta` |
| **Confidence overall/factors** | ConfidenceBuilder | scores+meta | Bundle keys |
| **Context** | feature_source, metadata, field_size | FeatureLoader | Bundle `context` |
| **HorseNumber / CandidateID** | ranking rows | Ranker/frame | 行キー |

### NOT inputs to CE（コード上・契約上）

| 概念 | 状態 | 根拠 |
|---|---|---|
| **Required** | CE 入力に無い | Pool/Required 非呼出; Projector フィールドなし |
| **Candidate Pool** | 無い | CE docstring |
| **Role** | 無い | 同上 |
| **Signal（WIC 生値）** | meta/frame 経由の間接のみ。CE 契約フィールドではない | Bundle 必須は CandidateID/Rank/Confidence |
| **base_model_score / adjusted / win_prob** | Scorer 産出だが Projector は Rank/Confidence のみ投影 | project_candidates L33–45 |
| **World as ranking input** | 無い（生成結果として入る） | V47 / evaluate 順序 |

### Facade が宣言する Required CE fields

> Required CE fields remain **CandidateID, Rank and Confidence**.

出典: `core_facade.py` L27–28。

→ World / SubWorld / meta は Bundle に載るが、**Required CE fields には含まれない**。

## Input Contract Statement

```text
CE External Input:  race_id
CE Internal Assembly Inputs:
  REQUIRED for rows: CandidateID, Rank, Confidence
  ASSEMBLED ALSO:    World, SubWorld, meta, overall_confidence, context
  NEVER ASSEMBLED:   Pool, Role, Required (as CE fields)
  COMPRESSED AWAY:   raw PE scores (base/adjusted/win_prob) at row projection
```
