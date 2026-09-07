# Version93 — Governance（Betting Policy Optimization）

**Date:** 2026-07-28  
**Verdict:** **A**（Coverage 制約下 ROI 最適化完了 / winner=`bet_L1_equal_field_gt_16_b0.5__dec_T5P7`）  
**Type:** Shadow only（Decision Layer Betting）

【Decision】

| Item | Value |
|---|---|
| Action Type | Betting Policy Optimization |
| ADR-008 / Architecture / Prediction | **未変更** |
| Decision structure | V92 Top5_Pool7 固定 |
| Production policy change | **No**（Shadow 推奨のみ） |
| Production Required | **No** |
| Expected Next Action | Winner `bet_L1_equal_field_gt_16_b0.5__dec_T5P7` を Shadow Betting 既定候補としてレビュー（別 Decision / M2 前） |

## 成果物

- `v93-betting-policy-optimization.md`
- `v93-betting-pareto.md`
- `v93-governance.md`
- `_v93-betting-policy-optimization.json`
- `app/decision/betting_params.py`
