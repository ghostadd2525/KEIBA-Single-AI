# W-S3 Conflict Matrix（Polarity）

**Date:** 2026-07-28  
**Parent ADR:** `w-s3-polarity-adr.md`  
**Rule:** 極性衝突の列挙のみ。Exclusion / Trigger 変更禁止。

---

## How to read

| Cell | Meaning |
|---|---|
| **OPP** | 逆極性 Must/支持（一方 High+、他方 Low+） |
| **F+ vs +** | 一方で High が Forbid-as-positive、他方で High が + |
| **SOLE-F+** | 同一 World 内で「単独使用 F+」制約 |
| **AND-F+** | 二 Signal 同時 High が F+ |
| empty | 契約上の極性衝突なし（両方 N / 同方向 Aux 等） |

Worlds: C=core · U=midupper · H=midhole · R=rank7 · M=mixed · B=bug

---

## Cross-World conflicts（primary）

| Signal | C↔U | C↔H | C↔R | C↔M | C↔B | U↔R | H↔R | Notes |
|---|---|---|---|---|---|---|---|---|
| top_gap | — | F+ vs − | **OPP** | — | — | — | — | core High+ vs rank7 Low+ |
| race_leg_difficulty | F+ vs +A | — | F+ vs +A | F+ vs +A | F+ vs +A | — | — | core 単独定義禁止 |
| chaos_score | F+ vs +A | F+ vs +A | **F+ vs +** | F+ vs +A | F+ vs +A | +A vs + | +A vs + | core Forbid vs rank7 Must |
| short_field_pressure | **F+/Low+ vs High+A** | — | F+ vs +A | F+ vs +A | — | — | — | core Low Aux vs others High Aux |
| late_stop | — | **AND-F+ vs +A** | — | — | — | — | — | with sustained |
| sustained | — | **AND-F+ vs +A** | — | — | — | — | — | with late_stop |
| high_pace | F+ vs +A | F+ vs +A | **F+ vs +** | F+ vs +A | — | +A vs + | +A vs + | core sole Forbid |
| phase_transition | — | — | — | **SOLE-F+** (M) | — | — | — | mixed 単独定義禁止 |
| aptitude_fit | — | — | — | — | — | — | — | midupper Must only |
| unexplained_single | — | — | — | — | — | — | — | mixed only |
| exception_flag | **F+ vs +** (C↔B) | — | — | — | **F+ vs +** | — | — | bug Must vs core Forbid DEFAULT混同 |

---

## Intra-World constraints

| World | Constraint ID | Signals | Rule |
|---|---|---|---|
| core | AND-F+ | late_stop ∧ sustained | 同時 High を正条件にしない（V44） |
| core | SOLE-F+ | difficulty / high_pace / chaos / sfp(High) | 単独または高値を core 正にしない |
| mixed | SOLE-F+ | phase_transition | 単独で mixed 定義禁止 |
| midhole | Must≠pace | late_stop, sustained | Aux のみ；Must 昇格禁止（V43/V44） |
| bug | Must≠chaos | chaos_score, difficulty | 極端は Aux；Must は exception_flag のみ |
| midupper | Must≠difficulty alone | race_leg_difficulty | difficulty 単独で midupper 定義禁止 |

---

## Conflict summary (Must-critical)

1. **`top_gap` OPP (core High+ ↔ rank7 Low+)** — 最重要の逆極性  
2. **`chaos_score` F+ vs + (core ↔ rank7)**  
3. **`high_pace` F+ vs + (core ↔ rank7)**  
4. **`exception_flag` F+ vs + (core ↔ bug)**  
5. **`short_field_pressure` Low+ Aux (core) vs High+ Aux (midupper Dev)**  

これらの衝突は **仕様上意図された境界**であり、単一グローバル「高い＝良い」を禁止する根拠になる。

---

## Relation to Exclusion 104（deferred）

W-S1: Must=True のとき常に exclude=True（104）。  
極性 ADR 固定後、**別観測**で「Exclude が F+ 方向と整合しているか」を評価する。  
本ドキュメントは衝突表のみ。再集計・規則変更なし。

---

*Conflict matrix only.*
