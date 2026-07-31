# Version49 — Prediction Contract Audit

**Date:** 2026-07-28  
**Type:** Research / Audit only（改善・実装禁止）  
**Public product contract (code):** `single-prediction-bundle/2.0`（`domains.BUNDLE_SCHEMA`）  
**HTTP:** `GET /v1/predictions`, `GET /v1/predictions/{race_id}`（`main.py`: PredictionBundle を共通契約）

## ① Prediction Entry Points

| ID | Entry | 実装 | 出力 |
|---|---|---|---|
| E1 | `GET /v1/predictions` | `prediction_adapter.list_with_meta` | PredictionBundle[] + envelope meta |
| E2 | `GET /v1/predictions/{race_id}` | `prediction_adapter.get_with_meta` | PredictionBundle + envelope meta |
| E3 | `PredictionAdapter.get_bundle` / `list_bundles` | Adapter 直 | Bundle（meta なし） |
| E4 | `RealAiPredictionSource._infer` | diagnose → map or mock | Bundle |
| E5 | `MockPredictionSource` | fixtures / template | Bundle（mock） |
| E6 | `ai_platform.single.api.get_prediction` | Single `predict` | **prediction_response**（Bundle ではない） |
| E7 | `run_single_prediction` / `diagnose_inference` | Mapper 側ラッパ | response → Bundle |

**公開 API の正本入口:** E1/E2（HTTP）。実推論時は E4→E6→Mapper。

---

## ④ Canonical Contract（結論先出し）

| 問い | 証明結果 |
|---|---|
| Prediction 公開正本は `evaluate_candidates` か？ | **No** — 主経路は呼ばない |
| `predict_ranking` か？ | **生成の Core 側入力**として Yes（薄投影） |
| 公開 DTO 正本は何か？ | **`PredictionBundle` (`single-prediction-bundle/2.0`)** |

詳細証明: `v49-contract-lineage.md`。

```text
evaluate_candidates  = AI Core Canonical CE（Prediction 非使用）
predict_ranking      = CE 互換 Ranking ビュー（World 無し）← Real 経路が使用
PredictionBundle     = Expect 公開契約 ← HTTP が返す正本
prediction_response  = Single 中間 DTO
```

---

## Governance 予告

複数 DTO（CE Bundle / RankingResult / prediction_response / PredictionBundle / Mock）が並存し、World は生成経路で到達不能 → **C（契約分裂）**。  
`v49-governance.md`。

## Artifacts

- `v49-prediction-contract.md`（本ファイル）
- `v49-contract-lineage.md`
- `v49-mapper-audit.md`
- `v49-information-loss.md`
- `v49-governance.md`
