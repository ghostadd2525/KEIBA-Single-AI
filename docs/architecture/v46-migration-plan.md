# Version46 — World Trigger Migration Plan

**Date:** 2026-07-28  
**Status:** Design ONLY（実装・コード・Production / Trigger / Signal 変更なし）  
**Goal:**

```text
V44 Trigger Specification
        │
        ▼  （安全な段階移行）
Production Trigger（現行 classify_world_line_type）
```

**Baseline (V45):** Mean Compliance **37%** / `core_world` **0%**（DEFAULT のみ）

---

## Principles

1. **Spec Authority** — 移行先の正本は V44。現行 Trigger は移行元の凍結ベースライン。  
2. **No Silent Cutover** — 決定経路を切り替える前に Shadow 観測と Stage PASS が必須。  
3. **Positive Match First** — core DEFAULT 除去は最終段。先に観測・Signal 充足・他 World 整合を固める。  
4. **Downstream Isolation** — 本計画の主対象は World Trigger 決定。Prediction / PE / CE / AI の接続変更は **別 Stage（後段）** とし、Trigger 移行と同時に行わない。  
5. **Rollback Always** — 各 Stage に Rollback Point を定義。PASS 失敗時は前 Stage 状態へ戻す。

本フェーズは計画文書のみ。実装承認は各 Stage の別ゲートで行う。

---

## Stage Overview

| Stage | Name | Production Decision 変更 | 主目的 |
|---|---|---|---|
| **S0** | Baseline Freeze | No | 現行挙動・V44/V45 を移行契約として固定 |
| **S1** | Shadow Dual-Eval | No | V44 Logic Form の並列評価（観測のみ） |
| **S2** | Must Signal Readiness | No | Must 概念の供給可否をゲート（生成変更は別承認） |
| **S3** | Threshold / Polarity ADR | No* | 極性判定の運用契約（数値は本 V46 では未決定） |
| **S4** | Per-World Shadow Compliance | No | World 単位で Shadow 適合を昇順に検証 |
| **S5** | Unsatisfied Semantics Shadow | No | 未充足→unsatisfied の観測（core 吸収を禁止する設計の検証） |
| **S6** | Flagged Soft Cutover | **Yes（限定）** | フラグ付きで V44 経路を限定環境に切替 |
| **S7** | DEFAULT Removal Cutover | **Yes** | core DEFAULT 廃止・Positive Match 本番化 |
| **S8** | Downstream Binding（別計画） | 条件付き | SubWorld / Role / Pool /（将来）PE — Trigger 安定後 |

\* S3 は設計 ADR。コード・閾値の Production 反映は S3 PASS 後の実装承認が別途必要。

詳細: `v46-stage-design.md`  
リスク: `v46-risk-analysis.md`  
統治: `v46-governance.md`

---

## Dependency Graph

```text
S0 Baseline Freeze
 └─► S1 Shadow Dual-Eval
      └─► S2 Must Signal Readiness
           └─► S3 Threshold/Polarity ADR
                └─► S4 Per-World Shadow Compliance
                     │    (推奨順: rank7 → bug → mixed → midupper → midhole → core)
                     └─► S5 Unsatisfied Semantics Shadow
                          └─► S6 Flagged Soft Cutover
                               └─► S7 DEFAULT Removal Cutover
                                    └─► S8 Downstream Binding（別ゲート）
```

**Hard dependencies**

| Stage | Depends on | Reason |
|---|---|---|
| S1 | S0 | 比較のベースライン固定 |
| S2 | S1 | Shadow で「Must 欠落」を定量化してから Readiness |
| S3 | S2 | 供給可能な Signal に対してのみ極性契約 |
| S4 | S3 | 適合判定に極性契約が必要 |
| S5 | S4（少なくとも core 以外の Shadow 安定） | 未充足の定義が他 World MATCH と干渉 |
| S6 | S5 PASS | 切替前に unsatisfied 挙動を観測 |
| S7 | S6 PASS + core Positive Match Shadow PASS | DEFAULT 除去は最大破壊点 |
| S8 | S7 PASS | 下流は Trigger 真理が安定してから |

**Parallelism（設計上許容）**

- S4 内の World 別 Shadow は **順次推奨**（干渉計測のため）。並列は研究環境のみ。
- S8 のサブ項目（SubWorld vs PE）は S7 後に分岐可能。PE 接続は V36 I3 参照・本計画の必須ではない。

---

## Migration Success Definition

移行完了（S7 PASS）の設計定義:

| 指標 | 目標（設計） |
|---|---|
| Specification Compliance（V45 同手法） | 全 World が Stage ゲート基準を満たす（数値目標は S3/S4 で確定） |
| core | Positive Match 経路のみ。DEFAULT 残余なし |
| 未充足 | unsatisfied / unclassified（silent core なし） |
| Rollback | S6/S7 いずれからも現行 Trigger へ即時復帰可能 |

S8 完了は「Trigger 移行完了」とは分離して扱う。

---

## Explicit Non-Goals（V46 本文書）

- コード実装
- Production / Trigger / Signal / Prediction / PE / CE / AI の変更
- Threshold 数値の決定
- 改善の実装手順書（本計画は Stage・依存・リスク・Rollback・PASS のみ）

---

## Document Index

| Doc | Content |
|---|---|
| `v46-migration-plan.md` | 本ファイル |
| `v46-stage-design.md` | Stage 詳細・PASS・Rollback |
| `v46-risk-analysis.md` | Breaking Risk / 影響モジュール |
| `v46-governance.md` | 統治・承認 |
