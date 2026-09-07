# Version44 — Semantic Contract → Trigger Spec Bridge

**Date:** 2026-07-28  
**From:** `v43-world-semantic-contract.md`  
**To:** `v44-world-trigger-specification.md` + `v44-trigger-logic.md`

## Conversion Table

| V43 要素 | V44 要素 | 変換規則 |
|---|---|---|
| G1 World=勝ち筋 | T0 Positive Match | 残余 DEFAULT を仕様から排除 |
| Purpose | Logic Form の Intent | 「何を検出するか」一文に固定 |
| Winning Pattern | Exclusion / 境界 | 他 World との排他条件へ |
| Required Signals | Must + Polarity | 欠落 = unsatisfied |
| Optional Signals | Aux | Must 非置換 |
| Forbidden Signals | Forbidden-as-positive / CORE_EXCLUDE 等 | 正条件使用を禁止 |
| Expected Characteristics | 検証観点（非閾値） | 成立時の観察特性として記録 |

---

## World-by-World Bridge

### core_world

| V43 | V44 Spec |
|---|---|
| 独立の能力決着 | `CORE_MUST = top_gap↑ AND ability_separation↑` |
| TopGap 大 / 能力差 | Must polarity ↑ |
| 格・長距離 | Aux |
| DEFAULT 禁止 | `FORBIDDEN_FORM` 明示 |
| 高 chaos / 高 sfp / late∧sust 禁止 | `CORE_EXCLUDE` |

### midupper_world

| V43 | V44 Spec |
|---|---|
| 上位能力 + 展開 + 適性 | 3 軸 AND（UPPER ∧ DEV ∧ APT） |
| difficulty / sfp | Aux（DEV の代替に difficulty 単独は不可） |
| rank7 / midhole 混同禁止 | `MIDUPPER_EXCLUDE` |

### midhole_world

| V43 | V44 Spec |
|---|---|
| 中位評価まで勝ち筋 | `mid_eval_band_open ∧ top_monopoly↓` |
| late_stop / sustained | Aux 固定（Must 昇格禁止） |

### rank7_world

| V43 | V44 Spec |
|---|---|
| Chaos・展開 > 能力 | chaos↑ ∧ pace_conflict↑ ∧ ability_subordinate |
| 低 TopGap | Must（ability_subordinate） |
| 現行 R5 に無い能力劣後 | Spec 上 Must（実装は触れない） |

### mixed_world

| V43 | V44 Spec |
|---|---|
| 複数勝ち筋共存 | `MULTI_PATH`（競合カウント） |
| phase のみ禁止 | `MIXED_EXCLUDE` |
| R1 複合圧力 | Aux バンドル |

### bug_world

| V43 | V44 Spec |
|---|---|
| 説明困難な特殊 | `exception_flag` Must |
| 残余≠bug | unlabeled_residual 禁止 |
| 極端 chaos∧difficulty | Aux |

---

## Layer Stack（権限）

```text
V32/V36  哲学: World = 勝ち筋
V33      Signal 搬送・生成契約
V43      Semantic Contract（意味）
V44      Trigger Specification（意味→Trigger 論理）  ← 本層
----     実装境界（本フェーズは越えない）
現行     TRIGGER_RULES / classify_world_line_type（観測のみ）
```

衝突時:

| 層 | 扱い |
|---|---|
| 意味・Trigger 仕様 | V43 / V44 が正本 |
| 実行コード | 現行実装（変更しない） |

## Out of Scope（明示）

- Threshold 数値の決定
- Trigger コード実装
- Signal 新規追加・配線
- Evaluation Order のプロダクトへの適用
- 改善・移行計画

## Completeness of Bridge

| World | V43→V44 Must 変換 | Logic Form 文書化 | 閾値なし遵守 |
|---|---|---|---|
| core | ✓ | ✓ | ✓ |
| midupper | ✓ | ✓ | ✓ |
| midhole | ✓ | ✓ | ✓ |
| rank7 | ✓ | ✓ | ✓ |
| mixed | ✓ | ✓ | ✓ |
| bug | ✓ | ✓ | ✓ |

**Bridge Status: COMPLETE（設計仕様として）**
