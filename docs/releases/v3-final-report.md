# Version 3 — Final Report

**Date:** 2026-07-24  
**Status:** **CLOSED**（研究クローズ）  
**Close ID:** `v3-close/1.0`  
**Companion:** [`v3-close-report.md`](./v3-close-report.md)

---

## 1. Decision Summary（確定）

| 項目 | Decision |
|------|----------|
| **PRR** | **HOLD** |
| **Go / No-Go** | **NO-GO**（即時本番投入不可） |
| **Production Integration** | **Design Complete**（PASS · 未実装） |
| **A-05** | **Official Production Candidate** |
| **A-03** | **Deprecated**（本番禁止 · Offline FAIL） |
| Version 3 Research | **CLOSED** |
| Production Rollout / Flag ON / Phase 3 / Version 4 | **未着手** |

---

## 2. エグゼクティブサマリー

Version 3 は V2（PE-V2-A · Hit 218）から分離した Offline Lab として、  
Representation → Admission → Selection → Evaluation → Purchase のパイプラインと  
Accuracy 介入（A-01〜A-05）を構築した。

Lab 合成では Baseline v3（A-01+A-03+A-04）が Hit **279** に到達したが、  
実データ Offline では A-03 過剰 promote により **FAIL**（59→42）。  
独立候補 **A-05 Favorite-Safe** が Offline / Validation / Shadow S0·S1 で **PASS**（59→66 · wr1=0）。

本番は未配線。PRR HOLD · NO-GO のまま研究をクローズする。  
公式本番候補は **A-05**。A-03 は Deprecated。

---

## 3. Architecture Summary

詳細: [`v3-architecture-summary.md`](./v3-architecture-summary.md)

```text
Input runners
  → Representation (P2 · optional)
  → Admission (A-05 candidate | A-03 deprecated | P3)
  → Selection (A-04 | P4)
  → Evaluation (A-01 Primary | A-02 Secondary)
  → Purchase (identity / 既存本番 · V3新Purchaseなし)
```

Lab パッケージ: `research/v3_lab/`（V2 Production 非 import）

---

## 4. Experiment Registry（最終版）

| Experiment ID | Phase | 結果 / 状態 |
|---------------|-------|-------------|
| v3-p1 … v3-p5 | Foundation | complete · frozen |
| v3-a01-d1 | Evaluation | PASS · Primary |
| v3-a02-d2 | Evaluation | PASS · Secondary · 同時ON禁止 |
| v3-a03-pool-coverage | Admission | Lab PASS · Offline **FAIL** · **Deprecated** |
| v3-a04-sel-history | Selection | PASS · Baseline v3 構成要素 |
| v3-lab-baseline-v3 | Freeze | Hit 279 · **本番禁止**（A-03含む） |
| offline-gate | Gate | FAIL（A-03スタック） |
| divergence / RCA | Analysis | PASS |
| admission-correction design | Design | PASS |
| v3-a05-favorite-safe | Admission | Accuracy+Validation **PASS** · **Official Candidate** |
| a05-shadow S0/S1 | Shadow | **PASS** |
| prr-final | Review | **HOLD** |
| production-integration | Design | **PASS** · 未実装 |
| **v3-close** | Close | **CLOSED** |

JSON スナップショット: `research/v3_lab/baselines/v3_close/experiment_registry_final.json`

---

## 5. Feature Flag Inventory（最終版）

| Flag | 既定 | 役割 | Close 時方針 |
|------|------|------|--------------|
| `F_V3_REPRESENTATION` | OFF | P2 | 維持 OFF |
| `F_V3_ADMISSION` | OFF | P3 | 維持 OFF |
| `F_V3_SELECTION` | OFF | P4 | 維持 OFF |
| `F_V3_RANK_D1_ENABLED` | OFF | A-01 | 候補スタック用 · 既定 OFF |
| `F_V3_RANK_D2_ENABLED` | OFF | A-02 | Secondary · 同時ON禁止 |
| `F_V3_A03_POOL_ADMIT_ENABLED` | OFF | A-03 | **Deprecated · 本番禁止** |
| `F_V3_A05_ADM_FAVSAFE_ENABLED` | OFF | A-05 | **Official Candidate · 既定 OFF** |
| `F_V3_A04_SEL_HISTORY_ENABLED` | OFF | A-04 | 候補スタック任意 |
| `F_V3_PURCHASE_ENABLED` 他 | OFF | stub | 未使用推奨 |
| `WIN5_V3_A05_SHADOW_RUNTIME_ENABLED` | false | Shadow | Lab 専用 |

**mutex:** A-03 ∧ A-05 禁止。

詳細: [`v3-close-report.md`](./v3-close-report.md) § Flag Inventory

---

## 6. Production Candidate 一覧

| 候補 | 状態 | 備考 |
|------|------|------|
| **A-05 Admission** | **Official Production Candidate** | Offline 66 · Shadow S0/S1 PASS |
| A-01 Evaluation | Stack 構成要素 | Primary |
| A-04 Selection | Stack 構成要素 | History Crowding |
| Baseline v3 (A-01+A-03+A-04) | Lab 記録のみ | **本番禁止** |
| A-03 | **Deprecated** | Offline FAIL |
| A-02 | Secondary | 同時ON禁止 |

**意図 To-Be スタック（未配線）:** Admission **A-05** · Selection A-04 · Evaluation A-01 · Purchase 既存本番

---

## 7. Known Risks

| リスク | 等級 |
|--------|------|
| A-03 誤投入 | Critical |
| API/Purchase 未配線のまま Flag ON | High |
| Lab 279 過信 | High |
| Flag 既定汚染 | High |
| A-05 長期ドリフト | Med |

詳細: [`v3-residual-risk-report.md`](./v3-residual-risk-report.md) · Close Report

---

## 8. Remaining TODO（V3 外 · 未着手）

1. PRR 条件付き GO  
2. Integration 実装（API/Purchase/Ops）  
3. Staging Rollback ドリル  
4. Canary Flag Mesh  
5. 公式 Baseline を A-05 系に再発行  
6. Version 4 企画（別プログラム）

---

## 9. Version 4 への引継ぎ

詳細: [`v4-handover-from-v3.md`](./v4-handover-from-v3.md)

要点: A-05 を起点に本番統合 · A-03 再挑戦禁止 · Dual-Gate（Lab+Offline）必須 · Flag 既定 OFF。

---

## 10. 停止

Version 3 Final Report をもって研究クローズを宣言する。  
Version 4 · Production Rollout · Phase 3 には着手しない。
