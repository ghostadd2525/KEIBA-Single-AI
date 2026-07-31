# Version31 — Schema Diff (07-25 before / after)

**Date:** 2026-07-27  

---

## ⑥ Timeline

| Date / artifact | n_cols | `race_leg_difficulty` | Writer (inferred) |
|-----------------|-------:|:---------------------:|-------------------|
| Local daily ≤ `2026-06-28` | 116 | Yes | Legacy pace_model → merge_market → daily copy |
| Local daily `2026-07-01`–`07-24` | （アーカイブ無し） | — | — |
| EC2 bak `20260724205804` | 72 | No | Already PI slim before unblock merge |
| EC2 / local daily `2026-07-25` | 72 | No | `race_refresh` / `build_features` |
| EC2 Shadow `2026-07-25` | 72 | No | Same PI generator |
| EC2 daily `2026-07-26` | 74 | No | PI + `display_order`, `horse_number_source` |
| EC2 global `demo_runners_pace_market_features.csv` | 116 | Yes | Legacy residual（Loader 下位優先） |

Local June–July daily folders present:  
`06-06,06-07,06-13,06-14,06-20,06-21,06-27,06-28`（全て 116）→ `07-25`（72）。

---

## Column counts

| Schema | Count | Delta vs 116 |
|--------|------:|-------------:|
| Legacy daily (≤06-28) | 116 | 0 |
| Slim daily 07-25 | 72 | −46 / +2 net path dependent |
| Slim daily 07-26 (EC2) | 74 | 72 + 2 integrity cols |
| Global (EC2) | 116 | legacy retained |

Net 116→72: **removed 46**, **added 2** (`turn`, `turn_race`).

---

## Pace / World signal presence matrix

| Signal | ≤06-28 daily | 07-25 daily | 07-26 daily | Global |
|--------|:------------:|:-----------:|:-----------:|:------:|
| `race_leg_difficulty` | Y | N | N | Y |
| `pace_collapse_risk` | Y | N | N | Y |
| `pace_collapse_risk_v2` | Y* | Y | Y | Y |
| `style_entropy` | Y | N | N | Y |
| `horse_count` | Y | N | N | Y |
| `field_size` | Y | Y | Y | Y |
| `leg_upset_risk` | Y | N | N | Y |
| `win5_leg` | Y | Y | Y | Y |
| `pre_world_*` seeds | Y | N | N | Y |

\* global/legacy may contain both `pace_collapse_risk` and `*_v2`.

---

## Frozen Ranker 28 vs schemas

Source: `models/win5_lgbm_ranker_features.json`（local win5-ai；EC2 `models/` は本 Audit 時点で未検出）

| Ranker feature | In 116 legacy daily | In 72/74 PI daily |
|----------------|:-------------------:|:-----------------:|
| `race_leg_difficulty` | Y | **N** |
| `leg_upset_risk` | Y | **N** |
| `pace_collapse_risk` | Y | **N** |
| `leg_style_fit_bonus` | Y | **N** |
| `front_count` | Y | **N** |
| `horse_count` | Y | **N** |
| `leg_favorite_bias` | Y | **N** |
| `nige_count` | Y | Y |
| history / market basics | Y | Y（概ね） |

→ 07-25 以後 daily は **凍結 28 のうち pace/leg 系を欠いたまま** Loader に入り、`enrich_stable_features` デフォルトに依存（V28/V29）。

---

## PI test contract note（事実）

`tests/test_pipeline.py::test_feature_columns_match_model_schema` は  
`pace_collapse_risk_v2` 等を「model features」として検査し、**`race_leg_difficulty` を要求しない**。  
これは凍結 JSON（上記）と **不一致** — PI 側の「model schema」言明が Ranker 正本と分岐している証拠。

---

## Ops event 07-25（列とは別軸）

`docs/ops/v2-publish-unblock-2026-07-25.md`:

- 主目的: 欠落 race の Shadow→Production **行マージ**（予測公開）
- Backup も既に 72 列
- **列スキーマ復元は当該オペの対象外**

---

## Guardrails

- 差分記録のみ。スキーマ修復なし。
