# Version 3 — Accuracy Phase 2 Final Report

**Date:** 2026-07-24  
**Close ID:** `v3-accuracy-phase2-close/1.0`  
**Status:** **CLOSED**  
**Design authority:** [`v3-design-report.md`](./v3-design-report.md)  
**Baseline v3:** `research/v3_lab/baselines/lab_baseline_v3_a01_a03_a04.json`  
**Code:** `research/v3_lab/phase2_close.py`（Registry / Baseline 記録のみ · アルゴリズム非変更）

---

## 1. 目的

Version 3 Accuracy Phase 2 の成果を固定し、正式な **Lab Baseline v3** を作成する。  
本 Close では新しい Accuracy アルゴリズムは実装しない。

---

## 2. Decision（確定）

| 項目 | 決定 |
|------|------|
| Lab Baseline v3 | **A-01 + A-03 + A-04** |
| Stack Hit | **279** / 285R |
| A-02 | Secondary Candidate として保持（スタック外） |
| D1+D2 同時 ON | **禁止** |
| Delete | **研究対象外**（残 miss 6） |
| 本番配線 | **行わない** |
| Phase 3 | **未着手** |

---

## 3. Phase 2 成果サマリ

| マイルストーン | 結果 |
|----------------|------|
| Phase 2 Research Design | Pool を主問題として定義 |
| A-03 Admission | Hit 255（vs A-01 246）· churn 0 · **PASS** · スタック採用 |
| Lab Configuration Freeze | Baseline v2 = A-01+A-03 · Hit 255 |
| Gap Analysis v2 | 残 = Boundary14 + Reorder10 + Delete6 · A-04=Selection |
| A-04 Selection | Hit **279**（vs v2 255）· churn 0 · **PASS** · スタック採用 |
| Phase 2 Close | 本レポート · Baseline v3 |

```text
Phase1 Close → A-03 → Config Freeze (v2) → Gap v2 → A-04 → Phase2 CLOSE (v3)
```

---

## 4. Lab Baseline v3

| 項目 | 値 |
|------|-----|
| Baseline ID | `v3-lab-baseline-v3-a01-a03-a04` |
| Parent | `v3-lab-baseline-v2-a01-a03` |
| Corpus | `a03-285-*` · 285R |
| Control Hit | **218** |
| Stack Hit | **279** |
| churn vs Control | **0** |
| churn vs Baseline v2 | **0** |
| 残 miss | **6（Delete only）** |

詳細: [`v3-phase2-baseline-v3-report.md`](./v3-phase2-baseline-v3-report.md)

### 構成図

```text
Representation (Baseline)
        ↓
Admission (A-03)
        ↓
Selection (A-04)
        ↓
Evaluation (A-01)
        ↓
Purchase (Baseline)
```

### Metric Snapshot

| Arm | Hit | Purchase | rank710 | rank46 | other | ROI |
|-----|-----|----------|---------|--------|-------|-----|
| Control OFF | 218 | 218 | 9 | 6 | 52 | 1.1418 |
| Baseline v2 | 255 | 255 | 0 | 6 | 24 | 2.7095 |
| **Baseline v3** | **279** | **279** | **0** | **6** | **0** | **3.0421** |

Δ v3 − Control: Hit **+61**  
Δ v3 − v2: Hit **+24**（Boundary+Reorder）

---

## 5. Candidate Registry v3

| 役割 | ID | Flag | In Stack | Status |
|------|-----|------|----------|--------|
| Evaluation Primary | **A-01** | `F_V3_RANK_D1_ENABLED` | Yes | frozen |
| Admission Primary | **A-03** | `F_V3_A03_POOL_ADMIT_ENABLED` | Yes | frozen |
| Selection Primary | **A-04** | `F_V3_A04_SEL_HISTORY_ENABLED` | Yes | frozen |
| Evaluation Secondary | A-02 | `F_V3_RANK_D2_ENABLED` | No | held |

正本: [`v3-accuracy-candidate-registry.md`](./v3-accuracy-candidate-registry.md)  
Artifact: `research/v3_lab/baselines/accuracy_phase2_close/accuracy_candidate_registry_v3.json`

---

## 6. Configuration Registry v3

| Configuration ID | `v3-lab-config-a01-a03-a04/1.0` |
|------------------|--------------------------------|
| Freeze / Close | `v3-accuracy-phase2-close/1.0` |
| Document | [`v3-lab-configuration-registry.md`](./v3-lab-configuration-registry.md) |
| Artifact | `.../accuracy_phase2_close/lab_configuration_registry_v3.json` |

ランタイム既定は引き続き全 Flag **OFF**（本番配線なし）。Registry は Lab 採用意図の正本。

---

## 7. Feature Flag Inventory（Phase 2 Close）

| Flag | 既定 | Lab Stack |
|------|------|-----------|
| `F_V3_RANK_D1_ENABLED` | OFF | **ON** |
| `F_V3_A03_POOL_ADMIT_ENABLED` | OFF | **ON** |
| `F_V3_A04_SEL_HISTORY_ENABLED` | OFF | **ON** |
| `F_V3_RANK_D2_ENABLED` | OFF | OFF（Secondary） |
| Representation / P3 Admission / P4 Selection / Purchase | OFF | OFF |

詳細: [`v3-feature-flag-inventory.md`](./v3-feature-flag-inventory.md)

---

## 8. Remaining Issues

| 層 | n | 研究対象 |
|----|---|----------|
| **Delete** | **6** | **対象外** |

Accuracy 研究スコープ内の残 miss は **0**。  
詳細: [`v3-remaining-issues.md`](./v3-remaining-issues.md)

---

## 9. 変更範囲（本 Close）

| 追加・更新 | Baseline v3 · Registries · Docs · Experiment Status · Remaining Issues |
|------------|------|
| **未変更** | A-01 / A-02 / A-03 / A-04 ロジック · Representation · Admission · Selection · Evaluation · Purchase · V2 Production · API / UI / Ops / Explain |

---

## 10. 停止

**Accuracy Phase 2 Close 完了。ここで停止する。**  
Phase 3 の研究には着手しない。
