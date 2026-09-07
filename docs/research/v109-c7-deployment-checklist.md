# Version109 Phase C7 — Deployment Checklist（Canary）

**Date:** 2026-07-29  
**用途:** Canary 前提条件の一覧。Production 切替チェックリストではない。

---

## 必須（ライブラリ / Flag 層）— 充足

| ID | 項目 | Status |
|---|---|---|
| lib_consumer_c1_c4 | Consumer 実装（C1–C4） | PASS |
| shadow_validation_c5 | Shadow Validation | PASS |
| ux_validation_c55 | UX Validation | PASS_WITH_NOTES（既知） |
| staging_validation_c6 | Staging Flag 検証 | PASS |
| feature_flags | W_CONSUMER_* 既定 OFF | PASS |
| version_contract | v1 schemas + PLATFORM-V1-CONTRACT | PASS |
| boundary_integrity | 逆依存なし | PASS |
| failure_recovery_flag_off | Flag OFF 復旧 | PASS |

---

## Canary トラフィック必須 — 不足（Blocker）

| ID | 項目 | Status | 備考 |
|---|---|---|---|
| http_canary_route | Canary HTTP / edge 経路 | **GAP** | 実装は別 Gate |
| metrics_dashboard | エラー率・遅延・Flag スナップショット | **GAP** | |
| alert_rules | Legacy 比較アラート | **GAP** | |
| traffic_split_control | 割合制御（1%→…） | **GAP** | |

---

## 推奨

| ID | 項目 | Status |
|---|---|---|
| ops_oncall_runbook_signoff | オンコール署名 | GAP（非 blocker） |

---

## 明示的にやらないこと（本 Checklist 外）

- Prediction / Semantic / Core / Contract 変更  
- Consumer 機能追加  
- Production 100% 切替  
