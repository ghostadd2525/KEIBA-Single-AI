# ADR-032 — World Trigger Formal Design Contract

**Status:** Accepted (design intent only — **not implemented**)  
**Date:** 2026-07-27  
**Deciders:** Architecture / Research (V22–V31 evidence base)  
**Scope:** Design judgment only. No code, CSV, Production, Prediction, World, or Trigger changes in this phase.

---

## Context

V22–V31 established:

| Finding | Source |
|---------|--------|
| Observed / simulated World mix ≈ **core 2% / midupper 98% / others 0%** vs design mix (core 30 / midupper 35 / rank7 15 / mixed 10 / bug 5 / midhole 5) | V22, V27 |
| Production `race_leg_difficulty` is **DEFAULT 0.5** on Core path | V28, V29 |
| Designed formula `add_win5_leg_difficulty_features` **still exists**; not deleted | V29, V30 |
| FeatureGenerator never calling the formula is **not** the primary break | V30 |
| True break: **pace_model → 116 Feature → daily writer replaced by PI `build_features` → 72/74** | V31 |
| Dual contract: design-canonical **116** vs ops-canonical **72/74** daily | V31 |
| `chaos_score` separately drops before meta (orthogonal gap) | V26 |

Design philosophy under test:

> **World は AI 最上流の勝ち筋分類である。**

World must classify race win-paths from **real condition signals**, upstream of Role / Pool / Purchase. Defaults that saturate Triggers violate that role.

---

## Decision summary

| Item | Decision |
|------|----------|
| Formal World design contract | **World Input Contract**（信号契約）を正本とする — 列数（116/72）ではない |
| Preferred architecture direction | **P4 — Signal Service / World Input Contract 分離** |
| Production feature binding (design intent) | P4 の下で、Production 日次特徴は **設計 pace Signals を正式に供給**する（形状は P2 に近い） |
| Rejected as formal design | **P3**（Research=116 / Production=72 の二重正本） |
| Acceptable legacy-faithful alternative | **P1**（運用がフル legacy を再所有できる場合） |
| Implementation | **Out of scope**（本 ADR は実装を承認しない） |

詳細比較: `v32-restoration-options.md`  
推奨根拠: `v32-recommendation.md`  
契約差分: `v32-contract-comparison.md`

---

## ① Original Architecture（設計当初契約）

```text
runners / history
  → demo_pace_model_v2.build_pace_features
       · win5_leg
       · style_entropy / pace_collapse_risk / horse_count
       · add_win5_leg_difficulty_features → race_leg_difficulty, leg_*
       · pre_world_* seeds（下流 seed）
  → demo_merge_market_into_pace
  → runners_pace_market_features.csv  ≈ 116 columns
  → FeatureLoader (daily or global)
  → PE (FeatureGenerator / Ranker 28 — includes difficulty/leg/pace_collapse_risk/…)
  → CE (score frame + race meta)
  → World Trigger (classify_world_line_type on meta signals)
  → SubWorld / Role / Candidate Pool / Purchase
```

**契約要点**

- World 入力は **pace 段で生成された可変信号**を CSV 搬送する。
- FeatureGenerator は probability 境界であり、難易度式の主生成点ではない。
- Ranker 凍結 28 も同一搬送列に依存する（`win5_lgbm_ranker_features.json`）。
- 列数 116 は **搬送形態**；本質は pace/World 信号の存在。

---

## ② Current Architecture（現行契約）

```text
shutuba → runners + horse_history_raw
  → pi_keibanet.features.build_features
       · history + market basics + v2 risk (pace_collapse_risk_v2, field_size, …)
       · does NOT call pace_model_v2
  → daily CSV ≈ 72/74 columns
  → FeatureLoader (daily preferred over global 116)
  → enrich_stable_features → STABLE_FEATURE_DEFAULTS['race_leg_difficulty']=0.5
  → PE / CE meta
  → World Trigger (difficulty≈0.5 constant; chaos often MISSING)
  → midupper saturation
```

**契約要点**

- Daily writer 正本は PI Race Refresh（V2 Ops）。
- 設計 pace Signals は daily に無い → DEFAULT 支配。
- Global 116 は残存しうるが Loader 優先順で日常不使用。
- Research が Production meta をコピーするため、観測も DEFAULT を反映する。

---

## Consequences（設計）

### Positive (if P4 direction is later implemented)

- World を「列スキーマ論争」から切り離し、**最上流信号契約**として固定できる。
- Production / Research が同一 World Input を共有できる（P3 排除）。
- chaos 等の別断絶を、同一契約面に段階追加できる。

### Negative / risks (design-level)

- 実装時は PE（凍結 28）・CE・World 分布に回帰が起きうる（V30 risk）。
- P4 は新境界の定義コストがある；拙速実装は禁止（本 ADR）。
- chaos_score 断絶は本決定だけでは閉じない（別 ADR / 後続）。

### Non-consequences of this phase

- コード・CSV・Trigger 閾値・World 定義・Production は **変更されない**。

---

## Related ADRs / evidence

- V24–V27 World Trigger / saturation / design gap  
- V28–V29 difficulty lineage / DEFAULT  
- V30 design restoration readiness = B  
- V31 CSV contract break = daily writer replacement  

## Guardrails

- ADR / Research only. Implementation requires a separate explicit approval.
