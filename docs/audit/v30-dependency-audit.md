# Version30 — Dependency Audit

**Date:** 2026-07-27  
**Hypothetical only:** `add_win5_leg_difficulty_features` を FeatureGenerator 経路へ戻した場合の依存洗い出し  
**実装なし**

## Module dependency

| Module | Required for FG restore? | Production status |
|--------|:------------------------:|-------------------|
| `demo_pace_model_v2.add_win5_leg_difficulty_features` | Yes | **Not on** `/opt/expect-ai/platform` PYTHONPATH |
| `demo_pace_model_v2.safe_series` / helpers | Yes（同ファイル内） | 同上 |
| Upstream `attach_win5_leg_from_races` | Optional if `win5_leg` already on frame | daily には `win5_leg` あり |
| Upstream `add_basic_race_counts` / `add_style_entropy` / `add_pace_collapse_risk` | Soft（欠損時は formula 内 default） | daily に style_entropy / pace_collapse_risk **欠** |
| `demo_probability_feature_utils.enrich_stable_features` | Order matter | 既存 FG が呼ぶ。**設計値があれば尊重、無ければ 0.5** |

### Import / deploy gap

FeatureGenerator が `from demo_pace_model_v2 import add_win5_leg_difficulty_features` する前提でも、現状 EC2 platform に当該 `.py` が無い。  
復元候補は「モジュール同梱」か「等価式の別モジュール移設」だが、本 Audit では実施しない。

---

## Input feature contract（designed formula）

Source: `demo_pace_model_v2.add_win5_leg_difficulty_features`

```text
leg_base_chaos      ← win5_leg map {1:0.46 … 5:0.64}; missing→0.50
leg_field_pressure  ← (horse_count-8)/10 clip; horse_count missing→groupby count or 12
upset_share         ← (sashi+oikomi+unknown)/horse_count
leg_upset_risk      ← 0.35*leg_base_chaos + 0.20*leg_field_pressure
                      + 0.20*pace_collapse_risk + 0.15*style_entropy + 0.10*upset_share
race_leg_difficulty ← mean(leg_upset_risk) by race_id
(+ side outputs: leg_favorite_bias, leg_style_fit_bonus; needs nige_prob/front_prob optional)
```

### Input columns

| Input | Used for | Missing behavior in formula |
|-------|----------|-----------------------------|
| `win5_leg` | leg_base_chaos | NA → 0.50 |
| `horse_count` | field_pressure, upset_share | derive from race_id count or 12 |
| `race_id` | aggregation / horse_count fallback | without race_id: difficulty = leg_upset_risk rowwise |
| `pace_collapse_risk` | 20% weight | safe_series → 0 |
| `style_entropy` | 15% weight | → 0 |
| `sashi_count` / `oikomi_count` / `unknown_count` | upset_share | → 0 |
| `nige_prob` / `front_prob` | leg_style_fit_bonus only | → 0（Trigger は未読） |

---

## Current FeatureLoader daily frame（EC2 2026-07-26）

**Present (usable):** `win5_leg`, `sashi_count`, `oikomi_count`, `nige_count`, `senkou_count`, `field_size`, `running_style`, `race_id`

**Absent vs designed inputs:**

| Designed | Daily status | Notes |
|----------|--------------|-------|
| `race_leg_difficulty` | **ABSENT** | 復元対象そのもの |
| `pace_collapse_risk` | **ABSENT** | `pace_collapse_risk_v2` のみ存在（別名・契約未接続） |
| `style_entropy` | **ABSENT** | 15% 項が恒常 0 |
| `horse_count` | **ABSENT** | `field_size` はあるが formula は読まない |
| `unknown_count` | **ABSENT** | upset_share が過小 |
| `front_count` | **ABSENT** | （counts は nige/senkou 系あり） |
| `nige_prob` / `front_prob` | **ABSENT** | side feature only |
| `leg_*` intermediates | **ABSENT** | |

### Partial-run implication（監査事実）

daily 上で式だけを機械実行すると:

- `win5_leg` + 推定頭数 + style counts で **ある程度の分散**は出うる
- `pace_collapse_risk` / `style_entropy` 欠落により **設計フル式の 35% 重み分が 0**
- `horse_count` 未配線のままなら field_pressure は race_id count / 12 依存（`field_size` 非使用）
- 結果は **旧 116 列 daily 上の設計値と数値一致しない**可能性が高い

---

## Prerequisites if wired into FeatureGenerator

1. **Module availability** on Core PYTHONPATH  
2. **Call order:** formula **before** or such that `enrich_stable_features` does not overwrite existing non-null `race_leg_difficulty`（現行 enrich は既存列尊重）  
3. **Input completeness policy:**  
   - A: フル式前提で欠列を先に生成（style_entropy / pace_collapse_risk）  
   - B: 部分式のまま許容（設計差分を受容）  
4. **Naming bridge:** `pace_collapse_risk_v2` ↔ `pace_collapse_risk`、`field_size` ↔ `horse_count` は現状 **未契約**  
5. **Side columns:** `leg_upset_risk` 等を frame に残すか否か（モデル 28 列外・World meta は `race_leg_difficulty` のみ）

---

## Insufficient columns checklist（restore blockers）

| Gap ID | Gap | Blocks “designed-equivalent” restore? |
|--------|-----|:--------------------------------------:|
| D1 | `demo_pace_model_v2.py` not on EC2 platform | Yes（呼出不能） |
| D2 | daily missing `pace_collapse_risk` | Yes（フル設計一致） |
| D3 | daily missing `style_entropy` | Yes（フル設計一致） |
| D4 | `horse_count` vs `field_size` unwired | Partial |
| D5 | `unknown_count` missing | Partial |
| D6 | Restoration locus unresolved（FG vs daily CSV pipeline） | Yes（どこに戻すか未決） |

---

## Guardrails

- 依存の列挙のみ。配線・別名マッピング・実装なし。
