# Version31 — Contract Owner

**Date:** 2026-07-27  
**目的:** ⑤ 116 列が正本か / 72 列が正本かを契約レイヤ別に証明する。

---

## Dual-contract verdict

| Layer | Canonical schema | Owner | Status vs Production daily |
|-------|------------------|-------|------------------------------|
| **L1 Design — Pace → World** | **116-col legacy**（pace_model + market merge） | `demo_pace_model_v2` + `demo_merge_market_into_pace` + feature dependency map | **Broken**（daily が 72/74） |
| **L2 Design — Frozen Ranker 28** | JSON feature_names including difficulty/leg/pace_collapse_risk/horse_count | `win5_lgbm_ranker_features.json` | **Broken** on daily（欠列→DEFAULT） |
| **L3 Ops — Race Refresh daily writer** | **72/74 PI `build_features` output** | `pi_keibanet.race_refresh` / V2 Addendum | **Active**（現行 daily 正本ライター） |
| **L4 Runtime — FeatureLoader preference** | Prefer daily over global | `FeatureLoader` | Enforces L3 over L1 residual global 116 |

### One-line answer

- **World / Ranker 設計の正本 = 116（legacy pace CSV）。**  
- **現行 Production daily 運用の正本ライター出力 = 72/74（PI）。**  
- 両者は同一ファイル名を共有しつつ **契約が分裂**している。

---

## Proof — why 116 is design-canonical

1. **Generation graph（V30）**  
   `history → pace_model_v2 → market merge → pace_market CSV → Loader → World`

2. **Frozen Ranker JSON** includes:
   - `race_leg_difficulty`, `leg_upset_risk`, `pace_collapse_risk`,
   - `leg_style_fit_bonus`, `front_count`, `horse_count`, `leg_favorite_bias`

3. **Empirical legacy daily**（≤2026-06-28）: 116 cols, difficulty **variable**（V30: unique_n≥5）

4. **Global CSV on EC2** still 116 with difficulty — residual of design path

---

## Proof — why 72/74 is ops-canonical for daily writes

1. **V2 Operations Addendum（2026-07-24 APPROVED）**  
   Pipeline ends at: `build_features → daily CSV → FeatureLoader`  
   正本として述べているのは **shutuba / runners 行集合**と Refresh 手順。  
   **116 列スキーマ維持は Addendum に無い。**

2. **Code owner of Production daily file**  
   `write_daily_features` → `build_features` → `to_csv(daily_features_path)`

3. **Shadow / bak / 07-25–26 daily** すべて 72/74 — 同一ジェネレータ

4. **PI compare `FEATURE_COMPUTED_COLS`**  
   includes `pace_collapse_risk_v2`, **excludes** `race_leg_difficulty`  
   → PI 比較契約も slim 側に寄っている

---

## Ownership map

| Artifact | Owner | Notes |
|----------|-------|-------|
| `demo_pace_model_v2.py` | Legacy Win5 AI scripts | Not on EC2 `/opt/expect-ai/platform` |
| `demo_merge_market_into_pace.py` | Legacy | 同上 |
| `pi_keibanet.features.build_features` | PI KeibaNet API | History port + v2 risk |
| `pi_keibanet.race_refresh` | PI timer/service | Daily CSV writer |
| `FeatureLoader` | Core overlay | Prefers daily; does not validate 116 |
| `enrich_stable_features` defaults | probability utils | Absorbs missing pace cols |

---

## Docstring conflict（fact）

`features.py`:

> Input/output schema matches Win5AI legacy exactly.

Measured: **does not match** 116-col `demo_runners_pace_market_features` legacy.  
Matches a **history-feature subset + v2 risk columns**, not full pace_model contract.

---

## Implication for “which is correct?”

| If question is… | Answer |
|-----------------|--------|
| World Trigger が読む difficulty の設計正本は？ | **116 / pace_model 列** |
| 今誰が daily ファイルを書いているか？ | **PI 72/74** |
| Loader が実際に読むのは？ | **daily 72/74**（日付が daily にある場合） |
| 契約は健全か？ | **No — L1/L2 vs L3/L4 分裂** |

本 Audit はどちらに「寄せるべきか」の実装判断を行わない（改善禁止）。

---

## Guardrails

- 所有者・正本レイヤの証明のみ。契約統合・実装なし。
