# Version44 — World Trigger Specification

**Date:** 2026-07-28  
**Status:** Design Specification ONLY（実装・コード・閾値・Signal 変更なし）  
**Type:** Research / Design  
**Bridge:**

```text
V43 World Semantic Contract（意味の正本）
        │
        ▼
V44 World Trigger Specification（本ドキュメント群）
        │  ← ここまでが本フェーズ
        ▼
（将来）Trigger Implementation  ← 本フェーズ対象外・禁止
```

## Purpose

V43 は「World とは何か」を固定した。  
V44 はそれを **Trigger 設計仕様**へ変換する公式レイヤを定義する。

本仕様が答える問い:

- どの Signal が必須か（Must）
- どの Signal が補助か（Aux）
- どの Signal を正条件に使ってはいけないか（Forbidden）
- どのような論理関係（AND / OR / 重み・極性）が設計意図に沿うか

本仕様が **答えない** 問い（禁止）:

- 数値 Threshold
- 実装コード / `TRIGGER_RULES` の書き換え
- Signal 生成・CSV・Production 変更
- 改善ロードマップ

---

## Spec Vocabulary

| 用語 | 定義 |
|---|---|
| **Must Signal** | 当該 World を Trigger で主張するために **必ず関与**する Signal（欠けると仕様上 unsatisfied） |
| **Aux Signal** | 精度・境界の補助。単独では World を確定しない |
| **Forbidden-as-positive** | 当該 World の **成立条件として使ってはならない** Signal / 用法 |
| **Polarity** | 同じ Signal でも「高いほど寄り」か「低いほど寄り」か（例: top_gap 大→core / 小→rank7） |
| **Logic Form** | Must 間の結合（AND / OR / 重み付き合成）と、Forbidden の排除関係 |
| **Positive Match** | World は残余 DEFAULT ではなく、仕様上 **正の成立条件**で選ばれる |

---

## Global Trigger Design Rules（全 World 共通）

### T0. Positive Match Principle

各 Canonical World（core を含む）は **正の Trigger 仕様**を持つ。  
「他が全部 FAIL したからこの World」は V44 仕様として **認めない**（V43 Forbidden / V41–V42 根拠）。

### T1. Semantic → Trigger 変換規則

| V43 項目 | V44 への変換 |
|---|---|
| Purpose / Winning Pattern | Logic Form の目的関数（何を検出するか） |
| Required Signals | Must Signal + Polarity |
| Optional Signals | Aux Signal + 役割（強化 / タイブレーク） |
| Forbidden Signals | Forbidden-as-positive + 排他 World への委譲 |
| Expected Characteristics | 成立時に観測されるべき特性（検証観点。閾値ではない） |

### T2. 論理プリミティブ（閾値なし）

許可する論理表現（設計レベル）:

1. **AND** — 複数 Must が同時に「契約上の方向」を満たす  
2. **OR** — 同義の別表現（代替経路）。異なる勝ち筋の OR は mixed 専用  
3. **AND-of-OR** — 必須軸は AND、各軸の表現手段は OR  
4. **Weighted support（補助）** — Aux は Must 成立後の信頼度・境界のみ。Must を置換しない  
5. **Exclusion** — Forbidden 方向が強い場合、当該 World は不成立（他 World へ）

**禁止:** 本仕様書内での数値カットオフ、ハードコード閾値表、疑似コードの if 連鎖実装。

### T3. Signal 極性カタログ（設計）

| Signal / Concept | core 向き | midupper 向き | midhole 向き | rank7 向き | mixed | bug |
|---|---|---|---|---|---|---|
| `top_gap` | **高** Must | 中 Aux | 低寄り Aux | **低** Must | — | — |
| 能力差 / 分布分離 | **大** Must | 中〜 Aux | 小寄り Must関連 | 小 Aux | — | — |
| 上位能力帯 | 強すぎると core 境界 | **Must** | Forbidden-as-def | Forbidden-as-def | — | — |
| 中位評価帯 | Forbidden-as-def | Forbidden-as-def | **Must** | Aux 可 | — | — |
| 適性 | — | **Must** | Aux | — | — | — |
| `chaos` | 高は Forbidden-as-pos | 中 Aux | 中 Aux | **高** Must | Aux | 極端 Aux |
| `high_pace` / 展開圧 | 高単独 Forbidden | Aux（展開軸） | Aux | **Must 系** | Aux | — |
| `short_field_pressure` | 高は Forbidden-as-pos | Aux（展開） | — | Aux | Aux | — |
| `difficulty` | 単独定義 Forbidden | Aux（非・能力帯） | — | Aux | Aux | 極端 Aux |
| `late_stop` / `sustained` | 高∧は Forbidden-as-pos | — | Aux のみ | — | — | — |
| 複数勝ち筋同時活性 | Forbidden | Forbidden | Forbidden | Forbidden | **Must** | — |
| 例外 / 説明不能標識 | Forbidden（≠DEFAULT） | — | — | — | — | **Must** |

---

## Per-World Trigger Spec（要約）

詳細ロジックは `v44-trigger-logic.md`。Signal 役割の横断表は `v44-signal-roles.md`。

### `core_world`

- **Must:** 能力決着軸（`top_gap` 高 polarity）AND 能力差・分布分離（大）  
- **Aux:** レース格、長距離寄り、低 route 圧（低 sfp）  
- **Forbidden-as-positive:** DEFAULT 残余、高 chaos、高 sfp、late_stop∧sustained  
- **Logic Form:** `AbilityResolution = GapHigh AND SeparationLarge`；Aux は support のみ  
- **Exclusion:** ChaosHigh OR MidBandOpen OR MultiPath → core 不成立

### `midupper_world`

- **Must:** 上位能力帯 AND 展開影響 AND 適性  
- **Aux:** difficulty、sfp（中）、top_gap（中）  
- **Forbidden-as-positive:** difficulty のみ、chaos∧high_pace（rank7 領域）、中位帯の広さ  
- **Logic Form:** `UpperAbility AND Development AND Aptitude`（各軸は内部 OR で表現手段を許す）

### `midhole_world`

- **Must:** 中位評価帯の開き AND 上位独占の弱さ  
- **Aux:** late_stop、sustained、中程度 chaos  
- **Forbidden-as-positive:** late_stop∧sustained を定義本体にする、高 TopGap 独占、極端 chaos のみ  
- **Logic Form:** `MidBandOpen AND WeakTopMonopoly`；pace 系は Aux のみ

### `rank7_world`

- **Must:** chaos 高 AND 展開/混戦圧 AND 能力劣後（top_gap 低 polarity）  
- **Aux:** 多頭、短〜中距離、difficulty  
- **Forbidden-as-positive:** 高 TopGap 能力決着、chaos なし difficulty のみ  
- **Logic Form:** `ChaosHigh AND PaceConflict AND AbilitySubordinate`

### `mixed_world`

- **Must:** 複数勝ち筋の同時活性（2+ World 意味の競合）OR 単一説明不能の明示  
- **Aux:** 複合圧力（sfp / phase / chaos / difficulty の同時立ち）  
- **Forbidden-as-positive:** phase 単独、単一明確勝ち筋の強制ラベル  
- **Logic Form:** `MultiPathActive`（競合カウント）— 単一軸の高値では不可

### `bug_world`

- **Must:** 例外 / 説明不能標識（core DEFAULT と非同一）  
- **Aux:** 極端 chaos ∧ 極端 difficulty  
- **Forbidden-as-positive:** 単なる高 chaos 全部、「どれにも非該当」= bug  
- **Logic Form:** `ExceptionFlag`（正の特殊標識）；残余ラベル禁止

---

## Evaluation Order（設計原則・閾値なし）

1. **除外（Exclusion）** — Forbidden 方向が支配的なら当該候補を落とす  
2. **Must 充足** — Positive Match で各 World の Logic Form を評価  
3. **競合** — 複数 World が Must 充足 → `mixed_world` 仕様へ（単一へ無理に落とさない）  
4. **Aux** — 境界・信頼度のみ。Must 未充足を Aux で埋めない  
5. **未充足** — どの World も Must 未充足のとき、仕様上は *unclassified / unsatisfied*（core への暗黙 DEFAULT は V44 では定義しない）

※ 現行実装の first-match + R8 DEFAULT は **観測仕様**であり、V44 設計仕様ではない。

---

## Document Index

| Doc | Content |
|---|---|
| `v44-world-trigger-specification.md` | 本ファイル（仕様総則） |
| `v44-trigger-logic.md` | World 別 Logic Form 詳細 |
| `v44-signal-roles.md` | Must / Aux / Forbidden 横断 |
| `v44-semantic-to-trigger-bridge.md` | V43→V44 変換対応表 |
| `v44-governance.md` | 統治 |

## Guardrails

- Design specification only.
- No Trigger code, no Thresholds, no Signal / Production / CSV changes.
- No improvement implementation roadmap.
