# Version31 — Column Removal Audit

**Date:** 2026-07-27  
**Compare:** local `2026-06-28` daily (116) vs `2026-07-25` daily (72)  
**Mechanism:** 非生成（generator gap）。116 ファイルを入力とした drop 変換は未検出。

---

## ② 削除（欠落）列一覧 — 46 columns

### A. pace_model_v2 / pre-world seed（World・難易度設計の中核）

| Column |
|--------|
| `race_leg_difficulty` |
| `leg_base_chaos` |
| `leg_field_pressure` |
| `leg_upset_risk` |
| `leg_favorite_bias` |
| `leg_style_fit_bonus` |
| `pace_collapse_risk` |
| `style_entropy` |
| `horse_count` |
| `front_count` |
| `unknown_count` |
| `senko_count` |
| `pace_type` |
| `is_nige` / `is_senkou` / `is_sashi` / `is_oikomi` |
| `pace_collapse_flow_seed` |
| `phase_chain_seed` |
| `route_position_shift_seed` |
| `traffic_release_flow_seed` |
| `pre_world_closer_share` |
| `pre_world_deletion_sensitivity_score` |
| `pre_world_flow_version` |
| `pre_world_front_share` |
| `pre_world_pacefit_stability_score` |
| `pre_world_route_dependency_score` |
| `pre_world_source_stage` |
| `pre_world_spread_need_score` |

### B. market merge / refetch 系

| Column |
|--------|
| `odds_refetched` |
| `popularity_refetched` |
| `horse_number_refetched` |
| `frame_number_refetched` |
| `horse_url_m` |

### C. race context / compat

| Column |
|--------|
| `_runner_date_dt` |
| `course_inout` / `course_layout` / `course_layout_race` / `course_race` / `course_turn` / `course_variant` |
| `race_number_race` / `race_url` |
| `target_distance_race` / `target_surface_race` |
| `track_condition_numeric` |

### D. Added in slim (not removals)

| Column | Notes |
|--------|-------|
| `turn` | 07-25+ |
| `turn_race` | 07-25+ |
| `display_order` | EC2 07-26（74 列化） |
| `horse_number_source` | EC2 07-26（74 列化） |

---

## ③ 削除理由

| Hypothesis | Judgment | Evidence |
|------------|----------|----------|
| 意図的 Slim スクリプトで 46 列 drop | **Unsupported** | drop リスト／Slim モジュール未発見 |
| pace_model を意図停止して Trigger 固定 | **Unsupported** | 当該コメント・フラグなし |
| **生成器が history のみを移植** | **Supported** | `features.py` docstring: *Ported from demo_runners_history_features.py*；`add_win5_leg_difficulty_features` 非呼出 |
| Race Refresh が daily 正本ライターになった | **Supported** | V2 Addendum: shutuba→`build_features`→daily CSV |
| docstring「legacy exact」 | **Contradicted by schema** | 116 legacy ≠ 72 PI 出力 |

明示 drop（コード）:

1. `build_features` 末尾: `_runner_date_dt`
2. `_add_risk_features` 末尾: 一時フラグ `is_nige`, `is_senkou`, `is_sashi_flag`, `is_oikomi`  
   （legacy 116 では同種フラグが残列として存在したケースあり）

**結論:** 「削除理由」= **PI daily 生成が pace_model 段を含まないこと**による欠落。意図的な World 列パージ文書は無い。

---

## ④ 個別追跡 — 設計重要列

| Column | Legacy origin | Current daily | Where lost |
|--------|---------------|---------------|------------|
| `race_leg_difficulty` | `add_win5_leg_difficulty_features` | ABSENT | `build_features` never calls pace_model |
| `pace_collapse_risk` | `add_pace_collapse_risk` in pace_model | ABSENT | 同上；代替 `pace_collapse_risk_v2` のみ |
| `style_entropy` | `add_style_entropy` in pace_model | ABSENT | 同上 |
| `horse_count` | pace / race meta | ABSENT | 同上；代替 `field_size` |
| `leg_upset_risk` 等 | pace_model | ABSENT | 同上 |
| `pace_collapse_risk_v2` | PI `_add_risk_features` | PRESENT | 設計名と不一致 |

---

## Explicit drop ≠ missing pace set

| Code drop | Covers race_leg_difficulty? |
|-----------|:---------------------------:|
| `_runner_date_dt` | No |
| temporary `is_*` | No |

pace 設計列は **drop 対象ではなく、生成グラフから外れている**。

---

## Guardrails

- 列挙・理由分類のみ。CSV 復元・列追加実装なし。
