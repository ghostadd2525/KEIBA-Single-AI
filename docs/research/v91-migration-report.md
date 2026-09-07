# Version91 — Migration Report（M1 Shadow）

**Generated:** `2026-07-28T11:14:29+00:00`  
**Parent:** ADR-008 / v90-migration-adr.md  
**Phase status:** M1 Shadow = **PASS**

## 実施内容

1. Decision Layer モジュール実装（Production 非接続）
2. Feature Flag 既定 OFF（`W_DECISION_LAYER_*`）
3. Dual Shadow（Decision OFF / ON）285R 実行
4. Prediction Fingerprint / Rank / Score 一致監査

## M0 → M1

| 項目 | M0 | M1（本版） |
|---|---|---|
| ADR-008 | Accepted / 実装未承認 | Architecture 固定のまま **M1 Shadow 実装** |
| Flag | 設計のみ | コード化・既定 OFF |
| Shadow | V89 研究スクリプト | `app/decision` + V91 runner |
| Production | 禁止 | **禁止継続** |

## 次 Phase（未承認）

- M2 Flagged Staging — 別 Decision 必須
- M3 Production Canary — 別 Decision 必須

## Rollback

1. `W_DECISION_LAYER_ENABLED=false`（既定）
2. Decision 出力 = Legacy OFF（互換ゲート PASS）
3. Prediction 非干渉（Fingerprint 一致）

## 不変条件（遵守）

| ID | 結果 |
|---|---|
| M-I0 Prediction 非変更 | PASS |
| M-I1 World→PE Weight 禁止 | PASS |
| M-I2 World Prior 主エンジン化禁止 | PASS |
| Rollback 副作用なし | PASS（設計） |
