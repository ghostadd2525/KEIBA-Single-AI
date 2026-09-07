# Version99 — AI Core Completeness Charter

**Date:** 2026-07-28  
**Status:** Charter（設計確定）· **Core への Decision 実装禁止**  
**ADR:** ADR-009  
**Parents:** ADR-003 · ADR-008 · V94–V98

---

## 一文

**AI Core は利益を最大化しない。全レースについて最も正確な World / Near Miss / Affinity / Transition / Expected Strategy を返す。購入（ROI・券種・Skip・資金）は Single AI / Win5 AI の Decision が担当する。**

---

## Core が返すもの

| 出力 | Core の成功条件 | Core がやらないこと |
|---|---|---|
| World | 契約どおりのラベル精度・再現性 | 勝ちチケット化 |
| Near Miss | Exclusion 近接の正しい分離と保持 | Risk SKIP 最適化 |
| Affinity | Must 近さの正確な計測 | Affinity で CEW 書き換え |
| Transition | 遷移・トレースの欠落なき説明 | 購入経路の最適化 |
| Expected Strategy | V75 的な「読み方」の明示 | 券種・金額・配分 |

---

## Decision が返すもの（Core 外）

| 出力 | Owner |
|---|---|
| Ticket / 券種 | Single / Win5 Decision |
| Skip / Risk ゲート | Single / Win5 Decision |
| 資金配分 / Budget | Single / Win5 Decision |
| ROI 最適化 | Single / Win5 Decision |

---

## 研究スコープの切替

| これまで混線しやすかったもの | 今後の所属 |
|---|---|
| V93 Betting Policy | Decision 研究 |
| V97 Affinity Decision Value | Decision 研究（結論: NO_VALUE） |
| V98 Near Miss ROI Pattern | Decision 研究（購入条件の参考） |
| V94–V96 Taxonomy / Affinity 測定 | **Core Completeness の入力資産** |
| V99 以降の主評価 | **Prediction / World / Near Miss Completeness** |

---

## Expected Strategy（定義の境界）

Expected Strategy とは:

- その World / Near Miss で **何を優先して読むべきか**（history / win_prob / 混戦注意 等）
- Explanation と Selector 意図の完全性

Expected Strategy とは **でない**:

- 単勝を何点買うか
- Skip するか
- 予算をどう割るか

---

## 関連

- `ADR-009-ai-core-completeness.md`
- `v99-completeness-evaluation.md`
- `v99-governance.md`
