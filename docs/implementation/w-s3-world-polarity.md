# W-S3 World Polarity Map

**Date:** 2026-07-28  
**Parent ADR:** `w-s3-polarity-adr.md`  
**Authority:** V43 Required/Forbidden · V44 T3 / Signal Roles / Logic Form

---

## Legend

| Symbol | Meaning for that World |
|---|---|
| **+** | Positive direction supports World |
| **−** | Negative direction supports World（反対側が Must/支持） |
| **N** | Neutral / no directional Must |
| **F+** | High/Present must not be used as positive definer |
| **+A** | Positive as Aux only（Must ではない） |

---

## Per-Signal × World

### `top_gap`

| World | Polarity | Direction that supports | Basis |
|---|---|---|---|
| core | **+** | High | Must top_gap↑（V44） |
| midupper | N / +A mid | Mid；高単独定義禁止 | Aux |
| midhole | **−** / F+ high monopoly | Low寄り Aux；High独占 F+ | V44 |
| rank7 | **−** | Low | Must ability_subordinate / top_gap↓ |
| mixed | N / +A | — | Aux optional |
| bug | N | — | N/A |

### `race_leg_difficulty`

| World | Polarity | Direction that supports | Basis |
|---|---|---|---|
| core | **F+** | High を正条件にしない | Forbidden 単独定義 |
| midupper | +A | Mid〜High as Aux（≠能力帯） | Aux；Must ではない |
| midhole | N | — | N/A |
| rank7 | +A | Mid〜High Aux | Aux |
| mixed | +A | 複合圧力の一員 | Aux |
| bug | +A extreme | 極端 High as Aux only | Must ではない |

### `chaos_score`

| World | Polarity | Direction that supports | Basis |
|---|---|---|---|
| core | **F+** | High 禁止 as positive | Forbid+ |
| midupper | +A | Mid | Aux |
| midhole | +A | Mid | Aux |
| rank7 | **+** | High | Must |
| mixed | +A | 複合 | Aux |
| bug | +A extreme | 極端 High Aux | Must ではない |

### `short_field_pressure`

| World | Polarity | Direction that supports | Basis |
|---|---|---|---|
| core | **F+** High；**+** Low as Aux | Low supports Aux | V44 core Aux sfp↓ |
| midupper | **+** as Aux(Dev) | High | Dev axis OR |
| midhole | N | — | N/A |
| rank7 | +A | High | Aux |
| mixed | +A | High in bundle | Aux |
| bug | N | — | N/A |

### `late_stop`

| World | Polarity | Direction that supports | Basis |
|---|---|---|---|
| core | **F+**（∧sustained） | 同時 High を正にしない | CORE_EXCLUDE 対応（規則変更なし） |
| midupper | N | — | N/A |
| midhole | +A | High | Aux only（Must 昇格禁止） |
| rank7 | N | — | N/A |
| mixed | N | — | N/A |
| bug | N | — | N/A |

### `sustained`

| World | Polarity | Direction that supports | Basis |
|---|---|---|---|
| core | **F+**（∧late_stop） | 同時 High を正にしない | 同上 |
| midupper | N | — | N/A |
| midhole | +A | High | Aux only |
| rank7 | N | — | N/A |
| mixed | N | — | N/A |
| bug | N | — | N/A |

### `high_pace`

| World | Polarity | Direction that supports | Basis |
|---|---|---|---|
| core | **F+**（単独） | High 単独正禁止 | V44 |
| midupper | +A | High as Dev | Aux(Dev) |
| midhole | +A | High | Aux |
| rank7 | **+** | High | Must pace_conflict |
| mixed | +A | High | Aux |
| bug | N | — | N/A |

### `phase_transition`

| World | Polarity | Direction that supports | Basis |
|---|---|---|---|
| core | N | — | N/A |
| midupper | +A | High as Dev | Aux(Dev) |
| midhole | N | — | N/A |
| rank7 | +A | High | Aux |
| mixed | +A；**F+ if sole definer** | High only in multi-pressure | V44 mixed |
| bug | N | — | N/A |

### `aptitude_fit`

| World | Polarity | Direction that supports | Basis |
|---|---|---|---|
| core | N | — | N/A |
| midupper | **+** | High | Must（供給は W-S2 Missing） |
| midhole | +A | High | Aux |
| rank7 | N | — | N/A |
| mixed | N | — | N/A |
| bug | N | — | N/A |

### `unexplained_single`

| World | Polarity | Direction that supports | Basis |
|---|---|---|---|
| core..rank7 | N | — | N/A |
| mixed | **+** | Present | Must OR 枝（W-S2 Missing） |
| bug | N | — | N/A |

### `exception_flag`

| World | Polarity | Direction that supports | Basis |
|---|---|---|---|
| core | **F+** | Present を DEFAULT と混同して正にしない | V44 |
| midupper..rank7 | N | — | N/A |
| mixed | N | — | （unexplained は別キー） |
| bug | **+** | Present | Must（W-S2 Missing） |

---

## Positive / Negative / Neutral（Signal 要約）

各 Signal の **主 Must World における正式極性**:

| Signal | Primary Must World | Formal polarity for that Must | Opposite |
|---|---|---|---|
| top_gap | core / rank7 | core: High+ · rank7: Low+ | 相互逆 |
| race_leg_difficulty | （Mustなし） | 主に Aux / F+ | — |
| chaos_score | rank7 | High+ | core: High F+ |
| short_field_pressure | （Mustなし；Dev Aux） | midupper Dev: High+ · core Aux: Low+ | core vs midupper |
| late_stop | （Mustなし） | midhole Aux High+ · core F+ with sust | — |
| sustained | （Mustなし） | midhole Aux High+ · core F+ with late | — |
| high_pace | rank7（pace_conflict） | High+ | core F+ sole |
| phase_transition | （Mustなし；Dev/mixed Aux） | High+ Aux；sole F+ mixed | — |
| aptitude_fit | midupper | High+ | Low− |
| unexplained_single | mixed | Present+ | Absent− |
| exception_flag | bug | Present+ | Absent− |

---

*Polarity map only. No Exclusion/Trigger changes.*
