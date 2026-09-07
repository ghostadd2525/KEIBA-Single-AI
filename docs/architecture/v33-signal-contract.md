# Version33 — Signal Contract Spec

**Date:** 2026-07-27  
**Parent:** `v33-world-input-contract.md`  
**Status:** Design definition only  

凡例:

- **Required** = World Input Contract 充足に必要  
- **Optional** = 分類に直接不要だが設計・監査・派生に有用  
- **DEFAULT可否** = World 契約上の扱い（技術フォールバックとは別。`v33-default-policy.md`）

---

## L1 — Primary Trigger inputs

### 1. `difficulty` / `race_leg_difficulty`

| Field | Spec |
|-------|------|
| 名称 | `race_leg_difficulty`（alias: `difficulty`） |
| 型 | `float` |
| 値域 | `[0.0, 1.0]` |
| 生成責務 | 設計式 `add_win5_leg_difficulty_features`（または契約等価） |
| 供給責務 | Signal Service → frame/meta へ race 単位で供給 |
| Consumer | World Trigger（`classify_world_line_type`）, CE meta, Research, Ranker 28 |
| 必須 | **Required** |
| Optional | — |
| DEFAULT可否 | **World 契約上 Forbidden**（欠落フォールバック 0.5 を正式値としない） |

設計式要約:  
`leg_upset_risk = 0.35*leg_base_chaos + 0.20*leg_field_pressure + 0.20*pace_collapse_risk + 0.15*style_entropy + 0.10*upset_share`  
`race_leg_difficulty = mean(leg_upset_risk by race_id)`

---

### 2. `chaos` / `chaos_score`

| Field | Spec |
|-------|------|
| 名称 | `chaos_score` |
| 型 | `float` |
| 値域 | `[0.0, 1.0]` |
| 生成責務 | PE/adjustment（現行: `build_pace_style_features` → diagnostic） |
| 供給責務 | Signal Service が **meta 到達まで**供給（現状断絶: V26） |
| Consumer | World Trigger, short_field 合成の一部, Research |
| 必須 | **Required** |
| Optional | — |
| DEFAULT可否 | **Forbidden as World policy**（`nz(...,0.0)` の恒常 0 も正式値としない） |

---

### 3. `field_pressure` / `short_field_pressure`

| Field | Spec |
|-------|------|
| 名称 | `short_field_pressure` |
| 型 | `float` |
| 値域 | `[0.0, 1.0]`（実装 clamp 前提） |
| 生成責務 | Trigger 補助関数 `calc_short_field_pressure(meta, candidate)` |
| 供給責務 | meta/candidate 上の入力（traffic, chaos, pace_collapse, field 文脈等）が先行充足 |
| Consumer | World Trigger（直接） |
| 必須 | **Required**（派生だが Trigger 直接読取） |
| Optional | — |
| DEFAULT可否 | **Conditional** — 入力欠落で 0 近傍に潰れる場合は *unsatisfied*；意図的中立 DEFAULT は認めない |

※ pace 成分 `leg_field_pressure` は別信号（L0）。混同禁止。

---

## L2 — Derived Trigger scores (`calc_world_line_score`)

### 4. `phase` / `phase_transition`

| Field | Spec |
|-------|------|
| 名称 | `phase_transition` |
| 型 | `float` |
| 値域 | `[0.0, 1.0]` 相当 |
| 生成責務 | `0.30*high_pace + 0.25*late_stop + 0.25*sustained + 0.20*traffic` |
| 供給責務 | 構成要素 meta/candidate の供給 |
| Consumer | World Trigger |
| 必須 | **Required**（構成要素の充足を含む） |
| Optional | — |
| DEFAULT可否 | **Forbidden as sole World policy**（構成欠落由来の擬似低値を正式としない） |

### 5. `late_stop`

| Field | Spec |
|-------|------|
| 名称 | `late_stop`（元: `late_stop_risk_score`） |
| 型 | `float` |
| 値域 | `[0.0, 1.0]` |
| 生成責務 | pace/world-line feature 生成側 |
| 供給責務 | meta または candidate へ供給 |
| Consumer | `calc_world_line_score` → Trigger（midhole 等） |
| 必須 | **Required** |
| Optional | — |
| DEFAULT可否 | **Forbidden as World policy** |

### 6. `sustained`

| Field | Spec |
|-------|------|
| 名称 | `sustained`（元: `sustained_run_possible_score`） |
| 型 | `float` |
| 値域 | `[0.0, 1.0]` |
| 生成責務 | pace/world-line feature 生成側 |
| 供給責務 | meta または candidate へ供給 |
| Consumer | Trigger（midhole 等） |
| 必須 | **Required** |
| Optional | — |
| DEFAULT可否 | **Forbidden as World policy** |

### 7. `high_pace`

| Field | Spec |
|-------|------|
| 名称 | `high_pace`（composite） |
| 型 | `float` |
| 値域 | `[0.0, 1.0]` |
| 生成責務 | max(`pace_collapse_risk`, `high_pace_score`, candidate pace fit) |
| 供給責務 | 構成 meta/candidate |
| Consumer | Trigger（rank7 等）, phase 合成 |
| 必須 | **Required** |
| Optional | — |
| DEFAULT可否 | **Forbidden as World policy** |

### 8. `world_line` / `world_line_score`

| Field | Spec |
|-------|------|
| 名称 | `world_line_score`（+ `world_integrated`, `traffic`） |
| 型 | `float` / `dict[str,float]` |
| 値域 | 各成分 `[0.0, 1.0]` 相当 |
| 生成責務 | `calc_world_line_score` |
| 供給責務 | 構成スコアの供給 |
| Consumer | 観測・下流；Trigger は主に分解成分を使用 |
| 必須 | **Optional**（分解成分が Required なら bundle 自体は Optional） |
| Optional | Yes（監査・Research） |
| DEFAULT可否 | **Allowed for observability only** |

---

## L0 — Prerequisites (designed difficulty / pace)

### 9. `pace_collapse` / `pace_collapse_risk`

| Field | Spec |
|-------|------|
| 名称 | `pace_collapse_risk` |
| 型 | `float` |
| 値域 | `[0.0, 1.0]` |
| 生成責務 | pace_model（設計） |
| 供給責務 | frame → meta（`detect_race_meta` がコピー） |
| Consumer | difficulty 式, high_pace 合成, short_field 合成, Ranker 28 |
| 必須 | **Required**（設計 difficulty / high_pace 前提） |
| Optional | — |
| DEFAULT可否 | **Forbidden as designed-signal substitute** |
| Alias note | `pace_collapse_risk_v2` は **未契約**。ブリッジ契約なしでは代替不可 |

### 10. `style_entropy`

| Field | Spec |
|-------|------|
| 名称 | `style_entropy` |
| 型 | `float` |
| 値域 | `[0.0, 1.0]`（設計式前提） |
| 生成責務 | pace_model `add_style_entropy` |
| 供給責務 | frame（difficulty 式入力） |
| Consumer | difficulty 式; formation 観測の一部 |
| 必須 | **Required**（設計 difficulty） |
| Optional | — |
| DEFAULT可否 | **Forbidden**（0 埋め部分式は設計不適合） |

### 11. `leg_field_pressure`（pace field pressure）

| Field | Spec |
|-------|------|
| 名称 | `leg_field_pressure` |
| 型 | `float` |
| 値域 | `[0.0, 1.0]` = clip((horse_count-8)/10) |
| 生成責務 | `add_win5_leg_difficulty_features` 内 |
| 供給責務 | 中間。最終必須は `race_leg_difficulty` |
| Consumer | difficulty 式 |
| 必須 | **Required-as-input**（式実行時） |
| Optional | 永続列としては Optional |
| DEFAULT可否 | horse_count 欠落時の式内 12 は **実装安全弁**；契約上は `horse_count` 供給を求める |

### 12. Supporting L0

| 名称 | 型 | 値域 | 必須 | DEFAULT可否 | 役割 |
|------|----|------|------|-------------|------|
| `win5_leg` | int/float | 1..5（設計 map） | Required-as-input | Forbidden（欠落→0.50 base は部分式） | `leg_base_chaos` |
| `horse_count` | int/float | ≥1 | Required-as-input | Forbidden as silent alias without contract | field pressure |
| `field_size` | int/float | ≥1 | Optional until **alias contract** | — | 現状未ブリッジ |
| `sashi_count` / `oikomi_count` / `unknown_count` | numeric | ≥0 | Required-as-input for full formula | Forbidden zero-fill as design-complete | upset_share |
| `leg_upset_risk` | float | [0,1] | Optional（中間） | — | difficulty 材料 |
| `leg_base_chaos` | float | [0,1] | Optional（中間） | — | difficulty 材料 |

---

## Related meta used by L2 (supply contract)

| 名称 | 必須 | DEFAULT可否 | Note |
|------|------|-------------|------|
| `late_stop_risk_score` | Required | Forbidden as World policy | → `late_stop` |
| `sustained_run_possible_score` | Required | Forbidden as World policy | → `sustained` |
| `high_pace_score` | Required-as-input | Forbidden as sole substitute if collapse also missing | → `high_pace` |
| `traffic_score` | Required-as-input for phase | Forbidden as World policy | → phase / short_field |
| `world_load_score` | Optional | Allowed | → world_integrated |

---

## Consumer map (summary)

| Consumer | Signals |
|----------|---------|
| `classify_world_line_type` | difficulty, chaos, short_field_pressure, phase, late_stop, sustained, high_pace |
| `calc_world_line_score` | late_stop*, sustained*, high_pace*, traffic*, world_load* |
| `calc_short_field_pressure` | traffic, chaos, pace_collapse, field context, … |
| `detect_race_meta` | copies difficulty, pace_collapse, … from frame |
| Research instrumentation | same contract keys（Production と同一） |
| Ranker 28 | difficulty, leg_*, pace_collapse_risk, horse_count, …（World 外だが同一搬送に依存） |

---

## Guardrails

- Spec only. No Trigger/World/code changes.
