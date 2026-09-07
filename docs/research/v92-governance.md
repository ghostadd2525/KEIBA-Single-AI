# Version92 — Governance（Decision Policy Optimization）

**Date:** 2026-07-28  
**Verdict:** **A**（16点探索完了 / Pareto 作成 / 推奨=`rank7_Top5_Pool7_s1`）  
**Type:** Decision Layer parameter optimization only

【Decision】

| Item | Value |
|---|---|
| Action Type | Decision Policy Optimization |
| ADR-008 | **未変更** |
| Architecture / Prediction / Ranking / Confidence / Calibration / World / Trigger | **未変更** |
| Decision Layer params | **探索・文書化** |
| Production default policy change | **No**（M1 互換維持。推奨は Shadow 候補） |
| Production Required | **No** |
| Expected Next Action | 推奨 `rank7_Top5_Pool7_s1` を Shadow 既定候補として M2 前レビュー（別 Decision）。ADR-008 変更禁止継続 |

## 推奨サマリ

- Max ROI: `rank7_Top3_Pool4_s1`
- Max Purchase Hit: `rank7_Top5_Pool4_s1`
- Balanced: `rank7_Top5_Pool7_s1`

## 成果物

- `v92-decision-policy-optimization.md`
- `v92-pareto-front.md`
- `v92-governance.md`
- `_v92-decision-policy-optimization.json`
