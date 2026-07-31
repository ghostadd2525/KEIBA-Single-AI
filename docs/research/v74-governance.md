# Version74 — Governance（World Strategy Validation）

**Date:** 2026-07-28  
**Verdict:** **B** — 一部重複する（安定 World は限定的だが、差の証拠あり）  
**Type:** Validation only（改善禁止）

## 根拠サマリ（285R / CEW）

| Item | Value |
|---|---|
| CEW 分布 | `{"unsatisfied": 176, "midupper_world": 6, "mixed_world": 6, "midhole_world": 24, "rank7_world": 65, "core_world": 8}` |
| 安定 World | ['midhole_world', 'rank7_world'] |
| 不安定 World | ['core_world', 'midupper_world', 'mixed_world'] |
| ゼロ World | ['bug_world'] |
| 符号逆転 | 2 |
| mean Top5 Jaccard (strategy stable) | 0.6667 |
| mean context profile corr (strategy stable) | 0.9959 |

【Decision】

| Item | Value |
|---|---|
| Action Type | World Strategy Validation |
| Implementation Required | **No** |
| Deployment Required | No |
| Configuration Required | No |
| Production Required | No |
| Rollback Required | No |
| Risk | None（読取のみ） |
| Expected Next Action | Verdict B を前提とした設計 Decision（本フェーズ改善禁止） |

## 遵守

| 制約 | |
|---|---|
| Trigger/Blueprint/Signal/Threshold/World Meaning 非変更 | PASS |
| PE/Prediction/Production 非変更 | PASS |
| 改善禁止 | PASS |
| ラベル = CEW のみ | PASS |
| 285R 実データのみ | PASS |

## 成果物

- `v74-world-strategy-validation.md`
- `v74-world-feature-separation.md`
- `v74-cross-world-similarity.md`
- `v74-governance.md`
- `_v74-world-strategy-validation.json`
