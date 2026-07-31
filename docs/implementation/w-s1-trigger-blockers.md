# W-S1 Trigger Blockers（Logic 停止点）

**Date:** 2026-07-28  
**Version:** 57  
**Source:** `decision_trace` on Unsatisfied 176  
**Rule:** 分類のみ。Trigger 実装変更禁止。

---

## Stop-point taxonomy

```text
V44 evaluation order (spec):
  Exclusion → Must → Conflict/mixed → Aux → Unsatisfied
W-S1 shadow evaluator:
  Per-world: Must + Exclude → match
  Then: match_set empty → unsatisfied
```

| Stop point | n | Trace evidence |
|---|---:|---|
| **E1 Exclusion after Must** | **104** | ≥1 world: `must=True`, `exclude=True`; not all-must-fail |
| **M0 All Must fail** | **72** | every world `must` is not True |
| **M1 mixed multi_path Must** | overlaps M0 | mixed `must_gaps` includes multi_path rule |
| **M2 bug exception_flag Must** | 176 structural | bug never matches without flag |
| **A0 Aux** | **0** | Aux does not gate match in W-S1 code |
| **P0 Polarity-only field** | **0** | no `polarity_reverse` key; folded into Must gaps |

---

## E1 detail — which Logic Forms reached Must then died on Exclude

| World Logic Form | must∧exclude count (within E1 races; multi OK) |
|---|---:|
| CORE_MATCH blocked by CORE_EXCLUDE | 81 |
| MIDUPPER_MATCH blocked by MIDUPPER_EXCLUDE | 32 |
| MIDHOLE_MATCH blocked by MIDHOLE_EXCLUDE | 13 |
| RANK7_MATCH blocked by RANK7_EXCLUDE | 1 |

**Critical observation:** `must=True & exclude=False` count = **0** across all Unsatisfied.  
No race had a clean Positive Match candidate that only lacked Aux.

---

## M0 detail — Must axes that fail (72 races)

| World | Dominant failing Must axes (counts in M0 set) |
|---|---|
| core | ability_separation↑ 53, top_gap↑ 37 |
| midupper | upper_ability_band↑ 43, aptitude_fit↑ 35, development_pressure↑ 25 |
| midhole | mid_eval_band_open↑ 50, top_monopoly↓ 27 |
| rank7 | chaos↑ 56, ability_subordinate↑ 35, pace_conflict↑ 25 |
| mixed | multi_path rule 72/72 |
| bug | exception_flag↑ (always) |

---

## What is *not* a Trigger blocker here

| Candidate | Verdict |
|---|---|
| Aux不足 | Not a blocker in W-S1 evaluator |
| Legacy first-match / DEFAULT | Affects Legacy label only; V44 unsatisfied is independent |
| Production Trigger thresholds | Shadow path; Production Decision unchanged |

---

## Blocker summary (for Governance)

1. **Primary structural blocker:** Exclusion firing whenever Must succeeds (104)  
2. **Secondary:** Complete Must failure (72) driven by ranking/chaos/aptitude gaps + mixed multi_path  
3. **Closed path:** bug via exception_flag（dataに flag 無し）

*Classification only.*
