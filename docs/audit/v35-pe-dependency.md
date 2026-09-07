# Version35 — PE World Dependency Map

**Phase:** V35 PE Dependency Audit  
**Mode:** Research / Audit only  
**Date:** 2026-07-28

---

## 調査対象チェーン

```
Race Context → World → SubWorld → Required → Candidate Pool → PE → CE → Prediction
```

コード上の実際の順序は設計図と **逆転**している箇所がある（World は Score/Rank **後**）。

---

## ② World Dependency — 参照箇所一覧

### A. Core CE / Prediction 経路（Hit・model_rank に直結）

| モジュール | ファイル | World | SubWorld | Required | Candidate Pool |
|------------|----------|:-----:|:--------:|:--------:|:--------------:|
| FeatureLoader | `ai_platform/core/features/...` | — | — | — | — |
| FeatureGenerator | idem | — | — | — | — |
| Scorer | `ai_platform/core/scoring` | — | — | — | — |
| Ranker | `ai_platform/core/ranking` | — | — | — | — |
| ConfidenceBuilder | `ai_platform/core/confidence` | meta 間接 | — | — | — |
| WorldClassifier | `ai_platform/core/world/__init__.py` | **生成** | **生成** | — | — |
| CandidateEvaluationProjector | `candidate_evaluation/__init__.py` | Meta 添付 | Meta 添付 | — | **明示除外** |
| CorePipeline.evaluate | idem | 出力キー | 出力キー | — | — |
| facade.evaluate_candidates | `core_facade.py` | パススルー | パススルー | — | — |
| facade.predict_full_bundle | idem | 含む | 含む | — | — |
| facade.predict_ranking | idem | **欠落** | **欠落** | — | — |
| single_prediction_mapper | `.../single_prediction_mapper.py` | **None 固定** | **None 固定** | — | — |

**WorldClassifier 実装:**

- `build_race_meta` → `legacy_core.detect_race_meta(scored_frame)`
- `classify_world` → `classify_world_line_type(meta)` / `classify_sub_world_type(meta, None)`
- 入力は **既にスコア済み frame + confidence**。ranking を再計算しない。

### B. Win5 Candidate Pool / Purchase 経路（購入・ガード）

| モジュール | ファイル | 参照内容 |
|------------|----------|----------|
| `build_candidate_pool` | `demo_ticket_optimizer_core.py` ~L9412 | `meta` を受け取る。**主ソートは `win_prob`**。World は pool 構成の主因ではない |
| SubWorld route / hard guard | 同ファイル多数 | `is_sub_world_hard_guard_candidate`, `resolve_race_sub_world_intent`, midupper_route 等 — **削除・ルート・再ピック** |
| world_line / observer keys | meta キー列挙 ~L1478 | `observer_world`, `world_line_type`, `resolved_world`, `sub_world_type` 等 — 観測・意図保持 |
| Required / Role | Win5 / challenge 周辺 | Prediction ranking の入力契約外（本 Audit では PE ranking 非依存と判定） |

### C. V34 Shadow AB（Research のみ）

| 項目 | 参照 |
|------|------|
| WIC difficulty 再構成 | `wic_shadow_ab.reconstruct_wic_difficulty` |
| World 再分類 | first-match simulation |
| PE top pick | **`frozen_pe_pick: True`** — Control/Shadow 同一 |

→ Research 経路でも Hit 用 PE pick は World に結合されていない（意図的凍結）。

---

## 参照パターン分類

| パターン | 意味 | 該当 |
|----------|------|------|
| **Producer** | World を生成する | WorldClassifier / legacy classify_* |
| **Annotator** | 既存 Rank にラベルを付ける | Projector WorldMeta |
| **Consumer（ranking）** | World で score/rank を変える | **不在** |
| **Consumer（purchase）** | World/SubWorld で購入候補を絞る | Win5 guards / re_pick |
| **Dropper** | World を破棄 | `predict_ranking`, mapper `None` |

---

## 依存グラフ（実装）

```
                    ┌─────────────┐
 feature frame ────►│ Scorer      │──► Ranker ──► ranking (固定)
                    └─────────────┘
                           │
                           ▼
                    detect_race_meta ──► classify_world / sub_world
                           │
                           ▼
                    CE rows (+ WorldMeta) ──► predict_ranking (world 削除)
                           │
                           ▼ (Win5 only, post-score)
                    build_candidate_pool(win_prob) ──► SubWorld guards ──► Purchase
```

---

## 要約

- **PE/CE ranking は World / SubWorld / Required / Candidate Pool を順位決定に参照しない。**
- World/SubWorld は **生成・添付・購入ガード** に現れる。
- Candidate Pool は **score 後・Win5 側**。Core CE ドキュメントが Pool 非依存を明記。
