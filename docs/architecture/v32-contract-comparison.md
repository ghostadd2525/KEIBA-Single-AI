# Version32 — Contract Comparison

**Date:** 2026-07-27  
**ADR:** `v32-world-adr.md`  
**Evidence:** V22–V31  

---

## ③ Design contract vs Current contract

| Dimension | Design contract (Original) | Current contract (Production daily) | Gap |
|-----------|----------------------------|-------------------------------------|-----|
| Feature generator | `pace_model_v2` + market merge | `pi_keibanet.features.build_features` | Generator substitution |
| Feature width | ≈ **116** | ≈ **72/74** | −46 design/pace/pre_world/market-refetch cols; +turn(+integrity) |
| Difficulty | Designed formula → variable `race_leg_difficulty` | Missing col → **DEFAULT 0.5** | Semantic saturation |
| Pace collapse | `pace_collapse_risk` | `pace_collapse_risk_v2` only（未ブリッジ） | Name/semantics split |
| Field size | `horse_count` | `field_size`（未エイリアス） | Alias gap |
| Style entropy | `style_entropy` | Absent | Missing signal |
| Leg family | `leg_*` present | Absent | Missing features |
| Pre-world seeds | `pre_world_*` present | Absent | Missing seeds |
| Loader preference | daily/global carrying design cols | **daily first** (slim) | Enforces current gap |
| PE Ranker 28 | Expects difficulty/leg/pace_collapse_risk/horse_count/… | Defaults fill missing | Silent degrade |
| CE meta | Copies frame difficulty | Copies 0.5 | Constant meta |
| World Trigger | Thresholds on variable signals | Operates on constants / MISSING chaos | Mix collapse ≈ midupper 98% |
| Research | Observes Production-path meta | Same DEFAULT leakage | Not an independent truth |

---

## Missing Features（不足 Feature）

設計搬送または Ranker 28 に対し、現行 daily で欠ける主要列:

| Feature | Design role |
|---------|-------------|
| `race_leg_difficulty` | World Trigger difficulty; Ranker 28 |
| `leg_upset_risk` / `leg_favorite_bias` / `leg_style_fit_bonus` | Ranker 28 / pace family |
| `leg_base_chaos` / `leg_field_pressure` | Difficulty components |
| `pace_collapse_risk` | Formula weight 20%; Ranker 28 |
| `style_entropy` | Formula weight 15% |
| `horse_count` | Formula field pressure; Ranker 28 |
| `front_count` | Ranker 28 |
| `unknown_count` / `senko_count`（legacy） | Upset share / style counts |
| `pre_world_*` seed set | Optimizer pre-world seeds |
| market `*_refetched` / some course context | Legacy merge/context（World 直接入力ではない場合あり） |

現行にあって設計名と異なるもの:

| Current | Design counterpart | Bridge contract |
|---------|-------------------|-----------------|
| `pace_collapse_risk_v2` | `pace_collapse_risk` | **None today** |
| `field_size` | `horse_count` | **None today** |

---

## Missing Signals（不足 Signal）

World Trigger / World research が必要とする信号面:

| Signal | Design source | Current Production |
|--------|---------------|--------------------|
| `race_leg_difficulty` / difficulty | pace formula | **DEFAULT 0.5** |
| `chaos_score` | Scorer diagnostic（別断絶） | Often **MISSING** → nz 0 |
| `short_field_pressure` | calc from meta/candidates | Present path（値は別監査） |
| `phase_transition` / `late_stop` / `sustained` / `high_pace` | world_line score from meta | Path exists; quality depends on upstream |
| `style_entropy` / field / collapse components | pace_model | Largely absent on daily |

V25–V27: difficulty 恒常化と chaos MISSING が非 midupper World 不通の主観測要因。

---

## Missing Meta（不足 Meta）

`detect_race_meta` / CE meta 上のギャップ:

| Meta key | Design expectation | Current |
|----------|-------------------|---------|
| `race_leg_difficulty` | Variable race-level difficulty | **0.5 constant** when col missing |
| `chaos_score` | Present for bug/mixed rules | Often absent |
| `pace_collapse_risk` | Copied when on frame | Often default/absent |
| Designed component metas (`leg_*`) | Available on frame for diagnostics | Absent on daily |

Bundle note（V29）: numeric difficulty は Bundle に載らない経路あり。World ラベル永続は別経路。**入力 meta の欠落が本比較の中心。**

---

## Contract identity statement

```text
Design identity  = pace-generated World/Ranker signals, conveyed upstream of PE→CE→World
Current identity = PI history+v2 risk daily schema + DEFAULT absorption + Trigger on degraded meta
```

これらは **同一ファイル名**（`demo_runners_pace_market_features.csv`）を共有するが、**同一契約ではない**（V31）。

---

## Guardrails

- 比較のみ。契約統合の実装なし。
