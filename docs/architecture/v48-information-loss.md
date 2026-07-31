# Version48 — Information Loss Audit（PE → CE → Prediction）

**Date:** 2026-07-28  
**Type:** Audit only  
**Rule:** 実コードのキー有無のみ。推測禁止。

## ④ Loss Pipeline

```text
PE Scorer/Ranker
  has: base_model_score, adjusted_model_score, win_prob, diagnostic, model_rank
        │
        ▼ project_candidates + Bundle assemble
CE CorePublicBundle
  keeps: Rank, Confidence, WorldMeta/SubWorldMeta, world, sub_world, meta, context
  loses at row: base/adjusted/win_prob/diagnostic（Confidence へ圧縮）
  never had: Pool, Role, Required
        │
        ├─ evaluate_candidates ──────────► FULL CE（world あり）
        ├─ resolve_core ─────────────────► world/meta あり（features=None）
        ├─ predict_ranking ──────────────► world/meta/WorldMeta 欠落
        └─ Single predict → mapper ──────► evaluation.world = None 固定
```

---

## Tracked fields

### World

| 段 | 状態 | 根拠 |
|---|---|---|
| PE Rank 入力 | 不使用 | V47 |
| CE Bundle | **保持** `world` + 行 `WorldMeta` | evaluate L104–105, Projector L39 |
| predict_ranking | **喪失**（キー無し） | facade L79–84 |
| Single predict | ranking のみ使用 → World 非取得 | prediction/__init__.py L33 |
| PredictionBundle | **明示破棄** `world: None` | mapper L410 |
| resolve_core | **保持** | facade L57 |

### SubWorld

| 段 | 状態 |
|---|---|
| CE | 保持 `sub_world` + `SubWorldMeta` |
| predict_ranking | 喪失 |
| PredictionBundle | `sub_world: None` |
| classify 時 candidate | 常に `None`（情報生成時点で候補文脈欠落） |

### Required

| 段 | 状態 |
|---|---|
| PE/CE | **契約フィールドとして非保持** |
| meta 内 | `race_required_pick` 等が meta に載る可能性（detect_race_meta） |
| predict_ranking | meta ごと喪失 |
| PredictionBundle | Required 契約なし |
| Win5 | optimizer 側で別管理（CE 経由ではない） |

### Role

| 段 | 状態 |
|---|---|
| CE | **非保持** |
| Prediction | 非保持 |
| Win5 Pool | optimizer 内 `assigned_role` 等（CE 外） |

### Pool

| 段 | 状態 |
|---|---|
| CE | **非保持・非呼出** |
| 全 Prediction 経路 | 非保持 |

### Meta

| 段 | 状態 |
|---|---|
| CE Bundle | **保持** `meta` |
| resolve_core | 保持 |
| predict_ranking | **喪失** |
| PredictionBundle | race_info へ部分マップ。World 分類用 meta 全文は非伝播 |
| Single explain | mapper 独自 meta（confidence_band 等）。CE meta 非直結 |

### Score 詳細（PE→CE）

| フィールド | PE | CE 行 | Prediction |
|---|---|---|---|
| base_model_score | Yes | **No** | No |
| adjusted_model_score | Yes | **No** | No |
| win_prob | Yes | **No**（Confidence に置換） | mapper が ranking score 等から再構成しうる |
| model_rank | Yes | as Rank | Yes |
| diagnostic | Yes | **No** | No |

---

## Loss Classification

| Loss ID | 内容 | 性質 |
|---|---|---|
| L1 | PE 生スコアの CE 行非投影 | 圧縮ロス |
| L2 | predict_ranking が world/sub_world/meta を落とす | **公開ビュー破壊** |
| L3 | PredictionBundle が world/sub_world を None 固定 | **明示的契約切断** |
| L4 | Required/Role/Pool が CE に存在しない | 設計上の非包含（喪失ではなく未契約） |
| L5 | SubWorld が candidate=None で生成 | 生成時情報欠落 |
| L6 | explain_payload 既定 OFF / Single が別 explain | 説明経路の二重化・欠落 |

## Critical finding

CE Canonical は World を保持するが、**Prediction 主経路は二段階で破棄**する（L2+L3）。  
したがって「CE に World がある」≠「AI 公開予測が World を持つ」。
