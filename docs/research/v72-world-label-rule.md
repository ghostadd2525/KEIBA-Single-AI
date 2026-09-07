# Version72 — World Label Rule

**Date:** 2026-07-28  
**Parent:** `v72-ground-truth-definition.md`  
**Authority:** V43 Semantic → V44 Logic Form（写し。改変しない）  
**実装禁止 / Threshold 数値禁止**

---

## 共通規則

1. 各 Primary World について `MATCH(w) = MUST(w) ∧ ¬EXCLUDE(w)`。  
2. Aux は **ラベル決定に使用しない**（信頼度・境界の記述のみ可）。  
3. Must 欠落（Signal / Concept が polarity 判定不能）⇒ 当該 `MUST(w)=false` ⇒ その World は MATCH しない。  
4. Aux や DEFAULT で Must を埋めない（V44 T2 / T0）。  
5. `winner_rank` / 人気 / Prediction score は **どの規則にも出現させない**。

---

## Primary World Rules（V44 写し）

### L-core — `core_world`

```text
MUST:
  top_gap↑ AND ability_separation↑

EXCLUDE:
  chaos↑
  OR short_field_pressure↑
  OR (late_stop↑ AND sustained↑)
  OR mid_eval_band_open↑
  OR multi_path_active          # 他 Primary MATCH が 1 つ以上
  OR exception_flag↑

MATCH := MUST AND NOT EXCLUDE
```

**Semantic 根拠（V43）:** 能力決着の独立勝ち筋。DEFAULT 残余ではない。

---

### L-midupper — `midupper_world`

```text
UPPER_AXIS := upper_ability_band↑
DEV_AXIS   := development_pressure↑
             # 表現 OR 可: phase↑ / short_field_pressure↑ / high_pace↑
             # difficulty↑ 単独では DEV_AXIS を満たさない（V43 Forbidden）
APT_AXIS   := aptitude_fit↑

MUST := UPPER_AXIS AND DEV_AXIS AND APT_AXIS

EXCLUDE:
  (chaos↑ AND high_pace↑)
  OR mid_eval_band_open↑
  OR (top_gap↑ AND NOT DEV_AXIS AND NOT APT_AXIS)

MATCH := MUST AND NOT EXCLUDE
```

**Aux（ラベル非使用）:** difficulty 中〜 / sfp 中 / top_gap 中。

---

### L-midhole — `midhole_world`

```text
MUST:
  mid_eval_band_open↑ AND top_monopoly↓

EXCLUDE:
  top_gap↑
  OR (定義本体 := late_stop↑ AND sustained↑)   # Aux 昇格禁止
  OR chaos↑↑（極端）

MATCH := MUST AND NOT EXCLUDE
```

**Aux（ラベル非使用）:** late_stop / sustained / chaos 中。

---

### L-rank7 — `rank7_world`

```text
MUST:
  chaos↑
  AND pace_conflict↑          # high_pace / 展開・混戦圧
  AND ability_subordinate↑    # top_gap↓ 等

EXCLUDE:
  top_gap↑
  OR (difficulty↑ AND NOT chaos↑)

MATCH := MUST AND NOT EXCLUDE
```

---

### L-bug — `bug_world`

```text
MUST:
  exception_or_inexplicable_flag↑
  AND NOT unlabeled_residual     # 「どれにも非該当」禁止

EXCLUDE:
  chaos↑ only（rank7 衝突）
  OR unlabeled_residual = core_default_pattern

MATCH := MUST AND NOT EXCLUDE
```

**注:** exception 標識が欠落している観測では `MUST=false` → bug は MATCH しない（V44）。  
欠落を wr 深穴で代替することは **禁止**（V71 C4）。

---

## Mixed Rule

### L-mixed — `mixed_world`

```text
PRIMARY := {core, midupper, midhole, rank7, bug}
P := { w ∈ PRIMARY | MATCH(w) }

MULTI_PATH := |P| ≥ 2
UNEXPLAINED_SINGLE := exception_flag↑ AND |P| = 0
                     # exception 欠落時、本枝は不成立

MUST := MULTI_PATH OR UNEXPLAINED_SINGLE
EXCLUDE := |P| = 1     # 単一明確パス

MATCH := MUST AND NOT EXCLUDE
```

**Aux（ラベル非使用）:** 複合圧力バンドル（sfp/phase/chaos/difficulty 同時）。  
**Forbidden:** phase↑ のみを mixed 定義にする（V43/V44）。

---

## Decision Tree（Expected World 確定）

```text
1. Evaluate MATCH for each Primary World (L-core … L-bug)
2. Evaluate MIXED_MATCH (L-mixed)
3. Let M = { w | MATCH(w) }   # mixed を含む

if |M| = 0 → Expected World = unsatisfied
if |M| = 1 → Expected World = the unique element of M
if |M| ≥ 2 → Expected World = mixed_world
```

これ以外の優先度表（Legacy R1…R8 first-match）は **GT に用いない**。

---

## ラベル集合

```text
{ core_world, midupper_world, midhole_world, rank7_world,
  mixed_world, bug_world, unsatisfied }
```

---

## 明示的非規則（V65 互換禁止）

```text
FORBIDDEN_AS_LABEL_RULE =
    any rule containing winner_model_rank
    OR popularity_rank
    OR prediction_score_band
    OR soft_score ∈ {0.5, 0.75, 1.0} as primary selector
```
