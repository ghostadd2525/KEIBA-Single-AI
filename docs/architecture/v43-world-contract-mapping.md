# Version43 — World Contract ↔ Existing Trigger Mapping

**Date:** 2026-07-28  
**Type:** Design mapping only（Trigger 変更なし）  
**Contract:** `v43-world-semantic-contract.md`  
**Trigger source:** `classify_world_line_type` / `TRIGGER_RULES` R1–R8

## 凡例

| 記号 | 意味 |
|---|---|
| FULFILLED | 契約 Required 概念が Trigger 正条件として符号化されている |
| PARTIAL | 関連 Signal はあるが契約意味と一致しない／近似のみ |
| MISSING | 契約 Required が Trigger に存在しない |
| CONTRADICTS | Trigger の意味が契約と矛盾（Wrong / Inverted） |

充足率 = (FULFILLED×1.0 + PARTIAL×0.5) / Required概念数（V42 採点と同型）

---

## `core_world`

| 契約要素 | 現行 Trigger | 判定 |
|---|---|---|
| Purpose: 能力決着の独立勝ち筋 | R8 `DEFAULT`（残余） | **CONTRADICTS** |
| Required: top_gap 大 | 未使用（関数は存在、Trigger 外） | **MISSING** |
| Required: 能力差の分離 | 未使用 | **MISSING** |
| Required: 非・高 chaos / 非 survival を正で示す | 正条件なし | **MISSING** |
| Optional: レース格 | 未使用 | MISSING（Optional） |
| Optional: 長距離 | 未使用（距離は sfp 短距離側） | CONTRADICTS（方向） |
| Forbidden: DEFAULT を core 定義にしない | R8 が DEFAULT | **CONTRADICTS** |

**Mapping 充足率: 0%**（V42 Semantic Score 0.00）

---

## `midupper_world`

| 契約要素 | 現行 Trigger | 判定 |
|---|---|---|
| Purpose: 上位能力 + 展開・適性 | R2 sfp∧difficulty / R7 difficulty | **PARTIAL〜CONTRADICTS** |
| Required: 上位能力帯 | 無し（difficulty≠上位能力） | **MISSING** |
| Required: 展開影響 | R2 `short_field_pressure` | **PARTIAL**（route 圧） |
| Required: 適性 | 無し | **MISSING** |
| Optional: difficulty | R2/R7 で使用 | PARTIAL（意味ずれ） |

**Mapping 充足率: 17%**（0.5/3）

---

## `midhole_world`

| 契約要素 | 現行 Trigger | 判定 |
|---|---|---|
| Purpose: 中位評価まで勝ち筋 | R4 late_stop∧sustained | **MISSING**（意味不一致） |
| Required: 中位評価帯 | 無し | **MISSING** |
| Required: 上位独占の弱さ | 無し | **MISSING** |
| Optional: late_stop/sustained | R4 正条件 | PARTIAL（契約上 Optional のみ） |

**Mapping 充足率: 0%**（Required 基準）

---

## `rank7_world`

| 契約要素 | 現行 Trigger | 判定 |
|---|---|---|
| Purpose: Chaos/展開 > 能力 | R5 chaos∧high_pace | **PARTIAL** |
| Required: chaos 高 | R5 | **FULFILLED** |
| Required: 展開/混戦圧 | R5 high_pace | **PARTIAL** |
| Required: 能力劣後（低 top_gap 等） | Trigger 未使用（別 pressure 関数に存在） | **MISSING** |

**Mapping 充足率: 50%**（1.5/3）

---

## `mixed_world`

| 契約要素 | 現行 Trigger | 判定 |
|---|---|---|
| Purpose: 複数勝ち筋の共存 | R1 複合 OR / R3 phase | **PARTIAL** |
| Required: 複数勝ち筋同時活性 | 明示なし。圧力 OR のみ | **PARTIAL** |
| Required: 単一説明不能の明示 | 無し | **MISSING** |
| Forbidden: phase のみで定義 | R3 が存在 | **CONTRADICTS**（契約 Forbidden に抵触する経路） |

**Mapping 充足率: 33%**（0.5/2）

---

## `bug_world`

| 契約要素 | 現行 Trigger | 判定 |
|---|---|---|
| Purpose: 説明困難な特殊ケース | R6 高 chaos∧高 difficulty | **PARTIAL** |
| Required: 説明不能/例外標識 | 無し | **MISSING** |
| Required: core DEFAULT と区別 | bug は正条件あり、core は DEFAULT — 区別は形式的のみ | **PARTIAL** |
| Optional: 極端 chaos∧difficulty | R6 | PARTIAL |

**Mapping 充足率: 25%**（0.5/2）

---

## Summary Table（⑦）

| World | Rules | Trigger Signals | Contract Fulfillment | Primary Gap |
|---|---|---|---:|---|
| core | R8 DEFAULT | （なし） | **0%** | 能力決着の正符号化なし |
| midupper | R2, R7 | sfp, difficulty | **17%** | 上位能力・適性なし |
| midhole | R4 | late_stop, sustained | **0%** | 中位評価帯なし |
| rank7 | R5 | chaos, high_pace | **50%** | 能力劣後（低 TopGap）未接続 |
| mixed | R1, R3 | sfp, phase, chaos, difficulty | **33%** | 共存の明示なし |
| bug | R6 | chaos, difficulty | **25%** | 例外標識なし |
| **平均** | — | — | **21%** | — |

## Missing Semantic（⑧ 要約）

横断リストは `v43-required-signals.md` / 詳細は契約正本と V42 gap を参照。

| World | 契約にあるが Trigger に無い主な概念 |
|---|---|
| core | top_gap 大, 能力差, 格, 長距離, 正の能力決着条件 |
| midupper | 上位能力帯, 適性 |
| midhole | 中位評価/rank/人気帯 |
| rank7 | 低 top_gap（能力劣後） |
| mixed | 複数勝ち筋の同時活性の明示 |
| bug | 説明不能・例外フラグ |

## Note

本表は **契約 vs 現行実装の差分観測**である。差分を埋める実装手順・改善案は記載しない（V43 禁止事項）。
