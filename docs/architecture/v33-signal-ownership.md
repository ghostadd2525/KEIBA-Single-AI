# Version33 — Signal Ownership

**Date:** 2026-07-27  
**Parent:** `v33-world-input-contract.md`  
**Status:** Design ownership map only（実装配置の強制ではない）

用語:

| Term | Meaning |
|------|---------|
| **Owner** | 契約・意味の責任者（何が正しい信号か） |
| **Producer** | 値を計算する実装モジュール（現状 / 設計） |
| **Transport** | 値を World 手前まで運ぶ経路 |
| **Consumer** | 値を読む主体 |

P4 下では将来 **Signal Service** が Transport/供給の統合境界になる。下表の Producer は現状監査に基づく。

---

## Ownership table

### Primary / Derived (World-facing)

| Signal | Owner | Producer (design) | Producer (current fact) | Transport (design) | Transport (current fact) | Consumer |
|--------|-------|-------------------|-------------------------|--------------------|--------------------------|----------|
| `race_leg_difficulty` | World Input Contract / Pace Design | `add_win5_leg_difficulty_features` | **Missing on daily** → `enrich_stable_features` 0.5 | Signal Service → frame → meta | daily 72/74 → DEFAULT → meta | Trigger, CE, Research, Ranker |
| `chaos_score` | World Input Contract / PE diagnostics | `build_pace_style_features` | diagnostic のみ生成 | Signal Service → **meta** | diagnostic で停止（V26） | Trigger, Research |
| `short_field_pressure` | World Trigger calc | `calc_short_field_pressure` | same | meta/candidate inputs | same（入力品質劣化あり） | Trigger |
| `phase_transition` | World Trigger calc | `calc_world_line_score` | same | derived in-process | same | Trigger |
| `late_stop` | World Input Contract | pace/world-line features → `late_stop_risk_score` | frame/meta 依存 | Signal Service → meta/candidate | 既存経路（カバレッジ別監査） | Trigger via L2 |
| `sustained` | World Input Contract | `sustained_run_possible_score` | frame/meta 依存 | Signal Service → meta/candidate | 既存経路 | Trigger via L2 |
| `high_pace` | World Input Contract | composite of collapse / high_pace_score / pace fit | collapse 欠落時は劣化 | Signal Service + L2 | partial | Trigger via L2 |
| `world_line_score` | World Trigger calc | `calc_world_line_score` | same | in-process | same | Research / downstream obs |

### Prerequisites (L0)

| Signal | Owner | Producer (design) | Producer (current fact) | Transport (design) | Transport (current fact) | Consumer |
|--------|-------|-------------------|-------------------------|--------------------|--------------------------|----------|
| `pace_collapse_risk` | Pace Design | `demo_pace_model_v2.add_pace_collapse_risk` | often absent; `*_v2` only on PI | Signal Service → frame → meta | PI daily has `*_v2` only（未ブリッジ） | difficulty, high_pace, short_field, Ranker, meta |
| `style_entropy` | Pace Design | `add_style_entropy` | **absent** on slim daily | Signal Service → frame | missing | difficulty formula |
| `win5_leg` | Race / Pace Design | races attach / stable id map | present on PI daily | frame | daily | difficulty base map |
| `horse_count` | Race meta / Pace | pace_model / runners | **absent**; `field_size` あり | Signal Service（alias 可は要契約） | unaliased | difficulty, Ranker |
| `leg_*` intermediates | Pace Design | `add_win5_leg_difficulty_features` | absent on slim daily | optional persist | missing | Ranker / audit |
| `sashi/oikomi/unknown_count` | Pace / style counts | pace_model / ensure_style_count | partial（sashi/oikomi あり, unknown 欠） | frame | partial | difficulty upset_share |

---

## Responsibility split (P4 intent)

```text
Owner (Contract)
  └─ defines meaning, range, required, DEFAULT policy

Signal Service (future supply boundary)
  └─ Producer adapters (pace / PE diagnostic / race meta)
  └─ Transport to World-facing meta
  └─ contract satisfaction check (design intent; not implemented here)

World Trigger (Consumer)
  └─ reads contract signals only
  └─ MUST NOT be the Owner of pace difficulty generation
```

Feature CSV width・PI `build_features`・legacy `pace_model` は **Producer/Transport の選択肢**であり Owner ではない。

---

## Satisfaction ownership

| Check | Owner |
|-------|-------|
| Contract schema (本 v33) | Architecture / Research |
| Runtime satisfaction (将来) | Signal Service |
| Trigger thresholds | World Trigger owner（変更は別承認・本フェーズ禁止） |
| Ranker 28 column presence | PE feature contract（World と隣接だが別契約） |

---

## Known ownership failures (facts)

| Failure | Broken link |
|---------|-------------|
| difficulty DEFAULT 0.5 | Producer(pace) 不通 → Transport(daily) 欠列 → fallback が実質 Producer 化 |
| chaos NULL at meta | Producer は動くが Transport→meta 欠落 |
| `*_v2` vs `pace_collapse_risk` | Producer 別名；Owner 未承認ブリッジ |

---

## Guardrails

- Ownership map only. No reassignment implementation.
