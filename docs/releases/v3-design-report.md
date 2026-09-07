# Version 3 — Design Report

**Date:** 2026-07-22（**Accuracy Phase 2 Close: 2026-07-24** · **V3 Close: 2026-07-24**）  
**Status:** **Version 3 CLOSED**（[`v3-close-report.md`](./v3-close-report.md) · [`v3-final-report.md`](./v3-final-report.md)）  
**Mode:** Version 2 = **保守** / Version 3 = Offline Lab（`research/v3_lab`）· **研究クローズ**  
**Control:** V2 Final（PE-V2-A ON）Hit **218**  
**不採用の継承:** RP-V2-A / CE-V2-A（再挑戦禁止）

**実装境界（Close）:** **PRR=HOLD** · **Go/No-Go=NO-GO** · A-05=Official Candidate · A-03=Deprecated · Integration Design Complete · 配線/Flag ON/Phase3/V4 **未着手**。  
詳細: [`v3-final-report.md`](./v3-final-report.md) · [`v3-close-report.md`](./v3-close-report.md) · [`v4-handover-from-v3.md`](./v4-handover-from-v3.md)

---

## 0. エグゼクティブサマリー

Version 2 は正式リリースまで完了し、Accuracy 最終構成は **PE-V2-A のみ**（Hit 218）で固定された。残 miss は Flag 継ぎ足しでは届かない天井にある。

Version 3 は V2 の延長ではなく、次を分離した **新世代アーキテクチャ**として設計した。

| 分離 | V3 名称 | V2 からの転換 |
|------|---------|---------------|
| 表現 | Representation / Feature Contract | 28 Feature 固定の前提を捨てる |
| 場 | Pool Construction + Admission | PE の局所 +1 から文脈可変へ |
| 選定 | Selection Policy（Reorder） | RePick Rescue を廃棄 |
| 評価 | Ranking / Survival Model | CE 温度を廃棄 |
| 購入 | Purchase Mapper | Delete 不変のまま外出し |

**本 Round（Design）の成果は設計文書。**  
**追記（2026-07-24）:** **V3-P1 Lab Harness** 実装。  
**追記（2026-07-24）:** **V3-P2 Representation**（Feature Generator / Contract 2.0 / Metrics / AB parity）。  
**追記（2026-07-24）:** **V3-P3 Admission**（AP-V3-A Banded Deep / Contract 2.0 / Metrics / AB parity）。  
**追記（2026-07-24）:** **V3-P4 Selection**（SEL-V3-RO Reorder-only / Contract 2.0 / Metrics / AB parity）。  
**追記（2026-07-24）:** **V3-P5 Freeze**（Pipeline/Contract/Flag/Registry/Baseline 固定）。  
**追記（2026-07-24）:** **A-01 Accuracy**（Evaluation D1 Recalibrator · Lab Hit 246 / churn 0 · PASS）。本番 ON は未実施。  
**追記（2026-07-24）:** **A-01 Validation**（285R 再現・Race Diff·隔離確認 · **Validation PASS**）。  
**追記（2026-07-24）:** **A-02 Accuracy**（Evaluation D2 Listwise Reranker · Lab Hit 242 / churn 0 · PASS）。A-01 非変更。本番 ON 未実施。  
**追記（2026-07-24）:** **Accuracy Candidate Review**（同一条件比較 · 採用順位 **A-01 > A-02**）。  
**追記（2026-07-24）:** **Accuracy Phase 1 CLOSE**（Primary=A-01 · Secondary=A-02 · 同時 ON 禁止 · 本番配線なし · Baseline 変更なし）。  
**追記（2026-07-24）:** **Accuracy Phase 2 Research Design**（Pool 残差を主問題 · A-03 Proposal · 実装なし）。  
**追記（2026-07-24）:** **A-03 Accuracy**（Admission Pool Coverage · Hit 255 / churn 0 · PASS）。Representation / Evaluation ロジック未変更。  
**追記（2026-07-24）:** **A-03 Validation**（solo 227 · stack 255 · Pool×9 再現 · **Validation PASS**）。  
**追記（2026-07-24）:** **Lab Configuration Freeze**（公式スタック A-01+A-03 · Baseline v2 Hit 255 · A-02 Secondary 保持）。  
**追記（2026-07-24）:** **Accuracy Gap Analysis v2**（残 miss 30 = Boundary14+Reorder10+Delete6 · A-04 = Selection · 実装なし）。  
**追記（2026-07-24）:** **A-04 Accuracy**（Selection History Crowding · Hit 279 / churn 0 · **PASS**）。  
**追記（2026-07-24）:** **Accuracy Phase 2 CLOSE**（Baseline v3 = A-01+A-03+A-04 · Hit 279 · Delete 対象外 · Phase 3 未着手）。  
**追記（2026-07-24）:** **Production Readiness Review**（Decision **HOLD** · 配線/Flag ON/Phase 3 不許可）。  
**追記（2026-07-24）:** **A-04 Validation**（Baseline v2→+A-04 · Hit 279 · Boundary14+Reorder10 · **PASS**）。  
**追記（2026-07-24）:** **Offline Gate**（実 285R · Control 59→Treatment 42 · churn 29 · **FAIL**）。Shadow / 配線 / Phase 3 未着手。  
**追記（2026-07-24）:** **Lab / Offline Divergence Analysis**（Lab 279 vs Offline 42 · 主因 A-03 過剰発火 · **解析完了・停止** · A-05/Shadow/Production/Phase3 未着手）。  
**追記（2026-07-24）:** **Admission Correction Design**（A-05 Favorite-Safe · A-03 非改変 · **設計のみ・実装なし** · PRR HOLD）。  
**追記（2026-07-24）:** **A-05 Accuracy**（Offline 59→66 · worsened_rank1=0 · **PASS** · Validation/Shadow/Production 未着手）。  
**追記（2026-07-24）:** **A-05 Validation**（2-round 再現 · SHA/隔離 · **PASS** · Shadow/Production/Phase3 未着手）。  
**追記（2026-07-24）:** **A-05 Shadow Evaluation Design**（設計のみ · 実装なし · PRR HOLD）。  
**追記（2026-07-24）:** **A-05 Shadow Implementation**（Runner/Logger/Comparator/Metrics · 評価窓未開始 · Flag 既定 OFF · PRR HOLD）。  
**追記（2026-07-24）:** **A-05 Shadow Evaluation S0**（real 285R · 59→66 · wr1=0 · **PASS** · Rollout/Flag ON/PRR Close 未着手）。  
**追記（2026-07-24）:** **A-05 Shadow Evaluation S1**（57日安定 · 直近14日 wr1=0 · S1 **PASS** · Readiness **HOLD**）。  
**追記（2026-07-24）:** **Production Readiness Final Review**（PRR Final **HOLD** · Go/No-Go **NO-GO** · Rollout/Flag ON/Phase3 未着手）。  
**追記（2026-07-24）:** **Production Integration Design**（A-05 統合設計のみ · 実装/配線なし · PRR HOLD）。  
**追記（2026-07-24）:** **Version 3 Close**（Final Report · Architecture Summary · V4 Handover · **CLOSED** · V4/Rollout/Phase3 未着手）。

---

## 1. 提出物一覧

| 提出物 | パス | 内容 |
|--------|------|------|
| **Version 3 Vision** | [`v3-vision.md`](./v3-vision.md) | 世代定義・成功条件・原則 |
| **Architecture Proposal** | [`v3-architecture-proposal.md`](./v3-architecture-proposal.md) | 論理パイプライン・コンポーネント |
| **Accuracy Strategy** | [`v3-accuracy-strategy.md`](./v3-accuracy-strategy.md) | 柱・Feature 候補・モデル責務 |
| **Experiment Roadmap** | [`v3-experiment-roadmap.md`](./v3-experiment-roadmap.md) | P0–P5・Flag 予約・Gates |
| **本 Design Report** | `v3-design-report.md` | 統合正本 |
| **P1 Lab Report** | [`v3-p1-lab-report.md`](./v3-p1-lab-report.md) | Lab 基盤実装報告 |
| **P2 Representation Report** | [`v3-p2-representation-report.md`](./v3-p2-representation-report.md) | Feature Generator / Contract 2.0 |
| **P3 Admission Report** | [`v3-p3-admission-report.md`](./v3-p3-admission-report.md) | AP-V3-A Banded Deep / Contract 2.0 |
| **P4 Selection Report** | [`v3-p4-selection-report.md`](./v3-p4-selection-report.md) | SEL-V3-RO Reorder-only / Contract 2.0 |
| **P5 Freeze Report** | [`v3-p5-freeze-report.md`](./v3-p5-freeze-report.md) | Lab 基盤固定 · Baseline |
| **A-01 Accuracy Report** | [`v3-a01-accuracy-report.md`](./v3-a01-accuracy-report.md) | D1 Recalibrator 285R AB |
| **A-01 Validation Report** | [`v3-a01-validation-report.md`](./v3-a01-validation-report.md) | 再現性・Race Diff・採用判定 |
| **A-01 Race Diff Report** | [`v3-a01-race-diff-report.md`](./v3-a01-race-diff-report.md) | 改善28 / 悪化0 |
| **A-02 Accuracy Report** | [`v3-a02-accuracy-report.md`](./v3-a02-accuracy-report.md) | D2 Reranker 285R AB |
| **Accuracy Candidate Review** | [`v3-accuracy-candidate-review.md`](./v3-accuracy-candidate-review.md) | A-01 vs A-02 採用順位 |
| **Accuracy Phase 1 Final Report** | [`v3-accuracy-phase1-final-report.md`](./v3-accuracy-phase1-final-report.md) | Phase 1 Close |
| **Accuracy Candidate Registry** | [`v3-accuracy-candidate-registry.md`](./v3-accuracy-candidate-registry.md) | Primary/Secondary |
| **Feature Flag Inventory** | [`v3-feature-flag-inventory.md`](./v3-feature-flag-inventory.md) | Phase 1 Close |
| **Experiment Status** | [`v3-experiment-status.md`](./v3-experiment-status.md) | Phase 1 Close |
| **Phase 2 Research Report** | [`v3-accuracy-phase2-research-report.md`](./v3-accuracy-phase2-research-report.md) | Phase 2 問題定義 |
| **Phase 2 Miss Taxonomy** | [`v3-phase2-miss-taxonomy.md`](./v3-phase2-miss-taxonomy.md) | 残 miss 体系 |
| **Phase 2 Improvement Taxonomy** | [`v3-phase2-improvement-taxonomy.md`](./v3-phase2-improvement-taxonomy.md) | 改善カテゴリ |
| **A-03 Design Proposal** | [`v3-a03-design-proposal.md`](./v3-a03-design-proposal.md) | A-03 問題定義 |
| **A-03 Accuracy Report** | [`v3-a03-accuracy-report.md`](./v3-a03-accuracy-report.md) | Pool Coverage Admission AB |
| **A-03 Validation Report** | [`v3-a03-validation-report.md`](./v3-a03-validation-report.md) | solo + A-01 stack 検証 |
| **A-03 Race Diff Report** | [`v3-a03-race-diff-report.md`](./v3-a03-race-diff-report.md) | Pool 改善9 / 悪化0 |
| **Lab Configuration Report** | [`v3-lab-configuration-report.md`](./v3-lab-configuration-report.md) | 公式スタック Freeze |
| **Lab Configuration Registry** | [`v3-lab-configuration-registry.md`](./v3-lab-configuration-registry.md) | 構成正本 |
| **Phase 2 Baseline Report** | [`v3-phase2-baseline-report.md`](./v3-phase2-baseline-report.md) | Baseline v2 Hit 255 |
| **Phase 2 Research Roadmap** | [`v3-accuracy-phase2-research-roadmap.md`](./v3-accuracy-phase2-research-roadmap.md) | R0–R9（Gap v2 含む） |
| **Gap Analysis v2** | [`v3-accuracy-gap-analysis-v2.md`](./v3-accuracy-gap-analysis-v2.md) | Baseline v2 残 miss 分類 |
| **Miss Taxonomy Gap v2** | [`v3-miss-taxonomy-gap-v2.md`](./v3-miss-taxonomy-gap-v2.md) | 残 miss 再凍結 |
| **A-04 Problem Definition** | [`v3-a04-problem-definition.md`](./v3-a04-problem-definition.md) | Selection 単一ステージ |
| **A-04 Accuracy Report** | [`v3-a04-accuracy-report.md`](./v3-a04-accuracy-report.md) | History Crowding · Hit 279 |
| **A-04 Validation Report** | [`v3-a04-validation-report.md`](./v3-a04-validation-report.md) | 再現性・Race Diff・採用判定 |
| **A-04 Validation Race Diff** | [`v3-a04-validation-race-diff-report.md`](./v3-a04-validation-race-diff-report.md) | Boundary14+Reorder10 / 悪化0 |
| **A-04 Race Diff Report** | [`v3-a04-race-diff-report.md`](./v3-a04-race-diff-report.md) | Lab AB 差分 |
| **Accuracy Phase 2 Final Report** | [`v3-accuracy-phase2-final-report.md`](./v3-accuracy-phase2-final-report.md) | Phase 2 Close · Baseline v3 |
| **Baseline v3 Report** | [`v3-phase2-baseline-v3-report.md`](./v3-phase2-baseline-v3-report.md) | Hit 279 固定 |
| **Remaining Issues** | [`v3-remaining-issues.md`](./v3-remaining-issues.md) | Delete 6 のみ |
| **Production Readiness Report** | [`v3-production-readiness-report.md`](./v3-production-readiness-report.md) | Decision HOLD |
| **Offline Gate Report** | [`v3-offline-gate-report.md`](./v3-offline-gate-report.md) | 実285R · **FAIL** |
| **Offline Gate Race Diff / Risk** | [`v3-offline-gate-race-diff-report.md`](./v3-offline-gate-race-diff-report.md) · [`v3-offline-gate-risk-summary.md`](./v3-offline-gate-risk-summary.md) | churn 29 |
| **Lab / Offline Divergence** | [`v3-lab-offline-divergence-report.md`](./v3-lab-offline-divergence-report.md) · [`v3-lab-offline-rca.md`](./v3-lab-offline-rca.md) · [`v3-lab-vs-offline-diff.md`](./v3-lab-vs-offline-diff.md) · [`v3-divergence-cause-ranking.md`](./v3-divergence-cause-ranking.md) | Lab279 vs Offline42 · 主因 A-03 |
| **Admission Correction Design** | [`v3-admission-correction-design.md`](./v3-admission-correction-design.md) · [`v3-admission-correction-spec.md`](./v3-admission-correction-spec.md) · [`v3-admission-correction-experiment-plan.md`](./v3-admission-correction-experiment-plan.md) · [`v3-admission-correction-flag-design.md`](./v3-admission-correction-flag-design.md) · [`v3-admission-correction-success-criteria.md`](./v3-admission-correction-success-criteria.md) | A-05 設計 · Design PASS |
| **A-05 Accuracy Report** | [`v3-a05-accuracy-report.md`](./v3-a05-accuracy-report.md) · [`v3-a05-race-diff-report.md`](./v3-a05-race-diff-report.md) | Offline PASS · Lab 218 |
| **A-05 Validation Report** | [`v3-a05-validation-report.md`](./v3-a05-validation-report.md) · [`v3-a05-validation-race-diff-report.md`](./v3-a05-validation-race-diff-report.md) | 再現性 · **PASS** |
| **A-05 Shadow Design** | [`v3-a05-shadow-design.md`](./v3-a05-shadow-design.md) · [`v3-a05-shadow-spec.md`](./v3-a05-shadow-spec.md) · [`v3-a05-shadow-rollout-plan.md`](./v3-a05-shadow-rollout-plan.md) · [`v3-a05-shadow-rollback-plan.md`](./v3-a05-shadow-rollback-plan.md) · [`v3-a05-shadow-acceptance-criteria.md`](./v3-a05-shadow-acceptance-criteria.md) | Design PASS |
| **A-05 Shadow Implementation** | [`v3-a05-shadow-implementation.md`](./v3-a05-shadow-implementation.md) · [`v3-a05-shadow-runbook.md`](./v3-a05-shadow-runbook.md) · [`v3-a05-shadow-log-spec.md`](./v3-a05-shadow-log-spec.md) · [`v3-a05-shadow-comparator-report.md`](./v3-a05-shadow-comparator-report.md) | 実装 PASS |
| **A-05 Shadow Evaluation** | [`v3-a05-shadow-evaluation-report.md`](./v3-a05-shadow-evaluation-report.md) · [`v3-a05-shadow-acceptance-result.md`](./v3-a05-shadow-acceptance-result.md) · [`v3-a05-shadow-risk-summary.md`](./v3-a05-shadow-risk-summary.md) | S0 **PASS** |
| **A-05 Shadow Evaluation S1** | [`v3-a05-shadow-s1-report.md`](./v3-a05-shadow-s1-report.md) · [`v3-a05-shadow-s1-acceptance-result.md`](./v3-a05-shadow-s1-acceptance-result.md) · [`v3-a05-shadow-s1-risk-summary.md`](./v3-a05-shadow-s1-risk-summary.md) · [`v3-a05-shadow-s1-production-readiness-recommendation.md`](./v3-a05-shadow-s1-production-readiness-recommendation.md) | S1 **PASS** · Readiness **HOLD** |
| **PRR Final** | [`v3-production-readiness-final-report.md`](./v3-production-readiness-final-report.md) · [`v3-residual-risk-report.md`](./v3-residual-risk-report.md) · [`v3-go-nogo-recommendation.md`](./v3-go-nogo-recommendation.md) · [`v3-prr-final-decision.md`](./v3-prr-final-decision.md) | **HOLD** · NO-GO |
| **Production Integration Design** | [`v3-production-integration-design.md`](./v3-production-integration-design.md) · [`v3-production-integration-spec.md`](./v3-production-integration-spec.md) · [`v3-production-integration-migration-plan.md`](./v3-production-integration-migration-plan.md) · [`v3-production-integration-rollout-checklist.md`](./v3-production-integration-rollout-checklist.md) · [`v3-production-integration-rollback-checklist.md`](./v3-production-integration-rollback-checklist.md) | 設計のみ |
| **Version 3 Close** | [`v3-final-report.md`](./v3-final-report.md) · [`v3-close-report.md`](./v3-close-report.md) · [`v3-architecture-summary.md`](./v3-architecture-summary.md) · [`v4-handover-from-v3.md`](./v4-handover-from-v3.md) | **CLOSED** |
| **Production Risk / Rollout / Rollback** | [`v3-production-risk-assessment.md`](./v3-production-risk-assessment.md) · [`v3-production-rollout-plan.md`](./v3-production-rollout-plan.md) · [`v3-production-rollback-plan.md`](./v3-production-rollback-plan.md) | 配線前計画 |
| **V2 Maintenance** | [`v2-maintenance-mode.md`](./v2-maintenance-mode.md) | V2 保守モード宣言 |

関連（履歴）:

| 文書 | 役割 |
|------|------|
| `v2-accuracy-final-report.md` | V2 Control の根拠 |
| `v2-known-limitations.md` | 持ち越し制限 |
| `v2-accuracy-v3-roadmap.md` | 初期メモ → **本 Design が上位** |

---

## 2. Vision（要約）

> 勝者を場に入れるだけでは足りない残 miss を、新しい表現と選定ポリシーで解く。  
> RePick は Rescue ではなく並べ替え。Evaluation は温度ではなく順位付けモデル。

**Goal:** Hit > 218 かつ churn_hit = 0（Corpus 285R）。

---

## 3. Architecture Proposal（要約）

```text
[A] Representation → [B] Pool Construction → [C] Selection Policy
                         ↘                 ↗
                           [D] Ranking Model
                                 ↓
                         [F] Purchase Mapper（既存・Delete 不変）
```

- V3 は Shadow / Flag Mesh / Offline Lab で V2 本番と隔離
- Prediction / PI / RaceCardSummary 契約は非破壊
- V2 コード変更禁止をアーキテクチャ制約として明記

---

## 4. Accuracy Strategy（要約）

### 4.1 三本柱

| 柱 | 内容 | 主レバー |
|----|------|----------|
| I | Representation First | Feature Contract · Ranking D1/D2 |
| II | Next-Gen Pool | Admission Policy（Banded / Coverage / Margin） |
| III | Selection as Reorder | SEL-V3-RO / SLOT（Rescue 禁止） |

### 4.2 Candidate Pool 次世代

容量付き集合 + Admission Policy。PE-V2-A は Control に内包。

### 4.3 Entry 判定

AP-V3-A Banded Deep を第一候補。匿名・上限・identity OFF を必須。

### 4.4 Candidate Evaluation 再設計

温度 Flag 廃止。Recalibrator / Reranker / Dual-head へ。

### 4.5 RePick 位置付け

RP-V2-A パラダイム廃棄。Selection Policy は補助・後段。

### 4.6 特徴量候補

F-V3-01..21（文脈・相対・市場代理）。ROI + リーク検査必須。F01 再開なし。

### 4.7 モデル責務

Encoder / Ranking / Admission / Selection / Purchase / Explain を表で分離（Strategy §6）。

---

## 5. Experiment Roadmap（要約）

| Phase | 目的 | 実装 |
|-------|------|------|
| **P0** | Design Freeze | 本 Round（完了） |
| **P1** | Miss Taxonomy + Lab Harness | 完了（2026-07-24） |
| **P2** | Representation（Feature / Contract） | 完了（2026-07-24） · Ranking D1/D2 は別承認 |
| **P3** | Pool Admission（AP-V3-A） | 完了（2026-07-24） · AP-V3-B/C は別承認 |
| **P4** | Selection Reorder（SEL-V3-RO） | 完了（2026-07-24） · SLOT/MARGIN は別承認 |
| **P5** | Stack Freeze + Lab Baseline | **完了（2026-07-24）** · Accuracy 実験は別承認 |

Hard Gate 共通: **Hit > 218 ∧ churn_hit = 0**。  
V2 Flag（REPICK/CE）は実験に使わない。

---

## 6. V2 保守との境界

| 領域 | Version 2（保守） | Version 3（設計） |
|------|-------------------|-------------------|
| Accuracy 本番 | PE-V2-A ON 固定 | 新 Flag 空間で将来検証 |
| RP / CE | OFF 固定 | 再利用禁止 |
| UI / Explain / Ops | 本番維持 | 本 Round 対象外 |
| コード | **変更しない** | **変更しない**（設計のみ） |

---

## 7. 設計完了判定

| チェック | 結果 |
|----------|------|
| Vision 文書 | **あり** |
| Architecture Proposal | **あり** |
| Accuracy Strategy（Pool/Entry/CE/RePick/Feature/モデル責務） | **あり** |
| Experiment Roadmap | **あり** |
| Design Report（本紙） | **あり** |
| コード変更 | **なし** |

**Version 3 設計 Round はここで完了し、停止する。**  
実装・AB・本番 Flag 追加は、別途の実装承認がない限り開始しない。

---

## 8. 次に必要なもの（本 Round 外・参考）

実装承認が出た場合の最初の作業は **V3-P1（Taxonomy Lock + Lab Harness）** のみ。  
それ以前に V3 コードを V2 ツリーへ混在させないこと。
