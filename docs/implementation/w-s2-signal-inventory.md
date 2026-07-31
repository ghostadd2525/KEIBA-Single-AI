# W-S2 Signal Inventory（Must only）

**Date:** 2026-07-28  
**Version:** 59  
**Scope:** Must 概念の供給インベントリ（Aux / Exclusion 対象外）

---

## Inventory columns

| Col | Meaning |
|---|---|
| Must | V44 Must concept |
| World | Owning world |
| Available | 実コード/実データで値を得られるか |
| Missing | 供給経路が無いか |
| Restore Status | Restored / Missing / Unknown（Feature restore 文脈；Derived は値があれば Restored） |
| Data Source | CSV / Feature / Meta / Derived |
| Evidence | 根拠パス |

---

## Full Must inventory

| Must | World | Available | Missing | Restore Status | Data Source | Evidence |
|---|---|---|---|---|---|---|
| top_gap↑ | core | Yes | No | Restored | Derived | `w_s1...ranking_concepts`；`get_context_top_gap` in `demo_ticket_optimizer_core.py` |
| ability_separation↑ | core | Yes | No | Restored | Derived | top1−median `win_prob` on 285 runners |
| upper_ability_band | midupper | Yes | No | Restored | Derived | top3 share of `win_prob` |
| development_pressure | midupper | Yes* | When unrestored | Restored 240 / Missing 45 | Feature | phase / sfp / high_pace via FeatureLoader+Scorer restore |
| aptitude_fit | midupper | No | **Yes** | Missing | — | 非Proxy本信号なし（Proxyは本フェーズ対象外） |
| mid_eval_band_open↑ | midhole | Yes | No | Restored | Derived | mid-rank `win_prob` share |
| top_monopoly↓ | midhole | Yes | No | Restored | Derived | top1 / sum `win_prob` |
| chaos↑ | rank7 | Yes* | When unrestored | Restored 240 / Missing 45 | Feature | Scorer `_diagnostic.chaos_score` |
| pace_conflict↑ | rank7 | Yes* | When unrestored | Restored 240 / Missing 45 | Feature | high_pace ∨ sfp ∨ phase（restore） |
| ability_subordinate↑ | rank7 | Yes | No | Restored | Derived | from top_gap low polarity input |
| multi_path_active | mixed | Yes | No | Restored | Derived | Shadow `primary_matches` count ≥ 2 |
| unexplained_single | mixed | No | **Yes** | Missing | — | 明示フラグなし（W-S1） |
| exception_flag | bug | No | **Yes** | Missing | — | corpus/method: absent；must_gap 285/285 |

\* Available when Feature restore succeeds（240/285）。

---

## Data Source roll-up

| Source | Must concepts |
|---|---|
| Derived | top_gap, ability_separation, upper_ability_band, mid_eval_band_open, top_monopoly, ability_subordinate, multi_path_active |
| Feature | development_pressure, chaos, pace_conflict（restore path） |
| Meta | （Must 直接供給なし — field_size/distance は Proxy 用途のため本表に非掲載） |
| CSV | FeatureLoader daily/global CSV は Feature restore の下位入力（直接 Must キーではない） |

---

## Restore coverage (Feature-backed Must)

| Metric | n |
|---|---:|
| Races with Feature restore OK | 240 |
| Races with Feature restore fail | 45 |
| Races with exception_flag | 0 |

---

## Missing Must list（Blocked axes）

1. `aptitude_fit`（midupper）  
2. `unexplained_single`（mixed OR 枝）  
3. `exception_flag`（bug）  

---

*Version59 — inventory only. No implementation.*
