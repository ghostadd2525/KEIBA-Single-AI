# Version44 — Trigger Logic Form（World 別）

**Date:** 2026-07-28  
**Parent:** `v44-world-trigger-specification.md`  
**Note:** 論理構造のみ。数値 Threshold・実装 if 連鎖は記載しない。

表記:

- `S↑` = Signal S が契約 polarity「高い／大きい」方向
- `S↓` = 低い／小さい方向
- `AND` / `OR` = 論理結合
- `support(·)` = Aux（Must を置換しない）
- `NOT` = Forbidden 方向の排除

---

## 1. `core_world`

### Intent → Detection

能力決着の勝ち筋を **正検出**する。

### Logic Form

```text
CORE_MUST =
    top_gap↑
    AND ability_separation↑

CORE_AUX_SUPPORT =
    support(race_grade 高格)
    AND/OR support(distance 長距離寄り)
    AND/OR support(short_field_pressure↓)

CORE_EXCLUDE =
    chaos↑
    OR short_field_pressure↑
    OR (late_stop↑ AND sustained↑)
    OR mid_band_open
    OR multi_path_active
    OR exception_flag

CORE_MATCH =
    CORE_MUST
    AND NOT CORE_EXCLUDE
    [ then optionally reinforced by CORE_AUX_SUPPORT ]
```

### 設計上の禁止形

```text
FORBIDDEN_FORM =
    CORE_MATCH := (all other worlds fail)   # DEFAULT 残余
```

### 重み付け（設計意図）

- Must 2 軸は **等価 AND**（片方欠落で unsatisfied）
- Aux は信頼度ブーストのみ。Must 欠落を補償しない
- Exclude が一つでも強い場合、core 不成立（他 World へ委譲）

---

## 2. `midupper_world`

### Intent → Detection

上位能力が主戦場 **かつ** 展開・適性が効く。

### Logic Form

```text
UPPER_AXIS =
    upper_ability_band↑
    # 表現手段は複数可（OR）だが「上位能力帯」意味を欠いてはならない

DEV_AXIS =
    development_pressure↑
    # 例: phase / route(sfp) / pace 系のいずれか（OR）
    # difficulty 単独は DEV_AXIS を満たさない（V43 Forbidden）

APT_AXIS =
    aptitude_fit↑
    # コース・距離・脚質適合などの適性表現（OR 可）

MIDUPPER_MUST =
    UPPER_AXIS AND DEV_AXIS AND APT_AXIS

MIDUPPER_AUX =
    support(difficulty 中〜)
    OR support(short_field_pressure 中)
    OR support(top_gap 中)

MIDUPPER_EXCLUDE =
    (chaos↑ AND high_pace↑)      # rank7 領域
    OR mid_band_open             # midhole 領域
    OR top_gap↑ AND NOT DEV_AXIS AND NOT APT_AXIS  # core 寄り純能力

MIDUPPER_MATCH =
    MIDUPPER_MUST
    AND NOT MIDUPPER_EXCLUDE
```

### 重み付け

- 3 Must 軸は **必須 AND**
- 各軸内部の代替 Signal は **OR**（同義表現）
- Aux は境界の微調整のみ

---

## 3. `midhole_world`

### Intent → Detection

中位評価まで勝ち筋が開いている。

### Logic Form

```text
MIDHOLE_MUST =
    mid_eval_band_open↑
    AND top_monopoly↓

MIDHOLE_AUX =
    support(late_stop↑)
    OR support(sustained↑)
    OR support(chaos 中)

MIDHOLE_EXCLUDE =
    top_gap↑（強い上位独占）
    OR (定義本体 := late_stop↑ AND sustained↑)  # Aux の昇格禁止
    OR chaos↑↑（極端 — rank7/bug 寄り）

MIDHOLE_MATCH =
    MIDHOLE_MUST
    AND NOT MIDHOLE_EXCLUDE
```

### 重み付け

- Must 2 軸 AND
- pace 系（late_stop/sustained）は **Aux 固定** — Must に昇格させない（V43）

---

## 4. `rank7_world`

### Intent → Detection

Chaos / 展開が能力以上に効く。

### Logic Form

```text
RANK7_MUST =
    chaos↑
    AND pace_conflict↑          # high_pace / 混戦・展開圧
    AND ability_subordinate↑    # top_gap↓ 等の能力劣後

RANK7_AUX =
    support(field_size 多頭)
    OR support(distance 短〜中)
    OR support(difficulty 中〜高)

RANK7_EXCLUDE =
    top_gap↑（能力決着）
    OR (difficulty↑ AND NOT chaos↑)  # midupper/bug 混同回避

RANK7_MATCH =
    RANK7_MUST
    AND NOT RANK7_EXCLUDE
```

### 重み付け

- 3 Must は AND（chaos 欠落は rank7 不成立）
- ability_subordinate は「能力以上に」を満たすために Must（V43）

---

## 5. `mixed_world`

### Intent → Detection

複数勝ち筋の共存 / 単一説明不能。

### Logic Form

```text
PATH_SET = { core_meaning, midupper_meaning, midhole_meaning, rank7_meaning, ... }

MULTI_PATH =
    count( paths in PATH_SET that are concurrently plausible ) >= 2

UNEXPLAINED_SINGLE =
    explicit_single_world_insufficient_flag↑

MIXED_MUST =
    MULTI_PATH
    OR UNEXPLAINED_SINGLE

MIXED_AUX =
    support( concurrent pressure bundle )
    # sfp / phase / chaos / difficulty が同時に立つことは「手がかり」であり定義本体ではない

MIXED_EXCLUDE =
    exactly_one_clear_path
    OR (定義本体 := phase↑ only)

MIXED_MATCH =
    MIXED_MUST
    AND NOT MIXED_EXCLUDE
```

### 重み付け

- 競合カウントが本体
- 複合圧力 Aux は MULTI_PATH の証拠になり得るが、**単軸高値では Must を満たさない**

---

## 6. `bug_world`

### Intent → Detection

通常ロジック外の特殊ケース。

### Logic Form

```text
BUG_MUST =
    exception_or_inexplicable_flag↑
    AND NOT ( unlabeled_residual )   # 「どれにも非該当」禁止

BUG_AUX =
    support(chaos↑↑ AND difficulty↑↑)

BUG_EXCLUDE =
    chaos↑ only（rank7 と衝突）
    OR unlabeled_residual = core_default_pattern

BUG_MATCH =
    BUG_MUST
    AND NOT BUG_EXCLUDE
```

### 重み付け

- 例外標識が Must
- 極端 chaos∧difficulty は Aux（弱い近似を定義本体にしない）

---

## Cross-World Conflict Resolution（設計）

```text
if count(MATCHING_WORLDS) >= 2:
    → prefer MIXED_MATCH semantics
elif count == 1:
    → that World
elif count == 0:
    → unsatisfied / unclassified
       (NOT silent core DEFAULT)
```

現行 first-match 優先度表は **実装観測**であり、本 Logic Form の一部ではない。

## Guardrails

- 閾値数値なし
- 実装コードなし
- Signal 変更手順なし
