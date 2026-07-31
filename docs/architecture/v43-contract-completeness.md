# Version43 — Contract Completeness

**Date:** 2026-07-28  
**Type:** Design metric only

## 定義（二層）

本フェーズは契約の **復元** が目的のため、完成度を二層で測る。

| 層 | 定義 | 本フェーズの結果 |
|---|---|---|
| **A. Spec Completeness** | ①Purpose〜⑥Characteristics が根拠付きで埋まり、Required/Optional/Forbidden が列挙されている割合 | 6 World すべて **100%**（契約書として復元完了） |
| **B. Trigger Mapping Completeness** | 現行 Trigger が契約 Required を満たす割合（V42 Semantic Score ×100 / 本 Mapping） | 平均 **21%**（実装は未束縛） |

⑨の報告値は、運用・統治上のギャップを示すため **B** を主指標とし、A を併記する。

採点規則（B）: FULFILLED=1.0 / PARTIAL=0.5 / MISSING・CONTRADICTS=0.0（Required 概念のみ）。

---

## Per-World Completeness

| World | A. Spec | B. Trigger Mapping | 契約 Required 概念数 | Fulfillment 内訳 |
|---|---:|---:|---:|---|
| `core_world` | 100% | **0%** | 5（能力決着正検出, TopGap大, 能力差, 格, 長距離※） | 0 aligned |
| `midupper_world` | 100% | **17%** | 3 | 展開 PARTIAL のみ |
| `midhole_world` | 100% | **0%** | 2 | 0 aligned |
| `rank7_world` | 100% | **50%** | 3 | chaos ALIGNED + pace PARTIAL |
| `mixed_world` | 100% | **33%** | 2 | 共存 PROXY のみ |
| `bug_world` | 100% | **25%** | 2 | 極端値 PROXY のみ |
| **平均** | **100%** | **21%** | — | — |

※ core の V42 採点は 5 概念。契約 Required の核は「正の能力決着 + TopGap/能力差」。格・距離は Optional だが V42 監査セットに含まれ 0% に寄与。

---

## Spec Completeness Checklist（A）

各 World について V43 契約正本で充足:

| 項目 | core | midupper | midhole | rank7 | mixed | bug |
|---|---|---|---|---|---|---|
| ① Purpose | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ② Winning Pattern | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ③ Required Signals | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ④ Optional Signals | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ⑤ Forbidden Signals | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ⑥ Expected Characteristics | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ⑦ Trigger Mapping | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ⑧ Missing Semantic | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

→ **Semantic Contract（仕様）は復元完了。**

---

## Interpretation（実装には触れない）

- A=100% / B=21% は矛盾ではない。  
  **契約は復元されたが、現行 Trigger は契約に束縛されていない**（V42 C と同一事実）。
- 最も Mapping が高いのは `rank7_world`（50%）。  
  最も低いのは `core_world` / `midhole_world`（0%）。

## Artifacts

- `v43-world-semantic-contract.md` — 契約正本
- `v43-world-contract-mapping.md` — Mapping 詳細
- `v43-required-signals.md` — Signal 行列
- `v43-governance.md` — 統治
