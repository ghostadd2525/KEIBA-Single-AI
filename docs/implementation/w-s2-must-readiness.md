# W-S2 Must Readiness Ledger

**Date:** 2026-07-28  
**Version:** 59  
**Scope:** Must Signal Readiness 台帳のみ  
**禁止:** Trigger / Signal / Prediction / PE / CE / World / Cutover / Production 変更、改善・実装  
**対象外（本台帳で扱わない）:** Exclusion / Polarity / Proxy / Cutover / Prediction  
**根拠:** V44 Must Sets、W-S1 Dual-Eval（285R）、`w_s1_shadow_dual_eval.py` / `v44_shadow_eval.py` / `demo_ticket_optimizer_core.get_context_top_gap`

**Prior Gate:** V58 Go/No-Go = B（条件付き開始）遵守

---

## Scoring（World Must Readiness %）

| Readiness | Score |
|---|---:|
| Ready | 1.0 |
| Partial | 0.5 |
| Blocked | 0.0 |

`Must Readiness % = 100 × Σ(score) / N_Must`

---

## Summary Table

| World | N Must | Ready | Partial | Blocked | **Must Readiness %** |
|---|---:|---:|---:|---:|---:|
| core_world | 2 | 2 | 0 | 0 | **100%** |
| midupper_world | 3 | 1 | 1 | 1 | **50%** |
| midhole_world | 2 | 2 | 0 | 0 | **100%** |
| rank7_world | 3 | 1 | 2 | 0 | **67%** |
| mixed_world | 2* | 1 | 0 | 1 | **50%** |
| bug_world | 1 | 0 | 0 | 1 | **0%** |

\* mixed Must = `multi_path_active` **OR** `unexplained_single`（2概念を台帳行として列挙。ORのため一方 Ready でも World は Partial）

**Mean (equal world weight):** (100+50+100+67+50+0)/6 ≈ **61%**

---

## Per-World Ledgers

詳細行は `w-s2-signal-inventory.md`。World 要約は `w-s2-world-readiness.md`。

### core_world — 100%

| Must | Available | Missing | Restore | Source | Readiness |
|---|---|---|---|---|---|
| top_gap↑ | Yes | — | Restored* | Derived（285 runners win_prob）; 関数 `get_context_top_gap` もコード上存在 | Ready |
| ability_separation↑ | Yes | — | Restored* | Derived（top−median win_prob） | Ready |

\*「Feature restore」ではなくコーパス runners から全285で値生成可能（W-S1 `ranking_concepts`）。

### midupper_world — 50%

| Must | Available | Missing | Restore | Source | Readiness |
|---|---|---|---|---|---|
| upper_ability_band | Yes | — | Restored* | Derived（top3 win_prob share） | Ready |
| development_pressure | Yes（条件付） | 非restore時欠落 | Restored 240 / Missing 45 | Feature（phase/sfp/high_pace via FeatureLoader+Scorer） | Partial |
| aptitude_fit | No（非Proxy本信号なし） | **Missing** | Missing | —（W-S1 の distance/field は本台帳対象外 Proxy） | Blocked |

### midhole_world — 100%

| Must | Available | Missing | Restore | Source | Readiness |
|---|---|---|---|---|---|
| mid_eval_band_open↑ | Yes | — | Restored* | Derived（mid-rank win_prob share） | Ready |
| top_monopoly↓ | Yes | — | Restored* | Derived（top1 share） | Ready |

### rank7_world — 67%

| Must | Available | Missing | Restore | Source | Readiness |
|---|---|---|---|---|---|
| chaos↑ | Yes（条件付） | 非restore時欠落 | Restored 240 / Missing 45 | Feature（Scorer `_diagnostic.chaos_score`） | Partial |
| pace_conflict↑ | Yes（条件付） | 非restore時欠落 | Restored 240 / Missing 45 | Feature（high_pace / sfp / phase） | Partial |
| ability_subordinate↑ | Yes | — | Restored* | Derived（from top_gap↓ polarity input） | Ready |

### mixed_world — 50%

| Must | Available | Missing | Restore | Source | Readiness |
|---|---|---|---|---|---|
| multi_path_active | Yes | — | Restored* | Derived（Shadow primary MATCH 件数≥2） | Ready |
| unexplained_single | No | **Missing** | Missing | —（明示フラグ無し） | Blocked |

### bug_world — 0%

| Must | Available | Missing | Restore | Source | Readiness |
|---|---|---|---|---|---|
| exception_flag | No | **Missing** | Missing | —（285R / W-S1 method: absent in corpus） | Blocked |

---

## Coverage evidence (285R)

| Fact | Value | Source |
|---|---|---|
| Dual-Eval races | 285 | `w-s1-dual-eval-rows.jsonl` |
| Feature restore OK | 240 | `w-s1-285r-evaluation.json` `dual_meta.n_restored` |
| Feature restore fail | 45 | 285−240 |
| exception_flag present | 0 | W-S1 method + bug must_gaps 285/285 |

---

## Explicit non-scope

- Exclusion 104件 → **S3**（本台帳不記載の判定対象）  
- Polarity / batch-median → **S3**  
- Proxy（aptitude distance/field）→ 対象外のため aptitude = **Missing/Blocked**  
- Cutover / Production Decision → 変更なし・未着手  

---

## S4 Blocked foreshadow（V46 / V58 条件）

| World | S4 implication |
|---|---|
| bug_world | Must Missing → **Blocked** 明示 |
| midupper（aptitude） | Must 1軸 Blocked → World Partial；S4 で midupper 完全適合は制限されうる |
| mixed（unexplained） | multi_path Ready のため完全 Blocked ではない |

---

*Version59 — ledger only. No code changes.*
