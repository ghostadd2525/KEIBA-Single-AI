# Version43 — Required / Optional / Forbidden Signals

**Date:** 2026-07-28  
**Type:** Design contract appendix（Signal 実装変更なし）  
**Parent:** `v43-world-semantic-contract.md`

命名は可能な限り V33 World Input Contract / 既存コードキーに合わせる。  
「Required」は **意味契約上の必要**であり、現行 Trigger が読んでいることと同義ではない。

---

## Cross-World Matrix

| Signal / Concept | core | midupper | midhole | rank7 | mixed | bug | Code existence |
|---|---|---|---|---|---|---|---|
| `top_gap`（大） | **R** | O | F | F | — | — | `get_context_top_gap` |
| `top_gap`（小） | F | O | O | **R** | O | — | 同上 + large-field pressure |
| 能力差 / 分布分離 | **R** | O | O | O | — | — | top1/top2/median 系 |
| 上位能力帯 | F | **R** | F | F | — | — | （Trigger 未符号化） |
| 中位評価帯 / mid rank | F | F | **R** | O | — | — | （Trigger 未符号化） |
| 適性 | — | **R** | O | — | — | — | （Trigger 未符号化） |
| `chaos` | F（高を正にしない） | O | O | **R** | O | O | `chaos_score` |
| `high_pace` | F（単独正にしない） | O | O | **R** | O | — | L2 / Trigger R5 |
| `short_field_pressure` | F（高を正にしない） | O | — | O | O | — | `calc_short_field_pressure` |
| `difficulty` | F（高のみで core/midupper 定義しない） | O | — | O | O | O | `race_leg_difficulty` |
| `phase` | — | O | — | O | O | — | `phase_transition` |
| `late_stop` | F（midhole 定義にしない） | — | O | — | — | — | `late_stop_risk_score` |
| `sustained` | F（同上） | — | O | — | — | — | `sustained_run_possible_score` |
| レース格 | O | O | — | — | — | O | `race_class` / `grade` |
| 距離（長） | O | — | — | — | — | — | `get_context_distance` |
| 距離（短）via sfp | F as core-positive | O | — | O | O | — | sfp 内 |
| 複数勝ち筋同時活性 | F | F | F | F | **R** | — | （Trigger 明示なし） |
| 説明不能 / 例外標識 | F（=DEFAULT にしない） | — | — | — | — | **R** | （Trigger 明示なし） |
| core=`DEFAULT` | **F**（禁止） | — | — | — | — | F（bug と混同禁止） | R8 |

凡例: **R**=Required / O=Optional / F=Forbidden（当該 World の正条件として） / —=契約上特に規定しない

---

## Per-World Lists

### core_world

- **Required:** `top_gap`（大）, 能力差（分布分離）, 能力決着の正条件（非 DEFAULT）
- **Optional:** レース格, 長距離, 低 sfp
- **Forbidden as positive:** DEFAULT 残余, 高 chaos, 高 sfp, late_stop∧sustained を core 定義にする

### midupper_world

- **Required:** 上位能力帯, 展開影響, 適性
- **Optional:** difficulty（脚難度）, sfp（中）, 中程度 top_gap
- **Forbidden as positive:** difficulty のみ, 高 chaos∧high_pace（rank7）, 中位帯の広さ（midhole）

### midhole_world

- **Required:** 中位評価帯, 上位独占の弱さ
- **Optional:** late_stop, sustained, 中程度 chaos
- **Forbidden as positive:** late_stop∧sustained のみを定義本体にする, 高 TopGap 独占, 極端 chaos のみ

### rank7_world

- **Required:** chaos（高）, 展開/混戦圧, 能力劣後（低 top_gap 等）
- **Optional:** 多頭, 短〜中距離, difficulty（中〜高）
- **Forbidden as positive:** 高 TopGap 能力決着, chaos なし difficulty のみ

### mixed_world

- **Required:** 複数勝ち筋の同時活性（または単一説明不能の明示）
- **Optional:** 高 sfp + 複合 OR, 高 phase
- **Forbidden as positive:** phase のみで mixed 定義, 単一明確勝ち筋の強制ラベル

### bug_world

- **Required:** 説明不能/例外標識（core DEFAULT と非同一）
- **Optional:** 極端 chaos∧difficulty
- **Forbidden as positive:** 単なる高 chaos 全部, 「どれにも非該当」= bug

---

## Relation to V33 Input Contract

V33 は **搬送・生成契約**（difficulty/chaos/sfp/phase/…）を定義した。  
V43 は **勝ち筋意味契約**であり、V33 Signal を消費しうるが、V33 に無い概念（上位能力帯・中位評価帯・適性・例外標識・top_gap の勝ち筋極性）を Required として追加定義する。

V33 と V43 は階層が異なる:

```text
V33 World Input Contract  →  Signal が存在しうる
V43 World Semantic Contract → 各 World がどの Signal 意味を必要とするか
現行 TRIGGER_RULES         → 実装（V43 非準拠・変更しない）
```

## Guardrails

- 本表は契約定義。Signal の新規実装・配線・閾値は行わない。
- 改善手順は書かない。
