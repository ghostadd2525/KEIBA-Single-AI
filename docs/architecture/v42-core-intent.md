# Version42 — Core Intent Audit

**Date:** 2026-07-28  
**Type:** Research / Audit only  
**Focus:** `core_world` Trigger は「能力決着」を検出しているか？

## 設計意図（正本）

`core_world` = **能力どおり決着するレース**という独立した勝ち筋。

例示概念（ユーザ正本）:

- TopGap が大きい
- 能力差が結果へ反映される
- G1 などレース格
- 長距離など能力差が効きやすい条件

## 実装の事実

### 1. core に正の Trigger が無い

`TRIGGER_RULES` R8 / `classify_world_line_type` 最終行:

```text
return "core_world"   # 他条件に当てはまらなかった場合
```

R8: `logic: DEFAULT`, `parts: []`

→ **能力決着を検出する条件式は存在しない。**

### 2. 能力決着関連 Signal のコード上の所在

| 概念 | コード上の存在 | World Trigger での使用 |
|---|---|---|
| TopGap (`top1_prob - top2_prob`) | **あり** — `get_context_top_gap`（`demo_ticket_optimizer_core.py`） | **なし** — `classify_world_line_type` / `TRIGGER_RULES` に未登場 |
| top_median_gap 等 | **あり** — probability compression / large-field pressure | **なし**（World 本体分類には未接続） |
| 能力差（明示スコア差） | Trigger Signal 集合に無し | **なし** |
| レース格 (`race_class` / `grade`) | metadata・bug観測・別モジュールには存在 | **World Trigger に無し** |
| 距離 | **あり** — `get_context_distance` → `calc_short_field_pressure` 内 | **短距離寄りで sfp を上げる**用途。長距離=core の正条件ではない |

### 3. TopGap の実際の使われ方（World 周辺）

`calc_large_field_topgap_rank7_pressure` docstring（実コード）:

> field_size>=15 → top_gap小 → **core_underの能力決着判定が強すぎる**

ここでの TopGap は:

- **小さい TopGap** = core（能力決着）が強すぎる文脈への **脱出圧**
- rank7 方向の route/sub_world 圧

であり、**大きい TopGap → core_world 確定** という設計思想の実装ではない。  
かつこの圧は `classify_world_line_type` の if 連鎖に **組み込まれていない**。

### 4. soft fitness 上の core 定義

`trigger_proximity_fitness`（research）:

```text
core_world = 1 - max(other worlds soft scores)
```

→ soft でも core は **残余**。能力決着の正スコアではない（V40/V41 と整合）。

### 5. Product docstring との衝突

`classify_world_line_type`:

> LGBMは能力評価専用。world_line側で **survival world** を判定する。

| 層 | 役割（実コード） |
|---|---|
| LGBM | 能力評価 |
| world_line / World Trigger | survival world 分類 |
| 設計正本の core | 能力決着の勝ち筋 |

→ **能力決着は LGBM 側に置かれ、World の core は「survival でない残り」になっている。**  
設計正本の「core = 能力決着勝ち筋」とは構造的に一致しない。

## Core Intent 判定

| 監査問い | 結果 |
|---|---|
| core Trigger は能力決着を検出するか？ | **No**（検出条件なし） |
| TopGap 大 → core か？ | **No**（Trigger 未使用） |
| 能力差 → core か？ | **No** |
| レース格 → core か？ | **No** |
| 長距離 → core か？ | **No**（距離は短距離 sfp に使われる） |
| core の実装意味は？ | **他 survival Trigger の残余（DEFAULT）** |

**結論:** 現 Trigger は core の設計思想を表現していない。V41 の「R1–R7 FAIL → R8」は運用結果であると同時に、**意味論上も core が勝ち筋ではなく DEFAULT ラベルであることの証明**である。
