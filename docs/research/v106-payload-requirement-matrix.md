# Version106 — Payload Requirement Matrix

**Date:** 2026-07-28  
**Mode:** Shadow Audit · 実装禁止  
**Parents:** V103 Payload · V106 Single/Win5 Contracts

---

## 凡例

| 記号 | 意味 |
|---|---|
| **必須** | 当該 Consumer UC の成立に Core 上必要 |
| **推奨** | あると説明・監査・抑制が正確 |
| **不要** | 当該 UC に不要、または使用禁止（括弧で禁止理由） |
| **KD** | KEEP_DERIVED（Consumer/Registry 導出） |
| **EXT** | Core 外入力（Market / Race Card / Decision Registry） |

---

## Matrix A — 評価対象 Payload × Consumer UC

| Payload | Single 券種 | Single 買い目 | Single 説明 | Win5 候補数 | Win5 保険 | Win5 難易度 |
|---|---|---|---|---|---|---|
| **World** | 必須 | 必須 | 必須 | 必須 | 必須 | 必須 |
| **Near Miss** | 必須* | 必須* | 必須* | 必須* | 必須* | 推奨* |
| **Near Miss Class** | 必須* | 推奨* | 必須* | 必須* | 必須* | 推奨* |
| **Affinity** | 不要 (V97) | 不要 (V97) | 推奨 | 不要 (V97) | 不要 (V97) | 推奨 |
| **Exclusion Reasons** | 不要 | 不要 | 必須 | 不要 | 不要 | 推奨 |
| **Explanation Confidence** | 不要 (V101) | 不要 (V101) | 必須 | 不要 (V101) | 不要 (V101) | 推奨 |
| **Transition** | 推奨 | 不要 | 必須 | 不要 | 不要 | 推奨 |
| **Must Gaps** | 推奨 | 不要 | 必須 | 推奨 | 推奨 | 推奨 |

\* `world_id=unsatisfied` 時。MATCH World では Near Miss 系は null（V103 PCS-4 系）で **不要**。

---

## Matrix B — 既出 Core 付帯（変更なし・参照）

| 項目 | Single 券種 | Single 買い目 | Single 説明 | Win5 候補数 | Win5 保険 | Win5 難易度 |
|---|---|---|---|---|---|---|
| Prediction Rank/Score | 推奨 | **必須** | 推奨 | **必須** | 推奨 | 推奨 |
| decision_trace.match/exclude | 推奨 | 不要 | **必須** | 推奨 | 推奨 | 推奨 |
| expected_strategy_ref | KD | KD | KD | KD | KD | KD |
| Natural Explanation | DO_NOT_EXPORT | — | KD (Presentation) | — | — | KD |

---

## Matrix C — Core に載せないもの（意図的）

| 項目 | 分類 | 根拠 |
|---|---|---|
| Ticket / 保険券 / Skip 指令 | EXT (Decision 出力) | V103 PCS-7 |
| Pool サイズ定数 (TopK/PoolN) | EXT (Decision Registry) | V92; V88 |
| race_difficulty スカラー | KD / EXT | 新 Semantic 禁止 |
| field_size | EXT (Race Card) | V88 条件。Core 意味ではない |
| odds / budget | EXT (Market) | ADR-010 |
| Prediction Confidence | 禁止（Core） | ADR-010 |

---

## 集計

| Consumer | 必須 Core Semantic（MATCH） | 必須 Core Semantic（unsatisfied） |
|---|---|---|
| Single 説明 | World, Transition, Must Gaps, Exclusion, EC | + Near Miss, Near Miss Class; Affinity 推奨 |
| Single 券種/買い目 | World (+ Prediction) | + Near Miss / Class |
| Win5 候補/保険 | World (+ Prediction) | + Near Miss / Class |
| Win5 難易度 | World（プロキシ） | + NM/EC 推奨。専用フィールド不要 |

---

## Related

- `v106-contract-gap-report.md`
- `v106-governance.md`
