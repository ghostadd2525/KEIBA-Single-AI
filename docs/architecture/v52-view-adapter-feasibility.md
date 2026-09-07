# V52 — View Adapter Feasibility Audit

**Date:** 2026-07-28  
**Scope:** Research / Architecture Audit only  
**Question:** Does `CorePublicBundle → View Adapter → PredictionBundle` suffice for **all** Consumers?  
**Locks:** Prediction / PE / CE / AI / World / Trigger / Signal / CorePublicBundle / PredictionBundle / Production — **変更・実装禁止**

**Inputs:** ADR-050 (V50), Impact (V51), live code + `PredictionBundle.d.ts` + `CorePipeline.evaluate`

---

## Verdict (summary)

**No. Pure View Adapter from CorePublicBundle alone cannot rescue all Consumers.**

Evidence: PredictionBundle 契約の必須ブロックのうち、`race_info` と `betting_recommendations` は CE に存在しない。現行 Mapper は **CE ではなく** `prediction_response`（= CE互換view + **Single Bet Builder**）を入力とする。Mock / catalog list は CE 非経由。

**Governance: C** — Adapterだけでは成立しない  
→ `v52-governance.md`

---

## Scope of “View Adapter”

本監査の Adapter 定義（V51 用語に合わせた厳密形）:

```
Input:  CorePublicBundle のみ（evaluate_candidates の戻り）
Output: PredictionBundle（single-prediction-bundle/2.0）
```

**含めないもの（別パイプライン）:**

| Extra | Evidence |
|---|---|
| `predict_ranking` / `predict_confidence` 経由の再投影 | facade は CE 投影だが Product 入口ではない |
| `build_bet_plan` / `build_bets` | `ai_platform/single/prediction/__init__.py` |
| `get_race` / catalog race_meta | `single_prediction_mapper._race_info` |
| Mock fixtures / `catalog_to_prediction_bundle` | `prediction_adapter.MockPredictionSource` |

これらを Adapter に混ぜた瞬間、それは「View Adapter」ではなく **Product Assembly Pipeline** になる。本監査は前者のみを判定する。

---

## ① Consumer Compatibility（要約）

詳細: `v52-consumer-compatibility.md`

| Consumer | Adapter alone? | Evidence-based reason |
|---|---|---|
| HTTP API (detail Real) | **No** | Bundle 要 `race_info` + `betting_recommendations`; CE に無し |
| HTTP API (list / catalog) | **No** | list-projection は catalog; CE 非呼び出し |
| GUI | **No** | mark / race_info / ai_confidence / bets / explain 依存 |
| Single | **N/A→No as Bundle consumer** | Single は Bundle Consumer ではなく **Bet 付き Producer**; CE 直結では bets 欠落 |
| Win5 Optimizer | **N/A** | evaluate_candidates / Bundle 非使用 |
| CLI (`single_ai`) | **No** | `get_prediction` → bets 含む prediction_response |
| Functions | **No** | Ready=runners; 実UIは mark/race_info; Mock/PI 経路併存 |
| Conversation | **No** | Bundle の evaluation / ai_confidence / explain / race_info |
| Challenge | **Partial→No alone** | mark は Rank から合成可だが **保存 Bundle / PI** 経路は Adapter 外 |
| Mock | **No** | CE 非ソース; Adapter 対象外 |
| Research (CE direct) | **N/A** | 既に CE; Bundle Adapter 不要 |

---

## ② Information Projection（要約）

詳細: `v52-projection-analysis.md`

| Class | Examples |
|---|---|
| そのまま投影 | `race_id`, `core_version`, `world`→`evaluation.world`, `sub_world`, Rank→model_rank, Confidence→win_prob/score 系 |
| 変換 | candidates[] → evaluation.runners[]; overall_confidence → ai_confidence.score; Rank→mark |
| 削除（Bundleに出さないと失われる） | `context.*`, `meta`（detect_race_meta）, per-candidate WorldMeta, `explain_payload`（flag時） |
| 追加生成（CEに無い） | `schema_version`, `race_info.*`, `mark`/`mark_rank`, `betting_recommendations`, `product_version`, `generated_at`, band/narrative, catalog UI 補助 |

---

## ③ One-way Projection

| Direction | Feasible? | Notes |
|---|---|---|
| CE → Bundle（部分） | **Partial one-way** | ranking/confidence/world は一方向写像可能 |
| CE → Bundle（完全契約） | **No** | 追加生成フィールドが必須 |
| Bundle → CE | **No** | race_info/bets/marks から CE `meta`/`context`/真の Confidence 構造は復元不可 |
| 逆変換が必要な Consumer | **なし（設計上）** | 問題は逆変換不足ではなく **正向の情報不足** |

結論: 「完全な一方向変換で Bundle 契約を満たす」は **不成立**。一方向で足りるのは **部分集合** のみ。

---

## ④ Hidden Dependencies（要約）

### PredictionBundle にしか無い（CE 非由来）

- `race_info`（date/venue/race_no/distance/surface/…）— Mapper は `get_race` + catalog meta
- `betting_recommendations` — Single `build_bet_plan` / `build_bets`
- `evaluation.runners[].mark` / `mark_rank` — Mapper `_MARK_BY_RANK`（Rank からの **Product 規則**）
- `schema_version` / `product_version` / Bundle 用 `generated_at`
- Mock / list-projection 専用フィールド・空 runners 許容パターン

### CorePublicBundle にしか無い（現行 Bundle に載らない／落とされる）

- `context`（feature_source path, feature_metadata）
- `meta`（`detect_race_meta` 出力）
- candidate `WorldMeta` / `SubWorldMeta`
- `confidence_factors` の CE 生形（Bundle は factors 配列へ部分転記は現状 Mapper 経由）
- `explain_payload`（Explain v2 flag ON 時のみ CE に付与; 現行 Mapper は別合成 explain）
- 現行 Mapper は **world を CE から取らず None 固定**（欠落は Adapter で埋められるが、今日は未実施）

---

## ⑤ Adapter Sufficiency

### Adapter だけで解ける（CE 部分集合）

| Problem | How |
|---|---|
| `evaluation.world = None`（View defect） | CE.`world` / `sub_world` をそのまま投影 |
| Ranking → runners | CandidateID/HorseNumber/Rank/Confidence → horse_*/model_rank/win_prob |
| overall confidence → ai_confidence.score | CE.`overall_confidence` |
| Research が CE を既に見る経路 | Adapter 不要（変更対象外） |

### Adapter だけでは解けない

| Problem | Missing dependency (code) |
|---|---|
| 完全な `race_info` | `ai_platform.race_data.get_race` + catalog meta（CE 外） |
| `betting_recommendations` | `bet_strategy` + `bet_builder`（CE 外 Product） |
| HTTP list / catalog projection | `catalogToPredictionBundle` / mocks（CE 非経由） |
| Mock engine | `MockPredictionSource`（CE 非経由） |
| Challenge 履歴 | DB `predictions.bundle_json` / PI fetch（再推論 Adapter ではない） |
| GUI Contract 全充足 | 上記欠落フィールドを Consumer が参照 |
| Single CLI 同等出力 | bets 欠落で現行 `prediction_response` 非同等 |

---

## Relation to V51

| V51 claim | V52 refinement |
|---|---|
| Dual-publish + CE→View Adapter が必要 | Dual は依然有効候補 |
| Adapter で Consumer 救済（含意） | **証明されず** — Adapter alone = **不成立** |
| Governance C（影響広範囲） | 本監査は別軸: **実現可能性 C** |

移行するなら次の設計候補は View Adapter **単体ではなく**  
`CE + RaceData + (optional) BetBuilder → Bundle` の **Assembly**（別 Decision）。それは本フェーズの「Adapterだけ」定義外。

---

## Expected Next Action（実装禁止）

1. Assembly Pipeline 設計 vs Pure Adapter の用語分離  
2. Bundle 契約を「View 必須フィールド」と「Product 必須フィールド」に分割監査（別フェーズ）  
3. **実装しない** — Decision Gate 前

---

*V52 Feasibility — research only. No code changes.*
