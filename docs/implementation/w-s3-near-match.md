# W-S3 Near Match Report（Exclusion removed ⇒ Positive Match）

**Date:** 2026-07-28  
**Version:** 61  
**Definition:** `must=True` AND `exclude=True` for ≥1 World

---

## Counts

| Scope | n |
|---|---:|
| Near Match ∩ Unsatisfied（本調査の 104） | **104** |
| Near Match on full 285R | **140** |
| Near Match with another World still MATCH | **36** |

---

## Cohort 104 — if Exclusion cleared

これらの 104 レースは、発火している Exclude を除けば、当該 World で **Positive Match になりうる**（Must は充足済み）。

| primary_near_world | n |
|---|---:|
| core_world | （primary 優先で多数；World 重複計上では core 81） |
| midupper_world | 32（重複可） |
| midhole_world | 13 |
| rank7_world | 1 |

---

## Winner Alignment on Near Match primary

| WA | n | Role in True/False |
|---|---:|---|
| aligned | 51 | → False Exclusion |
| soft | 25 | → True Exclusion（本定義） |
| misaligned | 28 | → True Exclusion |

---

## Caveat

Exclude 除去は **本フェーズでは実施しない**（Trigger/Exclusion 変更禁止）。  
本表は Shadow 上のカウンターファクト観測。

Rows: `w-s3-exclusion-104-rows.jsonl`

---

*Near Match inventory only.*
