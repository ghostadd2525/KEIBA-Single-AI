# Version85 — Governance（Base Probability Redesign Investigation）

**Date:** 2026-07-28  
**Verdict:** **A**（underconfident Worlds=6/6；再定義案文書化完了 / 実装なし）  
**Type:** Research Investigation only

【Decision】

| Item | Value |
|---|---|
| Action Type | Base Probability Audit & Redesign Proposal |
| Implementation Required | **No** |
| PE Required | **No**（禁止） |
| Production Required | **No** |
| Trigger / Blueprint / World / Interaction | 非変更 |
| Rollback Required | No |
| Risk | None（読取調査） |
| Expected Next Action | 案 A（World Prior Anchor）の **Shadow Calibration**（別 Decision）。Interaction/PE/Production は継続禁止 |

## 遵守

| 制約 | 結果 |
|---|---|
| 実装禁止 | PASS |
| 改善（PE反映）禁止 | PASS |
| Production / Trigger / Blueprint / World / Interaction / PE 非変更 | PASS |

## 主結論

1. V84 p_base（win_prob mass）は全主要 World で systematic underconfidence。
2. Interaction は本問題の主因ではない（V84＋本監査で Interaction 未使用でも乖離）。
3. 次の設計焦点は Base Probability 再定義（案 A 優先）。

## 成果物

- `v85-base-probability-audit.md`
- `v85-calibration-analysis.md`
- `v85-candidate-definition.md`
- `v85-governance.md`
- `_v85-base-probability-audit.json`
