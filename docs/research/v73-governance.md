# Version73 — Governance（Contract Intent Evaluation）

**Date:** 2026-07-28  
**Verdict:** **A** — V69 Shadow が Legacy より CEW に近い  
**Type:** Evaluation only（改善禁止）

## 根拠（285R / Contract のみ）

| Metric | Legacy | V69 Shadow |
|---|---:|---:|
| Contract Intent Accuracy | 0.0561 | 1.0000 |
| Macro-F1 | 0.1036 | 1.0000 |
| Δ Acc (V69−Legacy) | — | 0.9439 |

**注:** CEW = V44 Logic Form オラクル。V69 は別 SUT。本 285R で World ラベル 285/285 一致は測定結果（GT≠SUT 定義）。

【Decision】

| Item | Value |
|---|---|
| Action Type | Contract Intent Evaluation（CEW） |
| Implementation Required | No（評価スクリプトのみ・Trigger 非変更） |
| Deployment Required | No |
| Configuration Required | No |
| Production Required | No |
| Rollback Required | No |
| Risk | None（読取評価） |
| Expected Next Action | Verdict A を受けた設計 Decision（本フェーズは改善禁止） |

## 遵守

| 制約 | |
|---|---|
| Trigger / Blueprint / Signal / Threshold 非変更 | PASS |
| PE / Prediction / Production 非変更 | PASS |
| 改善禁止 | PASS |
| GT = V72 CEW のみ | PASS |
| winner_rank / 人気 / Pred score / V65 非使用 | PASS |

## Prediction 併記（非 GT）

- Hit `218` / Purchase `218` / rank710 `14` / other_miss `18`
- Fingerprint `d3c43162ebf143239c456521a745d4af12d9cd53c78c561d351d559d88f93f2a`

## 成果物

- `v73-contract-intent-evaluation.md`
- `v73-world-metrics.md`
- `v73-confusion-matrix.md`
- `v73-governance.md`
- `_v73-contract-intent-evaluation.json`
